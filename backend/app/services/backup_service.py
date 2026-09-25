"""
Real backup engine — the data-safety floor of the whole app.

Three jobs, one module:
  1. build_dump(db)        — full JSON snapshot of every portfolio table,
                             with a content checksum embedded so a file can
                             be verified before it is ever restored.
  2. write_backup_file(db) — persists that snapshot to /app/data/backups/
                             (a compose volume, so it lives OUTSIDE the
                             database container and survives restarts,
                             rebuilds, and a total DB-volume loss), and
                             prunes to the newest KEEP_FILES copies.
                             Called nightly by the scheduler at 02:00 and
                             reusable from the manual endpoints.
  3. restore_dump(db, dump)— replaces all rows from a dump, with real type
                             coercion (isoformat strings back to datetime/
                             date, floats back to Decimal) — the previous
                             restore passed raw JSON strings into timestamp
                             columns, which asyncpg rejects, so restores of
                             any table with a date column failed outright —
                             and resets every Postgres identity sequence
                             afterwards so the next insert can never collide
                             with a restored primary key.
"""

import hashlib
import json
import os
from datetime import datetime, date, timezone
from decimal import Decimal
from pathlib import Path

from loguru import logger
from sqlalchemy import select, delete, text, Date, DateTime, Numeric, Enum as SAEnum

import base64

from app.models.portfolio import Portfolio, Company, Holding, Note, PortfolioSnapshot
from app.models.transaction import Transaction, Installment, Dividend, BonusShare, Cash, CashLedger
from app.models.market import (Goal, Allocation, AIResult, LibraryBook, Watchlist,
                               WatchlistGroup, Report, Settings, LiquidityPlan)

# Order matters for restore: parents before the children that reference them
# on insert; reversed for the delete pass.
# NOTE: goals (→portfolio) and allocation (→companies) MUST be here — they hold
# real user data (investment targets / target weights) and, more critically,
# they FK-reference the backed-up tables. Leaving them out made restore's
# `DELETE FROM companies/portfolio` violate a foreign-key constraint on real
# Postgres data and abort the whole restore (it silently "worked" only on
# FK-less sqlite tests). ai_results (regenerable AI cache) also FK-references
# companies, so it's cleared before the delete pass in restore_dump.
TABLES = [
    ("portfolio", Portfolio),
    ("companies", Company),
    ("holdings", Holding),
    ("transactions", Transaction),
    ("installments", Installment),
    ("dividends", Dividend),
    ("bonus_shares", BonusShare),
    ("cash", Cash),
    ("cash_ledger", CashLedger),
    ("notes", Note),
    ("goals", Goal),
    ("allocation", Allocation),
    ("portfolio_snapshots", PortfolioSnapshot),
    # كتب المكتبة: بيانات وصفية (بلا FK لبقية الجداول). ملفات الكتب نفسها
    # (PDF/الغلاف/النصّ) تُضمَّن في نسخة التنزيل عبر قسم library_files.
    ("library_books", LibraryBook),
    ("watchlist_groups", WatchlistGroup),
    ("watchlist", Watchlist),
    # التقارير المُصدَرة وإعدادات الخادم: بيانات مستخدم حقيقية كانت خارج
    # النسخة فتُفقد عند الاستعادة. (الاستعادة تتخطّى أي جدول غائب عن الملف،
    # فالنسخ القديمة تبقى آمنة — انظر restore_dump.)
    ("reports", Report),
    ("settings", Settings),
    # خطّة السيولة: قرارات المالك نفسها — نسبة كل شركة من الدفعة، وأيّ
    # الدفعات نُفِّذت (t1..t5)، وأوامر الشراء. كانت خارج النسخة، فمن يستعيد
    # بعد فقد الخادم يستعيد محفظته كاملةً ثم يجد خطّته فارغة بلا إنذار.
    # تأتي بعد companies لأنها تشير إليها (والحذف يمرّ معكوساً).
    ("liquidity_plan", LiquidityPlan),
]

# حدّ إجمالي حجم ملفات الكتب المضمَّنة في نسخة التنزيل (حماية الذاكرة/الحجم).
LIBRARY_FILES_CAP = int(os.environ.get("BACKUP_LIBRARY_CAP_MB", "1200")) * 1024 * 1024

KEEP_FILES = 14  # two weeks of nightly copies

