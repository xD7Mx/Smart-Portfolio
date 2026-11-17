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
  ٢ **التقرير** (‏compose · D746): بعد إغلاق السوق أيامَ التداول تُحسب أرقامُ الجلسة في `research_paper` (المؤشّرُ ومؤشّراتُه
    المالية، والقطاعات، والإحصاءات، والأسواقُ العالمية والسلعُ والعملات، والنظرةُ الفنية ونظرتُنا، وأفضلُ اختياراتنا بنطاق الشراء
    والمستهدف ووقف الخسارة) — ويكتب النموذجُ النصَّ الحرَّ وحده: العنوانَ والأخبارَ المحلية والعالمية وما يعني مراكزَنا وما يُتابَع؛
    كلُّ سطرٍ بأرقام مصادره وما لا مصدرَ له يُحذف. والمصادرُ تُلزِم ولا تُعرض (بأمر المالك: «اعتمدها ولا تذكرها»).
  ٣ **الورقة**: على هيئة «التقرير اليوميّ والنظرة الفنية» لبيوت الأبحاث — أربعُ صفحاتٍ مؤرّخةٍ بيوم الجلسة، تُعرض في التطبيق
    وتُرسَل ملفَّ PDF إلى تلغرام. والمكتبةُ لا تُعرض: القراءةُ تعمل في الخفاء.
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
BACKFILL_V = 2                                                     # نسخةُ تقرير الأرشيف — ما كُتب بنسخةٍ أقدم يُعاد (‏D749: كُتبت الأولى بلا إغلاقات الشركات)
KEEP_REPORTS = 600                                                # تقريرٌ لكلّ محفظةٍ لكلّ جلسة — أرشيفٌ يتّسع لنحو سنة
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
  "risks": ["مخاطرُ ذكرها التقرير"],
  "session": {{"date": "تاريخُ الجلسة التي يصفها التقرير YYYY-MM-DD أو null", "close": null, "value_bn": null, "volume_mn": null, "trades": null, "up": null, "down": null}},
  "regional": [{{"market": "دبي", "close": null, "d1": null, "mtd": null, "ytd": null}}],
  "rates": [{{"name": "سايبور 3 أشهر", "value": null, "d1_bp": null, "mtd_bp": null, "ytd_bp": null}}]}}
والحقولُ الثلاثةُ الأخيرة أرقامٌ مجرّدةٌ كما في جداول التقرير (النسبُ بلا علامة %، والقيمةُ بالمليار والكمّيةُ بالمليون). و"regional" **كلُّ صفوف**
جدول «الأسواق الإقليمية» (السعودية ودبي وأبو ظبي والكويت وقطر وعمان والبحرين ومصر — ما ورد منها)، و"rates" **كلُّ صفوف** جدول «أسعار الفائدة بين
البنوك» (سايبور لآجاله وسوفر وإيبور) — وإن لم يرد الجدولُ فقائمةٌ فارغة."""

COMPOSE_PROMPT = """أنت رئيسُ قسم الأبحاث في مدير محفظةٍ سعوديٍّ مخضرم — انتقائيٌّ دقيق، يربط الحدثَ بالمحفظة ولا يقول ما لا دليلَ عليه.
اكتب الأقسامَ النصّية في «التقرير اليوميّ» لمحفظة «{pname}» عن جلسة {today} بعد إغلاق السوق. أرقامُ الجلسة والجداولُ والنظرةُ الفنية
محسوبةٌ في التطبيق فلا تكرّرها؛ ودورُك: العنوان، والأخبارُ المحلية والعالمية، وما يعني مراكزَنا، وما يُتابَع.

المصادرُ المقروءةُ مرقّمة (لا مصدرَ غيرها). كلُّ سطرٍ يحمل أرقامَ مصادره في "src" — لا تُعرض للقارئ، وإنما تُلزمك ألّا تكتب إلا منها.
وأرقامُ التطبيق مصدرٌ رقمُه 0.
{sources}

السياقُ التاريخيّ (خلاصةُ ثلاثين يوماً — للربط والمقارنة لا للنقل):
{context}

جلسةُ اليوم (المصدر 0): {market}

مراكزُ المحفظة (المصدر 0):
{portfolio}

