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

import base64
import json
from datetime import date

from loguru import logger

STORE = "know:{}"
YEARS = 5
MAX_MB = 14                      # حدُّ الإرسال المضمَّن للنموذج ~20MB بعد الترميز
NIGHT_FILES = 24                 # ملفّاتُ الليلة الواحدة — بالتتابع، لا أكثر
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
        win = [l for l in links if l["filed"][:4] == str(y + 1) and l["filed"][5:7] in ("01", "02", "03", "04")]
        if win and win[0] not in out:
            out.append(win[0])
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


async def _read_pdf(data: bytes, name: str, sym: str) -> dict | None:
    import httpx
    from app.core.config import settings
    from app.services.usage_tracker import can_call, record
    if not settings.AI_API_KEY or not can_call("gemini"):
        return None
    from app.services.ai_content import _extract_json_obj
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}")
    body = {"contents": [{"parts": [
                {"inline_data": {"mime_type": "application/pdf", "data": base64.b64encode(data).decode()}},
                {"text": PROMPT.format(name=name, sym=sym)}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1500}}
    del data
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(url, json=body)
        if r.status_code != 200:
            logger.warning("القارئ البصري {}: HTTP {}", sym, r.status_code)
            return None
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        obj = _extract_json_obj(text)
        return obj if isinstance(obj, dict) and obj.get("points") else None
    except Exception as e:                                        # noqa: BLE001
        logger.warning("القارئ البصري {}: {}", sym, type(e).__name__)
        return None


def prune(files: dict, today: date | None = None) -> dict:
    """يُبقي خمسَ سنواتٍ فقط — بنهاية الفترة إن عُرفت وإلا بتاريخ الإيداع."""
    today = today or date.today()
    cut = f"{today.year - YEARS}-01-01"
    return {k: v for k, v in files.items() if (v.get("period") or v.get("filed") or "9") >= cut}


async def learn(symbol: str, name: str = "", budget: int = 3, report: dict | None = None) -> int:
    """يقرأ ما لم يُقرأ من ملفّات الشركة (حتى `budget`) ويحفظ نقاطه. يعيد عددَ المقروء."""
    from app.services import lastgood
    from app.services.tadawul_http import fetch_bytes
    from app.services.tadawul_pdf import MIN_FREE_MB, mem_available_mb, pdf_links
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
            break
        try:
            st, data = await fetch_bytes(f["url"], referer=f["referer"])
        except Exception:                                         # noqa: BLE001
            continue
        if st != 200 or not data.startswith(b"%PDF"):
            continue
        if len(data) > MAX_MB * 1024 * 1024:
            files[fid] = {"filed": f["filed"], "skipped": "حجمٌ كبير"}
            continue
        obj = await _read_pdf(data, name or sym, sym)
        del data
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
    if done or files != (rec.get("files") or {}):
        lastgood.save(STORE.format(sym), {"files": prune(files), "at": date.today().isoformat()})
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
    """المحفظةُ أوّلاً، ثمّ غرفةُ التداول، ثمّ السوقُ بحجمه."""
    seen: dict[str, str] = {}
    try:
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.portfolio import Holding
        async with AsyncSessionLocal() as db:
            for s, in (await db.execute(select(Holding.symbol).where(Holding.quantity > 0))).all():
                seen.setdefault(_sym(s), "")
    except Exception as e:                                        # noqa: BLE001
        logger.debug("القارئ البصري: المحفظة {}", e)
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
    rep: dict = {"read": 0}
    week = (date.today() - timedelta(days=7)).isoformat()
    with background():
        for sym, name in await _priority():
            if remaining_fraction("gemini") <= 1 - BUDGET_SHARE:
                rep["توقّف: نصيبُ الحصّة"] = 1
                break
            if rep["read"] >= max_files:
                break
            if load(sym).get("at", "") >= week:                    # فُحصت هذا الأسبوع
                continue
            try:
                n = await learn(sym, name, budget=min(3, max_files - rep["read"]), report=rep)
            except Exception as e:                                # noqa: BLE001
                logger.warning("القارئ البصري {}: {}", sym, e)
                continue
            rep["read"] += n
    logger.info("القارئ البصري: {}", json.dumps(rep, ensure_ascii=False))
    return rep
