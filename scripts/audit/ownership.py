#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D270 — هيكلُ الملكية بالمتصفّح: اكتشافٌ لا مسارٌ محفوظ، وجهلٌ لا يُملأ.
#
# أربعةُ بنودٍ قِيست مرسومةً بجافاسكربت (‏200 وصفرُ صفوف) فلا يبلغها انتحالُ
# البصمة. والمتصفّحُ يبلغها، ويجلب معه ثلاثةَ أخطار:
#
#   ٠· **مسارٌ محفوظٌ يصمت يومَ يدور** — فتُقرأ الروابطُ بأسمائها العربية
#   ١· **رقمٌ بلا علامة نسبةٍ يُقرأ نسبةً** — فلا يُقرأ إلا ما فُهم
#   ٢· **صفٌّ لم يُفهَم يُصفَّر** — بل يُترك، والبندُ الفارغُ يغيب
#   ٣· وغيابُ المتصفّح **يُقال باسمه** لا يُخلَط بغياب البيانات
#   ٤· وقراءةٌ شائخةٌ لا تُقرأ حاضراً
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import datetime as _dt  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.services import lastgood, ownership as ow  # noqa: E402

BASE = "https://www.argaam.com"

# ══ الصفحةُ كما قِيست فعلاً (بنك الرياض · معرِّف 47) ══
# الأسماءُ والمسارات منسوخةٌ من مخرَج المسبار على الخادم، لا مؤلَّفة.
# وفيها فخُّها: روابطُ سوقٍ عامّةٌ بالأسماء نفسِها بلا معرِّف شركة.
HOME = """<html><body>
 <a href="/ar/monitors/market-ownership/3">ملكية المستثمرين الأجانب</a>
 <a href="/ar/shareholder/shareholders-history/date/marketid/3">قائمة كبار الملاك</a>
 <a href="/ar/shareholder/shareholders-history-deals?marketid=3&amp;pageno=1">الصفقات الخاصة</a>
 <a href="/ar/monitors/analyst-estimates">توقعات المحللين</a>
 <a href="/ar/shareholder/major-shareholders/company/marketid/3/companyid/47/بنك-الرياض">كبار المساهمين</a>
 <a href="/ar/company/foreignownershipdetails/marketid/3/companyid/47/بنك-الرياض">ملكية الأجانب</a>
 <a href="/ar/shareholder/major-shareholders/company-deals/marketid/3/companyid/47/بنك-الرياض">الصفقات الخاصة</a>
 <a href="/ar/analystestimates/analystrecomendationsestimate/3/47/4">توصيات المحللين</a>
</body></html>"""

# ── ٠ · الروابطُ تُكتشَف بمسارها، والسوقُ لا يُعرَض تحت اسم شركة ──────────
links = ow.tab_links(HOME, BASE, company_id="47")
check(set(links) == set(ow.TABS),
      "٠ البنودُ الأربعةُ تُكتشَف بأسمائها ومساراتها كما وردت",
      str(sorted(links)))
check("/companyid/47/" in links["major_holders"]
      and links["major_holders"].startswith(BASE),
      "٠ب ويُكمَّل أصلُ الرابط", links["major_holders"][-40:])
check("shareholders-history-deals" not in links["insider_deals"]
      and "company-deals" in links["insider_deals"],
      "٠ج ورابطُ السوق العامُّ لا يُؤخذ للشركة — رقمٌ صحيحٌ في مكانٍ خاطئ "
      "أسوأُ من الغياب", links["insider_deals"][-45:])
check("monitors/market-ownership" not in links["foreign"],
      "٠د ولا «ملكية المستثمرين الأجانب» للسوق بدل ملكية الشركة",
      links["foreign"][-45:])

# ويومَ يدور المسار: النصُّ سندٌ ثانٍ فيُكتشَف الرابطُ الجديد.
moved = HOME.replace("/ar/shareholder/major-shareholders/company/marketid/3/companyid/47/بنك-الرياض",
                     "/ar/co/v2/holders/3/47")
