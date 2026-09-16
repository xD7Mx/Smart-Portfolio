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

import asyncio
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
    # ══ أسماءٌ أُضيفت **بالحرف** من ملفّات المالك ══ (D335)
    # قِيس بأداة `xbrl_labels.py` على أربع شركاتٍ (‏2222 · 2030 · 2060 ·
    # 2310): بنودٌ مطلوبةٌ موجودةٌ في الملفّ الرسميّ بأسماءٍ لم تكن في
    # خريطتنا. وأخطرُ ما كشفه القياس: **دَينُ أرامكو المحفوظُ ٨٫٢ مليار**
    # وملفُّها يقول `borrowings - current 46,871` + `non-current 308,365`
    # (أي ٣٥٥ مليار بالمليون) — فنسبةُ المديونية في الحوكمة كانت تُحسب
    # على جزءٍ من الدَّين. والأسماءُ أدناه منقولةٌ من المخرَج لا مجتهَدة.
    "revenue": ("total revenue", "revenue", "total revenues",
                "revenue from contracts with customers", "external revenue",
                # ══ ولغةُ البنك تُنقَل كما نُشرت ══ (D372)
                # قِيس على خادم المالك: `revenue` غائبٌ في **ثلاثةِ بنوكٍ
                # من ثلاثة**، وقائمةُ البنك لا تحمل كلمةَ «إيراد» أصلاً.
                # وفي ملفّ 1010 صفٌّ منشورٌ بهذا الاسم = 6,938,847 — وهو
                # دخلُه الإجماليُّ من التمويل والاستثمار. منقولٌ بالحرف.
                # وهو دخلُ العمولة والتمويل: لا يشمل أتعابَ الخدمات، فهو
                # **أدنى حدٍّ منشورٍ** لا تقديرٌ أعلى منه.
                "special commission income/ gross financing and investment income"),
    # ودخلُ العمولة **الصافي** يُقرأ مفتاحاً مساعداً لا إيراداً ولا
    # مصروفاً: منه وحدَه تُشتقّ تكلفةُ تمويلِ البنك بهويّةٍ حسابية.
    "_commission_net": (
        "special commission income (expense)/ financing and investment"
        " income (expense), net",),
    "net_income": ("profit (loss) for period", "profit (loss)",
                   "profit (loss) for the period",
                   "profit (loss), attributable to equity holders of parent company"),
    # وحقوقُ الملكية بصياغات القطاعات كما قِيست: البنكُ والشركةُ والأمُّ.
    "equity": ("total equity", "equity attributable to owners of parent",
               "total equity attributable to owners of parent",
               "total equity attributable to equity holders of company",
               "total equity attributable to equity holders of bank",
               "equity attributable to shareholders of the bank",
               "total equity attribute to shareholder of the parent company",
               # ونُقل من مخرَج السلع الرأسمالية (‏1212 · 1214 · 1302):
               # صفٌّ منشورٌ بهذا الاسم. و«total equity and liabilities»
               # الذي ظهر في الإعلام **لا يُنقَل**: مجموعُ طرفِ الميزانية
               # كلِّه لا حقوقُ الملكية — واسمٌ شبيهٌ لا يُلبَّس معنىً.
               "equity attributable to shareholders of the company"),
    "total_assets": ("total assets",),
    "total_liabilities": ("total liabilities",),
    "eps": ("total basic earnings (loss) per share",
            "basic earnings (loss) per share from continuing operations"),
    # ══ وتكلفةُ التمويل باسمها في صفّ التسوية ══ (D344)
    # قِيس على خادم المالك: `interest_expense` يغيب في ٣٤ ورقةً من ٩٠،
    # ويسقط معه `ebit` لأنه يُشتقّ منه. وفي الملفّات نفسِها **صفٌّ منشورٌ**
    # اسمُه `adjustments for finance costs` (‏2030 = 11,984 · 4334 =
    # 779,941) — تكلفةُ تمويلِ الفترة تُردّ في تسوية التدفّق التشغيليّ.
    # منقولٌ بالحرف من المخرَج لا مجتهَداً.
    "interest_expense": ("finance costs", "adjustments for finance costs"),
    # ══ بنودٌ يطلبها محرّكُ التدفّقات ولا يقوم بدونها ══ (D266)
    # كان يخصم درجةَ ثقةٍ لـ«بنودٍ ناقصة» لأن ثلاثةً منها لم تُطابَق:
    # الربحُ قبل الزكاة (يُشتقّ منه التشغيليُّ بجمع تكلفة التمويل)،
    # وإجماليُّ الدَّين (قروضٌ متداولةٌ وغيرُ متداولة)، وعددُ الأسهم.
    # وأسماؤها هنا **كما وردت في الملفّ الرسميّ المقيس** لا تقريباً.
    "pretax_income": (
        "profit (loss) before zakat and income tax from continuing operations",
        # وترتيبُ الكلمات يختلف في ملفّات البنوك — والمطابقةُ بالنصّ لا
        # بالمعنى، فاسمٌ بترتيبٍ آخرَ اسمٌ آخر (‏1010 = 2,982,516 ·
        # 1080 = 1,679,073). منقولٌ بالحرف (D344).
        "profit (loss) from continuing operations before zakat and income tax",
        "profit (loss) before tax",
        "profit (loss) before zakat and income tax",
        "profit (loss) for period before zakat and income tax",
        "income before income taxes and zakat",
        # ══ ولغةُ التأمين تُنقَل كما نُشرت ══ (D372)
        # قِيس بمسح القطاعات الثلاثةِ على خادم المالك: `pretax_income`
        # غائبٌ في **ثلاثِ شركاتِ تأمينٍ من ثلاث** (‏8010 · 8012 · 8020)،
        # وفي ملفّاتها نفسِها صفّانِ منشوران بهذَين الاسمَين. والمؤمِّنُ
        # مُلزَمٌ بالإفصاح كغيره، فغيابُ البند كان عجزَ خريطةٍ لا نقصَ
        # سوق. منقولٌ بالحرف من المخرَج لا مجتهَداً.
        "income (loss) from continuing operations before zakat and income tax",
        "net profit (loss) for period (before zakat expenses and income tax)"),
    "borrowings_current": ("current borrowings", "short-term borrowings",
                           "current portion of long-term borrowings",
                           "borrowings - current",
                           "current portion of long term loans",
                           "short term borrowings",
                           "loans and borrowings", "borrowings",
                           "unsecured bank loans"),
    "borrowings_noncurrent": ("non-current borrowings", "long-term borrowings",
                              "noncurrent borrowings",
                              "borrowings - non-current",
                              "debt securities, term loans, borrowings and sukuks in issue",
                              # والمفردُ والجمعُ اسمانِ لا اسم: ملفُّنا
                              # المقيسُ يقول «term loan» و«sukuk» مفردَين
                              # (‏1010 = 47,583,268 · 1080 = 461,499)،
                              # فكان الفرقُ حرفَين يحجب الدَّينَ (D344).
                              "debt securities, term loan, borrowings and sukuk in issue"),
    "lease_current": ("current lease liabilities", "finance lease, current"),
    "lease_noncurrent": ("non-current lease liabilities",
                         "finance leases, non-current"),
    # ══ أسماءٌ من المسح الشامل لثلاثةٍ وعشرين قطاعاً ══ (D338)
    # قِيس: «عددُ الأسهم» ينقص في **كلّ** القطاعات تقريباً، وكلُّها تنشره
    # بصيغة «weighted average number of equity shares outstanding» وما
    # يشبهها — ولم تكن في الخريطة. والصياغاتُ أدناه منقولةٌ من المخرَج.
    "shares_outstanding": ("number of shares outstanding",
                           "issued capital, number of shares",
                           "weighted average number of ordinary shares outstanding",
                           "weighted average number of equity shares outstanding",
                           "weighted average number of ordinary shares",
                           "weighted average number of shares outstanding",
                           "weighted average outstanding number of shares",
                           "weighted average number of shares",
                           "average number of shares outstanding during the period",
                           "weighted average number of ordinary shares outstanding (for basic eps)",
                           "weighted average number of outstanding shares"),
    "operating_cash_flow": (
        "cash flows from (used in) operating activities",
        "net cash flows from (used in) operating activities"),
    # والمصروفُ الرأسماليُّ في ملفّ أرامكو «capital expenditures = -94,743»
    # وفي الطاقة «capital expenditures - cash basis»، والبنوكُ والتأمينُ
    # «purchase of property and equipment» — ثلاثُ صياغاتٍ مقيسةٌ لبندٍ
    # واحدٍ هو بابُ مسار التدفّق الحرّ (D338). و«additions» تُترك: عامّةٌ
    # تصلح لأصولٍ غير رأسمالية، فإضافتُها تخمينٌ لا نقل.
    "capex": ("purchase of property, plant and equipment",
              "purchase of property, plant and equipment, classified as investing activities",
              "capital expenditures",
              "capital expenditures - cash basis",
              "purchase of property and equipment",
              "purchase of property and equipment, insurance/ takaful operations cash flow"),
    "ending_cash": ("cash and cash equivalents at end of period",
                    "cash and cash equivalents", "bank balances and cash"),
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
             "borrowings_noncurrent", "lease_current", "lease_noncurrent",
             "_commission_net"}
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
        # ══ تكلفةُ تمويلِ البنك بهويّةٍ حسابيةٍ لا باسمٍ شبيه ══ (D372)
        # المزلقُ الذي كاد يوقعني: صفُّ «... net = 3,376,189» في ملفّ 1010
        # **دخلٌ صافٍ لا مصروف**، وربطُه بـ`interest_expense` يُدخل
        # مصروفاً وهميّاً ويقلب الربحَ التشغيليّ. والمصروفُ لا يُنشَر
        # مستقلّاً في هذا التصنيف، ويُشتقّ بفرقٍ لا لبسَ فيه:
        #     مصروفُ العمولة = الدخلُ الإجماليُّ − الدخلُ الصافي
        # (‏1010: 6,938,847 − 3,376,189 = 3,562,658). وهو طرحٌ من رقمَين
        # منشورَين، لا تقريبٌ ولا اجتهادٌ في معنى اسم.
        _gross, _net = p.get("revenue"), p.get("_commission_net")
        if (p.get("interest_expense") is None
                and isinstance(_gross, (int, float))
                and isinstance(_net, (int, float))
                and _gross > _net > 0):
            p["interest_expense"] = round(_gross - _net, 2)
            p["interest_expense_derived"] = "إجماليُّ دخلِ العمولة − صافيه"
        p.pop("_commission_net", None)
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
        # ══ عددُ الأسهم يُشتقّ من رقمَين منشورَين ══ (D335)
        # قِيس أن البنودَ لا تحمل «عدد الأسهم» في أيٍّ من الملفّات الأربعة
        # المقروءة، وتحمل **صافي الربح وربحيةَ السهم** معاً. والقسمةُ
        # بينهما عددُ الأسهم المرجَّح بتعريفه (‏EPS = الربح ÷ الأسهم) —
        # حسابٌ على منشورٍ لا اختلاق. ولا يُشتقّ من «رأس المال» لأن
        # القيمةَ الاسمية تختلف بين الشركات فيصير الرقمُ ظنّاً.
        # ويُوسَم `shares_source` كي لا يُقرأ منشوراً وهو مشتقّ.
        _ni, _eps = p.get("net_income"), p.get("eps")
        if (p.get("shares_outstanding") is None and _ni is not None
                and isinstance(_eps, (int, float)) and abs(_eps) > 1e-9):
            _sh = _ni / _eps
            if _sh > 0:
                p["shares_outstanding"] = round(_sh, 0)
                p["shares_source"] = "مشتقٌّ: صافي الربح ÷ ربحية السهم"
        if i < len(starts):
            p["period_start"] = starts[i]
        periods.append(p)

    periods = [p for p in periods if len(p) > 3]        # عمودٌ بلا بندٍ واحدٍ ليس فترة
    periods.sort(key=lambda p: p["as_of"])
    return {"periods": periods, "rounding": meta.get("rounding"),
            "kind": meta.get("period_kind"), "audited": meta.get("audited")}


