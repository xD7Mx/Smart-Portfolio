#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D211 — اسمٌ غيرُ معرَّفٍ يمرّ إلى الحزمة فيُطفئ الشاشة.
#
# ## ما وقع
# نُقلت بطاقتا النبذة والإدارة إلى ملفٍّ مشترك (D209)، وفي أثناء النقل
# بقي `canWrite` مُستعمَلاً في ثلاثة مواضع بلا تعريف — فرمى المتصفّح
# `ReferenceError` عند أوّل رسم، وسقطت شجرةُ React كلُّها: **شاشةٌ سوداء**
# رآها المالكُ بعد التركيب.
#
# ## لماذا لم يُمسَك
# بناءُ الواجهة `lint:hooks && vite build`: الأوّلُ يفحص قواعدَ الخطّافات
# وحدَها، والثاني يُترجم بلا فحصِ أنواع (‏esbuild يحذف الأنواع ولا يتحقّق
# منها). فما من خطوةٍ تسأل: أهذا الاسمُ معرَّف؟
#
# ## الحارس
# يُشغَّل `tsc --noEmit` ويُرفَض **صنفٌ واحدٌ** من أخطائه: «لا أجد هذا
# الاسم» (‏TS2304 · TS2552). لا تُشترط سلامةُ الأنواع كلِّها — في الشيفرة
# ملاحظاتٌ قديمةٌ لا تُسقط شاشة — بل يُمنع ما يُسقطها.
#
# ## D691 — و«الملاحظاتُ القديمة» كانت تُخفي عطباً حيّاً
# من تسعة أخطاء أنواعٍ تُركت: مخزنُ الإعدادات يُعلن `setShowClock` ولا ينفّذه
# (‏TS2739)، وصفحةُ الإعدادات تمرّره إلى مفتاح «إظهار الساعة» — فالنقرُ يرمي
# `onChange is not a function` ولا تختفي الساعة. فلا تُصنَّف الأخطاءُ إلى
# مُسقطٍ ومحتمَل: الفحصُ الثاني يشترط أن تخلو الواجهةُ من خطأ أنواعٍ أصلاً.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONT = ROOT / "frontend"
FATAL = re.compile(r"error TS(2304|2552):")


def main() -> int:
    if not (FRONT / "node_modules" / "typescript").exists():
        print("… تعذّر الفحص: TypeScript غيرُ مثبَّت في اعتماديات الواجهة.")
        return 0
    r = subprocess.run(["npx", "tsc", "--noEmit"], cwd=FRONT,
                       capture_output=True, text=True)
    bad = [l for l in (r.stdout + r.stderr).splitlines() if FATAL.search(l)]
    for l in bad[:20]:
        print("     " + l.strip())
    ok1 = not bad
    print(f"{'PASS' if ok1 else 'FAIL'} ١ لا اسمَ مستعملاً بلا تعريف في الواجهة"
          f" — {len(bad)} موضعاً")
    errs = [l for l in (r.stdout + r.stderr).splitlines() if re.search(r"error TS\d+:", l)]
    for l in errs[:20]:
        print("     " + l.strip()[:200])
    ok2 = not errs and r.returncode == 0
    print(f"{'PASS' if ok2 else 'FAIL'} ٢ ولا خطأَ أنواعٍ أصلاً — المُعلَنُ غيرُ المنفَّذ عطبٌ حيّ لا ملاحظة (‏D691)"
          f" — {len(errs)} خطأً")
    ok = ok1 and ok2
    print()
    print("النتيجة:", "نظيف ✔" if ok else "فيه ملاحظات ✘")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
