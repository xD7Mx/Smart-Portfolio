"""القارئُ البصريّ لملفّات الشركات (D557) — معرفةٌ تُبنى خمسَ سنواتٍ لكلّ شركة.

قال المالك: «يجب أن يكون رأيُ الذكاء هو ما ستقوله أنت لي كمستشارٍ ماليّ … قارئٌ بصريٌّ
لملفّات الشركات، لديه الأرقامُ تلقائياً، ويتميّز بقراءة الملفّات بصرياً بشكلٍ خفيف
ويختصرها في نقاطٍ رئيسية لتكون لديه معرفةٌ تُبنى خلال خمس سنوات — دون أن يؤثّر على
خادمي أو عمل التطبيق السلس».

فالقراءةُ هكذا:
  · **الملفُّ لا يُفتح على الخادم.** لا PyMuPDF ولا قراءةً ضوئية (علّقت الخادمَ مرّتين،
    D477): يُنزَّل الملفُّ الرسميُّ من «تداول» ويُرسَل كما هو إلى النموذج متعدّد
    الوسائط، فيراه صفحاتٍ — جداولَ وإيضاحاتٍ وتقريرَ مراجع — ويعيد نقاطاً مختصرة.
    ما على الخادم تنزيلٌ وحفظُ سطورٍ قليلة.
  · **خفيفٌ ومحروس.** دفعةٌ صغيرةٌ ليلاً (لا عند فتح الصفحة)، ملفٌّ ملفٌّ بالتتابع،
    وتتوقّف إن قلّت الذاكرةُ أو جاوز النموذجُ نصيبَ الخلفية من حصّته، أو كان الملفُّ
    أكبرَ من الحدّ. والمقروءُ لا يُعاد.
  · **المعرفةُ خمسُ سنوات.** لكلّ سنةٍ ملفُّها السنويّ، ولأحدثِ فترةٍ ملفُّها — فتتراكم
    نقاطٌ مختصرةٌ بتواريخها، ويُحذف ما جاوز خمسَ سنوات.
  · **لا اختلاق.** النموذجُ يُلزَم بما في الملفّ حرفاً؛ وما لم يُقرأ لا يُقال عنه شيء.
"""
from __future__ import annotations

import json
from datetime import date

from loguru import logger

STORE = "know:{}"
YEARS = 5
# ‏D565: قِيس في ليلةٍ كاملة أنّ حدَّ 150MB أوقف القراءةَ كلَّها تقريباً (254 شركةً زيرت، 11 قُرئت،
# و29 نداءً للنموذج): المتاحُ على الخادم 110–175MB. فلم يعد الملفُّ يُحمَل في الذاكرة إطلاقاً —
# يُنزَّل قطعاً إلى القرص ويُرفع قطعاً إلى «ملفّات» النموذج ويُشار إليه — فالذروةُ قطعةٌ واحدة
# (~256KB) لا أضعافُ الملفّ؛ ويكفي حدٌّ يترك للنظام هامشَه.
MAX_MB = 40                      # حدُّ حجم الملفّ على القرص (لا يمسّ الذاكرة)
MIN_FREE_MB = 60
# ‏D560: قال المالك «شهران كثير، أقصاه يومان أو أسبوع». السوقُ ~273 شركة × 6 ملفّات ≈ 1,640:
# بـ400 ليلاً تكتمل في أربع ليالٍ، والمحفظةُ في ساعتها الأولى. العددُ لا يرفع ذروةَ الذاكرة —
# الملفّاتُ بالتتابع وكلٌّ يُحرَّر قبل التالي — وإنما يطيل الوقت، والليلُ متّسع.
NIGHT_FILES = 400
BUDGET_SHARE = 0.6               # لا تُقرأ ملفّاتٌ إن استُهلك 60٪ من حصّة اليوم


def _sym(s) -> str:
    return str(s).replace(".SR", "").strip()


def load(symbol: str) -> dict:
    from app.services import lastgood
    return lastgood.load(STORE.format(_sym(symbol))) or {}