async def filings_for_ex(symbol: str,
                         company_url: str | None = None) -> tuple[list[dict], str | None]:
    """روابطُ ملفّات XBRL **ومعها سببُ الفراغ** إن كان (D362).

    ══ لماذا سببٌ لا قائمةٌ فارغةٌ فقط ══
    قِيس على خادم المالك: الحصادُ ردّ «بلا ملفّات: ‎82» ثلاثَ مرّاتٍ
    متطابقةً، وبعد أن فصّلتُ مراحلَ **تحميل الملفّات** جاء «تعذّرَ
    تحميلها: ‎0» — أي أنّي وضعتُ المِقياسَ في المرحلة الخطأ، والمنعُ قبله
    في هذه الدالّة. وكانت تعود فارغةً من **أربعة مواضعَ** بلا أثر: لا
    رابطَ · صفحةٌ لا تُقرأ · لا خدمةَ في الصفحة · نداءٌ لا يُجيب. وكاشفٌ
    خارجيٌّ (‏`filings_door.py`) أثبت أن ‎37 من ‎40 من هذه الأوراق لها
    **18 ملفّاً** فعلاً — فالمنعُ عندنا، وبلا سببٍ مطبوعٍ لا يُعرَف أينَ.
    """
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for
    url = company_url or (row_for(symbol) or {}).get("company_url")
    if not url:
        return [], "لا رابطَ لصفحة الشركة في اللقطة"
    full = ORIGIN + url if url.startswith("/") else url
    status, page = await fetch(full)
    if status != 200 or not page:
        # محاولةٌ ثانيةٌ: الصفحةُ ستّمئة كيلوبايت والقراءةُ متزامنة.
        await asyncio.sleep(1.5)
        status, page = await fetch(full)
    if status != 200 or not page:
        return [], f"صفحةُ الشركة HTTP {status}"
    mb = _BASE.search(page)
    ep = next((m.group(0) for m in _NJ.finditer(page)
               if m.group(1) == "statementsTabData"), None)
    if not mb:
        return [], "صفحةُ الشركة بلا <base>"
    if not ep:
        return [], "لا خدمةَ statementsTabData في الصفحة"
    status, body = await fetch(mb.group(1).rstrip("/") + "/" + ep,
                               params={"statementType": "6", "reportType": "1",
                                       "requestLocale": "en"},
                               referer=full)
    if status != 200:
        await asyncio.sleep(1.5)
        status, body = await fetch(mb.group(1).rstrip("/") + "/" + ep,
                                   params={"statementType": "6",
                                           "reportType": "1",
                                           "requestLocale": "en"},
                                   referer=full)
    if status != 200:
        return [], f"نداءُ قائمةِ الملفّات HTTP {status}"
    out = []
    for href in re.findall(r"href=[\"']([^\"']+)[\"']", body or ""):
        if "XBRL_DOCS" not in href or not href.endswith(".html"):
            continue
        d = re.search(r"_(\d{4}-\d{2}-\d{2})_", href)
        out.append({"url": href, "filed": d.group(1) if d else None})
    out.sort(key=lambda x: x["filed"] or "", reverse=True)
    return out, (None if out else "القائمةُ تُجيب ولا ملفَّ XBRL فيها")


