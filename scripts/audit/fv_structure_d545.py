#!/usr/bin/env python3
"""حارسُ D545: عادلُ صافولا (+194٪) — هوامشُ الشركة قبل إعادة هيكلتها لا تُطبَّع
عليها اليوم، ومضاعفُ الإيراد يُصحَّح بهامش الشركة إلى هامش أقرانها.

    python3 scripts/audit/fv_structure_d545.py
"""
import os, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import fair_value_models as F

# سنواتُ صافولا السنويةُ كما في «تداول» (كاشف hist_door · 2026-09-29)
ANN = [
    {"as_of": "2023-12-31", "revenue": 24149521000.0, "ebit": 2179049000.0, "ebitda": 3302155000.0,
     "net_income": 1070476000.0, "equity": 8397145000.0, "shares_outstanding": 911168539.0},
    {"as_of": "2024-12-31", "revenue": 23986655000.0, "ebit": 13002889000.0, "ebitda": 14157853000.0,
     "net_income": 9915352000.0, "equity": 4620330000.0, "shares_outstanding": 945892713.0},
    {"as_of": "2025-12-31", "revenue": 26081053000.0, "ebit": 1342480000.0, "ebitda": 2540839000.0,
     "net_income": 940499000.0, "equity": 5516027000.0, "shares_outstanding": 300000000.0},
]
kept = F._same_company(ANN, 300000000.0)
check([p["as_of"] for p in kept] == ["2025-12-31"],
      "١ سنواتٌ بعدد أسهمٍ يبعد عن اليوم أكثرَ من الثلث (قبل إعادة الهيكلة) لا تُطبَّع عليها الهوامش",
      str([p["as_of"] for p in kept]))
check(len(F._same_company(ANN[:1] * 3, 911168539.0)) == 3, "٢ شركةٌ بلا إعادة هيكلةٍ تبقى سنواتُها الثلاث")

i = F.Inputs(symbol="2050", price=24.46, shares=300000000.0, annual=ANN,
             ttm={"revenue": 26081053000.0, "net_income": 940499000.0, "ebit": 1377000000.0,
                  "ebitda": 2540839000.0, "pretax_income": 1100000000.0},
             balance={"total_debt": 2664518000.0, "ending_cash": 1051382000.0, "equity": 5360505000.0},
             ttm_source="Q2 2026")
bs = F.base_of(i)
check(bs is not None and abs(bs.ebit_margin_n - 1342480000.0 / 26081053000.0) < 1e-9,
      "٣ هامشُ الربح التشغيليّ المطبَّع لصافولا هامشُها بهيكلها الحاليّ (5.1٪) لا 9٪ من 2023",
      f"{bs.ebit_margin_n if bs else None}")
i.peers = {"ev_sales": [(1.95, 1.0)] * 6,
           "_rec": {str(k): {"ebitda_margin": 0.20} for k in range(6)}}
xs, f = F._ev_sales_adj(i, bs)
check(abs(f - (2540839000.0 / 26081053000.0) / 0.20) < 1e-9 and abs(xs[0][0] - 1.95 * f) < 1e-9,
      "٤ مضاعفُ الإيراد للأقران يُصحَّح بهامش EBITDA للشركة ÷ وسيط هامشهم", f"f={f:.3f}")
m = {x["key"]: x["value"] for x in F.multiple_models(i, bs)}
check(m.get("peer_ev_sales") is not None and m["peer_ev_sales"] < 100,
      "٥ نموذجُ قيمة المنشأة/الإيراد لصافولا لم يعد 166 لسهمٍ بـ24", str(m.get("peer_ev_sales")))
print(f"{'FAIL' if fail else 'PASS'} D545 — عادلُ صافولا: الهيكلُ الحاليّ وهامشُ الإيراد")
sys.exit(fail)