def pick(links: list[dict], today: date | None = None) -> list[dict]:
    """من روابط القوائم: أحدثُ ملفّ، ثمّ لكلّ سنةٍ من الخمس ملفُّها السنويّ.

    السنويُّ لسنة Y يُودَع عادةً بين يناير وأبريل من Y+1 — فيؤخذ أحدثُ ما أُودع فيها."""
    today = today or date.today()
    links = sorted([l for l in links if l.get("filed")], key=lambda l: l["filed"], reverse=True)
    if not links:
        return []
    out = [links[0]]
    for y in range(today.year - 1, today.year - YEARS - 1, -1):          # الأحدثُ أوّلاً
        # يناير–مارس أوّلاً: أبريل موسمُ الربع الأول، فلا يُؤخذ إلا إن لم يُودَع السنويُّ قبله
        yr = [l for l in links if l["filed"][:4] == str(y + 1)]
        win = [l for l in yr if l["filed"][5:7] in ("01", "02", "03")] or [l for l in yr if l["filed"][5:7] == "04"]
        if win and win[-1] not in out:
            out.append(win[-1])
    return out


PROMPT = """أنت محلّلٌ ماليٌّ سعوديٌّ خبير. أمامك ملفُّ القوائم المالية الرسميّ لشركة {name} ({sym}) كما أُودع في «تداول».
اقرأه بصرياً — الجداولَ والإيضاحاتِ وتقريرَ المراجع — واستخرج ما يهمّ مستثمراً يقرّر، **مختصراً**.

قواعد ملزمة:
- كلُّ رقمٍ تذكره يجب أن يكون مكتوباً في الملفّ نفسِه، بوحدته (ألف/مليون ريال). لا تقدير ولا حساب من عندك إلا نسبةَ تغيّرٍ بين رقمين في الملفّ.
- ما لا تجده في الملفّ لا تذكره.
- بالعربية الفصحى، وكلُّ نقطةٍ سطرٌ واحدٌ قصير.

أعد JSON فقط:
{{
  "period": "YYYY-MM-DD نهاية الفترة",
  "kind": "annual أو quarter",
  "points": ["4-6 نقاط: الإيراد والربح وتغيّرهما، والتدفّق النقدي التشغيلي، والدين والسيولة، والتوزيعات — بأرقام الملفّ"],
  "flags": ["0-3 نقاط تحذيرية إن وُجدت فقط: رأيٌ متحفّظ أو لفتُ انتباه من المراجع، استمراريةٌ، خسائرُ متراكمة، مخصّصاتٌ أو انخفاضُ قيمةٍ كبير، أطرافٌ ذوو علاقة لافتة، قضايا، تغيّرٌ محاسبيّ"],
  "auditor": "اسمُ المراجع ونوعُ رأيه (نظيف/متحفّظ/لفت انتباه) إن ظهر",
  "verdict": "جملةٌ واحدة: ما الذي يقوله هذا الملفُّ عن الشركة"
}}"""


async def _upload(path: str, sym: str) -> tuple[str | None, str | None]:
    """‏D565: يُرفع الملفُّ من القرص إلى «ملفّات» النموذج قطعاً — لا يُحمَل في الذاكرة كاملاً.
    يعيد (file_uri, name) أو (None, None)."""
    import asyncio
    import os
    import httpx
    from app.core.config import settings
    size = os.path.getsize(path)
    base = "https://generativelanguage.googleapis.com"

    def chunks():
        with open(path, "rb") as fh:
            while True:
                b = fh.read(256 * 1024)
                if not b:
                    break
                yield b

    try:
        async with httpx.AsyncClient(timeout=180) as c:
            r = await c.post(f"{base}/upload/v1beta/files?key={settings.AI_API_KEY}",
                             headers={"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                                      "X-Goog-Upload-Header-Content-Length": str(size),
                                      "X-Goog-Upload-Header-Content-Type": "application/pdf",
                                      "Content-Type": "application/json"},
                             json={"file": {"display_name": f"sp-{sym}"}})
            up = r.headers.get("x-goog-upload-url")
            if r.status_code != 200 or not up:
                logger.warning("القارئ البصري {}: بدءُ الرفع HTTP {}", sym, r.status_code)
                return None, None
            r = await c.post(up, content=chunks(), headers={"Content-Length": str(size), "X-Goog-Upload-Offset": "0",
                                                            "X-Goog-Upload-Command": "upload, finalize"})
            if r.status_code != 200:
                logger.warning("القارئ البصري {}: الرفع HTTP {}", sym, r.status_code)
                return None, None
            f = (r.json() or {}).get("file") or {}
            name, uri = f.get("name"), f.get("uri")
            for _ in range(10):                                   # ‏PDF يُعالَج عادةً فوراً؛ وإلا ينتظر قليلاً
                if f.get("state") in (None, "ACTIVE"):
                    break
                await asyncio.sleep(3)
                g = await c.get(f"{base}/v1beta/{name}?key={settings.AI_API_KEY}")
                f = g.json() if g.status_code == 200 else f
            return uri, name
    except Exception as e:                                        # noqa: BLE001
        logger.warning("القارئ البصري {}: الرفع {}", sym, type(e).__name__)
        return None, None


