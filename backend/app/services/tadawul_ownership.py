"""هيكلُ الملكية من «تداول» — المصدرُ الرسميّ أوّلاً (D277).

## تصحيحُ مسار

قال المالك: «لدينا مصدرُ السوق الرسميّ، ولا شيءَ غيرُ متوفّر — واعتبره
دليلَ تخاذل». وهو محقّ: «تداول» تنشر هذه البنودَ في صفحة كلّ شركة، وأنا
نفسي كنتُ قد اكتشفتُ نقاطَها (‏`foreginOwnerShip` ·
`historicalBoardMembersWithDates`) حين فتحتُ طبقةَ الجلب المنتحِل — ثمّ
ذهبتُ إلى «أرقام» وبنيتُ عليها طبقةَ متصفّحٍ ثقيلةً، وقلتُ «غير متوفّر»
عمّا هو متوفّر. فالترتيبُ يعود إلى موضعه: **تداول ← أرقام**.

## وكيف تُقرأ

البوّابةُ تُولّد معرِّفاتٍ في المسار، فلا يُثبَّت مسار. ولا يُثبَّت **اسمُ
النداء** أيضاً: تُقرأ أسماءُ النداءات الموجودةُ في صفحة الشركة نفسِها
وتُصنَّف بكلماتها (ownership · shareholder · board) — فإن غيّرت «تداول»
اسماً بقي الاكتشافُ عاملاً، وإن اختفى بندٌ قيل غيابُه ولم يُختلق.

بلا متصفّح، وبلا نداءٍ لكلّ شركة في وقت الطلب: القراءةُ في الجدولة.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone

from loguru import logger

STORE_KEY = "tadawul_own:{sym}"
MAX_AGE_DAYS = 30
MAX_ROWS = 60

_BASE_RE = re.compile(r"<base[^>]+href=[\"']([^\"']+)", re.I)
_EP_RE = re.compile(r"p0/[A-Za-z0-9_=]*=NJ([A-Za-z]{4,60})=/")

# كلماتُ التصنيف: البندُ يُعرَف من اسم ندائه لا من ترتيبه في الصفحة.
KINDS = {
    "foreign": re.compile(r"foreg|foreign.*owner|owner.*foreign", re.I),
    "board": re.compile(r"board.*member|member.*board", re.I),
    "major_holders": re.compile(r"(major|large|top).*(share|holder)|holder.*struct", re.I),
}

# مرشّحاتُ أسماء الحقول — أيُّها وُجد قُرئ، وما لم يوجد غاب.
NAME_KEYS = ("name", "shareholderName", "memberName", "investorName",
             "nameAr", "nameEn", "ownerName", "categoryName", "type")
PCT_KEYS = ("percentage", "percent", "ownershipPercentage", "ratio",
            "ownership", "share", "value")


def _num(x) -> float | None:
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = re.sub(r"[,\s%]", "", str(x or ""))
    try:
        return float(s)
    except ValueError:
        return None


def _pick(row: dict, keys) -> object:
    low = {str(k).lower(): v for k, v in row.items()}
    for k in keys:
        v = low.get(k.lower())
        if v not in (None, "", "-"):
            return v
    return None


def normalize(rows: list) -> list[dict]:
    """صفوفُ «اسمٌ · نسبة». وصفٌّ بلا اسمٍ أو نسبةٍ معقولةٍ يُترك."""
    out: list[dict] = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        name = _pick(r, NAME_KEYS)
        pct = _num(_pick(r, PCT_KEYS))
        if not name or pct is None or not (0.0 <= pct <= 100.0):
            continue
        row = {"name": str(name).strip(), "percent": round(pct, 4)}
        # حقولٌ إضافيةٌ تُقرأ إن وُجدت — ولا تُختلق.
        for key, names in (("position", ("position", "jobTitle", "title")),
                           ("at", ("date", "asOfDate", "updateDate"))):
            v = _pick(r, names)
            if v:
                row[key] = str(v).strip()
        out.append(row)
        if len(out) >= MAX_ROWS:
            break
    return out


# ══ والنداءاتُ تعيد HTML لا JSON ══ (D708)
# قِيس على الخادم (‏ownership_url_door · run 38583314249 · ownership_html_door · run 38583682788): الصفحةُ تُقرأ
# والنداءاتُ الثلاثةُ فيها، لكنّ شيفرتَها تطلبها `dataType: 'html'` فتعيد **أجزاءً تُلصق في الصفحة**: ‏foreginOwnerShip
# قطعةٌ فيها الحدُّ والفعليُّ (ومصفوفةُ الرسم ‎`{name, y}`)، و‏historicalBoardMembersWithDates جدولٌ (تاريخُ التداول ·
# المساهم · الصفة · النسبة …)، و‏historyOfMajorShareHolder جدولان (كبارُ الملاك ثمّ فترةُ الحظر) ويطلب ‎history. وكان القارئُ
# يفترض JSON فيسقط بندُه صامتاً: 0 من 272 والحارسُ أخضرُ على صفوفٍ مصطنعة. فيُقرأ ما يصل بشكله.
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_HAS_WORD = re.compile(r"[A-Za-z\u0600-\u06FF]")
POSITIONS_AR = {
    "chairman": "رئيس مجلس الإدارة", "vice chairman": "نائب رئيس مجلس الإدارة",
    "deputy chairman": "نائب رئيس مجلس الإدارة", "board of directors": "عضو مجلس الإدارة",
    "board member": "عضو مجلس الإدارة", "member": "عضو مجلس الإدارة",
    "managing director": "العضو المنتدب", "ceo": "الرئيس التنفيذي",
    "chief executive officer": "الرئيس التنفيذي", "cfo": "المدير المالي",
    "chief financial officer": "المدير المالي", "senior executive": "كبار التنفيذيين",
    "senior executives": "كبار التنفيذيين", "secretary": "أمين سرّ المجلس",
}


def _text(s: str) -> str:
    import html as _html
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


def _position_ar(p: str) -> str:
    """الصفةُ بالعربية إن عُرفت، وإلّا كما نشرتها «تداول» — لا تُخمَّن."""
    return POSITIONS_AR.get(" ".join(str(p or "").lower().split()), str(p or "").strip())


def parse_foreign(fragment: str) -> list[dict]:
    """قطعةُ الملكية الأجنبية ← صفوفُ «اسمٌ · نسبة». مصدرُها مصفوفةُ الرسم في القطعة نفسِها، وبديلُها عناصرُ القائمة."""
    pairs = re.findall(r"name:\s*'([^']*)'\s*,\s*y:\s*(-?[\d.]+)", fragment or "")
    if not pairs:
        for li in re.findall(r"<li\b.*?</li>", fragment or "", re.S | re.I):
            h = re.search(r"<h2[^>]*>(.*?)</h2>", li, re.S | re.I)
            for lab, val in re.findall(r"<span[^>]*>(.*?)</span>\s*<strong[^>]*>(.*?)</strong>", li, re.S | re.I):
                pairs.append((f"{_text(h.group(1)) if h else ''} {_text(lab)}".strip(), _text(val)))
    at = re.search(r"Last updated on\s*:?\s*(\d{4}-\d{2}-\d{2})", fragment or "", re.I)
    out = []
    for name, val in pairs:
        pct = _num(val)
        if pct is None or not (0.0 <= pct <= 100.0):
            continue
        low = name.lower()
        label = ("الحدُّ الأعلى لملكية الأجانب" if "max" in low else
                 "المستثمرون الاستراتيجيون الأجانب" if "strategic" in low else
                 "ملكيةُ الأجانب الفعلية" if "actual" in low else name.strip())
        row = {"name": label, "percent": round(pct, 4)}
        if at:
            row["at"] = at.group(1)
        out.append(row)
    return out


def parse_rows_html(fragment: str) -> list[dict]:
    """جدولُ «تداول» ← صفوفُ «اسمٌ · نسبة · صفة». الاسمُ أوّلُ خليّةٍ نصّية، والنسبةُ أوّلُ خليّةٍ بعلامة ‎%، والصفةُ النصّيةُ
    التالية؛ وإن حمل الجدولُ تاريخَ تداولٍ لكلّ صفّ قُرئ أحدثُه وحده (الجدولُ أيّامٌ متتالية لا تُجمع)."""
    rows = []
    for tr in re.findall(r"<tr\b.*?</tr>", fragment or "", re.S | re.I):
        tds = [_text(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", tr, re.S | re.I)]
        if len(tds) < 2:
            continue
        words = [c for c in tds if _HAS_WORD.search(c) and not _DATE.fullmatch(c) and "%" not in c]
        pcts = [c for c in tds if "%" in c]
        pct = _num(pcts[0]) if pcts else None
        if not words or pct is None or not (0.0 <= pct <= 100.0):
            continue
        row = {"name": words[0], "percent": round(pct, 6)}
        if len(words) > 1:
            row["position"] = _position_ar(words[1])
        d = next((c for c in tds if _DATE.fullmatch(c)), None)
        if d:
            row["at"] = d
        rows.append(row)
    latest = max((r["at"] for r in rows if r.get("at")), default=None)
    if latest:
        rows = [r for r in rows if r.get("at") == latest]
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: -r["percent"]):
        if r["name"] not in seen:
            seen.add(r["name"])
            out.append(r)
    return out[:MAX_ROWS]


def parse_response(kind: str, raw: str) -> list[dict]:
    """ردُّ النداء بشكله: ‏JSON إن كان (كما افتُرض أوّلاً)، وإلّا HTML — وما لا يُفهم يغيب لا يُصفَّر."""
    try:
        data = json.loads(raw)
    except Exception:                                             # noqa: BLE001
        if kind == "foreign":
            return parse_foreign(raw)
        if kind == "major_holders":
            # ‏الردُّ جدولان: كبارُ الملاك (5٪ فأكثر) أوّلاً، ثمّ المساهمون الخاضعون لفترة الحظر — فلا يُخلطان
            tables = re.findall(r"<table\b.*?</table>", raw or "", re.S | re.I)
            return parse_rows_html(tables[0] if tables else raw)
        return parse_rows_html(raw)
    rows = data.get("data") if isinstance(data, dict) else data
    return normalize(rows if isinstance(rows, list) else [])


def call_params(kind: str, sym: str) -> dict:
    """ما تمرّره شيفرةُ الصفحة نفسُها لكلّ نداء. ولكبار الملاك ‎history=0 بلا تاريخ — العرضُ الأوّلُ في الصفحة (أحدثُ يوم)؛
    قِيس (‏run 38584582392): بلا ‎history يردّ 500، وبمدى سنةٍ (‎history=1) ربعُ مليون حرفٍ لأيّامٍ متكرّرة."""
    p = {"requestLocale": "en", "symbol": sym}
    if kind == "major_holders":
        p["history"] = "0"
    return p


async def company_page(sym: str) -> str | None:
    """صفحةُ الشركة في «تداول» — رابطُها من لقطة السوق لا مؤلَّفاً."""
    from app.services.tadawul_market import row_for
    from app.services.tadawul_http import fetch

    url = (row_for(sym) or {}).get("company_url")
    if not url:
        return None
    if url.startswith("/"):
        url = "https://www.saudiexchange.sa" + url
    status, body = await fetch(url)
    return body if status == 200 and body else None


async def read_symbol(sym: str) -> dict:
    """يقرأ ما تنشره «تداول» لشركةٍ — أو سببَ التعذّر بنصِّه."""
    from app.services.tadawul_http import fetch

    body = await company_page(sym)
    if not body:
        return {"error": "لم تُقرأ صفحةُ الشركة في «تداول»"}
    mb = _BASE_RE.search(body)
    if not mb:
        return {"error": "لم يُعثر على أساس الصفحة"}
    base = mb.group(1).rstrip("/")

    names = sorted(set(_EP_RE.findall(body)))
    if not names:
        return {"error": "لا نداءَ في صفحة الشركة", "names": []}

    out: dict = {"names_seen": names}
    for kind, rx in KINDS.items():
        hit = next((n for n in names if rx.search(n)), None)
        if not hit:
            continue
        ep = next(m.group(0) for m in _EP_RE.finditer(body) if m.group(1) == hit)
        status, raw = await fetch(f"{base}/{ep}",
                                  params=call_params(kind, sym), referer=base)
        if status != 200 or not raw:
            out.setdefault("failed", {})[kind] = f"HTTP {status}"
            continue
        got = parse_response(kind, raw)
        if got:                       # بندٌ بلا صفٍّ مفهومٍ يغيب لا يُصفَّر
            out[kind] = got
            out[f"{kind}_call"] = hit
    return out


async def refresh(sym: str) -> dict:
    """يقرأ ويحفظ — ولا يُكتب شيءٌ حين لا يُقرأ شيء."""
    from app.services import lastgood

    sym = str(sym or "").replace(".SR", "").strip()
    rec = await read_symbol(sym)
    body = [k for k in KINDS if k in rec]
    if not body:
        return {"error": rec.get("error") or "لم يُقرأ بندٌ واحدٌ مفهوم",
                "names_seen": rec.get("names_seen", [])[:12]}
    rec |= {"symbol": sym, "as_of": datetime.now(timezone.utc).date().isoformat(),
            "source": "تداول — صفحة الشركة"}
    lastgood.save(STORE_KEY.format(sym=sym), rec)
    logger.info("ملكيةُ «تداول» {}: {}", sym, ", ".join(body))
    return {"ok": True, "symbol": sym, "sections": body}


def reading(symbol) -> dict | None:
    """المحفوظُ لشركةٍ — أو None إن غاب أو شاخ."""
    from app.services import lastgood
    m = re.search(r"\b(\d{4})\b", str(symbol or ""))
    if not m:
        return None
    rec = lastgood.load(STORE_KEY.format(sym=m.group(1)))
    if not isinstance(rec, dict):
        return None
    try:
        age = (date.today() - date.fromisoformat(str(rec.get("as_of")))).days
    except Exception:                                             # noqa: BLE001
        return None
    return None if age > MAX_AGE_DAYS else rec
