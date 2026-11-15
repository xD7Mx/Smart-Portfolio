"""قسمُ الأبحاث — «مختبرُ الأبحاث» الجديد (‏D745 · بأمر المالك 2026-11-15).

قال المالك: «دراسةٌ شاملةٌ لجميع التقارير اليومية والدورية والاقتصادية… القارئُ البصريّ يقرأ كلَّ تقريرٍ جديدٍ بنفسه، والذكاءُ يرتّب
المعلومات ويدمجها ويربطها ويحفظ سياقَها التاريخيّ، ويفكّر كمدير محفظةٍ أو رئيسِ قسم أبحاث… تقريرٌ خاصٌّ بمحفظتنا بتصميمنا، من
المصادر الموثوقة نفسِها لا من رأسه — الأخبارُ المحلية والعالمية موجودةٌ في التقارير… يومياً ويُرسَل على تلغرام… والقسمُ الثاني
توصياتٌ إن وُجدت، انتقائيةٌ بعقلٍ متقدّم».

فالقسمُ ثلاثُ مراحل:
  ١ **القراءة** (‏ingest): تقاريرُ الجزيرة كابيتال والراجحي المالية وجدوى (‏research_reports) — اليوميةُ أوّلاً ثمّ الاقتصاديةُ
    والقطاعيةُ والدورية ثمّ تقاريرُ الشركات — يُنزَّل ملفُّها الرسميّ ويُرسَل إلى النموذج متعدّد الوسائط فيراه صفحاتٍ (القارئُ
    البصريّ نفسُه · file_reader) ويعيد مذكّرةً منظّمة: العنوانُ والنقاطُ والسوقُ والأخبارُ المحلية والعالمية والاقتصادُ والقطاعاتُ
    والشركاتُ ومخاطرُها — من نصّ التقرير حرفاً. والمقروءُ لا يُعاد، والمذكّراتُ تبقى سنةً فيتكوّن السياقُ التاريخيّ.
  ٢ **التقرير** (‏compose): لكلّ محفظةٍ تقريرُها اليوميّ: مذكّراتُ الأيام الثلاثة الأخيرة كاملةً وخلاصةُ ثلاثين يوماً سياقاً،
    ومراكزُ المحفظة بملفّ التطبيق (السعرُ العادل وصعودُه وقرارُ التطبيق وموقفُ المستشار ووزنُ المركز) — فيكتب النموذجُ بلسان
    رئيس قسم أبحاث: السوق، والأخبارُ المحلية والعالمية، والقطاعات، ومراكزُنا، وما يُتابَع. وكلُّ سطرٍ يحمل رقمَ مصدره، وما لا
    مصدرَ له يُحذف عند التحقّق.
  ٣ **التوصيات**: صفرٌ إلى ثلاث، ولا تُقبل إلا لرمزٍ في المحفظة أو مذكورٍ في المصادر، وبسببٍ من المصادر ومن أرقام التطبيق معاً؛
    وإن لم يكن ما يستحقّ قيل ذلك وسببُه.
ثمّ يُحفظ التقريرُ ويُرسَل في التطبيق وتلغرام. والقراءةُ في عمليةٍ منفصلة (ذاكرةُ الخادم 1GB — كالقارئ البصريّ).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date, datetime, timedelta

from loguru import logger

KEEP_NOTES_DAYS = 365
KEEP_REPORTS = 120
MAX_PDF = 25 * 1024 * 1024
_KIND_RANK = {"تقرير يوميّ": 0, "تقرير اقتصاديّ": 1, "تقرير قطاعيّ": 2, "تقرير دوريّ": 2, "تقرير شهريّ": 2, "تقرير شركة": 3}

READ_PROMPT = """أنت محلّلٌ في قسم أبحاث مدير محفظة. أمامك تقريرٌ منشور: «{title}» من {source} بتاريخ {date} (صنفُه: {kind}).
اقرأه كاملاً بصرياً — النصوصَ والجداولَ والرسوم — وأعد JSON فقط بهذه المفاتيح. كلُّ ما تكتبه من نصّ التقرير وأرقامه حرفاً بلا استنتاجٍ
من خارجه، وما لم يرد فيه فاتركه فارغاً أو null. والأرقامُ لاتينية، والنصُّ عربيٌّ فصيحٌ موجز.
{{"headline": "خلاصةُ التقرير في جملة",
  "points": ["أهمُّ ما فيه — ثماني نقاطٍ على الأكثر"],
  "market": {{"tasi": "إغلاقُ تاسي وتغيّرُه إن ذُكرا", "turnover": "قيمةُ التداول إن ذُكرت", "summary": "حالُ السوق في جملة"}},
  "local_news": ["أخبارٌ محلية سعودية وردت فيه"],
  "global_news": ["أخبارٌ وأسواقٌ عالمية وردت فيه"],
  "macro": ["مؤشّراتٌ اقتصادية: النفط · الفائدة · التضخّم · الناتج — كما وردت"],
  "sectors": [{{"name": "القطاع", "view": "إيجابي|سلبي|محايد", "note": "ما قيل عنه"}}],
  "companies": [{{"symbol": "رمزٌ من أربعة أرقام إن ذُكر وإلا null", "name": "الشركة", "view": "إيجابي|سلبي|محايد", "target": null, "note": "ما قيل عنها"}}],
  "risks": ["مخاطرُ ذكرها التقرير"]}}"""

COMPOSE_PROMPT = """أنت رئيسُ قسم الأبحاث في مدير محفظةٍ سعوديٍّ مخضرم — بمنهج كبار رؤساء الأبحاث في السوق السعودية: انتقائيٌّ، دقيق، يربط الحدثَ
بالمحفظة، ولا يقول ما لا يملك عليه دليلاً. اكتب التقريرَ اليوميّ الخاصَّ بمحفظة «{pname}» ليوم {today}.

