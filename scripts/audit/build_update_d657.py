#!/usr/bin/env python3
"""حارسُ D657: نشرُ الواجهة يصل المالكَ بلا إعادة تحميلٍ يدويّة — قِيس: «تعديلاتي لم أجدها» والخادمُ يقدّمها كلَّها."""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0
def check(ok, label):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}")
src = (ROOT / "frontend/src/registerSW.ts").read_text(encoding="utf-8")
check('fetch("/index.html", { cache: "no-store" })' in src, "١ يُقرأ index.html من الخادم بلا كاش")
check("live !== cur" in src and "dispatchEvent(new CustomEvent(UPDATE_EVENT" in src.split("checkBuild")[1],
      "٢ ويُقارَن ملفُّ البناء بما حُمِّل، وإن اختلف ظهر «نسخة جديدة جاهزة»")
check("setInterval(checkBuild, 5 * 60 * 1000)" in src and 'visibilityState === "visible") checkBuild()' in src,
      "٣ كلَّ خمس دقائق وعند العودة إلى الصفحة")
check('document.addEventListener("visibilitychange", reloadWhenHidden)' in src.split("checkBuild")[1],
      "٤ والإعادةُ حين تُخفى الصفحة — لا تحت يد المالك")
sw = (ROOT / "frontend/public/sw.js").read_text(encoding="utf-8")
check("Network-First" in sw, "٥ ومستندُ HTML من الشبكة أوّلاً فيصل البناءُ الجديد عند الإعادة")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