async def filings_for(symbol: str, company_url: str | None = None) -> list[dict]:
    """الواجهةُ القديمةُ كما هي — لئلّا ينكسر نداءٌ قائم."""
    files, _ = await filings_for_ex(symbol, company_url)
    return files


def withhold_unsafe(symbol, periods: list[dict]) -> int:
    """يسحب كلَّ بندٍ قِيس أن مطابقتَه خاطئةٌ في صنف الورقة — ويُعلن سببَه.

    ولا يُترك رقمٌ خاطئٌ يُقدَّم لأن الفراغَ يُكره: الفراغُ المعلَنُ يقول
    «لا أعرف» وهو صادق، والرقمُ الخاطئُ يقول «أعرف» وهو كاذب — ويُحسَب
    فيه هامشُ الربح والعائدُ والسعرُ العادل ولا يشتكي أحد. تُعاد عدّةُ
    ما سُحب.
    """
    if _arch_of(symbol) != "insurance":
        return 0
    n = 0
    for p in periods or []:
        if p.pop("revenue", None) is not None:
            n += 1
            p["revenue_withheld"] = (
                "إجماليُّ إيرادِ المؤمِّن يُنشَر في قائمتَين متوازيتَين"
                " (عملياتُ تأمينٍ · مساهمون)، وما طابَق كان شطرَ"
                " المساهمين — فلا يُقدَّم رقمٌ حتى يُنقَل اسمُ الأقساط")
    return n