المصادرُ المقروءةُ مرقّمة (لا مصدرَ غيرها): كلُّ ما تكتبه عن السوق والأخبار والقطاعات والشركات يجب أن يكون منها، ويحمل أرقامَ مصادره
في "src". وأرقامُ التطبيق للمراكز (السعر العادل · القرار · الموقف) مصدرٌ مستقلّ رقمُه 0.
{sources}

السياقُ التاريخيّ (خلاصةُ ثلاثين يوماً من التقارير — للربط والمقارنة لا للنقل):
{context}

مراكزُ المحفظة (المصدر 0 — أرقامُ التطبيق):
{portfolio}

السوقُ الآن: {market}

أعد JSON فقط:
{{"headline": "عنوانُ اليوم في جملةٍ واحدة",
  "market": {{"summary": "حالُ السوق في جملتين", "points": [{{"text": "...", "src": [1]}}]}},
  "local": [{{"text": "خبرٌ محليّ وأثرُه", "src": [1]}}],
  "global": [{{"text": "خبرٌ عالميّ وأثرُه على السوق السعودية", "src": [2]}}],
  "sectors": [{{"name": "القطاع", "view": "إيجابي|سلبي|محايد", "text": "...", "src": [1]}}],
  "portfolio": [{{"symbol": "1120", "stance": "إيجابي|محايد|سلبي|انتباه", "text": "ما يعني المركزَ اليومَ من المصادر وأرقام التطبيق", "src": [0, 1]}}],
  "watch": [{{"text": "ما يُتابَع في الأيام القادمة", "src": [1]}}],
  "recommendations": [{{"symbol": "1120", "action": "شراء|إضافة|تخفيف|بيع|انتظار", "why": "السببُ من المصادر ومن أرقام التطبيق معاً", "condition": "شرطُ التنفيذ إن وُجد", "src": [0, 1]}}],
  "no_rec_reason": "إن لم تكن توصية: لماذا"}}
