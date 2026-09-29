#!/usr/bin/env python3
"""حارسُ D548: عقلُ التطبيق الواحد — رأيُ الذكاء وتقريرُ الشركة يقرآن ملفّاً واحداً من
محرّكاتنا ونموذج الأبحاث، والتوصيةُ قرارُ التطبيق لا قاعدةٌ ثانية.

    python3 scripts/audit/app_mind_d548.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import app_mind as M
an = {"decision": {"label": "شراء", "reason": "جودةٌ عالية وسعرٌ دون العادل"},
      "financial": {"score": 85, "verdict": "قوية"},
      "scores": {"quality": {"score": 80}, "safety": {"score": 70}, "valuation": {"score": 60}, "timing": {"score": 50}},
      "fair_value": 76.55, "fair_value_low": 60.0, "fair_value_high": 90.0, "fair_value_upside_pct": 20.1,
      "fair_value_conf": "متوسطة"}
e = M.engines(an, "1120")
check(any(x.startswith("قرارُ التطبيق: شراء") for x in e) and any("الدرجةُ المالية 85" in x for x in e)
      and any("الأركانُ الأربعة" in x for x in e) and any("السعرُ العادل 76.55" in x for x in e),
      "١ سطورُ المحرّكات: القرارُ بسببه والدرجةُ والأركانُ والسعرُ العادلُ بنطاقه وثقته", " | ".join(e)[:200])
note = {"forecast": {"revenue": {"value": 5e9, "label": "الربعُ المقابل", "mape": 4.2, "hit": 80, "tested": 12}},
        "growth": {"years": ["2021", "2025"], "rev_cagr": 8.0, "ni_cagr": 10.0, "margin_first": 10.0, "margin_last": 12.0},
        "seasonality": {"strongest": "الرابع", "shares": {"الرابع": 30.0}, "years": 4},
        "price": {"since": "2010-03", "cagr": 9.0, "tasi_cagr": 2.0, "max_dd": -40.0,
                  "div": {"since": "2010", "years_paid": 15, "regularity": 94, "cagr": 7.0}},
        "pe_band": {"current": 16.2, "low": 12.0, "high": 22.0, "median": 16.0, "position": 60}}
r = M.research(note)
check(len(r) == 7 and "خطؤها التاريخيُّ 4.2٪" in r[0], "٢ سطورُ الأبحاث: التوقّعُ ودقّتُه والنموُّ والموسميةُ والسهمُ والتوزيعاتُ والمكرّر", str(len(r)))
op = M.attach({"sentiment_label": "شراء"}, {"engines": e, "research": r})
check(op.get("engines_bullets") == e and op.get("research_bullets") == r, "٣ القسمان يُلحقان بالرأي كما هما أياً كان كاتبُه")
ai = (ROOT / "backend/app/api/v1/endpoints/ai.py").read_text(encoding="utf-8")
ac = (ROOT / "backend/app/services/ai_content.py").read_text(encoding="utf-8")
qr = (ROOT / "backend/app/services/quarter_report.py").read_text(encoding="utf-8")
so = (ROOT / "frontend/src/components/analysis/StockOpinion.tsx").read_text(encoding="utf-8")
check("dossier(s, analysis)" in ai and "attach(opinion, _mind)" in ai and "mind_lines" in ac and "{mind_ctx}" in ac,
      "٤ رأيُ الذكاء (النموذجُ والقواعد) يقرأ الملفَّ نفسَه ويُلحَق به")
check('"recommendation": decision or recommendation(total)' in qr, "٥ توصيةُ تقرير الشركة قرارُ التطبيق الواحد")
check("engines_bullets" in so and "research_bullets" in so, "٦ بطاقةُ رأي الذكاء تعرض القسمين")
print(f"{'FAIL' if fail else 'PASS'} D548 — عقلُ التطبيق الواحد")
sys.exit(fail)
