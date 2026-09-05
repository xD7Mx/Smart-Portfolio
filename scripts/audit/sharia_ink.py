#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D181 — هلالُ الشرعية يحمل لونَه في المظهرين، ولا يبتلعه توريثٌ عامّ.
#
# رأى المالكُ الهلالَ أسودَ في صفحة السهم رغم أن الألوانَ الثلاثةَ مكتوبةٌ
# في المكوّن. والسببُ ترجيحُ الانتقاء لا خطأٌ في اللون: القاعدةُ العامّة
# `html.light svg { color: inherit }` ترجيحُها (0,1,1) وصنفُ اللون
# `text-[var(--pos-ink)]` ترجيحُه (0,1,0) — فيرث الهلالُ حبرَ العنوان.
#
#   قِيس قبل العلاج (فاتح):  #111111 · #111111 · #111111
#   وبعده:                   #16a34a · #c2410c · #dc2626
#   والداكن كان صحيحاً في الحالين — فلذلك لم يُرَ العطبُ إلا في مظهرٍ واحد.
#
# والعلاجُ في موضعين: لونُ الهلال بنمطٍ مباشرٍ لا يغلبه انتقاء، والقاعدةُ
# العامّةُ تستثني ما لُوّن قصداً — فلا يعود العطبُ لأيقونةٍ أخرى.
#
# فحصٌ بنيويّ لا لفظيّ: يقيس أن القاعدةَ ليست عامّةً مطلقة، وأن المكوّن
# لا يضع لونَ الحكم في صنفٍ يُغلَب.
# ─────────────────────────────────────────────────────────────────────────
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONT = ROOT / "frontend" / "src"
fail = 0


def say(ok, label, detail=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")


css = (FRONT / "styles" / "globals.css").read_text(encoding="utf-8")
css_nc = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

# ١ · لا توريثَ مطلقاً يبتلع كلَّ أيقونةٍ في الفاتح.
bare = re.search(r"html\.light\s+svg\s*\{", css_nc)
say(bare is None,
    "١ لا قاعدةَ توريثٍ مطلقةٍ لكلّ svg في المظهر الفاتح",
    "استُثني ما لُوّن قصداً" if bare is None else "عادت `html.light svg { … }` بلا استثناء")

# ٢ · والقاعدةُ الموجودة تستثني اللونَ الصريح — صنفاً أو نمطاً.
guarded = re.search(r"html\.light\s+svg:not\([^{]*\{[^}]*color:\s*inherit", css_nc)
say(bool(guarded), "٢ والتوريثُ يستثني ما حمل لوناً صريحاً")

# ٣ · ولونُ الهلال نمطٌ مباشر: `style={{ color: … }}` لا صنفُ Tailwind.
ui = (FRONT / "components" / "common" / "UI.tsx").read_text(encoding="utf-8")
badge = ui[ui.index("export function ShariaBadge"):]
badge = badge[:badge.index("\nexport ")] if "\nexport " in badge else badge
say("text-[var(" not in badge,
    "٣ لونُ الهلال لا يوضع بصنفٍ يغلبه انتقاءٌ أعلى")
say("style={{ color:" in badge, "٤ بل بنمطٍ مباشر")

# ٥ · وللحالات الثلاث ثلاثةُ رموزٍ مختلفة — لا لونَ واحدٌ لثلاثة أحكام.
tones = set(re.findall(r"var\(--[a-z-]+\)", ui[ui.index("SHARIA_TONE"):ui.index("export function ShariaBadge")]))
say(len(tones) == 3, "٥ ثلاثةُ ألوانٍ لثلاثة أحكام", " · ".join(sorted(tones)))

print()
print("النتيجة:", "نظيف ✔" if not fail else "فيه ملاحظات ✘")
sys.exit(fail)
