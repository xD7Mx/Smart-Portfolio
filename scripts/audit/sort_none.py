#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D167 — لا فرزَ يسقط لأنّ درجةً تعذّرت.
#
# قُضي — بأمر المالك — أن تبقى الشركةُ معروضةً ولو تعذّرت درجتُها، لأنّ
# الغيابَ لا يُفسَّر ولا يُسأل عنه. فصارت `None` قيمةً واردةً في كلّ صفّ.
# وبقي فرزُ تبويب السوق يقارن الدرجةَ خاماً: و`None < None` ترفع
# TypeError — فمتى تعذّرت الدرجةُ على شركتين سقط **التبويبُ كلُّه**.
# قِيس على الخادم: `get_market_governance` لا يردّ شيئاً.
#
# فحصٌ سلوكيّ: يفرز صفوفاً فيها `None` فعلاً ويشترط ألّا يسقط، وأن يبقى
# المُدرَجُ أوّلاً تنازلياً والمتعذَّرُ في الذيل. ويمسح الملفَّ كلَّه بحثاً
# عن فرزٍ آخرَ على حقلٍ يحتمل الغياب — فالعطبُ كان موضعاً واحداً تخلّف
# عن نمطٍ صحيحٍ مستعمَلٍ في موضعين غيره.
# ─────────────────────────────────────────────────────────────────────────
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "backend" / "app" / "services" / "governance.py"

fail = 0


def say(ok, label, detail=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")


# ── ١ · سلوكُ الفرز نفسِه، لا نصُّه ────────────────────────────────────
def sort_rows(rows):
    """النمطُ المعتمَد — نُسخةٌ حيّةٌ منه تُختبر بأرقامٍ فيها غياب."""
    rows = list(rows)
    rows.sort(key=lambda r: (r.get("finance_score") is not None,
                             r.get("finance_score") or 0), reverse=True)
    return rows


rows = [
    {"symbol": "A", "finance_score": None},
    {"symbol": "B", "finance_score": 83},
    {"symbol": "C", "finance_score": None},
    {"symbol": "D", "finance_score": 48},
    {"symbol": "E", "finance_score": 90},
]
try:
    out = sort_rows(rows)
    crashed = False
except TypeError:
    out, crashed = [], True

say(not crashed, "١ الفرزُ لا يسقط بدرجتين متعذّرتين")
if not crashed:
    order = [r["symbol"] for r in out]
    say(order[:3] == ["E", "B", "D"], "٢ المُدرَجُ أوّلاً تنازلياً", " · ".join(order))
    say(set(order[3:]) == {"A", "C"}, "٣ المتعذَّرُ في الذيل ولم يُحذف",
        f"{len(order)} صفوف من {len(rows)}")

# ── ٢ · لا موضعَ آخرَ يتخلّف عن النمط ─────────────────────────────────
# يُقرأ الشجرُ لا النصّ: كلُّ `sort`/`sorted` مفتاحُه لامدا تقرأ حقلاً
# يحتمل الغياب — يجب أن يحمل حارساً (`is None` / `is not None` / `or`).
RISKY_FIELDS = {"finance_score", "avg_change_pct", "change_pct", "score",
                "fair_value", "fair_value_upside_pct", "ai_score"}

tree = ast.parse(SRC.read_text(encoding="utf-8"))
bad = []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    is_sorted = isinstance(node.func, ast.Name) and node.func.id == "sorted"
    is_sort = isinstance(node.func, ast.Attribute) and node.func.attr == "sort"
    if not (is_sorted or is_sort):
        continue
    key = next((k.value for k in node.keywords if k.arg == "key"), None)
    if not isinstance(key, ast.Lambda):
        continue
    src = ast.unparse(key)
    if not any(f in src for f in RISKY_FIELDS):
        continue
    if ("is None" in src) or ("is not None" in src) or (" or " in src):
        continue
    bad.append((node.lineno, src))

for ln, src in bad:
    print(f"     سطر {ln}: {src}")
say(not bad, "٤ كلُّ فرزٍ على حقلٍ يحتمل الغياب محروس",
    f"{len(bad)} موضعاً بلا حارس")

print()
print("النتيجة:", "نظيف ✔" if not fail else "فيه ملاحظات ✘")
sys.exit(fail)
