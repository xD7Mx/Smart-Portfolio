#!/usr/bin/env python3
"""حارسُ D599: ما لا يحمله جدولُ «المعلومات المالية» لا يُحسب صفراً —
الدَّينُ والنقدُ يُنقلان من أحدث فترةٍ نشرتهما، والتدفّقُ الحرُّ لا يُحسب بلا إنفاقٍ رأسماليٍّ معروف.

    python3 scripts/audit/fv_debt_capex_d599.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services.fair_value_models import balance_of, base_of, Inputs
# زين كما قِيس: أحدثُ فترةٍ من الجدول (حقوقٌ بلا دَين)، وآخرُ XBRL يحمل الدَّين
q = [{"as_of": "2025-12-31", "total_debt": 14e9, "ending_cash": 2e9, "equity": 10.8e9},
     {"as_of": "2026-06-30", "equity": 10.9e9, "source": "تداول — المعلومات المالية"}]
b = balance_of(q, [])
check(b.get("total_debt") == 14e9 and b.get("ending_cash") == 2e9, "١ الدَّينُ والنقدُ من أحدث فترةٍ نشرتهما — لا صفر")
check(b.get("equity") == 10.9e9, "٢ والحقوقُ من الأحدث كما هي")
check(b.get("debt_asof") == "2025-12-31", "٣ ويُعلَن تاريخُ المنقول")
b2 = balance_of([{"as_of": "2026-06-30", "total_debt": 1e9, "equity": 5e9}], [])
check(b2.get("total_debt") == 1e9 and "debt_asof" not in b2, "٤ وما يحمل دَينَه لا يُمسّ")
check(balance_of([{"as_of": "2026-06-30", "equity": 5e9}], []).get("total_debt") is None, "٥ وبلا دَينٍ منشورٍ أصلاً لا يُختلق")
# سابك: سنواتٌ من الجدول بلا إنفاقٍ رأسماليّ — لا تدفّقَ حرٌّ يساوي التشغيليَّ كلَّه
ann = [{"as_of": f"{y}-12-31", "year": y, "revenue": 120e9, "net_income": 1e9, "operating_cash_flow": 20e9, "equity": 150e9}
       for y in (2023, 2024, 2025)]
i = Inputs(symbol="2010", price=47.0, shares=3e9, annual=ann, ttm=dict(ann[-1]), balance=ann[-1], ttm_source="t")
bs = base_of(i)
check(bs is not None and bs.fcf_margin_n is None, "٦ لا تدفّقَ حرٌّ بلا إنفاقٍ رأسماليٍّ معروف (كان 16.7٪ = التشغيليُّ كلُّه)",
      str(bs and bs.fcf_margin_n))
ann2 = [dict(p, capex=-8e9) for p in ann]
bs2 = base_of(Inputs(symbol="2010", price=47.0, shares=3e9, annual=ann2, ttm=dict(ann2[-1]), balance=ann2[-1], ttm_source="t"))
check(bs2 and abs(bs2.fcf_margin_n - 0.1) < 1e-9, "٧ والإنفاقُ السالبُ الإشارة يُطرح لا يُضاف: (20 − 8) ÷ 120 = 10٪", str(bs2 and bs2.fcf_margin_n))
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
