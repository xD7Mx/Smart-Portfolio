#!/usr/bin/env python3
"""حارسُ D666 (المالك 2026-10-10): «أفتقد الأحداثَ الجوهرية — لا أراها. اجعلها بنفس طريقة البطاقات الأخرى ووسمها؛ الشكلُ
الجماليّ والتصميمُ الموحّد للتطبيق ميزةٌ لنا. وانتبه أن تُظهر الميزاتِ في وضع الحاسوب وتنسى وضعَ الجوال».

العطب: بطاقةُ الأحداث الجوهرية في آخر تبويب «تقييم الأداء» بعد الدرجات والخطوط الحمراء، ووسومُها كبسولاتٌ بلون العلامة
لا رقعُ المفكرة الصلبة؛ وبطاقاتُ «التوقعات» شكلٌ ثالث. ثلاثُ نسخٍ لبطاقةٍ واحدة.
الجذر: كلُّ ميزةٍ كُتبت ببطاقتها لا بمكوّنٍ مشترك، ومكانُها اختير بقرب بياناتها لا بقرب عين المالك.
والقياسُ في الجوال والحاسوب معاً: `cards_d666.mjs` (390 و1280).
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


src = ROOT / "frontend/src"
ec_p = src / "components/common/EventCard.tsx"
check(ec_p.exists(), "١ بطاقةُ الحدث مكوّنٌ واحدٌ مشترك")
ec = ec_p.read_text(encoding="utf-8") if ec_p.exists() else ""
el = (src / "components/market/EventsList.tsx").read_text(encoding="utf-8")
me = (src / "components/analysis/MaterialEvents.tsx").read_text(encoding="utf-8")
ap = (src / "components/analysis/AnalysisPanel.tsx").read_text(encoding="utf-8")
cp = (src / "pages/CompanyPage.tsx").read_text(encoding="utf-8")
sv = (src / "components/market/StockView.tsx").read_text(encoding="utf-8")
check('className="ev-tag inline-block"' in ec and "event-item" in ec and "CompanyLogo" in ec and 'className="tag-b' in ec,
      "٢ والبطاقةُ بلغة المفكرة: شعارٌ · وسمٌ صلب · اسمٌ ورمز · عنوانٌ بتاريخه")
fc = el[el.index("function ForecastsPanel"):el.index("export default function EventsList")] if "function ForecastsPanel" in el else ""
row = el[el.index("function EventRow"):el.index("function EventRow") + 900] if "function EventRow" in el else ""
check("<EventCard" in row and "<EventCard" in fc and "<EventCard" in me,
      "٣ المفكرةُ والتوقعاتُ والأحداثُ الجوهرية كلُّها البطاقةُ نفسُها — لا نسخٌ تتباعد")
check("var(--tag-" in me and "rounded-full" not in me and "var(--brand)" not in me,
      "٤ ووسمُ الحدث الجوهريّ رقعةٌ من عائلة وسوم المفكرة — لا كبسولةٌ بلون العلامة")
check("<MaterialEvents symbol={company.symbol} />" in cp and "<MaterialEvents symbol={symbol} />" in sv and "<MaterialEvents" not in ap,
      "٥ والأحداثُ الجوهرية في «نظرة عامة» لصفحتَي السهم — تظهر عند الفتح في الجوال والحاسوب، ومرّةً واحدة")
css = (src / "styles/globals.css").read_text(encoding="utf-8")
check("--tag-contract:" in css, "٦ ولونُ وسم العقد رمزٌ في الدليل لا قيمةٌ ثابتة")
check(" dir=\"ltr\">{fmtCardDate" not in ec, "٧ والتاريخُ بلا قلبِ اتجاه — قُلب فظهر «202026/09/» في الجوال")
# ‏D667 (بأمر المالك: «إذا لم يوجد شعار ضع أيقونة التطبيق ليملأ فراغ الشعار حتى يكون أجمل»)
cl = (src / "components/common/CompanyLogo.tsx").read_text(encoding="utf-8")
lg = (src / "components/common/Logo.tsx").read_text(encoding="utf-8")
check("<Logo size={32} flat />" in ec and "<Logo size={size} flat />" in cl and "base.slice(0, 4)" not in cl and "co-logo" in cl,
      "٩ D667 لا شعار ⇒ علامةُ التطبيق: في البطاقة بلا شركة، وفي شعار الشركة الغائب — لا فراغ ولا مربّعُ رمز")
check("flat ?" in lg, "١٠ D667 والعلامةُ داخل البطاقة بلا هالة — الهالةُ للترويسة وحدها")
rs = (ROOT / "scripts/audit/run.sh").read_text(encoding="utf-8")
check("node scripts/audit/cards_d666.mjs" in rs, "٨ والقياسُ في المتصفّح بعرضَي الجوال والحاسوب ضمن اللجنة")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
