#!/usr/bin/env python3
"""حارسُ D644: الأحداثُ الجوهرية تُعرض للمستثمر بنصّها العربيّ ومصدرها — عرضٌ يقرأ المستخرِجَ المجمَّد ولا يعدّله."""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0
def check(ok, label):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}")
ev = (ROOT / "backend/app/services/events_view.py").read_text()
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text()
fz = (ROOT / "scripts/audit/engine_freeze_d635.py").read_text()
me = (ROOT / "frontend/src/components/analysis/MaterialEvents.tsx").read_text()
cp = (ROOT / "frontend/src/pages/CompanyPage.tsx").read_text()
sv = (ROOT / "frontend/src/components/market/StockView.tsx").read_text()
ec = (ROOT / "frontend/src/components/common/EventCard.tsx").read_text()
check("from app.services.material_events import events_for" in ev and '"events_view.py"' not in fz,
      "١ العرضُ يقرأ المستخرِجَ ولا يعدّله، وهو خارجَ ملفّات المحرّك المجمَّدة — لا يمسّ رقماً")
check('(d or {}).get("title")' in ev, "٢ العنوانُ العربيّ من صفحة الإفصاح لا عنوانُ القائمة الإنجليزيّ")
check('@router.get("/material-events/{symbol}")' in mk, "٣ نقطةُ العرض موجودة")
check("<MaterialEvents symbol={company.symbol} />" in cp and "<MaterialEvents symbol={symbol} />" in sv,
      "٤ والبطاقةُ في «نظرة عامة» لصفحتَي السهم (D666 — كانت في آخر «تقييم الأداء» فلم يجدها المالك)")
check('dir="ltr"' in me and "min-h-[32px]" in ec and 'rel="noopener noreferrer"' in ec and "nu-latn" in ec,
      "٥ التاريخُ بأرقامٍ لاتينية، والرابطُ هدفُ لمسٍ ≥ 32px ويُفتح خارجياً بأمان (البطاقةُ الموحّدة · D666)")
check("#" not in me.split("export default")[1].replace("{/*", "").split("*/}")[0] or "var(--" in me,
      "٦ الألوانُ من رموز الدليل")
check("why_not" in me and "يُعدّ في سجلّ الأعمال" in me, "٧ العقدُ يقول هل يُعدّ في سجلّ الأعمال ولماذا لا")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
