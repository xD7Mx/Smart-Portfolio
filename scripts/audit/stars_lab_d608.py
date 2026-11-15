#!/usr/bin/env python3
"""حارسُ D607–D608: مختبرُ السلّة يحسب كما يحسب اختبارُ النجوم ولا يكتب في المحفظة؛ ومفتاحُ حركة السعر/الرسم.

    python3 scripts/audit/stars_lab_d608.py
"""
import os, pathlib, sys, tempfile   # noqa: E401
# مخزنُ حالةٍ مؤقّتٌ قبل استيراد المحرّك — لا يُكتب في حالة الخادم الحقيقية (‏audit_sandbox)
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services.stars_backtest import basket
data = {"tasi": {"2015-01": 100, "2015-02": 101, "2015-03": 102},
        "px": {"A": {"m": [["2015-01", 10], ["2015-02", 11], ["2015-03", 12.1]]},
               "B": {"m": [["2015-01", 20], ["2015-02", 20], ["2015-03", 19]]}}}
r = basket(data, ["A", "B", "C"], "2015-01")
check(r["total"] == 7.6 and r["tasi_total"] == 2.0, "١ أوزانٌ متساويةٌ تُعاد شهرياً: (+5٪ ثمّ +2.5٪) = 7.6٪ مقابل تاسي 2٪", str(r["total"]))
check(r["missing"] == ["C"], "٢ وشركةٌ بلا سجلّ أسعارٍ تُسمّى ولا تُختلق")
check([c["symbol"] for c in r["contrib"]] == ["A", "B"], "٣ ومساهمةُ كلِّ سهمٍ مرتّبة")
late = basket({"tasi": data["tasi"], "px": {"A": data["px"]["A"], "D": {"m": [["2015-02", 5], ["2015-03", 6]]}}}, ["A", "D"], "2015-01")
check(late["months"] == 2, "٤ والمدرَجُ لاحقاً يدخل حين يبدأ سعرُه")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text()
seg = mk.split('@router.get("/stars-lab")')[1].split("@router")[0]
check("lab(" in seg and "Holding" not in seg and "commit" not in seg, "٥ المختبرُ قراءةٌ فقط — لا يكتب في المحفظة")
sp = (ROOT / "frontend/src/pages/ResearchLab.tsx").read_text()   # ‏D745: المختبرُ صار قسمَ الأبحاث
check("marketApi.researchDesk(" in sp and "الماضي ليس وعداً" not in sp, "٦ المختبرُ هو الصفحة (‏D745: قسمُ الأبحاث) — بلا حاشيةٍ تفسيرية")
cp = (ROOT / "frontend/src/pages/CompanyPage.tsx").read_text()
nc = (ROOT / "frontend/src/components/chart/ProChart.tsx").read_text()
poc = (ROOT / "frontend/src/components/analysis/PriceOrChart.tsx").read_text()
# ‏D739: المفتاحُ في PriceOrChart، والرسمُ الاحترافيُّ بإعداد صفحة السهم: أسبوعيٌّ وD7M افتراضاً
check("<PriceOrChart" in cp and 'preset="stock"' in poc and "d7m: true" in nc[nc.index("const IND_STOCK"):nc.index("const IND_STOCK") + 260],
      "٧ صفحةُ السهم: مفتاحٌ بين حركة السعر والرسم على D7M الأسبوعيّ")
pp = (ROOT / "frontend/src/pages/PortfolioPage.tsx").read_text()
check("newAvgCost" in pp.split("نصيبه من التوازن")[0] and "line-through" in pp, "٨ بطاقةُ المعاملة: المتوسطُ الجديد ومعاينةُ النقص قبل التأكيد")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
