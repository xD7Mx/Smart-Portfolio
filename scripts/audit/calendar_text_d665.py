#!/usr/bin/env python3
"""حارسُ D665 (المالك 2026-10-10): «أُحبَط حين لا أرى تفاصيلَ لعنوان الخبر».

العطب: قِيس (`calendar_text_door.py`) في أوّل 70 حدثاً من مفكرة السوق: أحداثُ «أرقام» 58 كلُّها بنصّ، وأخبارُ «أرقام» الواردةُ
عبر قارئ الأخبار 11 كلُّها بلا نصّ («عموميةُ سينومي سنترز توافق على زيادة رأس المال»، «الأسماك تُعلن نشرة الإصدار»،
«نهايةُ أحقية أسهم منحة»…). روابطُها تحويلاتُ قارئ الأخبار لا مقالات، فلا يقرؤها قارئُ «أرقام»؛ وعناوينُها الصحفية
لا تشبه عناوينَ إفصاحاتها في «تداول» لفظاً، وبديلُ النوع يعرف الأرباحَ والجمعيةَ وحدَهما ويقف عند أوّل عائلة.
"""
import datetime as dt, os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services.tadawul_disclosure import kind_fallback   # noqa: E402
d = dt.date(2026, 10, 9)
rows = [{"date": "2026-10-08", "title": "تعلن شركة سينومي سنترز عن نتائج اجتماع الجمعية العامة غير العادية المتضمنة زيادة رأس المال"},
        {"date": "2026-10-07", "title": "تعلن الشركة عن نشرة إصدار أسهم حقوق الأولوية"},
        {"date": "2026-09-01", "title": "تعلن الشركة عن توزيع أرباح نقدية"},
        {"date": "2026-04-01", "title": "تعلن الشركة عن دعوة مساهميها لحضور اجتماع الجمعية العامة العادية"}]
cases = [
    ("عمومية سينومي سنترز توافق على زيادة رأس مال الشركة بنسبة 8.98%", "رأس المال"),
    ("هيئة السوق تُوافق على زيادة رأس مال سينومي سنترز بنسبة 9% عن طريق أسهم منحة", "رأس المال"),
    ("الأسماك تُعلن نشرة الإصدار الخاصة بطرح أسهم حقوق أولوية", "أولوية"),
    ("اليوم.. نهاية أحقية أسهم منحة لشركة تكافل الراجحي", "رأس المال"),
    ("عمومية سبكيم العالمية تفوض مجلس الإدارة بتوزيع أرباح مرحلية", "أرباح"),
]
for title, need in cases:
    r = kind_fallback(rows, title, d)
    check(bool(r) and need in r["title"], f"١ «{title[:44]}…» ← إفصاحُ «تداول» عن «{need}»", (r or {}).get("title", "—")[:60])
# وعناوينُ القائمة كما تصل فعلاً — بالإنجليزية (قِيس بعد النشر الأوّل: 11 من 11 بلا نصّ لأنّ الشرطَ عربيٌّ وحدَه)
en = [{"date": "2026-10-08", "title": "Arabian Centres Co. announces the results of the Extraordinary General Assembly Meeting including capital increase"},
      {"date": "2026-10-07", "title": "Saudi Fisheries Co. announces the publication of the Rights Issue Prospectus"},
      {"date": "2026-09-01", "title": "The company announces its Board of Directors recommendation to distribute cash dividends"}]
for title, need in [("عمومية سينومي سنترز توافق على زيادة رأس مال الشركة بنسبة 8.98%", "capital"),
                    ("الأسماك تُعلن نشرة الإصدار الخاصة بطرح أسهم حقوق أولوية", "Rights Issue"),
                    ("عمومية سبكيم العالمية تفوض مجلس الإدارة بتوزيع أرباح مرحلية", "dividends")]:
    r = kind_fallback(en, title, d)
    check(bool(r) and need in r["title"], f"١ب «{title[:40]}…» ← الإفصاحُ بعنوانه الإنجليزيّ كما تصل القائمة", (r or {}).get("title", "—")[:60])
check(kind_fallback(rows, "خبرٌ عن موضوعٍ آخر تماماً", d) is None, "٢ وما لا عائلةَ له لا يُنسب إليه إفصاحٌ — لا نصَّ أصدقُ من نصٍّ خاطئ")
check(kind_fallback(rows, "عمومية الشركة توافق", None) is None, "٣ وبلا تاريخٍ لا مطابقةَ بالنوع")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
