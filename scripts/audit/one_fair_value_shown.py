#!/usr/bin/env python3
"""سعرٌ عادلٌ واحدٌ على الشاشات كلِّها — تقديرُ المحرّك (D431).

    python3 scripts/audit/one_fair_value_shown.py

قال المالك وهو ينظر إلى صفحة «الغاز والتصنيع الأهلية»: «هناك سعران
عادلان — لا أريد تناقضات، أريد رقماً واحداً للسعر العادل يكون هو الأجدرَ
بهذه الثقة والاسم، لا واحداً فوق والثاني تحت». فوقٌ: ‎47.26 من المحرّك.
وتحتٌ في «البيانات المالية»: «السعر العادل ≈88.07 ‎+44.7٪ · ثقة منخفضة».

والثاني **القيمةُ النسبيةُ إلى القطاع** (‏`rel_value`): وسيطُ مضاعفات
النظائر وحدَه. والمحرّكُ يأخذ مضاعفَ القطاع مساراً **من بين مساراته**
مع قوائم الشركة نفسِها، ويُعايِر ثقتَه — فرقمُه هو الأجدرُ بالاسم،
والنسبيُّ مُدخَلٌ فيه لا منافسٌ له. وكان النسبيُّ في خمسة ملفّات يلبس
اسمَ «السعر العادل» أو يحلّ محلَّه صامتاً حين يمتنع المحرّك.

فالقاعدة: **لا يُعرَض `rel_value` ولا `rel_upside_pct` في أيّ شاشة**،
والسعرُ العادلُ `fair_value` وحدَه، وحيث يمتنع المحرّكُ «—». ويُقرأ
النصُّ بعد نزع التعليقات، فشرحٌ في تعليقٍ ليس عرضاً.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"
if not SRC.is_dir():
    print("⚠ لا مجلَّدَ واجهةٍ في هذه البيئة — لم يُقَس")
    sys.exit(0)


def _strip(t: str) -> str:
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"(?m)^\s*//.*$", "", t)
    t = re.sub(r"\{/\*.*?\*/\}", "", t, flags=re.S)
    return t


bad: list[str] = []
files = 0
for f in sorted(list(SRC.rglob("*.tsx")) + list(SRC.rglob("*.ts"))):
    if f.name.endswith(".d.ts") or "/types" in str(f):
        continue
    files += 1
    body = _strip(f.read_text(encoding="utf-8"))
    for i, ln in enumerate(body.splitlines(), 1):
        if re.search(r"\brel_(value|upside_pct|low|high|conf)\b", ln):
            bad.append(f"{f.relative_to(ROOT)}:{i}: {ln.strip()[:90]}")

ok = not bad
print(f"{'PASS' if ok else 'FAIL'} ١ لا شاشةَ تعرض القيمةَ النسبيةَ رقماً منافساً"
      f" — {files} ملفّاً" + ("" if ok else f" · {len(bad)} موضعاً"))
for b in bad[:30]:
    print(f"     {b}")
print(("FAIL" if bad else "PASS")
      + " D431 — سعرٌ عادلٌ واحدٌ على الشاشات كلِّها: تقديرُ المحرّك")
sys.exit(1 if bad else 0)
