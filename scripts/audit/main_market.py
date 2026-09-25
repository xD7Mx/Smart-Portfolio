#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D170 — «نمو» لا تُعرض، والشرطُ مصدرُه واحد.
#
# قال المالك: «أخرِج شركاتِ نمو من الظهور ونكتفي بالسوق الرئيسي». وكان
# الكونُ يمرّ كاملاً (‏409) في مسح الحوكمة، فتصدّرت «نمو» قائمةَ الفرص:
# الإشاراتُ الستُّ تكافئ النموَّ السريعَ وقلّةَ الدين وذاك طبعُ الصغيرة،
# و«نمو» رقيقةُ التداول محدودةُ الإفصاح.
#
# والجذرُ أعمقُ من الاستبعاد: `not s.startswith("9")` كان **منسوخاً
# نصّاً** في ثلاثة مواضع وغائباً عن خمسة — بينما `universe.main_market`
# موجودةٌ منذ D136 ولا أحد يستعملها. وهو عينُ عطبِ D169: علاجٌ يُنسخ
# يدوياً بلا حارسٍ يمنع السادس.
#
# فحصان: أنّ الكونَ المعروض ‎٢٧٣ فعلاً (سلوكيّ)، وأنّ أحداً لا يعيد
# كتابةَ الشرط بيده (بالشجر).
# ─────────────────────────────────────────────────────────────────────────
import ast
import pathlib
import sys

# ══ فحصٌ لا يكتب في بيانات المالك ══ (D160)
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.data.market_universe import MARKET_UNIVERSE           # noqa: E402
from app.data.universe import census, is_main, main_market      # noqa: E402

fail = 0


def say(ok, label, detail=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")


c = census(MARKET_UNIVERSE)
say(c["unknown"] == 0, "١ لا رمزَ مجهولَ السوق", f"{c['unknown']} مجهولاً")
main = main_market(MARKET_UNIVERSE)
say(len(main) == c["main"] and c["main"] + c["nomu"] == c["total"],
    "٢ الكونُ ينقسم سوقين بلا بقيّة",
    f"رئيسة {c['main']} · نمو {c['nomu']} · الكلّ {c['total']}")
from app.data.universe import is_etf  # ‏D486: صناديقُ المؤشرات 94xx رئيسة
say(not any(str(s).startswith("9") and not is_etf(s) for s in main),
    "٣ لا رمزَ «نمو» (9xxx عدا صناديق المؤشرات 94xx) في السوق الرئيسة")
say(all(is_main(s) for s in main), "٤ كلُّ معروضٍ رئيسيّ")

# ── الشرطُ مصدرُه واحد ─────────────────────────────────────────────────
# يُقرأ الشجرُ بحثاً عن `startswith("9")` مكتوباً بيدٍ خارج `universe.py`
# — وهو الموضعُ الوحيدُ الذي يملك تعريفَ السوق.
SRC = ROOT / "backend" / "app"
ALLOWED = {SRC / "data" / "universe.py"}
offenders = []
for path in SRC.rglob("*.py"):
    if path in ALLOWED or "__pycache__" in str(path):
        continue
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "startswith"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "9"):
            offenders.append((path.relative_to(ROOT), node.lineno))

for rel, ln in offenders:
    print(f"     {rel}:{ln}")
say(not offenders,
    "٥ تعريفُ «نمو» في موضعٍ واحدٍ لا يُنسَخ",
    f"{len(offenders)} نسخةً يدوية")

# ── ٦ · و«نمو» ما تزال تُعرف حيث يلزم أن تُعرف ────────────────────────
# استبعادُها من العرض شيء، وكشفُها في التقييم شيءٌ آخر: من يملك ورقةَ
# «نمو» يجب أن يرى خصمَ سيولتها وسقفَ قرارها. فحصٌ سلوكيّ يستدعي
# المصنّفَ نفسَه بدل قراءة نصّ.
say(is_main("2222") and not is_main("9536"),
    "٦ المصنّفُ يفرّق الرمزين", "2222 رئيسيّ · 9536 نمو")
from app.data.universe import is_nomu as _in                      # noqa: E402
say(_in("9536.SR") and _in("9536") and not _in("2222"),
    "٧ الكشفُ يعمل بلاحقة .SR وبدونها")

print()
print("النتيجة:", "نظيف ✔" if not fail else "فيه ملاحظات ✘")
sys.exit(fail)