def _arch_of(symbol) -> str | None:
    """نمطُ الورقة من مسطرة الأنماط — أو لا شيء (لا مسطرةَ ثانية)."""
    try:
        from app.data.archetype_spec import archetype_for
        from app.data.market_universe import MARKET_UNIVERSE
    except Exception:                                             # noqa: BLE001
        return None
    b = str(symbol or "").replace(".SR", "").strip()
    meta = MARKET_UNIVERSE.get(b) or MARKET_UNIVERSE.get(f"{b}.SR") or {}
    return archetype_for((meta or {}).get("sector"))


async def read_symbol(symbol: str, *, max_files: int = 8,
                      reasons: dict | None = None) -> dict | None:
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
    files, why = await filings_for_ex(symbol)
    if not files:
        # السببُ يُسجَّل حيث يقع — فالحاصدُ يطبعه مصنَّفاً (D362)
        if reasons is not None and why:
            reasons[why] = reasons.get(why, 0) + 1
        return None
    annual: list[dict] = []
    quarterly: list[dict] = []
    used: list[dict] = []
    # ══ ويُفصَل تعذّرُ التحميل عن تعذّرِ الفهم ══ (D360)
    # قِيس على خادم المالك بالكاشف `filings_door.py`: **37 من 40** ورقةً
    # قيل فيها «بلا ملفّات» لها **18 ملفّاً** فعلاً. والسببُ أن في هذه
    # الدالّة موضعَين يعودان بـ`None`، و`refresh` تعدّهما معاً «بلا
    # ملفّات»: أحدُهما لا قائمةَ له، والآخرُ **قائمتُه موجودةٌ ولم يُحمَّل
    # منها ملفّ**. فالعبارةُ تكذب على المالك وتُخفي موضعَ العطب.
    http_fail = 0
    parse_fail = 0
    for f in files[:max_files]:
        status, html = await fetch(ORIGIN + f["url"])
        if status != 200 or not html:
            # ومحاولةٌ ثانيةٌ بمهلةٍ قصيرة: الملفُّ ميجاباتٌ عدّة والقراءةُ
            # متزامنة، فتعذّرٌ عارضٌ أرجحُ من ملفٍّ معطوب. ولا ثالثةَ —
            # فالإلحاحُ على مصدرٍ يمنع ليس أدباً.
            await asyncio.sleep(1.5)
            status, html = await fetch(ORIGIN + f["url"])
        if status != 200 or not html:
            http_fail += 1
            continue
        got = parse(html)
        if not got.get("periods"):
            parse_fail += 1
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
        # قائمةُ الملفّات موجودةٌ — فيُعاد سجلٌّ فارغٌ **يحمل سببَه**، ولا
        # يُقال «بلا ملفّات» لشركةٍ أودعت (D360).
        return {"symbol": symbol, "annual": [], "quarterly": [],
                "files": len(files), "http_fail": http_fail,
                "parse_fail": parse_fail,
                "as_of": date.today().isoformat()}
    # ══ ورقمٌ مطابَقٌ خطأً أسوأُ من فراغٍ معلَن ══ (D374)
    #
    # قِيس على خادم المالك: `revenue` لـ8010 = 24,332,000 وأقساطُها
    # بالمليارات. وطباعةُ **المطابَق** كشفت السبب: الاسمُ الذي طابق
    # `«total revenue»` صحيحُ الظاهر، لكنّ **قائمةَ المؤمِّن قائمتان
    # متوازيتان** — عملياتُ تأمينٍ وعملياتُ مساهمين — وقارئُنا يأخذ أوّلَ
    # عمودٍ يجده. والدليلُ في المخرَج نفسِه: `ending_cash` طابَق مرّتَين
    # (‏1,606,362 لعمليات التأمين · 52,981 للمساهمين). فـ«إجماليُّ
    # الإيراد» في شطر المساهمين دخلُ استثمارٍ لا أقساطاً.
    #
    # والمالكُ يحارب الفراغ — وأنا معه — لكنّ الفراغَ المعلَنَ يقول «لا
    # أعرف» وهو صادق، والرقمُ الخاطئُ يقول «أعرف» وهو كاذب: يُحسَب فيه
    # هامشُ الربح والعائدُ على الأصول والسعرُ العادل ولا يشتكي أحد. فإلى
    # أن يُنقَل اسمُ إيراد المؤمِّن بالحرف من شطره الصحيح، **يُسحَب**
    # ويُعلَن سببُه — ولا يُقدَّم.
    withhold_unsafe(symbol, annual + quarterly)
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


