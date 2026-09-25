#!/usr/bin/env python3
"""حارسُ D486: صناديقُ المؤشرات (94xx) في السوق الرئيسة، و«نمو» اختياريٌّ في الدليل.

    python3 scripts/audit/etf_nomu_d486.py
"""
import os, sys, tempfile
# الحاضنةُ قبل أيّ استيرادٍ من app (D160 · D429)
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
fail = 0
def check(ok, label):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}")

from app.data.universe import is_main, is_nomu, main_market
from app.data.market_universe import MARKET_UNIVERSE as U
etfs = sorted(s for s, m in U.items() if (m.get("sector") or "") == "صناديق المؤشرات المتداولة")
check(len(etfs) >= 10 and all(is_main(s) for s in etfs),
      f"١ صناديقُ المؤشرات ({len(etfs)}) في السوق الرئيسة لا «نمو» — {', '.join(etfs[:4])}…")
check(is_nomu("9510") and is_nomu("9570") and is_main("2222"),
      "٢ وشركاتُ «نمو» باقيةٌ «نمو»، والرئيسةُ رئيسة")
check(all(s in main_market(U) for s in etfs), "٣ ومحرّكاتُ السوق الرئيسة تراها (main_market)")
D = open(os.path.join(ROOT, "frontend/src/components/market/CompanyDirectory.tsx"), encoding="utf-8").read()
M = open(os.path.join(ROOT, "backend/app/api/v1/endpoints/market.py"), encoding="utf-8").read()
check('"nomu": market_of(sym) == NOMU' in M and "useState(true)" in D and "(showNomu || !r.nomu)" in D,
      "٤ مفتاحُ «نمو» في الدليل اختياريّ، والجميعُ يظهر افتراضاً")
check('aria-label="القطاع"' in D and "كل القطاعات" in D,
      "٥ اختيارُ القطاع مباشرةً بجانب البحث")
print(f"{'FAIL' if fail else 'PASS'} D486 — صناديقُ المؤشرات و«نمو»")
sys.exit(fail)
