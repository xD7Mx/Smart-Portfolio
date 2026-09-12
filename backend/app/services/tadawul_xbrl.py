"""القوائمُ الرسميةُ من ملفّات XBRL في «تداول» (D263).

## لماذا

الدرجةُ والسعرُ العادل يُبنيان على القوائم، وكانت من ياهو: ناقصةً،
ومحدودةَ الحصّة، وبلا ربعيٍّ أصلاً (قال المالك: «ياهو لا يدعم الربع
سنوي، والقوائمُ تُحدَّث عنده متى شاء»). وقياسُ المصادر على الخادم ردَّ
تبويبَ القوائم في «تداول» (متجمّدٌ عند منتصف ‎2023) وصفحاتِ «أرقام»
(مرسومةً بجافاسكربت) — وأبقى مساراً واحداً رسمياً وحديثاً وآليَّ
القراءة: **ملفّاتُ XBRL** المرفقةُ بكلّ إفصاح.

وهي أعلى ما يمكن: مدقَّقةٌ (‏`Status of report: Audited`)، موحَّدةٌ
(‏`Consolidated`)، بتصنيف IFRS الكامل، ومؤرَّخةٌ بفترتها وبتاريخ إيداعها.

## البنية كما قِيست على الخادم (ملفّ «سابك»)

  · أقسامٌ بأرقامها: `[300200]` المركزُ المالي · `[300300]` الدخل ·
    `[300700]` التدفّقاتُ النقدية …
  · ولكلّ قسمٍ صفّا `Start Date` و`End Date` يحملان أعمدةَ الفترات.
  · و`Level of rounding used in financial statements` = `Thousands`
    — فالأرقامُ تُضرَب في ألف، ولا يُفترَض ذلك بل يُقرأ.
  · و`Period covered by financial statements` = `Annual` أو ربعيّ.

## القيد الحاكم: لا بندَ يُخمَّن

المطابقةُ بأسماء IFRS الرسمية كما وردت بنصّها، لا بالتقريب. وبندٌ لم
يُعرَف يُترك — **ولا يُملأ حقلٌ بأقربِ اسمٍ شبيه**: «إجمالي الالتزامات»
في خانة «حقوق الملكية» أسوأُ من لا بيانات، والدرجةُ تُبنى على هذه
الحقول فيصير الخطأُ حكماً على شركة.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

from loguru import logger

STORE_KEY = "market:xbrl"          # رمزٌ ← {annual:[…], quarterly:[…], …}
MAX_AGE_DAYS = 200                 # إيداعٌ أقدمُ من ذلك ليس «أحدثَ قوائم»
_NJ = re.compile(r"p0/[A-Za-z0-9_=]*=NJ([A-Za-z]+)=/")
_BASE = re.compile(r"<base[^>]+href=[\"']([^\"']+)", re.I)
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_TD = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
ORIGIN = "https://www.saudiexchange.sa"

# ══ أسماءُ IFRS كما وردت في الملفّ الرسميّ — لا تقريبَ ولا اجتهاد ══
# المفتاحُ حقلُنا، والقيمةُ أسماءٌ مقبولةٌ مرتّبةٌ بالأولوية.
LABELS: dict[str, tuple[str, ...]] = {
    "revenue": ("total revenue", "revenue", "total revenues"),
    "net_income": ("profit (loss) for period", "profit (loss)",
                   "profit (loss) for the period"),
    "equity": ("total equity",),
    "total_assets": ("total assets",),
    "total_liabilities": ("total liabilities",),
    "eps": ("total basic earnings (loss) per share",
            "basic earnings (loss) per share from continuing operations"),
    "interest_expense": ("finance costs",),
    # ══ بنودٌ يطلبها محرّكُ التدفّقات ولا يقوم بدونها ══ (D266)
    # كان يخصم درجةَ ثقةٍ لـ«بنودٍ ناقصة» لأن ثلاثةً منها لم تُطابَق:
    # الربحُ قبل الزكاة (يُشتقّ منه التشغيليُّ بجمع تكلفة التمويل)،
    # وإجماليُّ الدَّين (قروضٌ متداولةٌ وغيرُ متداولة)، وعددُ الأسهم.
    # وأسماؤها هنا **كما وردت في الملفّ الرسميّ المقيس** لا تقريباً.
    "pretax_income": (
        "profit (loss) before zakat and income tax from continuing operations",
        "profit (loss) before tax",
        "profit (loss) before zakat and income tax"),
    "borrowings_current": ("current borrowings", "short-term borrowings",
                           "current portion of long-term borrowings"),
    "borrowings_noncurrent": ("non-current borrowings", "long-term borrowings",
                              "noncurrent borrowings"),
    "lease_current": ("current lease liabilities",),
    "lease_noncurrent": ("non-current lease liabilities",),
    "shares_outstanding": ("number of shares outstanding",
                           "issued capital, number of shares",
                           "weighted average number of ordinary shares outstanding"),
    "operating_cash_flow": (
        "cash flows from (used in) operating activities",
        "net cash flows from (used in) operating activities"),
    "capex": ("purchase of property, plant and equipment",
              "purchase of property, plant and equipment, classified as investing activities"),
    "ending_cash": ("cash and cash equivalents at end of period",
                    "cash and cash equivalents"),
}

_META = {
    "rounding": "level of rounding used in financial statements",
    "period_kind": "period covered by financial statements",
    "audited": "status of report",
}
_MULT = {"thousands": 1_000.0, "millions": 1_000_000.0, "units": 1.0,
         "ones": 1.0, "billions": 1_000_000_000.0}


def _clean(x: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x or "")
                  .replace("&nbsp;", " ").replace("\xa0", " ")).strip()


def _norm(x: str) -> str:
    return re.sub(r"\s+", " ", _clean(x)).strip().lower().rstrip(":")


def _num(x) -> float | None:
    s = str(x or "").replace(",", "").strip()
    if not s or s in ("-", "—", "&nbsp;"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    v = float(m.group(0))
    return -abs(v) if neg else v


def parse(html: str) -> dict:
    """ملفُّ XBRL ← {periods:[…], rounding, kind, audited} — أو فارغ.

    الفتراتُ أعمدةٌ: `End Date` يحمل نهايةَ كلّ عمود، والبنودُ تحته.
    وأوّلُ عمودٍ هو الأحدث (كما في الملفّ المقيس).
    """
    rows: list[list[str]] = []
    for tr in _TR.findall(html or ""):
        cells = [_clean(c) for c in _TD.findall(tr)]
        if any(cells):
            rows.append(cells)
    if not rows:
        return {}

    meta: dict = {}
    ends: list[str] = []
    starts: list[str] = []
    vals: dict[str, list[float | None]] = {}

    def _label_key(lbl: str) -> str | None:
        n = _norm(lbl)
        for key, names in LABELS.items():
            if n in names:
                return key
        return None

    for cells in rows:
        head, rest = _norm(cells[0]), cells[1:]
        for k, name in _META.items():
            if head == name and rest:
                meta.setdefault(k, _clean(rest[0]))
        if head == "end date" and rest and not ends:
            ends = [_clean(x) for x in rest if re.search(r"\d{4}-\d{2}-\d{2}", x)]
        if head == "start date" and rest and not starts:
            starts = [_clean(x) for x in rest if re.search(r"\d{4}-\d{2}-\d{2}", x)]
        key = _label_key(cells[0])
        if key and key not in vals:
            # قِيمُ الصفّ بترتيب أعمدته؛ وما ليس رقماً (مرجعُ إيضاحٍ مثلاً)
            # يسقط — والأعمدةُ تُقصَّ على عدد الفترات لاحقاً.
            vals[key] = [_num(x) for x in rest]

    if not ends:
        return {}
    mult = _MULT.get(_norm(meta.get("rounding", "")), 1.0)
    money = {"revenue", "net_income", "equity", "total_assets",
             "total_liabilities", "interest_expense", "operating_cash_flow",
             "capex", "ending_cash", "pretax_income", "borrowings_current",
             "borrowings_noncurrent", "lease_current", "lease_noncurrent"}
    # وعددُ الأسهم عددٌ لا مال: لا يُضرَب في وحدة التقريب (كربحية السهم).

    periods: list[dict] = []
    for i, end in enumerate(ends):
        p: dict = {"as_of": end, "year": int(end[:4])}
        for key, series in vals.items():
            v = series[i] if i < len(series) else None
            if v is None:
                continue
            p[key] = round(v * mult, 2) if key in money else v
        # نسبةُ المديونية تُشتقّ من بندين مقروءين لا تُنسَخ من مكانٍ آخر.
        ta, tl = p.get("total_assets"), p.get("total_liabilities")
        if ta and tl is not None and ta > 0:
            p["debt_ratio"] = round(tl / ta * 100, 2)
        ocf, capex = p.get("operating_cash_flow"), p.get("capex")
        if ocf is not None and capex is not None:
            p["free_cash_flow"] = round(ocf - abs(capex), 2)
        # ══ مشتقّاتٌ من بنودٍ مقروءةٍ لا من تخمين ══
        # الربحُ التشغيليُّ لا يُنشَر باسمه في هذا التصنيف، ويُشتقّ حسابياً:
        # ربحٌ قبل الزكاة + تكلفةُ التمويل. ولا يُشتقّ إن غاب أحدُهما.
        pre, fin_cost = p.get("pretax_income"), p.get("interest_expense")
        if pre is not None and fin_cost is not None:
            p["ebit"] = round(pre + abs(fin_cost), 2)
        # وإجماليُّ الدَّين مجموعُ ما قُرئ من قروضٍ والتزاماتِ إيجار — وما
        # لم يُقرأ منها لا يُفترَض صفراً: إن غابت كلُّها يبقى الحقلُ غائباً.
        _debt = [p.get(k) for k in ("borrowings_current", "borrowings_noncurrent",
                                    "lease_current", "lease_noncurrent")
                 if isinstance(p.get(k), (int, float))]
        if _debt:
            p["total_debt"] = round(sum(_debt), 2)
        if i < len(starts):
            p["period_start"] = starts[i]
        periods.append(p)

    periods = [p for p in periods if len(p) > 3]        # عمودٌ بلا بندٍ واحدٍ ليس فترة
    periods.sort(key=lambda p: p["as_of"])
    return {"periods": periods, "rounding": meta.get("rounding"),
            "kind": meta.get("period_kind"), "audited": meta.get("audited")}


async def filings_for(symbol: str, company_url: str | None = None) -> list[dict]:
    """روابطُ ملفّات XBRL للشركة، الأحدثُ أوّلاً — أو قائمةٌ فارغة."""
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for
    url = company_url or (row_for(symbol) or {}).get("company_url")
    if not url:
        return []
    status, page = await fetch(ORIGIN + url if url.startswith("/") else url)
    if status != 200 or not page:
        return []
    mb = _BASE.search(page)
    ep = next((m.group(0) for m in _NJ.finditer(page)
               if m.group(1) == "statementsTabData"), None)
    if not (mb and ep):
        return []
    status, body = await fetch(mb.group(1).rstrip("/") + "/" + ep,
                               params={"statementType": "6", "reportType": "1",
                                       "requestLocale": "en"},
                               referer=ORIGIN + url)
    if status != 200:
        return []
    out = []
    for href in re.findall(r"href=[\"']([^\"']+)[\"']", body or ""):
        if "XBRL_DOCS" not in href or not href.endswith(".html"):
            continue
        d = re.search(r"_(\d{4}-\d{2}-\d{2})_", href)
        out.append({"url": href, "filed": d.group(1) if d else None})
    out.sort(key=lambda x: x["filed"] or "", reverse=True)
    return out


async def read_symbol(symbol: str, *, max_files: int = 8) -> dict | None:
    """أحدثُ قوائمَ رسميةٍ للشركة: سنويةٌ وربعية — أو None.

    وتُقرأ ثمانيةُ ملفّاتٍ من الأحدث: الملفُّ يحمل فترتين، وثقةُ الدرجة
    تُحسب من **سنواتٍ متاحة** (خمسٌ = علامةٌ كاملة) ومن اكتمال البنود —
    فثلاثةُ ملفّاتٍ كانت تعطي أربعَ فتراتٍ بالكاد، أي ثقةً محبوسةً دون
    بابها بسببِ قراءةٍ ضيّقةٍ لا بسببِ الشركة (D282). والقراءةُ ليليةٌ لا
    تمسّ زمنَ استجابة الشاشة، وتُلغي خصماً مستحقّاً بدل أن تُسكته.

    تُقرأ ملفّاتٌ قليلةٌ من الأحدث (الملفُّ الواحد ميجاباتٌ عدّة)، ويُفرَز
    كلٌّ إلى سنويٍّ أو ربعيٍّ **بما يقوله الملفُّ عن نفسه** لا بتخمينٍ من
    تاريخه.
    """
    from app.services.tadawul_http import fetch
    files = await filings_for(symbol)
    if not files:
        return None
    annual: list[dict] = []
    quarterly: list[dict] = []
    used: list[dict] = []
    for f in files[:max_files]:
        status, html = await fetch(ORIGIN + f["url"])
        if status != 200 or not html:
            continue
        got = parse(html)
        if not got.get("periods"):
            continue
        kind = _norm(got.get("kind") or "")
        bucket = annual if kind.startswith("annual") else quarterly
        for p in got["periods"]:
            if not any(x["as_of"] == p["as_of"] for x in bucket):
                bucket.append(p)
        used.append({"filed": f["filed"], "kind": got.get("kind"),
                     "audited": got.get("audited"), "rounding": got.get("rounding"),
                     "periods": len(got["periods"])})
    if not (annual or quarterly):
        return None
    annual.sort(key=lambda p: p["as_of"])
    quarterly.sort(key=lambda p: p["as_of"])
    return {"symbol": symbol, "annual": annual, "quarterly": quarterly,
            "files": used, "source": "تداول — XBRL",
            "as_of": datetime.now(timezone.utc).date().isoformat()}


def _store() -> dict:
    from app.services import lastgood
    rec = lastgood.load(STORE_KEY)
    return rec if isinstance(rec, dict) else {}


def save_symbol(symbol: str, rec: dict) -> None:
    from app.services import lastgood
    st = _store()
    st[str(symbol)] = rec
    lastgood.save(STORE_KEY, st)


def for_symbol(symbol, kind: str = "annual") -> list[dict]:
    """فتراتُ الشركة المحفوظة — أو فارغةٌ إن غابت أو شاخ إيداعُها."""
    sym = str(symbol or "").replace(".SR", "").strip()
    rec = _store().get(sym)
    if not isinstance(rec, dict):
        return []
    try:
        age = (date.today() - date.fromisoformat(str(rec.get("as_of")))).days
    except Exception:                                             # noqa: BLE001
        return []
    if age > MAX_AGE_DAYS:
        return []
    rows = rec.get(kind)
    return rows if isinstance(rows, list) else []


async def refresh(symbols: list[str]) -> dict:
    """يقرأ مجموعةَ رموزٍ ويحفظ ما فُهم — ويعيد تقريراً بما دخل وما تعذّر."""
    rep = {"قُرئت": 0, "بلا ملفّات": 0, "لم تُفهم": 0}
    for sym in symbols:
        try:
            rec = await read_symbol(sym)
        except Exception as e:                                    # noqa: BLE001
            logger.debug("XBRL {}: {}", sym, e)
            rec = None
        if rec is None:
            rep["بلا ملفّات"] += 1
            continue
        if not (rec.get("annual") or rec.get("quarterly")):
            rep["لم تُفهم"] += 1
            continue
        save_symbol(sym, rec)
        rep["قُرئت"] += 1
    logger.info("XBRL: {}", rep)
    return rep
