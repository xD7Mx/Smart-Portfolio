"""نتائجُ الشركات ربعياً وسنوياً — من «أرقام» للسوق كلِّه (D253).

## لماذا

طلب المالك ربعياً في البيانات المالية: «كانت سابقاً على ياهو فاضية».
وقياسُ المصادر على الخادم أعطى خريطةً صريحة:

  · تبويبُ القوائم في «تداول» **متجمّدٌ عند منتصف ‎2023** (وبعضُ الشركات
    يردّ فارغاً) — فلا يُبنى عليه حكمٌ على سوق ‎2026.
  · صفحاتُ «أرقام» للقوائم والنِسَب وصفحةُ الصفقات الخاصّة في «تداول»
    كلُّها تُرسَم بجافاسكربت: لا جدولَ في مصدرها ولا نداءَ جلبٍ ظاهر.
  · و**مسارٌ واحدٌ يُرسَم في الخادم فعلاً**: نتائجُ الشركات في «أرقام»
    (‏274 صفّاً في صفحةٍ واحدة) — ربعياً (‏fptype 3) وسنوياً (‏4).

فهذا الملفُّ يأخذ ما قِيس أنه يعمل، ويترك ما قِيس أنه لا يعمل.

## القيد الحاكم: الرمزُ يُقرأ ولا يُخمَّن

جدولُ «أرقام» يسمّي الشركةَ باسمها المختصر («كيمانول»)، لا برمزها.
ومطابقةُ الأسماء تقريباً تُدخل أرباحَ شركةٍ في ملفّ أخرى — وهو أسوأُ من
لا بيانات. فالرمزُ يُؤخذ من **معرِّف الشركة في الرابط** داخل الصفّ
(‏`companyid/NN`) عبر خريطة `argaam_ids` المقيسة، وما لم يُعرف معرِّفُه
يُترك ويُعَدّ في التقرير. لا مطابقةَ باسمٍ ولا بقربِ اسم.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from loguru import logger

BASE = "https://www.argaam.com"
STORE_KEY = "market:argaam_results"
QUARTER, ANNUAL = "3", "4"
MIN_ROWS = 100            # دون ذلك: جلبٌ فشل لا سوقٌ تقلّص

_CID = re.compile(r"companyid[/=](\d+)", re.I)
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_TD = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)


def _clean(x: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip()


def _num(x) -> float | None:
    """«(337.03)» سالبٌ بين قوسين، و«89.54 %» نسبة، و«-» لا شيء."""
    s = str(x or "").replace(",", "").replace("٪", "").replace("%", "").strip()
    if not s or s in ("-", "—"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    v = float(m.group(0))
    return -abs(v) if neg else v


def parse(body: str, ids: dict) -> tuple[dict[str, dict], dict]:
    """صفحةُ النتائج ← رمزٌ ← {السابق، الحالي، التغيّر٪، الفترة، التاريخ}.

    ويعود معها تقريرُ ما لم يُفهم — فلا يُقال «نجح» على صمت.
    """
    by_cid = {str(cid): sym for sym, cid in (ids or {}).items()}
    out: dict[str, dict] = {}
    rep = {"صفوف": 0, "بلا معرِّف": 0, "معرِّفٌ مجهول": 0, "بلا رقمين": 0}
    head: list[str] = []
    for tr in _TR.findall(body or ""):
        raw = _TD.findall(tr)
        cells = [_clean(c) for c in raw]
        cells_nb = [c for c in cells if c]
        if len(cells_nb) < 4:
            continue
        if not head and not _CID.search(tr):
            head = cells_nb                      # ترويسةٌ: منها اسمُ الفترتين
            continue
        rep["صفوف"] += 1
        m = _CID.search(tr)
        if not m:
            rep["بلا معرِّف"] += 1
            continue
        sym = by_cid.get(m.group(1))
        if not sym:
            rep["معرِّفٌ مجهول"] += 1
            continue
        prev, cur = _num(cells_nb[2]), _num(cells_nb[3])
        if prev is None and cur is None:
            rep["بلا رقمين"] += 1
            continue
        out[sym] = {
            "date": cells_nb[0] or None,
            "name": cells_nb[1] or None,
            "prev": prev,
            "current": cur,
            "change_pct": _num(cells_nb[4]) if len(cells_nb) > 4 else None,
            "prev_label": head[2] if len(head) > 2 else None,
            "current_label": head[3] if len(head) > 3 else None,
        }
    return out, rep


async def fetch(fptype: str, year: int) -> tuple[str, str | None]:
    """صفحةُ النتائج — أو (فارغ، سببُ التعذّر)."""
    from app.services.tadawul_http import fetch as _http
    url = f"{BASE}/ar/company/financial-result/market/3/fptype/{fptype}/{year}/3"
    try:
        status, body = await _http(url, referer=BASE + "/ar")
    except Exception as e:                                        # noqa: BLE001
        return "", f"{type(e).__name__}: {e}"
    if status != 200 or not body:
        return "", f"HTTP {status} من صفحة النتائج"
    return body, None


async def refresh(year: int | None = None) -> dict:
    """يجلب الربعيَّ والسنويَّ ويحفظهما — أو يعيد سببَ التعذّر بلا كتابة."""
    from app.services.argaam_ids import build
    year = year or datetime.now(timezone.utc).year
    ids = await build()
    if len(ids) < 200:
        return {"error": f"خريطةُ معرِّفات «أرقام» ناقصة ({len(ids)})"}
    out: dict = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "year": year}
    counts: dict = {}
    for label, fp in (("quarter", QUARTER), ("annual", ANNUAL)):
        body, why = await fetch(fp, year)
        if why:
            counts[label] = {"error": why}
            continue
        rows, rep = parse(body, ids)
        if len(rows) < MIN_ROWS:
            counts[label] = {"error": f"فُهم {len(rows)} صفّاً (الحدّ {MIN_ROWS})",
                             "تقرير": rep}
            continue
        out[label] = rows
        counts[label] = {"count": len(rows), "تقرير": rep}
    if not any(k in out for k in ("quarter", "annual")):
        logger.warning("نتائجُ «أرقام» لم تُقرأ: {}", counts)
        return {"error": "لم يُفهم أيُّ جدول", "تفصيل": counts}
    from app.services import lastgood
    lastgood.save(STORE_KEY, out)
    logger.info("نتائجُ «أرقام»: {}", counts)
    return {"ok": True, "تفصيل": counts}


def results(kind: str = "quarter") -> dict[str, dict]:
    """المحفوظُ — ربعياً أو سنوياً. وما غاب يعود فارغاً لا مختلَقاً."""
    from app.services import lastgood
    rec = lastgood.load(STORE_KEY)
    if not isinstance(rec, dict):
        return {}
    rows = rec.get(kind)
    return rows if isinstance(rows, dict) else {}


def for_symbol(symbol) -> dict:
    """نتيجةُ شركةٍ ربعياً وسنوياً — أو فارغ."""
    sym = str(symbol or "").replace(".SR", "").strip()
    q, a = results("quarter").get(sym), results("annual").get(sym)
    out = {}
    if q:
        out["quarter"] = q
    if a:
        out["annual"] = a
    return out
