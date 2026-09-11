"""المعدَّلُ الخالي من المخاطر بالريال — آخرُ حاجزٍ أمام محرّك القيمة العادلة (D249).

## لماذا

محرّكُ خصم التدفّقات جاهزٌ إلا من رقمٍ واحد: `risk_free_sar`. كلُّ ما عداه
مقيسٌ ومؤرَّخ — علاوةُ المخاطر من داموداران، والبيتا من «أرقام» (‏40/40).
والملفُّ يحمل القيمةَ **فارغةً عمداً** و`params.py` يرفض العملَ بمفترَض.
فكان الجوابُ مكتوباً في المسبار: «يجب تعبئتها يدوياً». واليدُ ليست مصدراً:
رقمٌ يُكتب مرّةً يشيخ بلا أن يُقال إنه شاخ، وهذا هو عطبُ «مصدرٌ واحدٌ
لمعنًى واحد» مقلوباً — لا مصدرَ أصلاً.

## المبدأ

المصدرُ هو سوقُ الصكوك الحكومية في «تداول» نفسِها: صكٌّ سياديٌّ **بالريال**
أجلُه قريبٌ من عشر سنوات، فعائدُه إلى الاستحقاق هو المعدَّل. لا سايبور
(سعرُ ما بين المصارف لا عائدُ سيادةٍ عشريّ)، ولا رقمٌ عامٌّ من ذاكرةٍ.

## أربعةُ قيودٍ تمنع رقماً مختلَقاً

  ١· **ترويسةٌ تُفهم أو امتناع.** لا تُخمَّن الأعمدةُ بموضعها؛ تُقرأ
     بأسمائها. وما لم تُفهم ترويستُه يُرفَض كلُّه ويُقال لماذا.
  ٢· **السيادةُ تُشترَط.** صكُّ شركةٍ عائدُه يحمل مخاطرَ ائتمانِها —
     فيُستبعَد ما لم يُعرَف مُصدِرُه حكومةً.
  ٣· **الأجلُ يُقاس لا يُفترَض.** يُختار الأقربُ إلى عشر سنواتٍ داخل
     نطاق `TENOR_BAND`، ويُسجَّل أجلُه الفعليُّ مع الرقم. وخارجَ النطاق
     امتناعٌ لا تقريب.
  ٤· **نطاقُ معقوليةٍ** من ملفّ المعايير نفسِه: ما خرج عنه جلبٌ فشل لا
     سوقٌ تغيّر.

وما يُحفَظ يُحفَظ في مخزن الحالة (‏`market:risk_free_sar`) لا في ملفٍّ
متتبَّع — فيعبر الحزمَ، وله تاريخٌ يُقرأ فيُعرَف متى شاخ.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone

from loguru import logger

STORE_KEY = "market:risk_free_sar"

# المضيفُ محجوبٌ عن بيئة التطوير — البنيةُ تُثبَّت بمسبارٍ على الخادم
# (‏scripts/audit/risk_free_probe.py) قبل الاعتماد، لا تُخمَّن.
SOURCES = (
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/sukuk-market-watch"
    "?locale=ar",
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/bonds-sukuk",
)

TARGET_YEARS = 10.0
TENOR_BAND = (6.0, 14.0)      # ما خرج عنه لا يُسمّى «عشريّاً»
MAX_AGE_DAYS = 45             # قراءةٌ أقدمُ من ذلك تُعدّ غائبة

_SOVEREIGN = re.compile(r"حكوم|سيادي|government|sovereign|kingdom|المملكة|وزارة\s*المالية",
                        re.I)
_NUM = re.compile(r"-?\d+(?:[.,]\d+)?")

# أسماءُ الأعمدة كما تظهر — عربيّةً وإنجليزيّة. المفتاحُ حقلُنا.
_ALIASES = {
    "name": ("اسم", "الاسم", "الأداة", "الصك", "instrument", "name", "security",
             "issue", "الإصدار"),
    "maturity": ("الاستحقاق", "تاريخ الاستحقاق", "maturity", "maturitydate",
                 "redemption"),
    "coupon": ("الكوبون", "العائد الاسمي", "معدل الكوبون", "coupon", "couponrate",
               "profitrate", "معدل الربح"),
    "price": ("السعر", "آخر سعر", "سعر الإغلاق", "price", "lastprice", "closeprice",
              "cleanprice"),
    "ytm": ("العائد إلى الاستحقاق", "العائد حتى الاستحقاق", "العائد", "yield",
            "ytm", "yieldtomaturity"),
}


def _norm(s: str) -> str:
    s = re.sub(r"[\s_\-/%()]+", "", str(s or "").lower())
    return s.replace("أ", "ا").replace("إ", "ا").replace("ى", "ي").replace("ة", "ه")


def _field_of(header_cell: str) -> str | None:
    h = _norm(header_cell)
    if not h:
        return None
    # الأطولُ أوّلاً: «العائد إلى الاستحقاق» قبل «العائد»، و«تاريخ الاستحقاق»
    # قبل «الاستحقاق» — وإلا التقط العامُّ ما هو للخاصّ.
    best: tuple[int, str] | None = None
    for field, names in _ALIASES.items():
        for n in names:
            nn = _norm(n)
            if nn and nn in h and (best is None or len(nn) > best[0]):
                best = (len(nn), field)
    return best[1] if best else None


def _num(cell) -> float | None:
    if isinstance(cell, (int, float)) and not isinstance(cell, bool):
        return float(cell)
    m = _NUM.search(str(cell or "").replace(",", ""))
    return float(m.group(0)) if m else None


def _pct(cell) -> float | None:
    """نسبةٌ تُقرأ كسراً عشريّاً: «4.75%» و‎4.75 و‎0.0475 كلُّها ‎0.0475."""
    v = _num(cell)
    if v is None:
        return None
    if v <= 0:
        return None
    return v / 100.0 if v > 0.5 else v


def _maturity(cell) -> date | None:
    s = str(cell or "").strip()
    if not s:
        return None
    for pat, order in (
        (r"(\d{4})-(\d{1,2})-(\d{1,2})", "ymd"),
        (r"(\d{4})/(\d{1,2})/(\d{1,2})", "ymd"),
        (r"(\d{1,2})/(\d{1,2})/(\d{4})", "dmy"),
        (r"(\d{1,2})-(\d{1,2})-(\d{4})", "dmy"),
    ):
        m = re.search(pat, s)
        if not m:
            continue
        a, b, c = (int(x) for x in m.groups())
        y, mo, d = (a, b, c) if order == "ymd" else (c, b, a)
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    return None


def parse_instruments(body: str) -> tuple[list[dict], str | None]:
    """أدواتُ الدين المدرَجة — أو (فارغ، سببُ التعذّر).

    يُقبل شكلان: JSON فيه صفوفٌ مفاتيحُها مفهومة، أو جدولُ HTML بترويسة.
    ولا يُقرأ عمودٌ بموضعه — بل باسمه (القيد ١).
    """
    body = body or ""
    rows: list[dict] = []

    # ── JSON ──
    try:
        data = json.loads(body)
        raw = data if isinstance(data, list) else next(
            (v for v in data.values() if isinstance(v, list)), [])
        for r in raw:
            if not isinstance(r, dict):
                continue
            row: dict = {}
            for k, v in r.items():
                f = _field_of(k)
                if f and row.get(f) in (None, ""):
                    row[f] = v
            if row.get("name"):
                rows.append(row)
        if rows:
            return rows, None
    except Exception:                                             # noqa: BLE001
        pass

    # ── HTML: ترويسةٌ ثمّ صفوف ──
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S | re.I)
    if not trs:
        return [], "لا جدولَ في المخرَج (صفحةٌ تغيّرت أو حمايةٌ ردّت صفحةً أخرى)"
    header: list[str | None] = []
    for tr in trs:
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
        if not cells:
            continue
        mapped = [_field_of(c) for c in cells]
        if not header:
            # ترويسةٌ صالحةٌ: فيها اسمٌ واستحقاقٌ على الأقلّ
            if {"name", "maturity"} <= {m for m in mapped if m}:
                header = mapped
            continue
        row = {f: cells[i] for i, f in enumerate(header)
               if f and i < len(cells) and cells[i]}
        if row.get("name"):
            rows.append(row)
    if not header:
        return [], "ترويسةٌ غيرُ مفهومة — لا عمودَ اسمٍ واستحقاقٍ معروفَين"
    if not rows:
        return [], "ترويسةٌ مفهومةٌ بلا صفوف"
    return rows, None


def ytm(price: float, coupon_rate: float, years: float, *, face: float = 100.0) -> float | None:
    """العائدُ إلى الاستحقاق — يُحلّ لا يُقرَّب.

    السعرُ نسبةٌ من القيمة الاسمية، والكوبونُ سنويٌّ كسراً عشريّاً. الدفعاتُ
    سنويّةٌ في `years` وما دونها، والأصلُ في آخرها. يُحلّ بالتنصيف —
    فالدالّةُ رِدْفةٌ في العائد، والتنصيفُ لا يتشعّب كنيوتن.
    """
    if not (price and price > 0) or years <= 0 or coupon_rate is None or coupon_rate < 0:
        return None

    def pv(y: float) -> float:
        c = face * coupon_rate
        t, total = years, 0.0
        # الدفعةُ الأولى قد تكون كسرَ سنةٍ (‏years=9.4 ⇒ 0.4 ثمّ 1,2,…)
        while t > 1e-9:
            total += c / (1.0 + y) ** t
            t -= 1.0
        return total + face / (1.0 + y) ** years

    lo, hi = -0.90, 1.00
    if pv(lo) < price or pv(hi) > price:
        return None                     # السعرُ خارج ما يمكن أن يُنتجه عائد
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if pv(mid) > price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def choose(rows: list[dict], *, today: date | None = None,
           sanity: tuple[float, float] = (0.02, 0.09)) -> tuple[dict | None, str | None]:
    """الصكُّ السياديُّ الأقربُ إلى عشر سنوات — أو (None، سببُ الامتناع)."""
    today = today or date.today()
    cands: list[dict] = []
    skipped = {"غير سيادي": 0, "بلا استحقاق": 0, "خارج النطاق": 0, "بلا عائد": 0,
               "خارج المعقولية": 0}
    for r in rows:
        name = str(r.get("name") or "")
        if not _SOVEREIGN.search(name):
            skipped["غير سيادي"] += 1
            continue
        mat = _maturity(r.get("maturity"))
        if mat is None:
            skipped["بلا استحقاق"] += 1
            continue
        years = (mat - today).days / 365.25
        if not (TENOR_BAND[0] <= years <= TENOR_BAND[1]):
            skipped["خارج النطاق"] += 1
            continue
        y = _pct(r.get("ytm"))
        how = "منشور"
        if y is None:
            cp, px = _pct(r.get("coupon")), _num(r.get("price"))
            y = ytm(px, cp, years) if (cp is not None and px) else None
            how = "محسوب"
        if y is None:
            skipped["بلا عائد"] += 1
            continue
        if not (sanity[0] <= y <= sanity[1]):
            skipped["خارج المعقولية"] += 1
            continue
        cands.append({"name": name, "maturity": mat.isoformat(),
                      "tenor_years": round(years, 2), "value": round(y, 5),
                      "basis": how})
    if not cands:
        why = "، ".join(f"{k}: {v}" for k, v in skipped.items() if v)
        return None, f"لا صكَّ سيادياً بأجلٍ عشريٍّ وعائدٍ مقروء ({why or 'لا صفوف'})"
    best = min(cands, key=lambda c: abs(c["tenor_years"] - TARGET_YEARS))
    best["peers"] = len(cands)
    return best, None


def _sanity_from_config() -> tuple[float, float]:
    try:
        from app.services.fair_value_engine.params import CONFIG_DIR
        raw = json.loads((CONFIG_DIR / "market_params.json").read_text(encoding="utf-8"))
        lo, hi = raw["risk_free_sar"]["sanity_range"]
        return float(lo), float(hi)
    except Exception:                                             # noqa: BLE001
        return 0.02, 0.09


async def refresh() -> dict:
    """يجلب ويقرأ ويحفظ — أو يعيد سببَ التعذّر بلا كتابة."""
    from app.services.tadawul_announcements import _raw_fetch
    sanity = _sanity_from_config()
    last: str | None = None
    for url in SOURCES:
        try:
            status, body = await _raw_fetch(url)
        except Exception as e:                                    # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            continue
        if status != 200:
            last = f"HTTP {status} من {url.rsplit('/', 1)[-1]}"
            continue
        rows, why = parse_instruments(body)
        if why:
            last = why
            continue
        best, why = choose(rows, sanity=sanity)
        if best is None:
            last = why
            continue
        rec = {
            "value": best["value"],
            "as_of": datetime.now(timezone.utc).date().isoformat(),
            "tenor_years": best["tenor_years"],
            "instrument": best["name"],
            "maturity": best["maturity"],
            "basis": best["basis"],
            "peers": best["peers"],
            "source": url,
            "rows_read": len(rows),
        }
        from app.services import lastgood
        lastgood.save(STORE_KEY, rec)
        logger.info("risk_free_sar = {} ({} سنة · {})",
                    rec["value"], rec["tenor_years"], rec["basis"])
        return rec
    logger.warning("risk_free_sar لم يُقرأ: {}", last)
    return {"value": None, "error": last or "لم يُفهم أيُّ مصدر"}


def reading() -> dict | None:
    """القراءةُ المحفوظة كاملةً — أو None إن غابت أو شاخت."""
    from app.services import lastgood
    rec = lastgood.load(STORE_KEY)
    if not isinstance(rec, dict) or not isinstance(rec.get("value"), (int, float)):
        return None
    try:
        age = (date.today() - date.fromisoformat(str(rec.get("as_of")))).days
    except Exception:                                             # noqa: BLE001
        return None
    if age > MAX_AGE_DAYS:
        return None
    return rec


def current() -> float | None:
    """الرقمُ وحدَه — منتِجٌ واحدٌ يقرأ منه `params.py` ولا يفترض."""
    rec = reading()
    return float(rec["value"]) if rec else None
