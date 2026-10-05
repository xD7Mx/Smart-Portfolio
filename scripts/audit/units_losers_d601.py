#!/usr/bin/env python3
"""حارسُ D601: (١) وحدةُ جدول «المعلومات المالية» لكلّ عمودٍ لا للجدول كلِّه؛
(٢) الخاسرُ في وسيط ثلاث سنواتٍ لا يُقيَّم بمضاعفات المبيعات.

    python3 scripts/audit/units_losers_d601.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

def tr(*c, h=False):
    t = "th" if h else "td"
    return "<tr>" + "".join(f"<{t}>{x}</{t}>" for x in c) + "</tr>"

from app.services.tadawul_financials import parse_table
T = "<table>" + "".join([
    tr("Balance Sheet", "2025-12-31", "2024-12-31", "2023-12-31", h=True),
    tr("Total Shareholders Equity (After Deducting the Minority Equity)", "1,678,961,000", "1,831,581,000", "1,271,795"),
    tr("All Figures in", "Units", "Units", "Thousands"),
]) + "</table>"
ps = {p["as_of"]: p for p in parse_table(T)}
check(ps["2025-12-31"]["equity"] == 1_678_961_000 and ps["2023-12-31"]["equity"] == 1_271_795_000,
      "١ ولاء: كلُّ عمودٍ بوحدته — 1.68 مليار و1.27 مليار لا 1.68 مليون", str([ps[k]["equity"] for k in sorted(ps)]))
T2 = T.replace(tr("All Figures in", "Units", "Units", "Thousands"), tr("All Figures in", "Units", "Lakhs", "Thousands"))
p2 = {p["as_of"]: p for p in (parse_table(T2) or [])}
check("equity" not in p2.get("2024-12-31", {}), "٢ وعمودٌ وحدتُه مجهولةٌ لا يُقرأ — لا يُفترض")
src = (ROOT / "backend/app/services/fair_value_models.py").read_text()
check('bs.margin_n is not None and bs.margin_n < 0' in src and '"peer_ps", "peer_ev_sales", "dcf_exit_5", "dcf_exit_10"' in src,
      "٣ والخاسرُ في وسيط ثلاث سنواتٍ تُستبعد له نماذجُ المبيعات (الميثانول 85 على 26)")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
