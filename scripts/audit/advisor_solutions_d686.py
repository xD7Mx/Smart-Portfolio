#!/usr/bin/env python3
"""حارسُ D686 — المستشارُ يجد الحلول، والهدفُ يحرّره المالك، ولا سطرَ تبريرٍ تحت العنوان (بأمر المالك 2026-10-11).

«المستشار لا يملك الحلول بالرغم من أنّه قادرٌ على الوصول للبيانات وقراءتها وحتى التقارير داخل تبويب التوقعات واصطياد بدائلَ
حكيمة» — قِيس: سأل «اقرأ تبويب التوقعات وأعطني انطباعاتك» فجاء ردٌّ عامّ، لأنّ التوقّعاتِ لم تكن في معطياته، ولا مرشّحَ من
السوق خارج المحفظة؛ فكلُّ «حلٍّ» تحذير. و«اجعل الأهداف قابلةً للتحرير وعدم حصرها للمليون».

    python3 scripts/audit/advisor_solutions_d686.py
"""
import os, pathlib, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import autopilot as AP, market_screener   # noqa: E402
ROWS = [  # صفوفُ الفرز بشكلها: مرشّحٌ صالح، ومركزٌ مملوك، وثقةٌ منخفضة، وجودةٌ ضعيفة، وقرارُ انتظار، وفرقٌ صغير
    {"symbol": "1180.SR", "name": "الأهلي", "sector": "البنوك", "price": 35.0, "fair_value": 42.0, "fair_value_upside_pct": 20.0,
     "finance_score": 82, "fair_value_conf": "مرتفعة", "decision": "شراء", "dividend_yield": 4.1},
    {"symbol": "2222.SR", "name": "أرامكو", "price": 24.0, "fair_value": 30.0, "fair_value_upside_pct": 25.0, "finance_score": 90,
     "fair_value_conf": "مرتفعة", "decision": "شراء قوي"},
    {"symbol": "4001.SR", "name": "أ", "price": 10, "fair_value_upside_pct": 40.0, "finance_score": 80, "fair_value_conf": "منخفضة", "decision": "شراء"},
    {"symbol": "4002.SR", "name": "ب", "price": 10, "fair_value_upside_pct": 30.0, "finance_score": 40, "fair_value_conf": "متوسطة", "decision": "شراء"},
    {"symbol": "4003.SR", "name": "ج", "price": 10, "fair_value_upside_pct": 30.0, "finance_score": 80, "fair_value_conf": "متوسطة", "decision": "انتظار"},
    {"symbol": "4004.SR", "name": "د", "price": 10, "fair_value_upside_pct": 5.0, "finance_score": 80, "fair_value_conf": "متوسطة", "decision": "شراء"},
    {"symbol": "4005.SR", "name": "هـ", "price": 10, "fair_value_upside_pct": 35.0, "finance_score": 70, "fair_value_conf": "متوسطة", "decision": "شراء قوي"},
]
market_screener.get_cached_screener = lambda: ROWS
alts = AP._market_alternatives({"2222"}) if hasattr(AP, "_market_alternatives") else []
check([a["الرمز"] for a in alts] == ["4005", "1180"],
      "١ البدائلُ من الفرز: قرارُ شراء، وثقةٌ غيرُ منخفضة، وجودةٌ ≥ 60، وفرقٌ ≥ 10٪، وليست في المحفظة — مرتّبةً بالفرق",
      str([a["الرمز"] for a in alts]))
check(bool(alts) and {"الفرق٪", "الجودة", "العادل", "قرار_المحرّك", "التوزيع٪"} <= set(alts[-1]),
      "٢ ولكلّ مرشّحٍ أرقامُه كما في الشاشة: العادلُ والفرقُ والجودةُ والتوزيع وقرارُ المحرّك")
src = (ROOT / "backend/app/services/autopilot.py").read_text(encoding="utf-8")
check(src.count("_market_alternatives(") >= 3 and src.count("await _forecast_digest()") >= 2 and '"solutions": [str(x)' in src
      and "الحلولُ قبل التحذير" in src and "فلخّص «تقارير_التوقعات» نفسَها" in src and "«يُدرس توقيتُه»" in src,
      "٣ والبدائلُ وتقاريرُ التوقعات في الرأي والحوار معاً، والموجِّهُ يأمر بحلولٍ مرقّمة لا بتشخيصٍ وحده — والمرشّحُ «يُدرس توقيتُه»")
check('"name": "الهدف"' in src and '"name": "المليون"' not in src,
      "٤ والهدفُ «الهدف» بمبلغه لا «المليون» — المالكُ يختار مبلغه")
gl = (ROOT / "backend/app/api/v1/endpoints/goals.py").read_text(encoding="utf-8")
ap = (ROOT / "frontend/src/components/governance/AutopilotCard.tsx").read_text(encoding="utf-8")
check('_cache.expire_containing("autopilot:")' in gl and "goalsApi.saveBuiltinConfig({ million_target: n })" in ap
      and 'aria-label="تعديل الهدف"' in ap and "<GoalAmount target={data?.target} />" in ap,
      "٥ والمبلغُ يُحرَّر في المستشار نفسِه ويُحفظ في إعداد الأهداف، ويُنسى رأيُ اليوم المحسوبُ على الهدف القديم")
check("يقرأ المحفظةَ والتطبيقَ كلَّه — رأيٌ واحد" not in ap and "حلولٌ نحو هدفك" in ap,
      "٦ ولا سطرَ تبريرٍ تحت عنوان المستشار، والحلولُ قسمٌ ظاهرٌ مرقّم")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