قواعد: التوصياتُ من صفرٍ إلى ثلاث، ولا توصيةَ إلا بدليلين: مصدرٌ بحثيّ وأرقامُ التطبيق؛ ولرمزٍ في المحفظة أو مذكورٍ في المصادر فقط.
والمراكزُ التي لا جديدَ عنها لا تُذكر. ولا تكتب نصيحةً عامّة. والأرقامُ لاتينية، والعربيةُ فصيحةٌ موجزة."""


def _dir() -> str:
    d = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "research_desk")
    os.makedirs(os.path.join(d, "reports"), exist_ok=True)
    return d


def _load(name: str, default):
    try:
        return json.load(open(os.path.join(_dir(), name), encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        return default


def _save(name: str, obj) -> None:
    p = os.path.join(_dir(), name)
    tmp = p + ".tmp"
    json.dump(obj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, p)


def knowledge() -> dict:
    k = _load("knowledge.json", {})
    k.setdefault("read", {})
    k.setdefault("notes", [])
    return k


def item_key(it: dict) -> str:
    return str(it.get("url") or f"{it.get('source')}|{it.get('title')}|{it.get('date')}")


def queue(items: list[dict], read: dict, today: date, days: int) -> list[dict]:
    """ما يُقرأ: غيرُ المقروء بملفٍّ ضمن المدى — اليوميُّ الأحدثُ أوّلاً، ثمّ الاقتصاديُّ والقطاعيّ والدوريّ، ثمّ الشركات."""
    floor = (today - timedelta(days=days)).isoformat()
    out = [it for it in items if it.get("url") and str(it.get("date") or "") >= floor and item_key(it) not in read]
    num = lambda it: int(re.sub(r"\D", "", str(it.get("date") or "")) or 0)   # noqa: E731
    return sorted(out, key=lambda it: (_KIND_RANK.get(str(it.get("kind")), 2), -num(it)))


def prune(k: dict, today: date) -> dict:
    floor = (today - timedelta(days=KEEP_NOTES_DAYS)).isoformat()
    k["notes"] = [n for n in k.get("notes", []) if str(n.get("date") or "") >= floor]
    keep = {n.get("key") for n in k["notes"]}
    k["read"] = {key: v for key, v in k.get("read", {}).items() if key in keep or str(v.get("date") or "") >= floor}
    return k


def _clean_note(obj: dict) -> dict:
    lst = lambda v, n: [str(x).strip() for x in (v or []) if str(x).strip()][:n]   # noqa: E731
    secs = [{"name": str(s.get("name") or "").strip(), "view": str(s.get("view") or "").strip(), "note": str(s.get("note") or "").strip()}
            for s in (obj.get("sectors") or []) if isinstance(s, dict) and s.get("name")][:12]
    cos = []
    for c in (obj.get("companies") or [])[:20]:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        sym = str(c.get("symbol") or "").strip()
        tgt = c.get("target")
        cos.append({"symbol": sym if re.fullmatch(r"\d{4}", sym) else None, "name": str(c["name"]).strip(), "view": str(c.get("view") or "").strip(),
                    "target": float(tgt) if isinstance(tgt, (int, float)) and tgt > 0 else None, "note": str(c.get("note") or "").strip()})
    m = obj.get("market") if isinstance(obj.get("market"), dict) else {}
    return {"headline": str(obj.get("headline") or "").strip(), "points": lst(obj.get("points"), 8),
            "market": {k: str(m.get(k) or "").strip() for k in ("tasi", "turnover", "summary")},
            "local_news": lst(obj.get("local_news"), 8), "global_news": lst(obj.get("global_news"), 8), "macro": lst(obj.get("macro"), 6),
            "sectors": secs, "companies": cos, "risks": lst(obj.get("risks"), 6)}


async def _download(it: dict) -> str | None:
    from app.services.research_reports import AJC_PAGE, ARC_PAGE, JADWA
    from app.services.tadawul_http import fetch_to_file
    src = str(it.get("source") or "")
    ref = AJC_PAGE if "الجزيرة" in src else ARC_PAGE if "الراجحي" in src else JADWA + "/ar"
    fd, path = tempfile.mkstemp(prefix="rd-", suffix=".pdf")
    os.close(fd)
    try:
        st, size = await fetch_to_file(str(it["url"]), path, referer=ref, timeout=120, max_bytes=MAX_PDF)
        with open(path, "rb") as fh:
            head = fh.read(5)
        if st == 200 and size > 1000 and head.startswith(b"%PDF"):
            return path
        logger.info("قسم الأبحاث: الملفّ {} HTTP {} · {} بايت", it.get("title"), st, size)
    except Exception as e:                                        # noqa: BLE001
        logger.warning("قسم الأبحاث: التنزيل {}", type(e).__name__)
    try:
        os.remove(path)
    except OSError:
        pass
    return None


async def _gemini(parts: list, max_tokens: int, temperature: float = 0.1) -> dict | None:
    import asyncio
    import httpx
    from app.core.config import settings
    from app.services.ai_content import _extract_json_obj
    from app.services.usage_tracker import can_call, record
    if not settings.AI_API_KEY:
        return None
    body = {"contents": [{"parts": parts}], "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}"
    for i in range(3):
        if not can_call("gemini"):
            return None
        try:
            record("gemini")
            async with httpx.AsyncClient(timeout=180) as c:
                r = await c.post(url, json=body)
            if r.status_code in (429, 500, 503) and i < 2:
                await asyncio.sleep(15 * (i + 1))
                continue
            if r.status_code != 200:
                logger.warning("قسم الأبحاث: النموذج HTTP {}", r.status_code)
                return None
            obj = _extract_json_obj(r.json()["candidates"][0]["content"]["parts"][0]["text"])
            return obj if isinstance(obj, dict) else None
        except Exception as e:                                    # noqa: BLE001
            logger.warning("قسم الأبحاث: النموذج {}", type(e).__name__)
            return None
    return None


async def _read(path: str, it: dict) -> dict | None:
    from app.services.file_reader import _forget, _upload
    uri, fname = await _upload(path, "research")
    if not uri:
        return None
    try:
        obj = await _gemini([{"file_data": {"mime_type": "application/pdf", "file_uri": uri}},
                             {"text": READ_PROMPT.format(title=it.get("title"), source=it.get("source"), date=it.get("date"), kind=it.get("kind"))}],
                            max_tokens=3000)
    finally:
        await _forget(fname)
    note = _clean_note(obj or {})
    return note if (note["headline"] or note["points"]) else None


async def _all_items() -> list[dict]:
    """كلُّ ما تنشره الجهات (لا آخرُ خمسةٍ يوميّة فقط كما في «التوقعات») — فالسياقُ التاريخيّ يُبنى من الماضي أيضاً."""
    import asyncio
    from app.services import research_reports as R
    res = await asyncio.gather(R._ajc(), R._jadwa(), R._arc(), return_exceptions=True)
    out: list[dict] = []
    for r in res:
        if isinstance(r, list):
            out += r
    return out


async def ingest(budget: int = 6, days: int = 10) -> dict:
    """يقرأ ما لم يُقرأ — ‏budget ملفّاتٍ على الأكثر، بالتتابع."""
    from app.services.usage_tracker import can_call
    today = date.today()
    k = knowledge()
    items = await _all_items()
    todo = queue(items, k["read"], today, days)[:budget]
    done = 0
    for it in todo:
        if not can_call("gemini"):
            break
        key = item_key(it)
        path = await _download(it)
        note = None
        if path:
            try:
                note = await _read(path, it)
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass
        k["read"][key] = {"date": it.get("date"), "source": it.get("source"), "title": it.get("title"), "kind": it.get("kind"),
                          "at": datetime.now().isoformat(timespec="minutes"), "ok": bool(note)}
        if note:
            k["notes"].append({"key": key, "date": it.get("date"), "source": it.get("source"), "title": it.get("title"),
                               "kind": it.get("kind"), "url": it.get("url"), **note})
            done += 1
        _save("knowledge.json", prune(k, today))
    logger.info("قسم الأبحاث: قُرئ {} من {} في الطابور ({} منشوراً)", done, len(todo), len(items))
    return {"read": done, "queued": len(todo), "published": len(items)}


async def ingest_cli() -> None:
    """للمجدول في عمليةٍ منفصلة: صباحاً اليوميُّ الجديد، وليلاً يتّسع المدى فيكتمل السياقُ التاريخيّ."""
    import sys
    night = "night" in sys.argv
    await ingest(budget=16 if night else 6, days=90 if night else 10)


# ── التقرير ─────────────────────────────────────────────────────────────────────

def recent_sources(notes: list[dict], today: date, days: int = 3, limit: int = 12) -> list[dict]:
    floor = (today - timedelta(days=days)).isoformat()
    pick = [n for n in notes if str(n.get("date") or "") >= floor]
    pick.sort(key=lambda n: (str(n.get("date") or ""), -_KIND_RANK.get(str(n.get("kind")), 2)), reverse=True)
    return pick[:limit]


def _fmt_source(i: int, n: dict) -> str:
    parts = [f"[{i}] {n.get('source')} — «{n.get('title')}» ({n.get('date')}, {n.get('kind')})", f"الخلاصة: {n.get('headline')}"]
    for lbl, key in (("نقاط", "points"), ("محليّ", "local_news"), ("عالميّ", "global_news"), ("اقتصاد", "macro"), ("مخاطر", "risks")):
        if n.get(key):
            parts.append(f"{lbl}: " + " | ".join(n[key]))
    m = n.get("market") or {}
    if any(m.values()):
        parts.append("السوق: " + " | ".join(v for v in m.values() if v))
    if n.get("sectors"):
        parts.append("قطاعات: " + " | ".join(f"{s['name']} ({s['view']}): {s['note']}" for s in n["sectors"]))
    if n.get("companies"):
        parts.append("شركات: " + " | ".join(f"{c['name']}{' ' + c['symbol'] if c.get('symbol') else ''} ({c['view']}"
                                              f"{', مستهدف ' + str(c['target']) if c.get('target') else ''}): {c['note']}" for c in n["companies"]))
    return "\n".join(parts)


def _context(notes: list[dict], today: date, exclude: set) -> str:
    floor = (today - timedelta(days=30)).isoformat()
    rows = [n for n in notes if str(n.get("date") or "") >= floor and n.get("key") not in exclude]
    rows.sort(key=lambda n: str(n.get("date") or ""), reverse=True)
    return "\n".join(f"- {n.get('date')} · {n.get('source')}: {n.get('headline')}" + (f" — {n['points'][0]}" if n.get("points") else "")
                     for n in rows[:40]) or "لا سياقَ بعد."


def validate(obj: dict, n_src: int, universe: set) -> dict:
    """لا سطرَ بلا مصدرٍ صحيح، ولا توصيةَ لرمزٍ خارج المحفظة والمصادر أو بلا دليلين (مصدرٌ بحثيّ + أرقامُ التطبيق)."""
    ok = lambda src: [s for s in (src or []) if isinstance(s, int) and 0 <= s <= n_src]   # noqa: E731
    def rows(v, need_research=True):
        out = []
        for r in (v or []):
            if not isinstance(r, dict) or not str(r.get("text") or "").strip():
                continue
            s = ok(r.get("src"))
            if not s or (need_research and not any(x > 0 for x in s)):
                continue
            out.append({**{k: r[k] for k in r if k not in ("src", "text")}, "text": str(r["text"]).strip(), "src": s})
        return out
    mk = obj.get("market") if isinstance(obj.get("market"), dict) else {}
    port = []
    for r in rows(obj.get("portfolio"), need_research=False):
        sym = str(r.get("symbol") or "").replace(".SR", "")
        if sym in universe:
            port.append({**r, "symbol": sym})
    recs = []
    for r in (obj.get("recommendations") or [])[:3]:
        if not isinstance(r, dict):
            continue
        sym = str(r.get("symbol") or "").replace(".SR", "")
        s = ok(r.get("src"))
        if sym in universe and 0 in s and any(x > 0 for x in s) and str(r.get("why") or "").strip():
            recs.append({"symbol": sym, "action": str(r.get("action") or "").strip(), "why": str(r["why"]).strip(),
                         "condition": str(r.get("condition") or "").strip(), "src": s})
    return {"headline": str(obj.get("headline") or "").strip(),
            "market": {"summary": str(mk.get("summary") or "").strip(), "points": rows(mk.get("points"))},
            "local": rows(obj.get("local")), "global": rows(obj.get("global")),
            "sectors": [r for r in rows(obj.get("sectors")) if r.get("name")],
            "portfolio": port, "watch": rows(obj.get("watch")), "recommendations": recs,
            "no_rec_reason": "" if recs else str(obj.get("no_rec_reason") or "").strip()}


async def _positions(db) -> list[dict]:
    import asyncio
    from app.api.v1.endpoints.allocation import get_allocation
    from app.services import advisor as A
    res = await get_allocation(db)
    d = (json.loads(res.body) if hasattr(res, "body") else res)["data"]
    items = sorted([it for it in d.get("items") or [] if float(it.get("market_value") or 0) > 0],
                   key=lambda it: -float(it.get("market_value") or 0))[:15]
    out = []
    for it in items:
        try:
            f = await asyncio.wait_for(A.dossier(db, str(it["symbol"]), it.get("name") or ""), timeout=40)
            st = A.stance(f)
        except Exception:                                         # noqa: BLE001
            continue
        out.append({"symbol": f["symbol"], "name": f.get("name"), "weight": f.get("weight"), "pnl": f.get("pnl_pct"), "price": f.get("price"),
                    "fv": f.get("fv"), "upside": f.get("upside"), "decision": f.get("decision"), "action": st.get("action"), "why": st.get("why")})
    return out


def _fmt_positions(ps: list[dict]) -> str:
    f = lambda v, s="": "—" if v is None else f"{v:.2f}{s}" if isinstance(v, (int, float)) else str(v)   # noqa: E731
    return "\n".join(f"- {p['symbol']} {p['name']}: الوزن {f(p.get('weight'), '%')} · الربح {f(p.get('pnl'), '%')} · السعر {f(p.get('price'))}"
                     f" · العادل {f(p.get('fv'))} · الصعود {f(p.get('upside'), '%')} · قرارُ التطبيق {p.get('decision') or '—'}"
                     f" · المستشار: {p.get('action') or '—'} ({p.get('why') or ''})" for p in ps) or "لا مراكز."


async def compose_for(db, pid: int, pname: str, today: date | None = None) -> dict | None:
    from app.services.market_data import market_service
    today = today or date.today()
    k = knowledge()
    srcs = recent_sources(k["notes"], today)
    if not srcs:
        return None
    ps = await _positions(db)
    tasi = None
    try:
        t = await market_service.get_price("^TASI.SR") or {}
        if isinstance(t.get("price"), (int, float)):
            tasi = {"price": float(t["price"]), "pct": float(t["change_percent"]) if isinstance(t.get("change_percent"), (int, float)) else None}
    except Exception:                                             # noqa: BLE001
        tasi = None
    market = f"تاسي {tasi['price']} ({tasi['pct']}%)" if tasi else "غير متوفّر"
    prompt = COMPOSE_PROMPT.format(pname=pname, today=today.isoformat(),
                                   sources="\n\n".join(_fmt_source(i + 1, n) for i, n in enumerate(srcs)),
                                   context=_context(k["notes"], today, {n.get("key") for n in srcs}), portfolio=_fmt_positions(ps), market=market)
    obj = await _gemini([{"text": prompt}], max_tokens=6000, temperature=0.2)
    if not obj:
        return None
    universe = {p["symbol"] for p in ps} | {c["symbol"] for n in srcs for c in n.get("companies") or [] if c.get("symbol")}
    rep = validate(obj, len(srcs), universe)
    names = {p["symbol"]: p["name"] for p in ps}
    names.update({c["symbol"]: c["name"] for n in srcs for c in n.get("companies") or [] if c.get("symbol") and c["symbol"] not in names})
    for r in rep["portfolio"] + rep["recommendations"]:
        r["name"] = names.get(r["symbol"], r["symbol"])
    rep.update({"date": today.isoformat(), "portfolio_id": pid, "portfolio_name": pname, "market_now": market, "tasi": tasi,
                "at": datetime.now().isoformat(timespec="minutes"),
                "sources": [{"n": i + 1, "source": n.get("source"), "title": n.get("title"), "date": n.get("date"), "kind": n.get("kind"),
                             "url": n.get("url")} for i, n in enumerate(srcs)]})
    return rep


def telegram_lines(r: dict) -> list[str]:
    L = [f"📑 التقرير اليوميّ — {r.get('portfolio_name')} · {r.get('date')}", "", r.get("headline") or ""]
    if r["market"].get("summary"):
        L += ["", "السوق: " + r["market"]["summary"]]
    for title, key, n in (("محليّاً", "local", 3), ("عالمياً", "global", 2)):
        if r.get(key):
            L += ["", title + ":"] + [f"• {x['text']}" for x in r[key][:n]]
    if r.get("portfolio"):
        L += ["", "محفظتنا:"] + [f"• {x['name']} — {x.get('stance', '')}: {x['text']}" for x in r["portfolio"][:6]]
    if r.get("recommendations"):
        L += ["", "التوصيات:"] + [f"• {x['action']} {x['name']}: {x['why']}" + (f" (الشرط: {x['condition']})" if x.get("condition") else "")
                                 for x in r["recommendations"]]
    elif r.get("no_rec_reason"):
        L += ["", "لا توصيةَ اليوم: " + r["no_rec_reason"]]
    L += ["", "المصادر: " + " · ".join(sorted({s["source"] for s in r.get("sources") or []}))]
    return [x for x in L if x is not None]


def save_report(r: dict) -> None:
    _save(os.path.join("reports", f"{r['date']}_{r['portfolio_id']}.json"), r)
    files = sorted(os.listdir(os.path.join(_dir(), "reports")))
    for f in files[:-KEEP_REPORTS]:
        try:
            os.remove(os.path.join(_dir(), "reports", f))
        except OSError:
            pass


def report_dates(pid: int) -> list[str]:
    try:
        return sorted({f.split("_")[0] for f in os.listdir(os.path.join(_dir(), "reports")) if f.endswith(f"_{pid}.json")}, reverse=True)
    except OSError:
        return []


def load_report(pid: int, day: str | None = None) -> dict | None:
    days = report_dates(pid)
    day = day if day in days else (days[0] if days else None)
    return _load(os.path.join("reports", f"{day}_{pid}.json"), None) if day else None


async def compose_all(send: bool = True) -> dict:
    """لكلّ محفظةٍ غيرِ مؤرشفة تقريرُها — يُحفظ ويُرسَل في التطبيق وتلغرام."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.portfolio_scope import reset_scope, set_scope
    from app.models.portfolio import Portfolio
    from app.services.advisor_memory import notify
    rep = {}
    async with AsyncSessionLocal() as db:
        ps = (await db.execute(select(Portfolio.id, Portfolio.name).where(Portfolio.is_archived.is_(False)).order_by(Portfolio.id))).all()
        try:
            for pid, pname in ps:
                set_scope(pid, False)
                r = await compose_for(db, pid, pname)
                if not r:
                    continue
                save_report(r)
                rep[pid] = len(r.get("sources") or [])
                if send:
                    L = telegram_lines(r)
                    await notify(L[0], L[2:], raw=True)
        finally:
            reset_scope()
    logger.info("قسم الأبحاث: التقارير {}", rep)
    return rep


def stats() -> dict:
    k = knowledge()
    notes = k["notes"]
    by = {}
    for n in notes:
        by[n.get("source")] = by.get(n.get("source"), 0) + 1
    last = max((v.get("at") or "" for v in k["read"].values()), default="")
    return {"notes": len(notes), "by_source": by, "last_read": last or None,
            "first": min((str(n.get("date")) for n in notes), default=None), "latest": max((str(n.get("date")) for n in notes), default=None)}


def library(limit: int = 60) -> list[dict]:
    notes = sorted(knowledge()["notes"], key=lambda n: str(n.get("date") or ""), reverse=True)[:limit]
    return [{"date": n.get("date"), "source": n.get("source"), "title": n.get("title"), "kind": n.get("kind"), "url": n.get("url"),
             "headline": n.get("headline"), "points": (n.get("points") or [])[:4]} for n in notes]
