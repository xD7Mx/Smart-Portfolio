"""مزامنةُ دليل السوق مع «تداول» — كونٌ ينمو مع السوق (D242).

## لماذا

كونُ التطبيق كان **ساكناً**: يُبنى من ملفّاتٍ في الشيفرة. فسأل المالك:
شركةٌ أوقفتها «تداول» — أتختفي؟ وإن عادت أترجع؟ واكتتابٌ جديد أيظهر؟
والجوابُ الصادقُ كان: لا تختفي (وتشيخ بلا أن يُقال إنها شاخت)، وتعود
وحدَها إن أُعيد تداولُها، **والاكتتابُ الجديد لا يظهر أبداً** حتى يُضاف
بيدٍ وتُبنى حزمة. أي أن السوقَ ينمو والتطبيقُ لا ينمو معه.

## المبدأ

المصدرُ هو «تداول» نفسُها — لا ياهو ولا تخمين. وما يُكتب لا يُكتب في
الشيفرة بل في **طبقةٍ فوقها** (‏`market:directory_overlay`) في مخزن
الحالة: فتعبر الحزمَ ولا تُلوّث ملفّاً متتبَّعاً.

## ثلاثةُ قيودٍ تحمي الكون من مزامنةٍ عمياء

  ١· **لا حذفَ أبداً.** رمزٌ غاب عن قائمة «تداول» يُوسَم «موقوفاً»
     بتاريخه ولا يُمحى — فسعرُه الأخير لا يُقرأ سعراً حالياً، وإن عاد
     رُفع الوسمُ وحدَه. الحذفُ يُفقد تاريخَ المالك، والوسمُ لا يُفقده.
  ٢· **قائمةٌ قصيرةٌ تُرفَض.** جلبٌ يعود بأقلّ من `MIN_LISTED` رمزاً
     ليس سوقاً تقلّص بل جلبٌ فشل (حمايةُ Akamai · صفحةٌ تغيّرت). فيُرفَض
     كلُّه ولا يُوسَم أحدٌ موقوفاً على أساسه.
  ٣· **كلُّ تغييرٍ يُسجَّل** بالرمز والقبل والبعد، ويُعاد في التقرير.

وأسماءُ الشيفرة تبقى مرجعاً: الطبقةُ تُكمل ولا تُبدّل ما هو صحيحٌ فيها
إلا حين يختلف الاسمُ الرسميُّ فعلاً.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from loguru import logger

OVERLAY_KEY = "market:directory_overlay"
LOG_KEY = "market:directory_sync_log"
MIN_LISTED = 200          # دون ذلك: جلبٌ فشل لا سوقٌ تقلّص

# مرشَّحاتُ المصادر — تُجرَّب بالترتيب، وأوّلُ ما يُفهم يُعتمد. والمضيفُ
# محجوبٌ عن بيئة التطوير، فالبنيةُ تُثبَّت بمسبارٍ على الخادم قبل الاعتماد
# (‏scripts/audit/tadawul_sync_probe.py) — لا تُخمَّن.
SOURCES = (
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/trading/participants-directory/issuer-directory",
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/main-market-watch",
)

_SYM = re.compile(r"\b(\d{4})\b")


def _now() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def overlay() -> dict:
    """الطبقةُ المحفوظة — رمزٌ ← {name?, sector?, suspended?, since?}."""
    from app.services import lastgood
    d = lastgood.load(OVERLAY_KEY)
    if not isinstance(d, dict):
        return {}
    # الحفظةُ تضيف مفاتيحَ خدمية (‏`_stale_since`) قيمتُها نصّ — تُستبعَد
    # كما يفعل مخزنُ الأساسيات. وإلا انهار الفرزُ على `str.get` (وقع فعلاً
    # في أوّل تشغيلٍ للحارس).
    return {k: v for k, v in d.items()
            if isinstance(v, dict) and not str(k).startswith("_")}


def _save_overlay(d: dict) -> None:
    from app.services import lastgood
    lastgood.save(OVERLAY_KEY, d)


def parse_listed(body: str) -> dict[str, dict]:
    """يُفهم من مخرَج «تداول»: رمزٌ ← {name, sector?}.

    يُقبل شكلان: JSON فيه صفوفٌ لها حقولُ رمزٍ واسم، أو جدولُ HTML.
    وما لم يُفهم يعود فارغاً — ولا يُخترع رمزٌ من نصّ.
    """
    out: dict[str, dict] = {}
    body = body or ""
    # ── JSON ──
    try:
        data = json.loads(body)
        rows = data if isinstance(data, list) else next(
            (v for v in data.values() if isinstance(v, list)), [])
        for r in rows:
            if not isinstance(r, dict):
                continue
            sym = next((str(r[k]) for k in ("symbol", "Symbol", "code", "companyCode",
                                            "tradingName", "symbolCode") if r.get(k)), "")
            m = _SYM.search(sym) or _SYM.search(json.dumps(r, ensure_ascii=False))
            if not m:
                continue
            name = next((str(r[k]).strip() for k in
                         ("name_ar", "companyNameAr", "companyName", "nameAr", "name")
                         if r.get(k)), "")
            sector = next((str(r[k]).strip() for k in
                           ("sector", "sectorNameAr", "sectorName") if r.get(k)), "")
            if name:
                out[m.group(1)] = {"name": name, **({"sector": sector} if sector else {})}
        if out:
            return out
    except Exception:                                             # noqa: BLE001
        pass
    # ── HTML: صفٌّ فيه رمزٌ رباعيٌّ ونصٌّ عربيّ ──
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S | re.I):
        cells = [re.sub(r"<[^>]+>", " ", c) for c in
                 re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
        cells = [re.sub(r"\s+", " ", c).strip() for c in cells]
        if len(cells) < 2:
            continue
        sym = next((_SYM.search(c).group(1) for c in cells if _SYM.fullmatch(c.strip())), None)
        if not sym:
            continue
        name = next((c for c in cells
                     if re.search(r"[ء-ي]", c) and not _SYM.fullmatch(c.strip())), "")
        if name:
            out[sym] = {"name": name}
    return out


async def _argaam_listed() -> dict[str, dict]:
    """قائمةُ المدرَجين من «أرقام» — مصدرٌ ثانٍ مقيسُ الوصول (D244).

    قِيس على الخادم أن «تداول» تردّ ‎403 على صفحتَي الدليل ومراقبة السوق
    (حمايةُ Akamai تمرّر صفحةَ الإعلانات ولا تمرّر هاتين). و«أرقام»
    تُقرأ يومياً في هذا التطبيق بنجاحٍ مُسجَّل، وصفحةُ مفكرتها تحمل
    فهرسَ الشركات برمزها واسمها العربيّ — فتصلح قائمةً.

    وليست بديلاً عن «تداول» في المعنى: إن نقصت عن حدّ القبول رُفضت كما
    تُرفض غيرُها، فلا يُوسَم أحدٌ موقوفاً على قائمةٍ ناقصة.
    """
    # ══ ومَعبرٌ واحدٌ لكلّ مضيف ══ (D312)
    # كان هذا النداءُ بـ`httpx` عادياً — والطريقةُ الذكيةُ صارت عامّةً
    # لأيّ مضيفٍ (D292)، فلا تبقى جلسةٌ ثانيةٌ في ملفٍّ على حِدَة: حجبٌ
    # يقع يوماً في «أرقام» يُصلَح في موضعٍ واحدٍ لا في كلّ ملفّ.
    from app.services.argaam_calendar import CAL_URL, _company_index
    from app.services.tadawul_http import smart_fetch
    status, body = await smart_fetch(CAL_URL, warm="https://www.argaam.com/ar",
                                     timeout=25)
    if status != 200 or not body:
        return {}
    idx = _company_index(body)
    return {sym: {"name": name} for name, (sym, _cid) in idx.items() if sym}


async def new_listings_from_announcements() -> dict[str, dict]:
    """رموزٌ جديدةٌ من إعلانات «تداول» — إضافةٌ فقط، لا وسمَ إيقاف (D244).

    صفحةُ الإعلانات تمرّ من الحماية (تُقرأ في التطبيق أصلاً)، وفيها
    «إدراجُ وبدءُ تداولِ أسهم شركة …». وهي قائمةُ **أحداثٍ** لا قائمةُ
    سوق: تكشف الوافدَ ولا تُثبت غيابَ أحد. فتُستعمل للإضافة وحدَها —
    فلا يبني وسمُ الإيقاف على مصدرٍ لا يعرف من بقي.
    """
    try:
        from app.services.tadawul_announcements import \
            fetch_tadawul_announcements as fetch_announcements
    except Exception:                                             # noqa: BLE001
        return {}
    try:
        items = await fetch_announcements()
    except Exception:                                             # noqa: BLE001
        return {}
    out: dict[str, dict] = {}
    for it in items or []:
        title = str((it or {}).get("headline") or (it or {}).get("title") or "")
        if "إدراج" not in title or "تداول" not in title:
            continue
        sym = str((it or {}).get("symbol") or "")
        m = _SYM.search(sym) or _SYM.search(title)
        if m:
            out[m.group(1)] = {"name": title}
    return out


async def fetch_listed() -> tuple[dict[str, dict], str | None]:
    """قائمةُ المدرَجين — «تداول» أوّلاً ثم «أرقام» — أو (فارغ، سببُ التعذّر)."""
    # ══ المَعبرُ الواحد بدل العميل المحجوب ══ (D250)
    # كان الجلبُ هنا يُردّ ‎403 فبُني بديلٌ من «أرقام». والحجبُ كان ببصمة
    # TLS لا بالرؤوس — فبانتحال بصمة كروم تُقرأ صفحاتُ «تداول» نفسُها،
    # ويبقى «أرقام» مسارَ احتياطٍ لا مصدراً أوّل.
    from app.services.tadawul_http import fetch as _raw_fetch
    last = None
    for url in SOURCES:
        try:
            status, body = await _raw_fetch(url)
        except Exception as e:                                    # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            continue
        if status != 200:
            last = f"HTTP {status} من {url.rsplit('/', 1)[-1]}"
            continue
        got = parse_listed(body)
        if len(got) >= MIN_LISTED:
            return got, None
        last = (f"فُهم {len(got)} رمزاً فقط من {url.rsplit('/', 1)[-1]} "
                f"(الحدّ {MIN_LISTED})")
    # ثمّ «أرقام» — مصدرٌ مقيسُ الوصول حين تردّ «تداول» ‎403.
    try:
        got = await _argaam_listed()
    except Exception as e:                                        # noqa: BLE001
        got, last = {}, f"أرقام: {type(e).__name__}: {e}"
    if len(got) >= MIN_LISTED:
        return got, None
    if got:
        last = f"فُهم {len(got)} رمزاً من «أرقام» (الحدّ {MIN_LISTED}) · {last or ''}"
    return {}, last or "لم يُفهم أيُّ مصدر"


def plan(listed: dict[str, dict]) -> dict:
    """خطّةُ التغيير بلا كتابةٍ — تُقرأ قبل أن تُطبَّق.

    والكونُ المقيسُ هو ما يعرضه التطبيق فعلاً (الدليلُ + الطبقة)، لا
    ملفُّ الشيفرة وحدَه.
    """
    from app.data.saudi_directory import SAUDI_DIRECTORY
    ov = overlay()
    known = set(SAUDI_DIRECTORY) | set(ov)
    added, renamed, resumed = [], [], []
    for sym, row in sorted(listed.items()):
        cur = {**(SAUDI_DIRECTORY.get(sym) or {}), **(ov.get(sym) or {})}
        if not cur:
            added.append({"symbol": sym, **row})
            continue
        # ══ التسميةُ تُقرأ ولا تُطبَّق ══ (بعد أوّل تشغيلٍ ناجح · D245)
        # قائمةُ «تداول» تحمل **اسمَ المتابعة** المختصر: «الرياض» لا «بنك
        # الرياض»، و«الراجحي» لا «مصرف الراجحي» — ‎138 صفّاً من هذا الجنس.
        # وأسماؤنا منسَّقةٌ مقصودة، فتطبيقُ المختصر تخريبٌ لا تحديث. فتُسجَّل
        # في التقرير ليقرأها المالك، ولا تُكتب. ويُملأ الاسمُ حيث لا اسمَ
        # عندنا فقط — وذاك إكمالٌ لا استبدال.
        if row.get("name") and not cur.get("name"):
            renamed.append({"symbol": sym, "from": None, "to": row["name"],
                            "fill": True})
        elif row.get("name") and cur.get("name") and row["name"] != cur["name"]:
            renamed.append({"symbol": sym, "from": cur["name"],
                            "to": row["name"], "fill": False})
        if cur.get("suspended") or (ov.get(sym) or {}).get("absent_runs"):
            # الحاضرُ اليومَ يُرفع وسمُه ويُصفّر عدّادُ غيابه معاً.
            resumed.append({"symbol": sym, "name": cur.get("name") or row.get("name")})
    # ══ غيابٌ مرّةً لا يكفي ══ (بعد أوّل تشغيلٍ ناجح · D245)
    # أوّلُ تشغيلٍ حقيقيٍّ رشّح عشرةَ رموزٍ للإيقاف، وفيها ثلاثةٌ أضفتُها
    # إلى الدليل أمسِ لأنها **مدرَجةٌ فعلاً** — فغيابُها عن قائمةٍ واحدةٍ
    # قد يكون ثقباً في الجلب أو في الفهم لا حقيقةً في السوق. وخطأُ هذا
    # الوسم يُقرأ في الشاشة «موقوفة» عن شركةٍ تُتداول.
    # فيُسجَّل الغيابُ أوّلاً (`absent_runs`)، ولا يُوسَم إلا بعد غيابين
    # متتاليين — أي أسبوعين. والحضورُ يُصفّر العدّاد.
    absent_now, gone = [], []
    for s in sorted(known - set(listed)):
        e = ov.get(s) or {}
        if e.get("suspended"):
            continue
        runs = int(e.get("absent_runs") or 0) + 1
        nm = ({**(SAUDI_DIRECTORY.get(s) or {}), **e}).get("name") or s
        (gone if runs >= 2 else absent_now).append(
            {"symbol": s, "name": nm, "absent_runs": runs})
    return {"listed": len(listed), "added": added, "renamed": renamed,
            "resumed": resumed, "suspended": gone, "absent_once": absent_now}


def apply_plan(p: dict) -> dict:
    """يكتب الخطّةَ في الطبقة — إضافةً ووسمَ إيقافٍ ورفعَه. ولا حذف."""
    ov = overlay()
    for row in p.get("added") or []:
        sym = row["symbol"]
        ov[sym] = {k: v for k, v in row.items() if k != "symbol" and v}
        ov[sym]["added"] = _now()
    for row in p.get("renamed") or []:
        if row.get("fill"):                 # إكمالُ اسمٍ غائبٍ فقط
            ov.setdefault(row["symbol"], {})["name"] = row["to"]
    for row in p.get("suspended") or []:
        ov.setdefault(row["symbol"], {}).update(
            {"suspended": True, "since": _now(), "absent_runs": 0})
    # غيابُ المرّة الأولى يُسجَّل عدّاً لا وسماً.
    for row in p.get("absent_once") or []:
        ov.setdefault(row["symbol"], {})["absent_runs"] = row["absent_runs"]
    for row in p.get("resumed") or []:
        e = ov.get(row["symbol"]) or {}
        e.pop("suspended", None)
        e.pop("since", None)
        e.pop("absent_runs", None)
        if e:
            ov[row["symbol"]] = e
        else:
            ov.pop(row["symbol"], None)
    _save_overlay(ov)
    # ══ يُعَدّ ما كُتب لا ما في الخطّة ══ (بعد تشغيلٍ خامس · D246)
    # قال التقريرُ «‏renamed: 138» وهو **لا يكتب** إلا التسميةَ الغائبة —
    # فعدَّ الخطّةَ وسمّاها تطبيقاً. وتقريرٌ يقول ما لم يفعل أخطرُ من
    # سكوت: المالكُ رآه وظنّ أسماءَه بُدِّلت.
    return {"added": len(p.get("added") or []),
            "renamed": sum(1 for r in (p.get("renamed") or []) if r.get("fill")),
            "renamed_reported_only": sum(1 for r in (p.get("renamed") or [])
                                         if not r.get("fill")),
            "suspended": len(p.get("suspended") or []),
            "resumed": len(p.get("resumed") or []),
            "absent_once": len(p.get("absent_once") or [])}


def log_run(entry: dict) -> None:
    from app.services import lastgood
    hist = lastgood.load(LOG_KEY)
    hist = hist if isinstance(hist, list) else []
    hist.append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entry})
    lastgood.save(LOG_KEY, hist[-50:])


async def sync(*, dry_run: bool = False) -> dict:
    """المزامنةُ كاملةً: جلبٌ ← خطّةٌ ← كتابةٌ ← سجلّ.

    ‏`dry_run` يعيد الخطّةَ ولا يكتب — وهو ما يُشغَّل أوّلَ مرّة.
    """
    listed, why = await fetch_listed()
    if not listed:
        # ══ الإضافةُ لا تنتظر القائمةَ الكاملة ══ (D244)
        # قائمةُ السوق قد تُحجب (‏403)، وإعلاناتُ «تداول» تمرّ. فمن
        # الإعلانات يُعرف الوافدُ الجديد — وهو أهمُّ ما سأل عنه المالك.
        # ولا يُوسَم أحدٌ موقوفاً هنا: مصدرُ الأحداث لا يعرف من بقي.
        fresh = await new_listings_from_announcements()
        p0 = plan({**{s: {"name": (r.get("name") or s)} for s, r in fresh.items()}})
        p0["suspended"] = []      # لا يُبنى وسمُ إيقافٍ على قائمةِ أحداث
        out = {"ok": False, "why": why, "partial": "إعلانات",
               "plan": p0, "applied": None}
        if not dry_run and p0["added"]:
            out["applied"] = apply_plan(p0)
            logger.info(f"🗂️ من الإعلانات: أُضيف {len(p0['added'])} رمزاً جديداً.")
        logger.warning(f"مزامنةُ الدليل: القائمةُ الكاملة تعذّرت ({why}) — "
                       f"اكتُفي بالإعلانات: جديد {len(p0['added'])}.")
        log_run({k: v for k, v in out.items() if k != "plan"} | {
            "counts": {"added": len(p0["added"])}})
        return out
    p = plan(listed)
    out = {"ok": True, "plan": p, "dry_run": dry_run}
    if not dry_run:
        out["applied"] = apply_plan(p)
        logger.info(
            "🗂️ مزامنةُ الدليل: مدرَجون {} · جديد {} · موقوف {} · عائد {} · تسمية {}"
            .format(p["listed"], len(p["added"]), len(p["suspended"]),
                    len(p["resumed"]), len(p["renamed"])))
    log_run({k: v for k, v in out.items() if k != "plan"} | {
        "counts": {k: len(p.get(k) or []) for k in
                   ("added", "renamed", "suspended", "resumed")},
        "listed": p["listed"]})
    return out
