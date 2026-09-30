#!/usr/bin/env python3
"""حارسُ D554: مستشارُ الريت — صافي الأصول من إعلان التوزيع نفسِه، والتوزيعاتُ بأحقّيتها،
والخصمُ على الصافي، وتنبيهُ التأخّر، والسعرُ العادلُ للريت = صافي أصوله المنشور.

    python3 scripts/audit/reit_advisor_d554.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from datetime import date
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import reit_advisor as R
# متنُ إعلان «تداول» الحقيقيّ — الراجحي ريت، توزيعُ الربع الثاني 2026 (كاشف reit_door)
T = """مقدمة | تعلن الراجحي المالية عن توزيع أرباح نقدية على مالكي وحدات صندوق الراجحي ريت عن الفترة من 1 أبريل 2026 إلى 30 يونيو 2026 على النحو التالي:
فترة استحقاق الأرباح | الربع الثاني من عام 2026م
إجمالي الأرباح الموزعة | 37,207,012.23 ريال سعودي
عدد الوحدات القائمة التي ستتم التوزيعات النقدية على أساسها | 275,607,498
قيمة الربح الموزع لكل وحدة | 0.135 ريال سعودي
نسبة التوزيع من صافي قيمة الأصول (%) | % 1.61
نسبة التوزيع من صافي قيمة الأصول كما في تاريخ | 1448-01-15 الموافق 2026-06-30
أحقية التوزيعات النقدية لمالكي الوحدات وذلك حسب سجل مالكي الوحدات بنهاية يوم | 1448-03-19 الموافق 2026-09-01"""
d = R.parse_distribution(T)
check(d and d["amount"] == 0.135 and d["nav_pct"] == 1.61 and d["nav_date"] == "2026-06-30"
      and d["eligibility"] == "2026-09-01" and abs(d["nav"] - 8.385) < 0.001 and d["units"] == 275607498,
      "١ من إعلان التوزيع: القيمةُ للوحدة ونسبتُها من الصافي وتاريخاه — والصافي = 0.135 ÷ 1.61٪ = 8.385", str(d))
ds = [{"amount": 0.12, "nav_pct": 1.37, "nav": round(0.12 / 0.0137, 3), "nav_date": "2024-12-31", "eligibility": "2025-07-31"},
      {"amount": 0.13, "nav_pct": 1.43, "nav": round(0.13 / 0.0143, 3), "nav_date": "2025-06-30", "eligibility": "2025-10-30"},
      {"amount": 0.14, "nav_pct": 1.55, "nav": round(0.14 / 0.0155, 3), "nav_date": "2025-06-30", "eligibility": "2026-02-12"},
      {"amount": 0.13, "nav_pct": 1.59, "nav": round(0.13 / 0.0159, 3), "nav_date": "2025-12-31", "eligibility": "2026-04-30"},
      d]
s = R.summarize(ds, ["2026-08-20"], 7.72, date(2026, 9, 30))
check(s["nav_date"] == "2026-06-30" and abs(s["premium"] - (7.72 / 8.385 - 1) * 100) < 0.1,
      "٢ أحدثُ صافٍ بتاريخه والخصمُ عليه (−7.9٪ للراجحي ريت عند 7.72)", f"{s.get('nav')} · {s.get('premium')}")
check(abs(s["ttm"] - (0.13 + 0.14 + 0.13 + 0.135)) < 1e-9 and not s["overdue"] and s["cadence_days"] in range(80, 110),
      "٣ توزيعاتُ 12 شهراً بالأحقّية، والإيقاعُ ربعيّ، ولا تأخّر", f"{s.get('ttm')} · {s.get('cadence_days')}")
late = R.summarize(ds, [], 7.72, date(2027, 3, 1))
check(late["overdue"] is True, "٤ تنبيهُ التأخّر إن جاوز الغيابُ مرّةً ونصفاً من الإيقاع")
src = (ROOT / "backend/app/services/fair_value_models.py").read_text(encoding="utf-8")
dv = (ROOT / "backend/app/services/tadawul_dividends.py").read_text(encoding="utf-8")
am = (ROOT / "backend/app/services/app_mind.py").read_text(encoding="utf-8")
check('if _arch(sym) == "reit":' in src and '"weights_kind": "reit_nav"' in src,
      "٥ السعرُ العادلُ للريت صافي أصوله المنشور لا نماذجُ الشركات")
check("from app.services.reit_advisor import cached as _reit" in dv and "reit_advisor import cached, summarize" in am,
      "٦ جدولُ التوزيعات يُكمَل بإعلانات الصندوق، وعقلُ التطبيق يقرأ المستشار")
td = (ROOT / "backend/app/services/tadawul_disclosure.py").read_text(encoding="utf-8")
check('ck = f"tadawul:annlist:v2:{sym}"' in td,
      "٧ D555 مفتاحُ قائمة الإفصاحات بإصدارٍ يحمل العنوان — القديمُ المخزَّن بلا TITLE أخفى التوزيعاتِ كلَّها")
print(f"{'FAIL' if fail else 'PASS'} D554 — مستشارُ الريت")
sys.exit(fail)