async def _forget(name: str | None) -> None:
    """يحذف الملفَّ المرفوع بعد قراءته (ينتهي وحده بعد يومين على أيّ حال)."""
    if not name:
        return
    import httpx
    from app.core.config import settings
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            await c.delete(f"https://generativelanguage.googleapis.com/v1beta/{name}?key={settings.AI_API_KEY}")
    except Exception:                                             # noqa: BLE001
        pass


async def _read_pdf(path: str, name: str, sym: str) -> dict | None:
    import asyncio
    import httpx
    from app.core.config import settings
    from app.services.usage_tracker import can_call, record
    if not settings.AI_API_KEY or not can_call("gemini"):
        return None
    from app.services.ai_content import _extract_json_obj
    uri, fname = await _upload(path, sym)
    if not uri:
        return None
    body = {"contents": [{"parts": [{"file_data": {"mime_type": "application/pdf", "file_uri": uri}},
                                    {"text": PROMPT.format(name=name, sym=sym)}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1500}}
    try:
        # ‏503 «مشغول» عارضٌ عند المزوّد (قِيس مرّتين): محاولةٌ ثانيةٌ بعد مهلة، ثمّ ثالثة (لا بديلَ: 2.5-flash غيرُ متاحٍ لهذا الحساب، و3.5 حصّتُه 20 يومياً)
        for i, model in enumerate((settings.AI_MODEL,) * 3):
            if not can_call("gemini"):
                return None
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.AI_API_KEY}"
            try:
                record("gemini")
                async with httpx.AsyncClient(timeout=180) as c:
                    r = await c.post(url, json=body)
                if r.status_code in (429, 500, 503) and i < 2:
                    logger.info("القارئ البصري {}: HTTP {} — يُعاد: {}", sym, r.status_code, r.text[:160].replace(settings.AI_API_KEY, "***"))
                    await asyncio.sleep(15 * (i + 1))
                    continue
                if r.status_code != 200:
                    logger.warning("القارئ البصري {}: HTTP {} بـ{}: {}", sym, r.status_code, model, r.text[:200].replace(settings.AI_API_KEY, "***"))
                    return None
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                obj = _extract_json_obj(text)
                return obj if isinstance(obj, dict) and obj.get("points") else None
            except Exception as e:                                # noqa: BLE001
                logger.warning("القارئ البصري {}: {}", sym, type(e).__name__)
                return None
        return None
    finally:
        await _forget(fname)


def _trim() -> None:
    """يُعيد الذاكرةَ إلى النظام بعد كلّ ملفّ — لا تبقى محجوزةً في كومة بايثون."""
    import gc
    gc.collect()
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:                                             # noqa: BLE001
        pass


def prune(files: dict, today: date | None = None) -> dict:
    """يُبقي خمسَ سنواتٍ فقط — بنهاية الفترة إن عُرفت وإلا بتاريخ الإيداع."""
    today = today or date.today()
    cut = f"{today.year - YEARS}-01-01"
    return {k: v for k, v in files.items() if (v.get("period") or v.get("filed") or "9") >= cut}


async def learn(symbol: str, name: str = "", budget: int = 3, report: dict | None = None) -> int:
    """يقرأ ما لم يُقرأ من ملفّات الشركة (حتى `budget`) ويحفظ نقاطه. يعيد عددَ المقروء."""
    from app.services import lastgood
    from app.services.tadawul_http import fetch_to_file
    from app.services.tadawul_pdf import mem_available_mb, pdf_links
    sym = _sym(symbol)
    rec = load(sym)
    files = dict(rec.get("files") or {})
    links, why = await pdf_links(sym)
    if why and report is not None:
        report[why] = report.get(why, 0) + 1
    done = 0
    for f in pick(links):
        if done >= budget:
            break
        fid = f["url"].rsplit("/", 1)[-1]
        if fid in files:
            continue
        free = mem_available_mb()
        if free is not None and free < MIN_FREE_MB:
            if report is not None:
                report["ذاكرةٌ غيرُ كافية"] = report.get("ذاكرةٌ غيرُ كافية", 0) + 1
                report["_mem"] = True                             # الدفعةُ تنتظر ولا تتوقّف
            break
        import os
        import tempfile
        fd, tmp = tempfile.mkstemp(prefix="sp-pdf-", suffix=".pdf")
        os.close(fd)
        try:
            try:
                st, size = await fetch_to_file(f["url"], tmp, referer=f["referer"], max_bytes=MAX_MB * 1024 * 1024 + 1)
            except Exception:                                     # noqa: BLE001
                continue
            with open(tmp, "rb") as fh:
                head = fh.read(5)
            if st != 200 or head != b"%PDF-":
                continue
            if size > MAX_MB * 1024 * 1024:
                files[fid] = {"filed": f["filed"], "skipped": "حجمٌ كبير"}
                continue
            obj = await _read_pdf(tmp, name or sym, sym)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        _trim()
        if not obj:
            if report is not None:
                report["تعذّرت القراءة"] = report.get("تعذّرت القراءة", 0) + 1
            break                                                 # حصّةٌ أو عطلٌ — لا يُلحّ
        files[fid] = {"filed": f["filed"], "period": str(obj.get("period") or "")[:10] or None,
                      "kind": obj.get("kind"), "points": [str(p) for p in obj.get("points") or []][:6],
                      "flags": [str(p) for p in obj.get("flags") or []][:3],
                      "auditor": obj.get("auditor"), "verdict": obj.get("verdict"),
                      "read_at": date.today().isoformat()}
        done += 1
    # ‏«مكتملة» إن قُرئ كلُّ مختار — فلا تُترك شركةٌ قُرئ بعضُها أسبوعاً كاملاً (عطبٌ قِيس بالقراءة)
    complete = all(f["url"].rsplit("/", 1)[-1] in files for f in pick(links))
    if done or files != (rec.get("files") or {}) or complete != rec.get("complete"):
        lastgood.save(STORE.format(sym), {"files": prune(files), "at": date.today().isoformat(), "complete": complete})
    return done


def knowledge(symbol: str, limit: int = 14) -> list[str]:
    """سطورُ المعرفة للرأي: أحدثُ فترةٍ بتفصيلها، ثمّ حكمُ كلِّ سنةٍ وتحذيراتُها."""
    files = [v for v in (load(symbol).get("files") or {}).values() if v.get("points")]
    files.sort(key=lambda v: v.get("period") or v.get("filed") or "", reverse=True)
    out: list[str] = []
    for i, v in enumerate(files):
        tag = f"[{'سنوي' if v.get('kind') == 'annual' else 'فترة'} {v.get('period') or v.get('filed')}]"
        if i == 0:
            out += [f"{tag} {p}" for p in v["points"]]
        elif v.get("verdict"):
            out.append(f"{tag} {v['verdict']}")
        out += [f"{tag} تحذير: {p}" for p in v.get("flags") or []]
        if v.get("auditor") and i == 0:
            out.append(f"{tag} المراجع: {v['auditor']}")
    return out[:limit]


def coverage(symbol: str) -> dict:
    files = [v for v in (load(symbol).get("files") or {}).values() if v.get("points")]
    ps = sorted(v.get("period") or v.get("filed") or "" for v in files)
    return {"files": len(files), "from": ps[0] if ps else None, "to": ps[-1] if ps else None}


async def _priority() -> list[tuple[str, str]]:
    """المحفظةُ أوّلاً، ثمّ قوائمُ المراقبة، ثمّ السوقُ بحجمه (D564)."""
    seen: dict[str, str] = {}
    try:
        # ‏الحيازةُ لا تحمل رمزاً — الرمزُ في الشركة (كان هذا يفشل صامتاً فتضيع أولويةُ المحفظة)
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.portfolio import Company, Holding
        async with AsyncSessionLocal() as db:
            q = select(Company.symbol).join(Holding, Holding.company_id == Company.id).distinct()
            for s, in (await db.execute(q.execution_options(skip_portfolio_scope=True))).all():
                if s:
                    seen.setdefault(_sym(s), "")
    except Exception as e:                                        # noqa: BLE001
        logger.warning("القارئ البصري: المحفظة {}", e)
    # ‏D564 بأمر المالك: قوائمُ المراقبة بعد المحفظة مباشرةً، ثمّ السوقُ بحجمه
    try:
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.market import Watchlist
        async with AsyncSessionLocal() as db:
            q = select(Watchlist.symbol).order_by(Watchlist.sort_order.asc(), Watchlist.id.asc())
            for s, in (await db.execute(q.execution_options(skip_portfolio_scope=True))).all():
                if s:
                    seen.setdefault(_sym(s), "")
    except Exception as e:                                        # noqa: BLE001
        logger.warning("القارئ البصري: المراقبة {}", e)
    try:
        from app.services.market_screener import get_cached_screener
        rows = sorted(get_cached_screener() or [], key=lambda r: -(r.get("market_cap") or 0))
        names = {str(r.get("symbol")): r.get("name") or "" for r in rows}
        for k in list(seen):
            seen[k] = names.get(k, "")
        for r in rows:
            seen.setdefault(str(r.get("symbol")), r.get("name") or "")
    except Exception:                                             # noqa: BLE001
        pass
    return [(s, n) for s, n in seen.items() if s.isdigit() and len(s) == 4]


async def nightly(max_files: int = NIGHT_FILES) -> dict:
    """دفعةُ الليلة: ملفّاتٌ قليلةٌ بالتتابع، بالأولوية، ضمن نصيبٍ من حصّة النموذج."""
    from datetime import timedelta
    from app.services.usage_tracker import background, remaining_fraction
    import asyncio
    rep: dict = {"read": 0, "companies": 0}
    week = (date.today() - timedelta(days=7)).isoformat()
    waits = 0
    with background():
        for sym, name in await _priority():
            if remaining_fraction("gemini") <= 1 - BUDGET_SHARE:
                rep["توقّف: نصيبُ الحصّة"] = 1
                break
            if rep["read"] >= max_files:
                break
            rec = load(sym)
            if rec.get("complete") and rec.get("at", "") >= week:  # مكتملةٌ وفُحصت هذا الأسبوع
                continue
            for _ in range(3):
                rep.pop("_mem", None)
                try:
                    n = await learn(sym, name, budget=min(YEARS + 1, max_files - rep["read"]), report=rep)
                except Exception as e:                            # noqa: BLE001
                    logger.warning("القارئ البصري {}: {}", sym, e)
                    n = 0
                rep["read"] += n
                # ذاكرةٌ قليلةٌ لحظياً (حصادُ XBRL مثلاً): ينتظر دقيقةً ويعيد — لا يُنهي الليلة
                if rep.get("_mem") and waits < 40:
                    waits += 1
                    await asyncio.sleep(60)
                    continue
                break
            rep["companies"] += 1
            await asyncio.sleep(2)                                # رفقٌ بـ«تداول» بين الشركات
    rep.pop("_mem", None)
    rep["waits"] = waits
    # ‏D564: تقريرُ الليلة محفوظٌ — يُعرف منه ما قُرئ ولماذا توقّف، بلا سجلّات الحاوية
    try:
        from datetime import datetime
        from app.services import lastgood
        lastgood.save("know:_last_run", {**rep, "at": datetime.now().isoformat(timespec="minutes")})
    except Exception:                                             # noqa: BLE001
        pass
    logger.info("القارئ البصري: {}", json.dumps(rep, ensure_ascii=False))
    return rep