أعد JSON فقط:
{{"headline": "عنوانُ اليوم في جملةٍ واحدة: ما جرى وما يعني محفظتنا",
  "local": [{{"text": "خبرٌ محليٌّ موجزٌ بأرقامه — اسمُ الشركة أو الجهة أوّلاً", "src": [1]}}],
  "global": [{{"text": "خبرٌ عالميٌّ أو حركةُ سوقٍ عالمية وأثرُها", "src": [2]}}],
  "portfolio": [{{"symbol": "1120", "text": "ما يعني هذا المركزَ اليومَ من الأخبار والتقارير", "src": [0, 1]}}],
  "watch": [{{"text": "حدثٌ أو مستوًى يُتابَع في الأيام القادمة", "src": [1]}}]}}
قواعد: الأخبارُ المحلية سبعٌ على الأكثر، والعالميةُ خمس، والمراكزُ ستّةٌ لا يُذكر منها إلا ما جاء فيه جديد، والمتابعةُ أربع.
لا تذكر أسماءَ الجهات الناشرة ولا المصادرَ في النصّ (لا «أرقام» ولا «تداول» بين قوسين، ولا اسمَ بيت أبحاث). ولا نصيحةَ عامّة.
والأرقامُ لاتينية، والعربيةُ فصيحةٌ موجزةٌ بأسلوب التقارير اليومية لبيوت الأبحاث."""


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
            "sectors": secs, "companies": cos, "risks": lst(obj.get("risks"), 6), **_clean_tables(obj)}


def _num(v):
    if isinstance(v, bool) or v is None:
        return None
    try:
        x = float(str(v).replace(",", "").replace("%", "").strip())
        return x if x == x and abs(x) < 1e13 else None
    except ValueError:
        return None


def _clean_tables(obj: dict) -> dict:
    """أرقامُ الجلسة وجدولا الأسواق الإقليمية والفائدة — أرقامٌ أو لا شيء، ولا صفَّ بلا اسمٍ وقيمة."""
    s = obj.get("session") if isinstance(obj.get("session"), dict) else {}
    d = str(s.get("date") or "").strip()
    sess = {"date": d if re.fullmatch(r"20\d\d-\d\d-\d\d", d) else None,
            **{k: _num(s.get(k)) for k in ("close", "value_bn", "volume_mn", "trades", "up", "down")}}
    reg = [{"market": str(x.get("market")).strip(), **{k: _num(x.get(k)) for k in ("close", "d1", "mtd", "ytd")}}
           for x in (obj.get("regional") or []) if isinstance(x, dict) and x.get("market") and _num(x.get("close"))][:10]
    rates = [{"name": str(x.get("name")).strip(), **{k: _num(x.get(k)) for k in ("value", "d1_bp", "mtd_bp", "ytd_bp")}}
             for x in (obj.get("rates") or []) if isinstance(x, dict) and x.get("name") and _num(x.get("value")) is not None][:8]
    return {"session": sess if any(v is not None for k, v in sess.items() if k != "date") else None, "regional": reg, "rates": rates}


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
                            max_tokens=4000)
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

def recent_sources(notes: list[dict], today: date, days: int = 3, limit: int = 12, upto: str | None = None) -> list[dict]:
    """مذكّراتُ الأيام الأخيرة — و`upto` سقفٌ لأرشيف ما مضى: لا يدخل تقريرَ جلسةٍ ما نُشر بعدها."""
    floor = (today - timedelta(days=days)).isoformat()
    pick = [n for n in notes if str(n.get("date") or "") >= floor and (upto is None or str(n.get("date") or "") <= upto)]
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


_HOUSES = re.compile(r"الجزيرة كابيتال|الراجحي المالية|جدوى للاستثمار|\((?:أرقام|تداول|رويترز|بلومبرغ|أرقام كابيتال)\)")


def validate(obj: dict, n_src: int, universe: set) -> dict:
    """لا سطرَ بلا مصدرٍ بحثيٍّ صحيح، ولا مركزَ خارج المحفظة، ولا اسمَ جهةٍ ناشرة في النصّ (بأمر المالك: «اعتمدها ولا تذكرها»)."""
    ok = lambda src: [s for s in (src or []) if isinstance(s, int) and 0 <= s <= n_src]   # noqa: E731

    def rows(v, n):
        out = []
        for r in (v or []):
            if not isinstance(r, dict) or not str(r.get("text") or "").strip():
                continue
            s = ok(r.get("src"))
            t = str(r["text"]).strip()
            if not any(x > 0 for x in s) or _HOUSES.search(t):
                continue
            out.append({**{k: r[k] for k in r if k not in ("src", "text")}, "text": t, "src": s})
        return out[:n]
    port = []
    for r in rows(obj.get("portfolio"), 6):
        sym = str(r.get("symbol") or "").replace(".SR", "")
        if sym in universe:
            port.append({**r, "symbol": sym})
    head = str(obj.get("headline") or "").strip()
    return {"headline": "" if _HOUSES.search(head) else head, "local": rows(obj.get("local"), 7), "global": rows(obj.get("global"), 5),
            "portfolio": port, "watch": rows(obj.get("watch"), 4)}


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
        out.append({"symbol": str(f["symbol"]).replace(".SR", ""), "name": f.get("name"), "weight": f.get("weight"), "pnl": f.get("pnl_pct"),
                    "price": f.get("price"), "fv": f.get("fv"), "upside": f.get("upside"), "decision": f.get("decision"),
                    "action": st.get("action"), "why": st.get("why")})
    return out


def _fmt_positions(ps: list[dict]) -> str:
    f = lambda v, s="": "—" if v is None else f"{v:.2f}{s}" if isinstance(v, (int, float)) else str(v)   # noqa: E731
    return "\n".join(f"- {p['symbol']} {p['name']}: الوزن {f(p.get('weight'), '%')} · الربح {f(p.get('pnl'), '%')} · السعر {f(p.get('price'))}"
                     f" · تغيّرُ اليوم {f(p.get('pct'), '%')} · العادل {f(p.get('fv'))} · الصعود {f(p.get('upside'), '%')}"
                     f" · قرارُ التطبيق {p.get('decision') or '—'} · نظرتُنا {p.get('view')}" for p in ps) or "لا مراكز."


def _market_line(m: dict) -> str:
    from app.services.research_paper import n2, p2
    t, b, tech = m["tasi"], m["breadth"], m["tech"]
    sec = [x for x in m.get("sectors") or [] if x.get("pct") is not None]
    return (f"تاسي {n2(t.get('close'))} ({p2(t.get('pct'))}) · قيمةُ التداول {((b.get('value') or 0) / 1e9):.2f} مليار · المرتفعة/المنخفضة "
            f"{b.get('up')}/{b.get('down')} · الأفضلُ قطاعاً {sec[0]['name'] if sec else '—'} والأضعفُ {sec[-1]['name'] if sec else '—'}"
            f" · نظرتُنا الفنية للمؤشّر: {tech.get('view')}")


# ── سجلُّ الجلسات والجداولُ المقروءة ─────────────────────────────────────────
def sessions_store(k: dict | None = None) -> dict:
    """سجلُّ الجلسات: ما سجّله التطبيقُ بعد كلّ إغلاق، وما قُرئ من أرقام الجلسات في التقارير اليومية لما قبله."""
    from app.services.research_paper import history_append
    st = _load("sessions.json", {})
    for n in (k or knowledge())["notes"]:
        s = n.get("session") or {}
        if n.get("kind") != "تقرير يوميّ" or not s.get("date") or s["date"] >= str(n.get("date") or ""):
            continue
        rec = {"value": s["value_bn"] * 1e9 if s.get("value_bn") else None, "volume": s["volume_mn"] * 1e6 if s.get("volume_mn") else None,
               "trades": s.get("trades"), "up": s.get("up"), "down": s.get("down"), "close": s.get("close"), "src": "report"}
        st = history_append(st, s["date"], rec)
    return st


def latest_tables(notes: list[dict], today: date, upto: str | None = None) -> tuple[dict, list[dict]]:
    """أحدثُ جدولٍ للأسواق الإقليمية ولأسعار الفائدة بين البنوك من تقارير الأيام السبعة الأخيرة — بتاريخ جلسته (وحتى `upto` لما مضى)."""
    floor = (today - timedelta(days=7)).isoformat()
    rows = sorted([n for n in notes if str(n.get("date") or "") >= floor and (upto is None or str(n.get("date") or "") <= upto)],
                  key=lambda n: str(n.get("date") or ""), reverse=True)
    # الجدولُ الكامل لا صفٌّ منه: أحدثُ مذكّرةٍ فيها ثلاثةُ أسواقٍ فأكثر غيرُ السعودية، وأحدثُ جدولِ فائدةٍ بآجالٍ ثلاثةٍ فأكثر
    full = lambda n: len([x for x in n.get("regional") or [] if "سعود" not in x["market"]]) >= 3   # noqa: E731
    reg = next(({"date": (n.get("session") or {}).get("date") or n.get("date"), "rows": n["regional"]} for n in rows if full(n)), {})
    sai = next((n["rates"] for n in rows if len(n.get("rates") or []) >= 3), next((n["rates"] for n in rows if n.get("rates")), []))
    return reg, [r for r in sai if "سايبور" in r["name"] or "سوفر" in r["name"] or "إيبور" in r["name"]]


async def compose_for(db, pid: int, pname: str, market: dict, today: date | None = None) -> dict | None:
    from app.services import research_paper as RP
    today = today or date.today()
    k = knowledge()
    srcs = recent_sources(k["notes"], today)
    ps = await _positions(db)
    rows = {}
    try:
        from app.services.market_screener import get_cached_screener
        rows = {str(r.get("symbol") or "").replace(".SR", ""): r for r in get_cached_screener() or []}
    except Exception:                                             # noqa: BLE001
        pass
    snap = {}
    try:
        from app.services.tadawul_market import usable_rows
        snap = usable_rows()[0] or {}
    except Exception:                                             # noqa: BLE001
        pass
    for p in ps:
        p["pct"] = RP._f((snap.get(p["symbol"]) or {}).get("change_pct"))
        p["trend"] = RP.trend_of(rows.get(p["symbol"]))
        p["view"] = RP.position_view(p)
    ai = {"headline": "", "local": [], "global": [], "portfolio": [], "watch": []}
    if srcs:
        prompt = COMPOSE_PROMPT.format(pname=pname, today=today.isoformat(),
                                       sources="\n\n".join(_fmt_source(i + 1, n) for i, n in enumerate(srcs)),
                                       context=_context(k["notes"], today, {n.get("key") for n in srcs}), portfolio=_fmt_positions(ps),
                                       market=_market_line(market))
        obj = await _gemini([{"text": prompt}], max_tokens=5000, temperature=0.2)
        if obj:
            ai = validate(obj, len(srcs), {p["symbol"] for p in ps})
    st = sessions_store(k)
    reg, sai = latest_tables(k["notes"], today)
    picks = await RP.picks_for({p["symbol"] for p in ps})
    rep = {"date": today.isoformat(), "portfolio_id": pid, "portfolio_name": pname, "at": datetime.now().isoformat(timespec="minutes"),
           "market": market, "averages": RP.averages(st, today.isoformat()), "analysis": RP.market_analysis(market, RP.averages(st, today.isoformat())),
           "tech_text": list(RP.tech_commentary(market)), "regional": reg, "saibor": sai, "positions": ps, "picks": picks,
           "no_pick_reason": "" if picks else "لم يجتمع في أيّ سهمٍ اليومَ قرارُ شراءٍ وصعودٌ إلى القيمة العادلة واتجاهٌ صاعدٌ بلا تشبّع.",
           **ai, "n_sources": len(srcs)}
    return rep


async def _market_text(day: date, market: dict, upto: str) -> dict:
    """نصُّ السوق لجلسةٍ مضت (العنوانُ والأخبارُ وما يُتابَع) — نداءٌ واحدٌ يشترك فيه تقريرُ كلِّ محفظة، ومن مذكّراتٍ حتى `upto` وحدها."""
    k = knowledge()
    srcs = recent_sources(k["notes"], day, upto=upto)
    if not srcs:
        return {"headline": "", "local": [], "global": [], "portfolio": [], "watch": [], "n_sources": 0}
    prompt = COMPOSE_PROMPT.format(pname="السوق", today=day.isoformat(), sources="\n\n".join(_fmt_source(i + 1, n) for i, n in enumerate(srcs)),
                                   context=_context([n for n in k["notes"] if str(n.get("date") or "") <= upto], day, {n.get("key") for n in srcs}),
                                   portfolio="لا مراكز — تقريرُ أرشيف.", market=_market_line(market))
    obj = await _gemini([{"text": prompt}], max_tokens=4000, temperature=0.2)
    v = validate(obj or {}, len(srcs), set())
    return {**v, "portfolio": [], "n_sources": len(srcs)}


async def backfill(sessions: int = 60) -> dict:
    """أرشيفُ الجلسات الماضية (‏D749 · بأمر المالك: «يتوفّر لجميع الأيام بتسلسلٍ تاريخيّ — 15 · 14 · 13»): لكلّ جلسةٍ من آخر `sessions`
    بلا تقرير تقريرُها من أرقامها هي (‏research_paper.market_at) ونصِّ مذكّراتها حتى الجلسة التالية. وتقريرُ الأرشيف الذي كُتب بلا أخبار
    يُعاد نصُّه حين تصل مذكّراتُ يومه. وصفحةُ المحفظة لا تُعاد لما مضى (المراكزُ مراكزُ اليوم)."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Portfolio
    from app.services import research_paper as RP
    async with AsyncSessionLocal() as db:
        ps = (await db.execute(select(Portfolio.id, Portfolio.name).where(Portfolio.is_archived.is_(False)).order_by(Portfolio.id))).all()
    ctx = await RP.history_context()
    st = sessions_store()
    today = date.today().isoformat()
    days = [b["date"][:10] for b in ctx["tasi"] if b["date"][:10] < today][-sessions:]
    nxt = {d: (days[i + 1] if i + 1 < len(days) else today) for i, d in enumerate(days)}
    notes = knowledge()["notes"]
    made, renewed = 0, 0
    for d in days:
        have = {pid: load_report(pid, d) for pid, _ in ps}
        have = {pid: r for pid, r in have.items() if r and r.get("date") == d}
        need = [(pid, pn) for pid, pn in ps if pid not in have or (have[pid].get("backfill") and have[pid].get("v") != BACKFILL_V)]
        stale = [(pid, pn) for pid, pn in ps if (pid, pn) not in need and pid in have and have[pid].get("backfill") and not have[pid].get("local")
                 and any(d <= str(n.get("date") or "") <= nxt[d] for n in notes)]
        if not need and not stale:
            continue
        m = RP.market_at(d, ctx, st)
        if not m:
            continue
        ai = await _market_text(date.fromisoformat(d), m, nxt[d])
        reg, sai = latest_tables(notes, date.fromisoformat(d), upto=nxt[d])
        av = RP.averages(st, d)
        for pid, pname in need + stale:
            save_report({"date": d, "portfolio_id": pid, "portfolio_name": pname, "at": datetime.now().isoformat(timespec="minutes"),
                         "market": m, "averages": av, "analysis": RP.market_analysis(m, av), "tech_text": list(RP.tech_commentary(m)),
                         "regional": reg, "saibor": sai, "positions": [], "picks": [], "no_pick_reason": "", "backfill": True, "v": BACKFILL_V, **ai})
        made += len(need)
        renewed += len(stale)
    logger.info("قسم الأبحاث: الأرشيف — كُتب {} وجُدّد {} ({} جلسة)", made, renewed, len(days))
    return {"made": made, "renewed": renewed, "sessions": len(days)}