check(ow.tab_links(moved, BASE, company_id="47").get("major_holders", "").endswith("/47"),
      "٠ه ومسارٌ دار يُلتقَط بنصِّه — لا يصمت الصفُّ بلا سبب")
check(not ow.tab_links("<a href='/x'>أخبار الشركة</a>", BASE, company_id="47"),
      "٠و وتبويبٌ ليس منها لا يُلتقَط بالتقريب")

# ── ١ · ٢ · لا يُقرأ إلا ما فُهم ────────────────────────────────────────
PAGE = """<table>
 <tr><th>المساهم</th><th>النسبة</th></tr>
 <tr><td>صندوق الاستثمارات العامة</td><td>70.00%</td></tr>
 <tr><td>المؤسسة العامة للتأمينات</td><td>9.5 %</td></tr>
 <tr><td>مساهمٌ بلا نسبة</td><td>—</td></tr>
 <tr><td>سطرٌ برقمٍ لا نسبة</td><td>1,240,000</td></tr>
</table>"""
rows = ow.parse(PAGE)
check([r["name"] for r in rows] == ["صندوق الاستثمارات العامة",
                                    "المؤسسة العامة للتأمينات"]
      and rows[0]["percent"] == 70.0 and rows[1]["percent"] == 9.5,
      "١ النسبةُ تُقرأ بعلامتها، ورقمٌ بلا علامةٍ ليس نسبة", str(rows))
check(all(r["percent"] is not None for r in rows),
      "٢ وصفٌّ لم يُفهَم يُترك — لا يُصفَّر ولا يُملأ بشبيهه")
check(ow.parse("<html>لا جدول</html>") == [],
      "٢ب وصفحةٌ بلا جدولٍ تعود فارغةً لا مختلَقة")
check(ow._pct("120%") is None and ow._pct("-3.2%") == -3.2,
      "٢ج ونسبةٌ خارج المعقول ليست نسبة", str(ow._pct("120%")))

# وأوسعُ جدولٍ يفوز: صفحةٌ فيها جدولُ تنقّلٍ صغيرٌ لا يُقرأ بدل الجدول.
NAV = "<table><tr><td>القطاع</td><td>50%</td></tr></table>" + PAGE
check(len(ow.parse(NAV)) == 2, "٢د وجدولُ الزينة لا يُقرأ بدل جدول المحتوى")

# ── ٢ه · ولا `<table>` في «أرقام» أصلاً ─────────────────────────────────
# قِيس: 0 جداولَ في 509 ألفَ حرف. فقارئُ الجداول وحدَه يعود صفراً دائماً،
# وصفرٌ مطلقٌ علامةُ قارئٍ في المكان الخطأ لا مصدرٍ فارغ (درسُ D257).
DIVS = """<div class="holder-full lh-norm">
   <div class="name">صندوق الاستثمارات العامة</div><div class="pct">37.50%</div></div>
 <div class="holder-full lh-norm">
   <div class="name">المؤسسة العامة للتأمينات الاجتماعية</div><div class="pct">9.14 %</div></div>
 <div class="holder-full lh-norm">
   <div class="name">مساهمٌ بلا نسبة</div><div class="pct">—</div></div>
 <div class="footer">جميع الحقوق محفوظة 2026</div>"""
dv = ow.parse(DIVS)
check([r["name"] for r in dv] == ["صندوق الاستثمارات العامة",
                                  "المؤسسة العامة للتأمينات الاجتماعية"]
      and dv[0]["percent"] == 37.5,
      "٢ه وصفوفُ الحاويات تُقرأ حين لا جدولَ في الصفحة", str(dv))
check(all(r["name"] != "جميع الحقوق محفوظة 2026" for r in dv),
      "٢و وكتلةٌ بلا نسبةٍ ليست صفَّ مساهم")
check(len({r["name"] for r in dv}) == len(dv),
      "٢ز ولا يتكرّر مساهمٌ من تداخل الحاويات")

# ── ٣ · غيابُ المتصفّح يُقال باسمه ───────────────────────────────────────
import app.services.browser_fetch as bf  # noqa: E402
import app.services.argaam_calendar as ac  # noqa: E402