BACKUP_DIR = Path(
    os.environ.get("BACKUP_DIR")
    or ("/app/data/backups" if os.path.isdir("/app/data") else
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups"))
)

# مخزن ملفات الكتب للنسخ الليلية — مُعنوَن بالمحتوى (blob باسم sha256): يُخزَّن
# كل ملف مرّة واحدة مهما تكرّر عبر النسخ الليلية، فلا تتضخّم مساحة القرص. تشير
# كل نسخة ليلية إليه بالـsha256 فقط (بلا نسخ البيانات)، ويُجمَع الزبالة تلقائياً.
LIBRARY_BLOB_DIR = BACKUP_DIR / "library-blobs"


# ── Dump ─────────────────────────────────────────────────────────

def _serialize(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "value"):  # enum
        return value.value
    return value


def _tables_checksum(tables: dict) -> str:
    canonical = json.dumps(tables, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_LAYOUT_PATH = "/app/data/layout.json" if os.path.isdir("/app/data") else os.path.join(os.getcwd(), "layout.json")


def _read_layout_file():
    try:
        with open(_LAYOUT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_layout_file(data) -> None:
    try:
        os.makedirs(os.path.dirname(_LAYOUT_PATH), exist_ok=True)
        with open(_LAYOUT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"restore layout write failed: {e}")


_DATA_DIR = os.path.dirname(_LAYOUT_PATH)

# إعداداتٌ يملكها المالك ويحرّرها بيده، تعيش ملفّاتٍ خارج قاعدة البيانات:
#   project.json        — تاريخ بداية المشروع، وهو مقام **العائد المركّب**.
#   goals_builtin.json  — أهداف الأشرطة الثلاثة في لوحة التحكّم.
# كانت خارج النسخة الاحتياطية، فاستعادةٌ بعد عطل تُعيد الأرقام وتفقد هذين:
# يعود العائد المركّب إلى تاريخٍ افتراضي وتعود الأهداف إلى قيمها الأصلية —
# فقدٌ صامت لإعدادٍ يظنّه المالك محفوظاً مع بياناته.
_SETTING_FILES = ("project.json", "goals_builtin.json")


def _read_setting_files() -> dict:
    out: dict = {}
    for name in _SETTING_FILES:
        try:
            with open(os.path.join(_DATA_DIR, name), encoding="utf-8") as f:
                out[name] = json.load(f)
        except Exception:
            continue
    return out


def _write_setting_files(data: dict) -> None:
    for name, payload in (data or {}).items():
        if name not in _SETTING_FILES:
            continue                      # لا نكتب إلا ما نعرفه بالاسم
        try:
            os.makedirs(_DATA_DIR, exist_ok=True)
            with open(os.path.join(_DATA_DIR, name), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"restore setting file {name} failed: {e}")
_PROFILE_PATH = os.path.join(_DATA_DIR, "profile.json")
_AVATAR_PATH = os.path.join(_DATA_DIR, "avatar.img")


def _read_profile() -> dict | None:
    """اسم العرض + الصورة الرمزية (base64) — لتعود مع النسخة الاحتياطية."""
    out: dict = {}
    try:
        with open(_PROFILE_PATH, encoding="utf-8") as f:
            out["name"] = (json.load(f) or {}).get("name", "")
    except Exception:
        pass
    try:
        if os.path.exists(_AVATAR_PATH):
            out["avatar"] = base64.b64encode(open(_AVATAR_PATH, "rb").read()).decode("ascii")
    except Exception:
        pass
    return out or None


def _write_profile(data: dict) -> None:
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        if "name" in data:
            with open(_PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump({"name": data.get("name", "")}, f, ensure_ascii=False)
        if data.get("avatar"):
            with open(_AVATAR_PATH, "wb") as f:
                f.write(base64.b64decode(data["avatar"]))
    except Exception as e:
        logger.warning(f"restore profile write failed: {e}")


def _collect_library_files() -> tuple[dict, bool]:
    """يجمع ملفات المكتبة (PDF/غلاف/نصّ) مُرمَّزة base64 مع sha256 لكل ملف —
    لتُضمَّن في نسخة التنزيل فتعود الكتب عند الاستعادة على سيرفر جديد.
    يعيد (الملفات, تجاوز_الحدّ). عند تجاوز الحدّ لا تُضمَّن (تبقى الوصفية فقط)."""
    from app.services.library_service import LIBRARY_DIR
    files: dict = {}
    if not LIBRARY_DIR.exists():
        return files, False
    members = [f for f in sorted(LIBRARY_DIR.glob("*"))
               if f.is_file() and not f.name.endswith(".tmp")]
    total = sum(f.stat().st_size for f in members)
    if total > LIBRARY_FILES_CAP:
        logger.warning(f"ملفات المكتبة ({total} بايت) تتجاوز حدّ التضمين — تُحفَظ الوصفية فقط.")
        return files, True
    for f in members:
        raw = f.read_bytes()
        files[f.name] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "data": base64.b64encode(raw).decode("ascii"),
        }
    return files, False


def _library_files_ref(blob_dir: Path) -> dict:
    """يخزّن ملفات المكتبة في مخزن blob مُعنوَن بالمحتوى (مرّة واحدة لكل sha256)
    ويعيد مراجع {اسم الملف: {sha256, size}} بلا نسخ البيانات — للنسخ الليلية.
    ملفات القرص تبقى المصدر؛ الـblob نسخة مشتركة لا تتكرّر عبر النسخ."""
    from app.services.library_service import LIBRARY_DIR
    refs: dict = {}
    if not LIBRARY_DIR.exists():
        return refs
    blob_dir.mkdir(parents=True, exist_ok=True)
    for f in sorted(LIBRARY_DIR.glob("*")):
        if not f.is_file() or f.name.endswith(".tmp"):
            continue
        raw = f.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        blob = blob_dir / sha
        if not blob.exists():  # إزالة تكرار: يُكتب مرّة واحدة فقط
            tmp = blob_dir / (sha + ".tmp")
            tmp.write_bytes(raw)
            tmp.rename(blob)
        refs[f.name] = {"sha256": sha, "size": len(raw)}
    return refs


async def build_dump(db, include_files: bool = False, blob_dir: Path | None = None) -> dict:
    # النسخ الاحتياطي/الاستعادة/الفورمات تعمل عبر كل المحافظ — نُلغي عزل
    # الجلسة كي تشمل كل البيانات وتحفظ portfolio_id كما هو (لا يُختم).
    from app.core.portfolio_scope import reset_scope
    reset_scope()
    """نسخة كاملة من جداول المحفظة. ملفات الكتب:
    - include_files=True → تُضمَّن base64 في النسخة (نسخة تنزيل مكتفية ذاتياً).
    - blob_dir مُمرَّر → مراجع sha256 لمخزن blob مشترك (النسخ الليلية، بلا تضخّم)."""
    dump: dict = {"version": 2, "generated_at": datetime.now(timezone.utc).isoformat(), "tables": {}}
    for name, model in TABLES:
        rows = (await db.execute(select(model))).scalars().all()
        dump["tables"][name] = [
            {c.name: _serialize(getattr(r, c.name)) for c in model.__table__.columns}
            for r in rows
        ]
    # Embedded integrity checksum over the data itself — restore verifies it
    # when present (version>=2), so a truncated/edited file is caught before
    # a single row is deleted.
    dump["checksum"] = _tables_checksum(dump["tables"])
    # تخطيط لوحة التحكم/القائمة (ترتيب الشاشات وأماكنها) محفوظ كملفّ JSON خارج
    # قاعدة البيانات — نُضمّنه في النسخة كي تعود أماكن الشاشات عند الاستعادة.
    lay = _read_layout_file()
    if lay is not None:
        dump["layout"] = lay
    prof = _read_profile()
    if prof is not None:
        dump["profile"] = prof
    settings_files = _read_setting_files()
    if settings_files:
        dump["settings_files"] = settings_files
    if include_files:
        libfiles, skipped = _collect_library_files()
        if libfiles:
            dump["library_files"] = libfiles
        if skipped:
            dump["library_files_skipped"] = True
    elif blob_dir is not None:
        refs = _library_files_ref(blob_dir)
        if refs:
            dump["library_files"] = refs
    return dump


# ── Nightly file backup + retention ──────────────────────────────

def _gc_library_blobs() -> None:
    """يحذف blobs الكتب التي لم تعد أي نسخة ليلية محفوظة تشير إليها — كي لا
    يكبر المخزن بعد حذف الكتب أو دوران النسخ. آمن: لا يحذف إلا غير المشار إليه."""
    if not LIBRARY_BLOB_DIR.exists():
        return
    referenced: set[str] = set()
    for j in BACKUP_DIR.glob("smart-portfolio-backup-*.json"):
        try:
            d = json.loads(j.read_text(encoding="utf-8"))
            for meta in (d.get("library_files") or {}).values():
                sha = meta.get("sha256")
                if sha:
                    referenced.add(sha)
        except Exception:
            # نسخة لا يمكن قراءتها → نتجاهلها بأمان (لا نحذف بناءً على الشكّ).
            continue
    for blob in LIBRARY_BLOB_DIR.glob("*"):
        if blob.is_file() and not blob.name.endswith(".tmp") and blob.name not in referenced:
            try:
                blob.unlink()
            except OSError:
                pass


async def write_backup_file(db) -> dict:
    """Write a full snapshot to BACKUP_DIR and prune old copies.
    Returns {name, size, checksum, kept}."""
    # النسخ الليلية تُضمّن ملفات الكتب عبر مخزن blob مشترك (مراجع sha256، بلا
    # تكرار للبيانات عبر النسخ) — فتُستعاد الكتب من أي نسخة ليلية دون تضخّم القرص.
    dump = await build_dump(db, blob_dir=LIBRARY_BLOB_DIR)
    payload = json.dumps(dump, ensure_ascii=False, indent=2).encode("utf-8")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = f"smart-portfolio-backup-{stamp}.json"

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    # Two backups within the same second (e.g. manual button pressed twice)
    # must never overwrite each other.
    n = 1
    while (BACKUP_DIR / name).exists():
        n += 1
        name = f"smart-portfolio-backup-{stamp}-{n}.json"
    tmp = BACKUP_DIR / (name + ".tmp")
    tmp.write_bytes(payload)
    tmp.rename(BACKUP_DIR / name)  # atomic: never leaves a half-written backup

    # Retention: keep the newest KEEP_FILES real backups.
    files = sorted(BACKUP_DIR.glob("smart-portfolio-backup-*.json"))
    for old in files[:-KEEP_FILES]:
        try:
            old.unlink()
        except OSError:
            pass
    kept = min(len(files), KEEP_FILES)

    # بعد التقليم: نُزيل blobs الكتب التي لم تعد أي نسخة باقية تشير إليها.
    _gc_library_blobs()

    # Record it in the backups list shown in the UI.
    from app.models.market import Backup
    db.add(Backup(
        backup_name=name, backup_type="FULL",
        file_size=len(payload), checksum=dump["checksum"],
    ))
    await db.commit()

    logger.info(f"💾 Backup written: {name} ({len(payload)} bytes), {kept} copies retained.")
    return {"name": name, "size": len(payload), "checksum": dump["checksum"], "kept": kept}


# ── Restore ──────────────────────────────────────────────────────

def _coerce(model, row: dict) -> dict:
    """JSON scalars back into what asyncpg actually accepts per column."""
    out = {}
    for c in model.__table__.columns:
        if c.name not in row:
            continue
        v = row[c.name]
        if v is not None and isinstance(v, str):
            if isinstance(c.type, DateTime):
                v = datetime.fromisoformat(v)
            elif isinstance(c.type, Date):
                v = date.fromisoformat(v)
            elif isinstance(c.type, SAEnum) and c.type.enum_class is not None:
                # أعمدة enum: على Postgres (نوع ENUM أصلي) لا يُقبل النصّ الخام،
                # بخلاف sqlite المتساهل — نحوّل القيمة المخزَّنة إلى عضو الـenum
                # الفعلي (مطابقةً بالقيمة ثم بالاسم)، فتعمل الاستعادة على الاثنين.
                ec = c.type.enum_class
                try:
                    v = ec(v)
                except ValueError:
                    try:
                        v = ec[v]
                    except KeyError:
                        pass  # قيمة غير معروفة — نمرّرها كما هي ليظهر خطأ واضح
        if v is not None and isinstance(c.type, Numeric) and isinstance(v, (int, float)):
            v = Decimal(str(v))
        out[c.name] = v
    return out


async def restore_dump(db, dump: dict) -> None:
    # النسخ الاحتياطي/الاستعادة/الفورمات تعمل عبر كل المحافظ — نُلغي عزل
    # الجلسة كي تشمل كل البيانات وتحفظ portfolio_id كما هو (لا يُختم).
    from app.core.portfolio_scope import reset_scope
    reset_scope()
    # سببُ التغيير في سجلّ تدقيق العمليات (D481)
    await db.execute(text("SELECT set_config('sp.audit_reason', :r, true)"), {"r": "استعادة نسخة احتياطية"})
    """Replace all rows from a dump inside one transaction, then reset the
    identity sequences. Raises ValueError with an Arabic message on any
    validation failure (nothing is deleted in that case)."""
    tables = dump.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("ملف النسخة الاحتياطية غير صالح")

    # Integrity check (files from version>=2 embed it; older files skip).
    expected = dump.get("checksum")
    if expected and _tables_checksum(tables) != expected:
        raise ValueError("فشل التحقق من سلامة الملف (checksum) — الملف معدَّل أو ناقص، لم يُلمس أي صف")

    # ملفات المكتبة (إن وُجدت): نتحقّق من سلامة كلٍّ عبر sha256 ونفكّ الترميز
    # كاملاً قبل لمس أي شيء — فإن أخفق أيٌّ منها تُلغى الاستعادة دون حذف صفّ.
    lib_files = dump.get("library_files")
    decoded_files: dict[str, bytes] = {}
    if isinstance(lib_files, dict):
        for fname, meta in lib_files.items():
            sha = meta.get("sha256")
            if meta.get("data") is not None:
                # نسخة تنزيل: البيانات مضمَّنة base64.
                try:
                    raw = base64.b64decode(meta["data"])
                except Exception:
                    raise ValueError(f"ملف مكتبة تالف داخل النسخة ({fname}) — لم يُلمس أي صف")
            elif sha:
                # نسخة ليلية: مرجع إلى مخزن blob المشترك على السيرفر.
                blob = LIBRARY_BLOB_DIR / sha
                if not blob.exists():
                    # الـblob غير متوفّر (نسخة ليلية نُقلت لسيرفر آخر) — نتخطّى
                    # هذا الملف بأمان (الوصفية تُستعاد، والملف يبقى إن وُجد).
                    logger.warning(f"blob مفقود لملف الكتاب {fname} ({sha}) — يُتخطّى.")
                    continue
                raw = blob.read_bytes()
            else:
                continue
            if sha and hashlib.sha256(raw).hexdigest() != sha:
                raise ValueError(f"فشل التحقق من سلامة ملف الكتاب ({fname}) — لم يُلمس أي صف")
            decoded_files[fname] = raw

    # نتائج الذكاء (ai_results) تشير إلى companies لكنها قابلة للتوليد — نمسحها
    # أولاً كي لا تعيق حذف الشركات بقيد المفتاح الأجنبي (تُعاد تلقائياً لاحقاً).
    await db.execute(delete(AIResult))
    # **أمان حاسم**: لا نمسح إلا الجداول الموجودة فعلاً في ملف النسخة. بدون
    # هذا الشرط، استعادة نسخة قديمة (أُنشئت قبل إضافة جدول جديد لـTABLES)
    # كانت ستحذف بيانات ذلك الجدول ولا تستعيدها — فقدانٌ صامت.
    present = [(n, m) for n, m in TABLES if isinstance(tables.get(n), list)]
    for name, model in reversed(present):
        await db.execute(delete(model))
    for name, model in present:
        for row in tables.get(name) or []:
            db.add(model(**_coerce(model, row)))
    await db.commit()

    # تخطيط الشاشات (إن وُجد في النسخة): يُكتب إلى ملفّه فتعود أماكن الشاشات.
    if dump.get("layout") is not None:
        _write_layout_file(dump["layout"])
    # الملف الشخصي (الاسم + الصورة): يُستعاد مع النسخة أيضًا.
    if isinstance(dump.get("profile"), dict):
        _write_profile(dump["profile"])
    # تاريخ بداية المشروع وأهداف لوحة التحكّم — إعدادات المالك خارج القاعدة.
    if isinstance(dump.get("settings_files"), dict):
        _write_setting_files(dump["settings_files"])

    # الآن نكتب ملفات الكتب على القرص (بعد التحقق أعلاه). نكتب ذرّياً، ثم نُزيل
    # ملفات يتيمة لكتبٍ لم تعد ضمن النسخة كي تُطابق الاستعادة النسخة تماماً.
    # يتمّ هذا فقط حين تحمل النسخة ملفات (نسخة التنزيل) — لا نلمس القرص في
    # النسخ الليلية الخفيفة (الملفات باقية على الفوليوم أصلاً).
    if isinstance(lib_files, dict):
        from app.services.library_service import LIBRARY_DIR
        LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        for fname, raw in decoded_files.items():
            tmp = LIBRARY_DIR / (fname + ".tmp")
            tmp.write_bytes(raw)
            tmp.rename(LIBRARY_DIR / fname)
        kept_ids = {str(r.get("id")) for r in (tables.get("library_books") or [])}
        for f in LIBRARY_DIR.glob("*"):
            if not f.is_file() or f.name.endswith(".tmp"):
                continue
            book_id = f.name.split(".", 1)[0]
            if f.name not in decoded_files and book_id not in kept_ids:
                try:
                    f.unlink()
                except OSError:
                    pass

    # Reset each table's id sequence past the restored max id — without
    # this, the first insert after a restore reuses an existing PK and
    # fails with a unique-constraint error.
    for name, model in present:
        tbl = model.__table__.name
        pk = model.__table__.primary_key.columns.keys()[0]
        try:
            await db.execute(text(
                f"SELECT setval(pg_get_serial_sequence('{tbl}', '{pk}'), "
                f"COALESCE((SELECT MAX({pk}) FROM {tbl}), 0) + 1, false)"
            ))
        except Exception as e:  # non-serial PK or sqlite in tests — not fatal
            logger.warning(f"Sequence reset skipped for {tbl}: {e}")
    await db.commit()


# ── إعادة ضبط المصنع (فورمات) ────────────────────────────────────

async def factory_reset(db) -> dict:
    # النسخ الاحتياطي/الاستعادة/الفورمات تعمل عبر كل المحافظ — نُلغي عزل
    # الجلسة كي تشمل كل البيانات وتحفظ portfolio_id كما هو (لا يُختم).
    from app.core.portfolio_scope import reset_scope
    reset_scope()
    # سببُ التغيير في سجلّ تدقيق العمليات (D481)
    await db.execute(text("SELECT set_config('sp.audit_reason', :r, true)"), {"r": "فورمات"})
    """امسح كل بيانات المستخدم وأعد التطبيق لوضعه الأساسي — بعد كتابة نسخة
    أمان تلقائية أولاً، فالمسح نفسه قابل للاستعادة دائماً. ملفات النسخ
    الاحتياطية على القرص لا تُمسّ إطلاقاً (هي طريق العودة).
    يُفرَّغ: جداول المحفظة كلها (TABLES) + الإشعارات والأهداف والتوزيع
    النسبي والتقارير ونتائج الذكاء وأخبار/مفكرة السوق المخزنة (تُعاد تعبئتها
    تلقائياً من الجالب المجدول). تبقى: إعدادات التشغيل وسجل النسخ."""
    from app.models.market import (
        Notification, Goal, Allocation, Report, AIResult, MarketNews, MarketEvent,
    )
    from app.services import cache

    safety = await write_backup_file(db)

    # خط دفاع ثانٍ: نسخة خفية في مجلد منقّط داخل السيرفر (backend/.vault على
    # المضيف عبر ربط ./backend:/app) — خارج مجلد النسخ المعتاد، لا تمسّها حزم
    # التحديث ولا تنظيف backups/، وتُكتشف يدوياً على سيرفر أمازون عند الحاجة.
    # نحتفظ بآخر 10 نسخ خفية.
    try:
        vault = Path("/app/.vault") if os.path.isdir("/app") else \
            Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / ".vault"
        vault.mkdir(exist_ok=True)
        src = BACKUP_DIR / safety["name"]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        (vault / f"vault-{stamp}.json").write_bytes(src.read_bytes())
        for old in sorted(vault.glob("vault-*.json"))[:-10]:
            old.unlink()
        logger.warning(f"Factory reset: hidden vault copy written to {vault}")
    except Exception as e:
        logger.error(f"Vault copy failed (non-fatal): {e}")

    extra = [Notification, Goal, Allocation, Report, AIResult, MarketNews, MarketEvent]
    for model in extra:
        await db.execute(delete(model))
    for _, model in reversed(TABLES):
        await db.execute(delete(model))
    await db.commit()
    cache.clear()
    logger.warning(f"Factory reset done — safety backup: {safety['name']}")
    return {"safety_backup": safety["name"]}