async def backfill_cli() -> None:
    await backfill(60)


def caption(r: dict) -> str:
    """تعليقُ ملفّ التقرير في تلغرام — مؤرَّخٌ بيوم الجلسة، وبلا مصادر."""
    import html
    from app.services.research_paper import day_label, n2, p2
    m = r.get("market") or {}
    t, b, tech = m.get("tasi") or {}, m.get("breadth") or {}, m.get("tech") or {}
    L = [f"<b>التقرير اليومي — {html.escape(day_label(r['date']))}</b>", html.escape(r.get("portfolio_name") or ""),
         f"تاسي {n2(t.get('close'))} ({p2(t.get('pct'))}) · قيمة التداول {((b.get('value') or 0) / 1e9):.2f} مليار ريال",
         f"نظرتنا: {html.escape(str(tech.get('view') or '—'))} · اختياراتنا اليوم: {len(r.get('picks') or [])}"]
    if r.get("headline"):
        L += ["", html.escape(r["headline"])]
    return "\n".join(L)[:1000]


def save_report(r: dict) -> None:
    # ‏D757: ما يحسبه الرسمُ ويخبّئه في الورقة (‏_d7m · _ri) لا يُحفظ — مفاتيحُه أرقامٌ يجعلها الحفظُ نصوصاً فيتعطّل الرسمُ عند القراءة
    m = dict(r.get("market") or {})
    for k in ("_d7m", "_ri"):
        m.pop(k, None)
    _save(os.path.join("reports", f"{r['date']}_{r['portfolio_id']}.json"), {**r, "market": m})
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
    r = _load(os.path.join("reports", f"{day}_{pid}.json"), None) if day else None
    return r if isinstance(r, dict) and isinstance(r.get("market"), dict) else None


