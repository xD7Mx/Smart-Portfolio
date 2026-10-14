#!/usr/bin/env python3
"""حارسُ D709 — لا سطرَ تبريرٍ في الصفحات (بأمر المالك 2026-10-14).

قال المالك: «لا أريد تبريراتٍ في الصفحة أو في التطبيق… احذف سطرَ التبرير في بطاقة المعاملة». وكانت بطاقةُ المعاملة تعرض تحت
التاريخ صندوقاً يشرح كلَّ نوع («يُخصم الإجمالي من السيولة المتاحة. وسم «إعادة استثمار» يُنقص…»)، ومعه شرحٌ تحت إقرار التجزئة،
وفي صفحة الشركة نسختُها وشرحُ مصدر التمويل وتعليلُ السعر المقترَح، وفي نافذة تعديل المركز تعليلُ فارق التسوية، وتحت حقل نبذة الشركة
تلميح، وحاشيتان في الحاسبات. فحُذفت كلُّها، وبقي ما ليس تبريراً: الإقرارُ نفسُه، وتأكيداتُ الحذف، وحالاتُ الفراغ والخطأ.
فالحارسُ يقرأ النصَّ الظاهرَ (بلا تعليقات) ويمنع عودتَها:

    python3 scripts/audit/no_justification_d709.py
"""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


def visible(path: pathlib.Path) -> str:
    s = path.read_text(encoding="utf-8")
    s = re.sub(r"\{/\*.*?\*/\}", "", s, flags=re.S)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", s)


PORT = visible(SRC / "pages" / "PortfolioPage.tsx")
COMP = visible(SRC / "pages" / "CompanyPage.tsx")
tx = PORT[PORT.index("function TransactionModal"):PORT.index("\nfunction ", PORT.index("function TransactionModal") + 10)]
check("hint[" not in tx and "يُخصم الإجمالي من السيولة" not in tx and "يُضاف صافي البيع" not in tx
      and "مثال: معامل 2" not in tx,
      "١ بطاقةُ المعاملة بلا سطر تبرير — الأرقامُ ومعاينتُها تكفي")
check("أُقرّ بأن كميات العمليات المسجَّلة قبل هذا التاريخ" in tx and "مُجزَّأة أصلاً" not in tx
      and "أُقرّ بأن كميات العمليات السابقة" in COMP and "مُجزَّأة أصلاً" not in COMP,
      "٢ وإقرارُ التجزئة باقٍ في البطاقتين (يحمي بياناتِ المحفظة) — وشرحُه تحته محذوف")
PHRASES = {
    "PortfolioPage.tsx": ["كي لا تمحوه إعادة بناء الحيازة", "لتسجيل شراء/بيع فعلي يعكس أثره"],
    "CompanyPage.tsx": ["فلا يتناقض معها", "«ضخ» = رأس مال جديد"],
    "CompanyProfileCards.tsx": ["نصّك يتقدّم على المصدر"],
    "CalculatorsPage.tsx": ["فلا يُعدّ أيٌّ منهما مرّتين", "لتقريب الصورة لا للضمان"],
    "AutopilotCard.tsx": ["الأهدافَ والقوائمَ وآراءَ البيوت والأحداثَ ومستوياتِ D7M…"],
}
left = []
for name, phrases in PHRASES.items():
    path = next(SRC.rglob(name))
    txt = visible(path)
    left += [f"{name}: {p}" for p in phrases if p in txt]
check(not left, "٣ ولا تبريرَ في صفحة الشركة ونافذة تعديل المركز ونبذة الشركة والحاسبات وتحميل المستشار", "؛ ".join(left))
check("تصحيحٌ للمركز وحده" in PORT and "استخدم هذا السعر" in COMP,
      "٤ وما ليس تبريراً باقٍ: تنبيهُ أثر تعديل المركز (واقعةٌ واحدة)، والسعرُ المقترَح بزرّه")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
