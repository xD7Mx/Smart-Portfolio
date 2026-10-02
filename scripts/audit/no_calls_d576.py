#!/usr/bin/env python3
"""حارسُ D576: لا مؤتمراتِ محلّلين في التطبيق — «تداول» لا يحمل منها إلا الموعدَ والرابط، والمالكُ قال:
«لا أريد مؤتمرات، أريد معلوماتٍ وفائدة؛ إن لم توجد فلا معنى لها». فلا تعود ميزةٌ بلا محتوى.

    python3 scripts/audit/no_calls_d576.py
"""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
pat = re.compile(r"investor_calls|InvestorCalls|investor-calls|investorCalls|مؤتمرُ المحلّلين|مؤتمر المحللين")
hits = [f"{p.relative_to(ROOT)}" for d in ("backend/app", "frontend/src") for p in (ROOT / d).rglob("*")
        if p.suffix in (".py", ".ts", ".tsx") and pat.search(p.read_text(errors="ignore"))]
print(("PASS" if not hits else "FAIL") + " لا أثرَ لمؤتمرات المحلّلين في الخادم والواجهة" + (f" — {hits}" if hits else ""))
sys.exit(1 if hits else 0)
