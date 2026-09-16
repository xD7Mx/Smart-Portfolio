#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D332 — للتطبيق هويّةُ تصميم، وكلُّ ميزةٍ تتبعها لا العكس.
#
# قال المالك: «سويتشُ الصفقات الخاصة لا يحاكي تصميمَ التطبيق وأسلوبَه —
# عدّله وامنع تكرارَه. فالتطبيقُ له هويّةُ تصميمٍ وأسلوب، وكلُّ ميزةٍ
# جديدةٍ أو تعديلٍ جديدٍ يتماشى مع هذه الهويّة وليس العكس».
#
# وكان مبدِّلُ المدى في «صفقات خاصة» مكتوباً بإطارٍ وأرضيةٍ وألوانٍ ثابتةٍ
# من عندي، والنمطُ المعتمَدُ قائمٌ في ستّة مواضع: `seg` + `seg-btn` + `on`
# (فيه ارتفاعُ اللمس ٣٢px ولونُ الهويّة وحلُّ «القلتش» في التحويم).
#
# فهذا الحارسُ يمسح الواجهةَ كلَّها ويمنع عودةَ الصنف:
#   ٠· لا مبدِّلَ مكتوباً باليد: زرُّ اختيارٍ (‏aria-pressed/selected) يُلوّن
#      نفسَه بأنماطٍ ثابتةٍ بدل `seg-btn`
#   ١· ولا قيمةَ لونٍ ثابتةٍ (‏#hex) في الأصناف الجديدة — الألوانُ رموزٌ
#   ٢· ولا أصنافَ «سويتشٍ» ثانيةٍ في الأنماط تُنافس القائم
#   ٣· والنمطُ المعتمَدُ مستعملٌ فعلاً — فلا حارسٌ يحرس نمطاً مهجوراً
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"
fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


TSX = sorted(SRC.rglob("*.tsx"))
CSS = (SRC / "styles" / "globals.css").read_text(encoding="utf-8")

# ── ٠ · لا مبدِّلَ مكتوباً باليد ─────────────────────────────────────────
hand: list[str] = []
for f in TSX:
    t = f.read_text(encoding="utf-8")
    for m in re.finditer(r"<button\b[\s\S]{0,420}?>", t):
        blk = m.group(0)
        if "aria-pressed" not in blk and "aria-selected" not in blk:
            continue
        if "seg-btn" in blk or "mk-tab" in blk or "inline-search-btn" in blk:
            continue
        # زرُّ اختيارٍ يرسم أرضيتَه بنفسه = مبدِّلٌ موازٍ للنمط المعتمَد
        if re.search(r"background(?:Color)?\s*:", blk):
            hand.append(f"{f.relative_to(SRC)}:{t[:m.start()].count(chr(10)) + 1}")
check(not hand,
      "٠ لا مبدِّلَ مكتوباً باليد — أزرارُ الاختيار بنمط `seg-btn` المعتمَد",
      " · ".join(hand[:6]) or f"{len(TSX)} ملفاً نظيفاً")

# ── ١ · ولا لونَ ثابتٍ في زرّ اختيار ────────────────────────────────────
hex_in_btn: list[str] = []
for f in TSX:
    t = f.read_text(encoding="utf-8")
    for m in re.finditer(r"<button\b[\s\S]{0,420}?>", t):
        blk = m.group(0)
        if "aria-pressed" not in blk and "aria-selected" not in blk:
            continue
        if re.search(r"#[0-9a-fA-F]{3,8}\b", blk):
            hex_in_btn.append(
                f"{f.relative_to(SRC)}:{t[:m.start()].count(chr(10)) + 1}")
check(not hex_in_btn,
      "١ ولا قيمةَ لونٍ ثابتةٍ في زرّ اختيار — الألوانُ رموزٌ للمظهرين",
      " · ".join(hex_in_btn[:6]) or "نظيف")

# ── ٢ · ولا أصنافَ مبدِّلٍ ثانيةٍ في الأنماط ─────────────────────────────
rivals = [c for c in ("segmented", "tab-switch", "range-switch", "toggle-btn",
                      "pill-btn", "chip-btn")
          if re.search(rf"\.{c}\b", CSS)]
check(not rivals,
      "٢ ولا أصنافَ مبدِّلٍ ثانيةٍ في الأنماط تُنافس `seg`",
      " · ".join(rivals) or "صنفٌ واحدٌ معتمَد")

# ── ٣ · والنمطُ المعتمَدُ مستعملٌ فعلاً ─────────────────────────────────
users = [str(f.relative_to(SRC)) for f in TSX
         if "seg-btn" in f.read_text(encoding="utf-8")]
check(re.search(r"\.seg-btn\b", CSS) and len(users) >= 5,
      "٣ والنمطُ المعتمَدُ مستعملٌ في مواضعَ عدّة — لا حارسٌ لنمطٍ مهجور",
      f"{len(users)} ملفاً: " + " · ".join(users[:4]))

# ── ٤ · ومبدِّلُ «صفقات خاصة» بعينه — موضعُ الملاحظة ────────────────────
SD = (SRC / "components" / "market" / "SpecialDeals.tsx").read_text(encoding="utf-8")
check('className="seg inline-flex' in SD and '"seg-btn whitespace-nowrap"' in SD,
      "٤ ومبدِّلُ مدى «صفقات خاصة» بالنمط المعتمَد — موضعُ ملاحظة المالك")
check(not re.search(r"var\(--brand-ink\)\W+color:\s*\"var\(--on-brand\)", SD),
      "٤ب ولا ألوانَ مبدِّلٍ مكتوبةً في الملفّ — تُقرأ من الصنف")

print(("FAIL" if fail else "PASS") + " D332 — الميزةُ تتبع الهويّة لا العكس")
sys.exit(fail)
