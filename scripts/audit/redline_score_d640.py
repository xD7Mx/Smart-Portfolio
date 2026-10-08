#!/usr/bin/env python3
"""حارسُ D640 · الإصدار الثاني: من وقع في خطٍّ أحمر يُستبعد ويُقال السبب — في المنتِج الواحد الذي تقرؤه البطاقةُ
والصفحةُ وجدولُ القوائم (D149)، فلا تُنشر درجةٌ نسبيةٌ «قوية» لشركةٍ بحقوقٍ سالبةٍ وخسارةِ سنوات."""
import os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
from app.services.scores import governed_finance_score, _finance_score_from_periods, exclusion_verdict   # noqa: E402

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

def yr(y, rev, ni, eq, ocf, fcf):
    return {"year": y, "revenue": rev, "net_income": ni, "equity": eq, "total_equity": eq, "operating_cash_flow": ocf,
            "free_cash_flow": fcf, "total_assets": 5e9, "total_debt": 1e9, "ending_cash": 2e8, "operating_income": ni * 1.2}
healthy = [yr(2021 + i, 1e9 * (1.08 ** i), 1.2e8 * (1.1 ** i), 1.5e9 + 1e8 * i, 1.6e8, 1.1e8) for i in range(5)]
cenomi_like = [yr(2021 + i, 2e9, -2e8 - 1e7 * i, 5e8 - 3e8 * i, 1e8, 5e7) for i in range(5)]   # خسارةٌ متتالية وحقوقٌ تنقلب سالبة
s0, l0 = governed_finance_score(healthy)
check(not l0 and s0 == _finance_score_from_periods(healthy), "١ الشركةُ بلا خطٍّ أحمر تبقى درجتُها الأصلية كما هي", str(s0))
s1, l1 = governed_finance_score(cenomi_like)
base1 = _finance_score_from_periods(cenomi_like)
ids = {x["id"] for x in l1}
check("loss_streak" in ids and "negative_equity" in ids, "٢ الخسارةُ المتتالية والحقوقُ السالبة تُشعلان خطّين", str(ids))
check(s1 == 0 or not base1, "٣ ومن اشتعل فيه خطٌّ أحمر تصير درجتُه صفراً (استبعاد) لا نسبيةً «قوية»", f"الأصلية {base1} ← {s1}")
check(exclusion_verdict(l1).startswith("استُبعدت الشركة من التقييم: خطٌّ أحمر — خسارةٌ"), "٤ والسببُ يُقال بنصّه", exclusion_verdict(l1)[:70])
an = (ROOT / "backend/app/services/analysis.py").read_text()
ge = (ROOT / "backend/app/services/governance_engine.py").read_text()
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text()
check("governed_finance_score(periods, symbol)" in an and "_finance_score_from_periods(periods)" not in an,
      "٥ الصفحةُ تقرأ المنتِجَ الواحد")
check("governed_finance_score(periods, symbol)" in ge and "governed_finance_score(periods, sym)" in mk,
      "٦ والبطاقةُ وجدولُ القوائم يقرآنه كذلك (D149: رقمٌ واحدٌ في كلّ شاشة)")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