async def deliver(r: dict) -> bool:
    """الورقةُ ملفَّ PDF إلى تلغرام بتعليقٍ مؤرَّخ، وإشعارٌ في التطبيق — وإن تعذّرت الطباعةُ فالتعليقُ نصّاً."""
    from app.services import research_paper as RP
    ok = False
    try:
        from app.services.saqr_bot import bot
        if bot.enabled:
            data = await RP.pdf(r)
            if data:
                ok = bool(await bot.send_file(data, f"daily-report-{r['date']}.pdf", caption(r)))
            if not ok:
                ok = bool(await bot.send(caption(r), keyboard=False))
    except Exception as e:                                        # noqa: BLE001
        logger.warning("قسم الأبحاث: تلغرام {}", type(e).__name__)
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.market import Notification, NotificationPriority
        async with AsyncSessionLocal() as db:
            db.add(Notification(category="advisor", priority=NotificationPriority.MEDIUM, title=f"التقرير اليومي — {RP.day_label(r['date'])}",
                                message=r.get("headline") or "صدر التقرير اليومي.", extra_data={"source": "research", "date": r["date"]}))
            await db.commit()
    except Exception as e:                                        # noqa: BLE001
        logger.warning("قسم الأبحاث: الإشعار {}", type(e).__name__)
    return ok


