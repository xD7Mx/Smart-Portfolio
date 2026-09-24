#!/usr/bin/env python3
"""«كلُّ قطاعٍ بما يليق به» — نماذجُ القيمة العادلة بحسب مجموعة «تداول» الصناعية (D470).

    python3 scripts/audit/fvm_sector_sets.py

قال المالك: «النموذجُ يتغيّر لكلّ قطاع — للريت وجدتُ أربعةَ نماذج… المحرّكُ ليس
شاملاً بل يطبّق نظريتي: كلُّ قطاعٍ بما يليق عليه». فيُنادى المحرّكُ على مدخلاتٍ
واحدةٍ بقطاعاتٍ مختلفة، ويُشترط أن تختلف النماذجُ بحسب طبيعة القطاع.
"""
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    import app  # noqa: F401
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)
from app.services import fair_value_models as F
if not hasattr(F, "model_set"):
    print("FAIL D470 — لا نماذجَ بحسب القطاع"); sys.exit(1)

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

A = [{"year": y, "revenue": 1e9 * (1 + .05 * k), "net_income": 4e8, "ebit": 5e8, "operating_cash_flow": 6e8,
      "capex": 1e8, "equity": 4e9, "eps": 0.4, "shares_outstanding": 1e9, "as_of": f"{y}-12-31"} for k, y in enumerate((2023, 2024, 2025))]
peers = {"pe": [12, 14, 16, 18, 20], "pb": [0.8, 0.9, 1.0, 1.1, 1.2], "ps": [5, 6, 7, 8, 9], "pocf": [9, 10, 11, 12, 13],
         "ev_ebit": [12, 14, 16, 18, 20], "ev_sales": [6, 7, 8, 9, 10], "yield": [.06, .065, .07, .075, .08]}
def run(sector, arch):
    i = F.Inputs(symbol="X", price=5.0, shares=1e9, annual=A, ttm=dict(A[-1]), balance={"equity": 4e9, "total_debt": 1e9, "ending_cash": 1e8},
                 ttm_source="t", archetype=arch, sector=sector, dps_ttm=0.36, peers=peers)
    r = F.value(i)
    return {m["key"] for m in r["models"]}, r.get("model_set")
reit, rn = run("REITs", "reit")
check(reit and reit <= {"ddm_stable", "ddm_two_stage", "peer_yield", "peer_pb", "peer_ps"} and "peer_yield" in reit,
      "١ الصندوقُ العقاريّ بالتوزيع وصافي الأصول وعائدِ الأقران — لا تدفّقَ حرٌّ ولا ربحٌ تشغيليّ", f"{sorted(reit)} · {rn}")
bank, _ = run("Banks", "bank")
check(bank and not bank & F._DCF and "epv" not in bank, "٢ المصرفُ بعائد الحقوق والتوزيع — بلا خصمِ تدفّقٍ حرّ", str(sorted(bank)))
soft, _ = run("Software & Services", "asset_light")
check(soft and "peer_pb" not in soft and soft & F._DCF, "٣ البرمجياتُ بالأرباح والمبيعات لا بالدفترية", str(sorted(soft)))
cons, cn = run("Consumer Staples Distribution & Retail", "consumer_defensive")
check(len(cons) > len(reit) and cons & F._DCF and "peer_pb" in cons, "٤ والتجزئةُ الاستهلاكيةُ بالنموذج الكامل", f"{len(cons)} · {cn}")
check(len({frozenset(reit), frozenset(bank), frozenset(soft), frozenset(cons)}) == 4, "٥ أربعةُ قطاعاتٍ بأربع مجموعاتِ نماذج مختلفة")
print(f"{'FAIL' if fail else 'PASS'} D470 — كلُّ قطاعٍ بما يليق به")
sys.exit(fail)