# معرِّفُ «أرقام» لبنك الرياض كما ردّه الخادم — لا رقمٌ من عندي.
async def _cid(sym, *a, **k):
    return "47"


ac._company_id = _cid                                            # type: ignore[assignment]


async def _boom(*a, **k):
    raise bf.BrowserUnavailable("playwright غير مركَّبة")


bf.render = _boom                                                # type: ignore[assignment]
res = asyncio.run(ow.refresh("1010"))
check("المتصفّح" in str(res.get("error") or ""),
      "٣ غيابُ المتصفّح حالةٌ باسمها لا «لا بيانات»", str(res)[:70])
check(ow.reading("1010") is None,
      "٣ب ولا يُكتب شيءٌ حين لا يُقرأ شيء")

# ── ٤ · المسارُ الكامل، ثمّ الشيخوخة ─────────────────────────────────────
async def _render(urls, **k):
    return {u: (HOME if "companyoverview" in u else PAGE) for u in urls}


bf.render = _render                                              # type: ignore[assignment]
res = asyncio.run(ow.refresh("1010"))
rec = ow.reading("1010") or {}
check(res.get("ok") and len(rec.get("major_holders") or []) == 2
      and rec.get("urls", {}).get("foreign", "").startswith(BASE),
      "٤ والمسارُ الكامل يحفظ ما قُرئ برابطه وتاريخه", str(res)[:80])

empty = {"error": None}


async def _render_blank(urls, **k):
    return {u: (HOME if "companyoverview" in u else "<html></html>") for u in urls}


bf.render = _render_blank                                        # type: ignore[assignment]
res2 = asyncio.run(ow.refresh("2010"))
check(not res2.get("ok") and ow.reading("2010") is None,
      "٤ب وتبويباتٌ فُتحت بلا صفٍّ مفهومٍ ليست نجاحاً", str(res2)[:70])

rec["as_of"] = (_dt.date.today()
                - _dt.timedelta(days=ow.MAX_AGE_DAYS + 2)).isoformat()
lastgood.save(ow.STORE_KEY.format(sym="1010"), rec)
check(ow.reading("1010") is None,
      f"٤ج وقراءةٌ أقدمُ من {ow.MAX_AGE_DAYS} يوماً لا تُقرأ حاضراً")

# ── ٥ · متصفّحٌ واحدٌ في الصورة لا اثنان ─────────────────────────────────
kw = bf._launch_kwargs()
check("--no-sandbox" in kw["args"],
      "٥ الإقلاعُ بلا صندوقٍ رمليّ — شرطُ كروميوم داخل حاوية")
dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
check("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1" in dockerfile
      and "chromium" in dockerfile,
      "٥ب ولا يُنزَّل متصفّحٌ ثانٍ لمعنًى واحد — كروميومُ الصورة نفسُه")

# ── ٦ · بطاقةٌ واحدةٌ تعرض ما قُرئ، والتطبيقُ يقيس نفسَه ────────────────
# دُرتُ ثلاثَ جولاتِ مسبارٍ بلا ميزةٍ تصل المالك. فالقياسُ ينتقل إلى
# التطبيق: وظيفةٌ أسبوعيةٌ تقرأ وتسجّل التغطيةَ في السجلّ.
SCH = (ROOT / "backend" / "app" / "scheduler" / "scheduler.py").read_text(encoding="utf-8")
check("job_ownership" in SCH and 'id="ownership_weekly"' in SCH,
      "٦ القراءةُ مجدوَلةٌ — لا دالّةٌ لا يستدعيها أحد")
check("ownership:coverage" in SCH,
      "٦ب والتغطيةُ تُسجَّل فتُعرَف بلا مسبارٍ رابع")

MK = (ROOT / "backend" / "app" / "api" / "v1" / "endpoints"
      / "market.py").read_text(encoding="utf-8")
check("from app.services.ownership import reading" in MK,
      "٦ج والبابُ القائمُ يحمل القراءةَ — لا مسارٌ ثانٍ لمعنًى واحد")