async def refresh(symbols: list[str], conc: int = 4) -> dict:
    """يقرأ مجموعةَ رموزٍ ويحفظ ما فُهم — ويعيد تقريراً بما دخل وما تعذّر.

    ══ وشرطٌ مفقودٌ لا يُقال «بلا ملفّات» ══ (D337)
    قِيس على خادم المالك: `refresh` بعد إعادة تشغيلٍ ردّ **«بلا ملفّات:
    ١٠»** لعشرِ شركاتٍ لكلٍّ منها ثمانيةَ عشرَ ملفّاً رسميّاً. والسببُ
    أن رابطَ صفحة الشركة يُقرأ من **لقطة السوق**، وكانت فارغةً بعد
    الإقلاع — فالرسالةُ تصف نتيجةً وسببُها آخر. فتُملأ اللقطةُ أوّلاً إن
    غابت، ويُفصَل «لا لقطة» عن «لا ملفّات» في التقرير.
    """
    rep = {"قُرئت": 0, "بلا ملفّات": 0, "ملفّاتٌ تعذّرَ تحميلها": 0,
           "لم تُفهم": 0, "بلا لقطةٍ للسوق": 0}
    why_empty: dict[str, int] = {}      # سببُ «بلا ملفّات» مصنَّفاً (D362)
    try:
        from app.services.tadawul_market import refresh as _mkt
        from app.services.tadawul_market import usable_rows
        if not (usable_rows()[0] or {}):
            logger.info("XBRL: لقطةُ السوق فارغةٌ — تُقرأ أوّلاً لأخذ روابط"
                        " صفحات الشركات")
            await _mkt()
        _snap = usable_rows()[0] or {}
    except Exception as e:                                        # noqa: BLE001
        logger.warning("XBRL: تعذّر تحضيرُ لقطة السوق: {}", type(e).__name__)
        _snap = {}
    # ══ والحصادُ يجري بتزامنٍ محدود ══ (D354)
    # قِيس على خادم المالك: حصادُ ستّين ورقةً استغرق **569 ثانية** —
    # ‎9.5 ثانيةً للورقة، لأن الحلقةَ كانت `for` بـ`await` داخلَها: تنتظر
    # كلَّ ملفٍّ قبل أن تطلب التالي. فحصادُ اللقطة كلِّها (‏272) ثلاثٌ
    # وأربعون دقيقةً من الانتظار على شاشة المالك — وهو عطبٌ لا قانونُ
    # طبيعة: أداةُ المسح تقرأ ‎409 صفحةً في نحو أربع دقائقَ بتزامنِ ستّة.
    #
    # والسقفُ **محدودٌ قصداً**: كلُّ ورقةٍ ملفٌّ مستقلٌّ (لا نداءٌ متكرّرٌ
    # لبابٍ واحدٍ فيقع تحت إيقاع المصدر)، لكنّ الأدبَ مع المصدر يقتضي
    # ألا نفتح عليه عشراتَ الوصلات. فأربعٌ افتراضاً، ولم أقِس عتبةَ
    # خنقٍ عنده — فلا أدّعي أنّ أكثرَ منها آمن.
    import asyncio as _aio

    sem = _aio.Semaphore(max(1, min(8, int(conc or 4))))
    lock = _aio.Lock()

    async def _one(sym) -> None:
        _b = str(sym).replace(".SR", "").strip()
        if _snap and not (_snap.get(_b) or {}).get("company_url"):
            # لا رابطَ لصفحة هذه الشركة في اللقطة: سببٌ يُقال باسمه.
            async with lock:
                rep["بلا لقطةٍ للسوق"] += 1
            return
        async with sem:
            try:
                rec = await read_symbol(sym, reasons=why_empty)
            except Exception as e:                                # noqa: BLE001
                logger.debug("XBRL {}: {}", sym, e)
                rec = None
        async with lock:
            if rec is None:
                rep["بلا ملفّات"] += 1
            elif not (rec.get("annual") or rec.get("quarterly")):
                # ملفّاتٌ موجودةٌ ولم تُقرأ: تعذّرُ تحميلٍ أم تعذّرُ فهم؟
                if rec.get("http_fail"):
                    rep["ملفّاتٌ تعذّرَ تحميلها"] += 1
                else:
                    rep["لم تُفهم"] += 1
            else:
                save_symbol(sym, rec)
                rep["قُرئت"] += 1
            _n = sum(rep.values())
            if _n % 25 == 0:
                logger.info("XBRL: {} من {}", _n, len(symbols))

    await _aio.gather(*(_one(s) for s in symbols), return_exceptions=True)
    logger.info("XBRL: {}", rep)
    if why_empty:
        logger.info("XBRL · سببُ «بلا ملفّات»: {}", why_empty)
        rep["تفصيلُ بلا ملفّات"] = dict(
            sorted(why_empty.items(), key=lambda kv: -kv[1]))
    return rep
