#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D214 — موضعُ التوافق الشرعيّ ثابتٌ لا يعود إلى الصدر.
#
# قال المالك: احذف بطاقةَ التوافق من صفحة السهم — الهلالُ يكفي — وضعها في
# صفحة الشركة تحت الهيكلة مكاناً ثابتاً. وقد نُقلت، ولم يبقَ عليها حارس:
# فأيُّ إعادةِ ترتيبٍ لاحقةٍ تردّها إلى الصدر بلا أن ينبح أحد.
#
# والقياسُ هنا على الترتيب لا على وجود النصّ: البطاقةُ **بعد** `OwnershipBar`
# في صفحة الشركة، و**قبل** النبذة؛ ومعدومةٌ في صفحة السهم مع بقاء الهلال.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


cp = (ROOT / "frontend/src/pages/CompanyPage.tsx").read_text(encoding="utf-8")
sv = (ROOT / "frontend/src/components/market/StockView.tsx").read_text(encoding="utf-8")

i_own = cp.find("<OwnershipBar")
i_sha = cp.find("<ShariaStatusIndicator")
i_prof = cp.find("<CompanyProfileCards")
check(i_own >= 0 and i_sha > i_own,
      "١ بطاقةُ التوافق بعد هيكلةِ الملكية لا في صدر الصفحة",
      f"ownership@{i_own} · sharia@{i_sha}")
check(i_prof > i_sha >= 0,
      "٢ وقبل النبذة والإدارة — موضعٌ واحدٌ محدّد",
      f"sharia@{i_sha} · profile@{i_prof}")
check("purification=" in cp and "sharia_source" in cp,
      "٣ وهي التفصيلُ الكامل: التطهيرُ والمصدر")
check("<ShariaStatusIndicator" not in sv,
      "٤ ولا بطاقةَ توافقٍ في صفحة السهم — تكرارٌ لِما قاله الهلال")
check("ShariaBadge" in sv or "sharia" in sv,
      "٥ والهلالُ باقٍ هناك يقول الحكمَ بلونه")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
