"""بصمةُ المحرّك الذي يعمل الآن (‏D647) — لا بصمةُ الأساس المجمَّد.

سجلُّ التحقّق (D638) يختم كلَّ صفٍّ ببصمة المحرّك التي أنتجته، ليُحكم على كلّ إصدارٍ بأيّامه. وكان يقرأها من
`engine_baseline.json` — أي بصمةَ الإصدار المجمَّد لا الشيفرةَ العاملة — فلمّا نُشر الإصدارُ الثاني صارت أيّامُه
تُنسب إلى 1.0 ويختلط الحكمان بعد 90 يوماً.

فالبصمةُ تُحسب هنا من الملفّات نفسِها بخوارزمية حارس التجميد (`scripts/audit/engine_freeze_d635.py`) وقائمتِه حرفاً
بحرف — وحارسُ D647 يُسقط أيَّ افتراقٍ بينهما. تعمل في المستودع (`<الجذر>/backend`) وفي الحاوية (`/app`) معاً:
الاسمُ المحسوب هو المسارُ من جذر المستودع في الحالين."""
from __future__ import annotations

import hashlib
import pathlib

# بترتيب حارس التجميد بعد الفرز — المسارُ من جذر المستودع
FILES = tuple(sorted([
    *(f"backend/app/services/{f}" for f in (
        "analysis.py", "fair_value.py", "data_quality.py", "statement_merge.py", "scores.py",
        "expert_panel.py", "sector_multiples.py", "governance_rules.py", "valuation_fields.py",
        "four_scores.py", "fair_value_models.py", "tadawul_financials.py", "tadawul_xbrl.py",
        "decision_engine.py", "technical.py", "market_valuation_sweep.py", "material_events.py",
        "red_lines.py", "confidence.py", "financial_features.py")),
    "backend/app/data/archetype_spec.py", "backend/app/data/governance_rules.yaml",
]))

_BACKEND = pathlib.Path(__file__).resolve().parents[2]      # ‎<الجذر>/backend · أو ‎/app في الحاوية


def fingerprint(backend_dir: str | pathlib.Path | None = None) -> str:
    base = pathlib.Path(backend_dir) if backend_dir else _BACKEND
    h = hashlib.sha1()
    for rel in FILES:
        f = base / rel.removeprefix("backend/")
        h.update(rel.encode())
        h.update(f.read_bytes() if f.exists() else b"<missing>")
    return h.hexdigest()[:12]
