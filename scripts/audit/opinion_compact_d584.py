#!/usr/bin/env python3
"""حارسُ D584: رأيُ الذكاء مختصرٌ بصوت مستشار — حكمٌ في سطر، وستُّ نقاطٍ قصيرةٍ على الأكثر بإشارتها،
وماذا أفعل، وما يغيّر رأيي؛ بلا إخلاءِ مسؤوليةٍ ولا فقراتٍ متراكمة. والبديلُ القاعديُّ بالصيغة نفسِها.

    python3 scripts/audit/opinion_compact_d584.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json"); os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services.rule_opinion import build_stock_opinion, tidy
a = {"price": 24.3, "fair_value": 28.1, "fair_value_upside_pct": 15.6, "decision": {"label": "شراء", "reason": "الجودة 72 · السلامة 68"},
     "financial": {"score": 72}, "fundamentals": {"roe": 14.2, "dividend_yield": 5.1, "pe_ratio": 13.4, "profit_margin": 11, "earnings_growth": -4},
     "technical": {"rsi": 41, "support": 23.5, "resistance": 26, "trend": "هابط"}}
o = build_stock_opinion("2222", "أرامكو", a)
check(o.get("verdict", "").startswith("شراء") and o.get("action") and o.get("change"), "١ البديلُ القاعديّ: حكمٌ وماذا أفعل وما يغيّر رأيي")
pts = o.get("points") or []
check(1 <= len(pts) <= 6 and all(len(p["t"].split()) <= 16 for p in pts) and all(p["tone"] in "+-=" for p in pts),
      "٢ ستُّ نقاطٍ قصيرةٍ على الأكثر، لكلٍّ إشارتُها", str([len(p["t"].split()) for p in pts]))
check("بيد المستثمر" not in (o.get("summary") or ""), "٣ لا إخلاءَ مسؤوليةٍ في الخلاصة")
t = tidy({"points": [{"t": "تدفّق النقد قويّ", "tone": "+"}, {"t": "هذا لا يُعدّ نصيحة", "tone": "="}] * 4, "action": "القرار بيد المستثمر"})
check(len(t["points"]) == 3 and t["points"][0]["t"] == "تدفّق النقد قويّ" and t["action"] is None,
      "٤ تُحذف جملُ إخلاء المسؤولية كاملةً ولا تُقصّ كلماتٌ من داخل الجمل («النقد»)")
src = (ROOT / "backend/app/services/ai_content.py").read_text()
check('"verdict"' in src and '"points"' in src and "أربع عشرة كلمة" in src and "ai:opinion:v7" in src and '"advisor_bullets"' not in src,
      "٥ توجيهُ النموذج بالصيغة المختصرة، ونسختُه تُبطل الرأيَ المخزَّن القديم")
ep = (ROOT / "backend/app/api/v1/endpoints/ai.py").read_text()
check("compact_opinion" in ep and "tidy(opinion)" in ep, "٦ كلُّ رأيٍ يُكمَل بالصيغة المختصرة ويُنظَّف قبل العرض")
fe = (ROOT / "frontend/src/components/analysis/StockOpinion.tsx").read_text()
check("ماذا أفعل" in fe and "ما يغيّر رأيي" in fe and "function Details" in fe, "٧ الواجهة: حكمٌ ونقاطٌ ثمّ ماذا أفعل وما يغيّر رأيي، والسندُ مطويّ")
sys.exit(fail)
