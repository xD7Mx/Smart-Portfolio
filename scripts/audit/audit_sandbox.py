#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D160 (عودة) — لا فحصَ يكتب في بيانات المالك المتتبَّعة.
#
# سُجِّل هذا العطبُ من قبل وعولج في أربعة سكربتات — وتخلّف `rank_check`،
# فعاد يلوّث `backend/lastgood.json` المتتبَّع ويمنع بناءَ الحزمة. وسكربتُ
# فحصٍ يغيّر حالةً ليس فحصاً.
#
# والعلاجُ الدائم ليس تصحيحَ الخامس، بل حارسٌ يمنع السادس: كلُّ سكربتِ
# فحصٍ يُدرج `backend` في مسار الاستيراد يجب أن يُحوّل مخزنَ الحالة إلى
# مجلّدٍ مؤقّت **قبل** أيّ استيرادٍ من `app` — لأنّ الوحداتِ تقرأ المسارَ
# عند تحميلها لا عند استعمالها. فيُقرأ الشجرُ ويُتحقَّق من **الترتيب**.
# ─────────────────────────────────────────────────────────────────────────
import ast
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
fail = 0

# ══ النطاقُ هو ما تشغّله اللجنةُ نفسُها ══
# المسابرُ التي تُشغَّل يدوياً على الخادم (‏score_dist · market_sweep ·
# probe_real …) تقرأ المخزنَ الحقيقيَّ **عن قصد** — وتحويلُها إلى مجلّدٍ
# مؤقّت يُفرغها من معناها. فالقاعدةُ لمن يُشغَّل هنا بلا إذنٍ ولا انتباه:
# تُقرأ أسماؤهم من `run.sh` نفسِه، فلا تتخلّف القائمةُ عن الواقع.
RUN_SH = HERE / "run.sh"
_names = set()
for _line in RUN_SH.read_text(encoding="utf-8").splitlines():
    _line = _line.strip()
    if _line.startswith("#") or "scripts/audit/" not in _line:
        continue
    for _tok in _line.split():
        if _tok.startswith("scripts/audit/") and _tok.endswith(".py"):
            _names.add(pathlib.Path(_tok).name)


def say(ok, label, detail=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")


def first_app_import_line(tree) -> int | None:
    """أوّلُ سطرٍ يستورد من `app` — بعده يفوت الأوان لتحويل المخزن."""
    best = None
    for node in ast.walk(tree):
        mod = None
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
        elif isinstance(node, ast.Import):
            mod = node.names[0].name if node.names else ""
        if mod and (mod == "app" or mod.startswith("app.")):
            best = node.lineno if best is None else min(best, node.lineno)
    return best


def sandbox_set_line(tree) -> int | None:
    """أوّلُ سطرٍ يُسند `LASTGOOD_PATH` في `os.environ`."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            if (isinstance(t, ast.Subscript)
                    and isinstance(t.value, ast.Attribute)
                    and t.value.attr == "environ"
                    and isinstance(t.slice, ast.Constant)
                    and t.slice.value == "LASTGOOD_PATH"):
                return node.lineno
    return None


offenders = []
checked = 0
for path in sorted(HERE.glob("*.py")):
    if path.name not in _names or path.name == "audit_sandbox.py":
        continue
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        continue
    imp = first_app_import_line(tree)
    if imp is None:
        continue                      # لا يستورد المحرّك — لا يكتب شيئاً
    checked += 1
    sb = sandbox_set_line(tree)
    if sb is None:
        offenders.append((path.name, "بلا مخزنٍ مؤقّت"))
    elif sb > imp:
        offenders.append((path.name, f"المخزنُ يُحوَّل في {sb} بعد استيراد app في {imp}"))

for name, why in offenders:
    print(f"     {name}: {why}")
say(bool(_names), "١ قائمةُ اللجنة قُرئت من run.sh", f"{len(_names)} سكربتاً")
say(not offenders,
    "٢ كلُّ فحصٍ في اللجنة يُحوّل مخزنَ الحالة قبل استيراد المحرّك",
    f"{checked} يستورد المحرّك · {len(offenders)} مخالفاً")

print()
print("النتيجة:", "نظيف ✔" if not fail else "فيه ملاحظات ✘")
sys.exit(fail)