CARD = (ROOT / "frontend" / "src" / "components" / "analysis"
        / "OwnershipBar.tsx").read_text(encoding="utf-8")
check("major_holders" in CARD and CARD.count(">هيكل الملكية<") == 1,
      "٦د والبطاقةُ واحدةٌ تُوسَّع — لا بطاقتان بالاسم نفسِه")
check("rows.length === 0 && holders.length === 0" in CARD,
      "٦ه ولا تُطوى البطاقةُ على أسماءٍ قُرئت لغياب النِّسَب المجمّعة")

# ── ٧ · الرسميُّ أوّلاً — وهو المتوفّر أصلاً ─────────────────────────────
# قال المالك: «هيكلُ الملكية متوفّرٌ على تداول… واعتبره دليلَ تخاذل». وهو
# محقّ: كنتُ قد اكتشفتُ نداءاتِها بنفسي ثمّ ذهبتُ إلى «أرقام» وبنيتُ طبقةَ
# متصفّحٍ ثقيلة، وقلتُ «غير متوفّر» عمّا هو متوفّر. فالترتيبُ يعود لموضعه.
from app.services import tadawul_ownership as tow  # noqa: E402

PAGE_TD = ('<base href="https://www.saudiexchange.sa/wps/portal/x/">'
           '<a href="p0/z1abc=NJforeginOwnerShip=/">الملكية الأجنبية</a>'
           '<a href="p0/z1abc=NJhistoricalBoardMembersWithDates=/">المجلس</a>'
           '<a href="p0/z1abc=NJgetMainNomucMarketDetails=/">السوق</a>')
names = sorted(set(tow._EP_RE.findall(PAGE_TD)))
check(len(names) == 3,
      "٧ أسماءُ النداءات تُقرأ من الصفحة لا تُثبَّت في الشيفرة", str(names))
check(next(n for n in names if tow.KINDS["foreign"].search(n)) == "foreginOwnerShip"
      and next(n for n in names if tow.KINDS["board"].search(n))
      == "historicalBoardMembersWithDates",
      "٧ب والبندُ يُعرَف باسم ندائه — فتغييرُ الاسم لا يُسكت الصفّ")
check(not any(tow.KINDS["foreign"].search(n) or tow.KINDS["board"].search(n)
              for n in ["getMainNomucMarketDetails"]),
      "٧ج ونداءُ السوق لا يُقرأ ملكيةً لشركة")

rows = tow.normalize([
    {"shareholderName": "صندوق الاستثمارات العامة", "percentage": "37.5"},
    {"memberName": "عضوٌ بلا نسبة"},
    {"name": "نسبةٌ خارج المعقول", "percentage": 140},
    {"nameAr": "عضو مجلس", "ownershipPercentage": 0.25, "position": "رئيس"},
])
check([r["name"] for r in rows] == ["صندوق الاستثمارات العامة", "عضو مجلس"]
      and rows[0]["percent"] == 37.5 and rows[1].get("position") == "رئيس",
      "٧د وصفٌّ بلا نسبةٍ معقولةٍ يُترك، والمنصبُ يُقرأ إن وُجد", str(rows))

MK2 = (ROOT / "backend" / "app" / "api" / "v1" / "endpoints"
       / "market.py").read_text(encoding="utf-8")
i_t = MK2.index("tadawul_ownership import reading")
i_a = MK2.index("ownership import reading as argaam_reading")
check("tadawul_reading(sym), argaam_reading(sym)" in MK2,
      "٧ه والبابُ يقرأ الرسميَّ أوّلاً ثمّ «أرقام» — بندًا بندًا")
SCH2 = (ROOT / "backend" / "app" / "scheduler"
        / "scheduler.py").read_text(encoding="utf-8")
check(SCH2.index("t_refresh(sym)") < SCH2.index("await refresh(sym)"),
      "٧و ولا يُفتح المتصفّحُ إلا لمن لم يُقرأ من الرسميّ")

print(("FAIL" if fail else "PASS") + " D270 — هيكلُ الملكية بالمتصفّح")
raise SystemExit(fail)