async def compose_all(send: bool = True, day: date | None = None) -> dict:
    """بعد إغلاق السوق: أرقامُ الجلسة مرّةً، ثمّ لكلّ محفظةٍ غيرِ مؤرشفة تقريرُها — يُحفظ ويُرسَل ملفّاً مؤرَّخاً.
    و`day` جلسةٌ بعينها (آخرُ جلسةٍ بعد منتصف الليل مثلاً) — ولا تُكتب إلا إن كانت آخرَ جلسةٍ في الشموع."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.portfolio_scope import reset_scope, set_scope
    from app.models.portfolio import Portfolio
    from app.services import research_paper as RP
    today = day or date.today()
    market = await RP.gather(today)
    if not market:
        return {}
    b = market["breadth"]
    st = RP.history_append(_load("sessions.json", {}), today.isoformat(),
                           {"value": b.get("value"), "volume": b.get("volume"), "trades": b.get("trades"), "up": b.get("up"),
                            "down": b.get("down"), "close": market["tasi"].get("close"), "src": "app"})
    _save("sessions.json", st)
    rep = {}
    async with AsyncSessionLocal() as db:
        ps = (await db.execute(select(Portfolio.id, Portfolio.name, Portfolio.is_default)
                               .where(Portfolio.is_archived.is_(False)).order_by(Portfolio.id))).all()
        # ‏D756 (المالك 2026-11-16): «بعد الإغلاق يصلني تقريران لا واحد، وأحجامُهما مختلفة» — كان يُرسَل تقريرُ كلِّ محفظة.
        # فيُكتب لكلّ محفظةٍ تقريرُها (يُقرأ في مختبرها)، ويُرسَل واحدٌ فقط: تقريرُ المحفظة الافتراضية، مرّةً واحدةً في اليوم.
        main = next((pid for pid, _, d in ps if d), ps[0][0] if ps else None)
        sent = _load("sent.json", {})
        try:
            for pid, pname, _ in ps:
                set_scope(pid, False)
                r = await compose_for(db, pid, pname, market, today)
                if not r:
                    continue
                save_report(r)
                rep[pid] = {"local": len(r["local"]), "global": len(r["global"]), "picks": len(r["picks"]), "positions": len(r["positions"])}
                if send and pid == main:
                    if sent.get(today.isoformat()):
                        rep[pid]["sent"] = "أُرسل سابقاً"
                    else:
                        rep[pid]["sent"] = await deliver(r)
                        if rep[pid]["sent"]:
                            sent[today.isoformat()] = pid
                            _save("sent.json", dict(sorted(sent.items())[-60:]))
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
