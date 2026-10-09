#!/usr/bin/env python3
"""حارسُ D652 (ملاحظاتُ المالك 2026-10-09): الرسمُ البيانيّ بجانب حركة السعر أينما فُتحت صفحةُ السهم، رسماً فقط، بإطاراتٍ كتريدنق فيو.

العطب: ‏١ المفتاحُ «حركة السعر / الرسم البياني» عاش في صفحة الشركة داخل المحفظة وحدها (دالّةٌ محلّية)، وصفحةُ السهم
خارجها تعرض حركةَ السعر وحدَها. ‏٢ تبويبُ الرسم يحمل جدولَ الإطارات وقرارَ الدخول فوق الرسم. ‏٣ الاختيارُ مددٌ (شهر…5 سنوات)
لا إطاراتٌ — «أتلخبط بها»."""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
import os, tempfile   # noqa: E401
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

src = ROOT / "frontend/src"
users = sorted(str(p.relative_to(src)) for p in src.rglob("*.tsx")
               if re.search(r'import PriceChart from', p.read_text(encoding="utf-8")))
check(users == ["components/analysis/PriceOrChart.tsx"], "١ حركةُ السعر لا تُعرض وحدَها في أيّ صفحة — تمرّ بالمفتاح المشترك", str(users))
for f in ("pages/CompanyPage.tsx", "components/market/StockView.tsx"):
    check("<PriceOrChart symbol=" in (src / f).read_text(encoding="utf-8"), f"٢ {f} يعرض المفتاحَ: حركةُ السعر والرسمُ البيانيّ")
nc = (src / "components/analysis/NativeChart.tsx").read_text(encoding="utf-8")
tfs = re.search(r"const TFS: \[string, string\]\[\] = (\[.*?\]);", nc)
check(bool(tfs) and all(x in tfs.group(1) for x in ('"ساعة"', '"4 ساعات"', '"يوم"', '"أسبوع"', '"شهر"')) and "RANGES" not in nc,
      "٣ الرسمُ بإطارات: ساعة · 4 ساعات · يوم · أسبوع · شهر — لا مدد")
check("marketApi.bars(symbol, range)" in nc, "٤ ويجلب شموعَ الإطار المختار")
check("const chartOnly = preset === \"d7m-weekly\"" in nc and "{!chartOnly && ind.d7m && (dash" in nc,
      "٥ وفي صفحة السهم رسمٌ فقط — لا جدولَ إطاراتٍ ولا قرارَ دخولٍ فوقه")
pc = (src / "components/analysis/PriceChart.tsx").read_text(encoding="utf-8")
check('"5 سنوات"' in pc, "٦ وحركةُ السعر تبقى على مددها كما أراد المالك")
check("D7M أسبوعي" not in (src / "pages/CompanyPage.tsx").read_text(encoding="utf-8")
      and "D7M أسبوعي" not in (src / "components/analysis/PriceOrChart.tsx").read_text(encoding="utf-8"),
      "٧ واسمُ التبويب «الرسم البياني» — لا «أسبوعي» والإطارُ يتبدّل")
from app.services.market_data import four_hour, monthly, BAR_FRAMES   # noqa: E402
h = [{"date": f"2026-10-08 {x:02d}:00", "open": x, "high": x + 1, "low": x - 1, "close": x + .5, "volume": 1} for x in (10, 11, 12, 13, 14)]
f4 = four_hour(h)
check([b["date"][11:] for b in f4] == ["10:00", "14:00"] and f4[0]["open"] == 10 and f4[0]["close"] == 13.5 and f4[0]["high"] == 14,
      "٨ الأربعُ ساعات على جلسة الرياض: 10:00 و14:00، فتحُ أوّل ساعةٍ وإغلاقُ آخرها", str([(b['date'], b['open'], b['close']) for b in f4]))
m = monthly([{"date": "2026-09-01", "open": 1, "high": 2, "low": 0, "close": 1.5, "volume": 1},
             {"date": "2026-09-30", "open": 3, "high": 5, "low": 2, "close": 4, "volume": 1},
             {"date": "2026-10-01", "open": 4, "high": 4, "low": 3, "close": 3.5, "volume": 1}])
check(len(m) == 2 and m[0]["high"] == 5 and m[0]["close"] == 4, "٩ والشهريُّ شمعةٌ لكلّ شهر")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
check(BAR_FRAMES == ("1h", "4h", "1d", "1wk", "1mo") and "if tf in BAR_FRAMES:" in mk, "١٠ والخادمُ يسلّم الإطاراتِ الخمسة")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
