#!/usr/bin/env python3
"""حارسُ D488 · D489: الإهلاكُ وEBITDA من «تداول»، ونموذجاهما، وشعاراتُ تداول.

    python3 scripts/audit/ebitda_d489.py
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

from app.services import tadawul_xbrl as X
from app.services import fair_value_models as F
# ١ · الصياغةُ المعياريّة كما في مخرَج تداول (16 من 19) + الاستهلاك
rows = [("Level of rounding used in financial statements", "Thousands"), ("End Date", "2025-12-31"),
        ("Revenue", "1,000"), ("Profit (loss) before zakat and income tax", "200"), ("Finance costs", "(50)"),
        ("Profit (loss)", "150"),
        ("Adjustments for depreciation and impairment (reversal of impairment) of property, plant and equipments", "80"),
        ("Adjustments for amortization and impairment (reversal of impairment) of intangible assets", "20")]
html = "<table>" + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in rows) + "</table>"
p = (X.parse(html).get("periods") or [{}])[0]
check(p.get("depreciation") == 100000.0 and p.get("ebitda") == 350000.0,
      "١ الإهلاكُ من تسويات قائمة التدفّقات (80+20) وEBITDA = الربحُ التشغيليّ + الإهلاك",
      f"{p.get('depreciation')} · {p.get('ebitda')}")
# ٢ · والإجماليُّ احتياطٌ بقيمته المطلقة
html2 = html.replace("Adjustments for depreciation and impairment (reversal of impairment) of property, plant and equipments", "Depreciation and amortisation").replace(
    "<tr><td>Adjustments for amortization and impairment (reversal of impairment) of intangible assets</td><td>20</td></tr>", "").replace(">80<", ">(90)<")
p2 = (X.parse(html2).get("periods") or [{}])[0]
check(p2.get("depreciation") == 90000.0, "٢ والإجماليُّ «Depreciation and amortisation» احتياطٌ بقيمته المطلقة", str(p2.get("depreciation")))
# ٣ · النموذجان يعملان بأقرانٍ لهم EV/EBITDA
A = [{"year": y, "as_of": f"{y}-12-31", "revenue": 1e9 * (1.05 ** k), "net_income": 1e8 * (1.05 ** k),
      "ebit": 1.5e8 * (1.05 ** k), "ebitda": 2.2e8 * (1.05 ** k), "operating_cash_flow": 1.8e8, "capex": 5e7,
      "equity": 4e9, "pretax_income": 1.3e8, "interest_expense": 2e7, "eps": 0.1} for k, y in enumerate(range(2021, 2026))]
peers = {"pe": [15, 18, 20, 22, 25], "pb": [1.5, 2, 2.5, 3, 3.5], "ps": [1, 1.5, 2, 2.5, 3], "pocf": [8, 10, 12, 14, 16],
         "ev_ebit": [10, 12, 14, 16, 18], "ev_sales": [1, 1.5, 2, 2.5, 3], "ev_ebitda": [6, 7, 8, 9, 10]}
i = F.Inputs(symbol="X", price=5.0, shares=1e9, annual=A, ttm=dict(A[-1]),
             balance={"equity": 4e9, "total_debt": 1e9, "ending_cash": 1e8}, ttm_source="t",
             archetype=None, sector="Energy", dps_ttm=0.2, peers=peers)
keys = {m["key"] for m in F.value(i)["models"]}
check({"dcf_ebitda_5", "dcf_ebitda_10", "peer_ev_ebitda"} <= keys,
      "٣ «DCF بخروج EBITDA» لخمسٍ وعشر و«مكرّرات EBITDA» تعمل من بيانات تداول", str(sorted(keys)))
check(len(F.MODEL_SETS["Energy"][1]) == 14 and len(F.MODEL_SETS["Consumer Staples"][1]) == 15
      and len(F.MODEL_SETS["Capital Goods"][1]) == 7 and len(F.MODEL_SETS["Consumer Durables"][1]) == 10,
      "٤ مجموعاتُ InvestingPro كاملةَ العدد: الطاقة 14 · التجزئة 15 · الرأسمالية 7 · المعمّرة 10")
check(not F.IP_MISSING, "٥ لا نموذجَ «غيرَ متوفّر» — كلُّها من تداول")
L = open(os.path.join(ROOT, "frontend/src/components/common/CompanyLogo.tsx"), encoding="utf-8").read()
check("tadawulgroup.sa/Resources/SEMOBILELOGOS/" in L and L.find("TV_LOGOS[base] || null") < L.find("SEMOBILELOGOS/${base}"),
      "٦ D488 (بأمر المالك: شعاراتُ تداول فيها أخطاء — الحبيب) TradingView أوّلاً وتداولُ احتياط")
M = open(os.path.join(ROOT, "backend/app/api/v1/endpoints/market.py"), encoding="utf-8").read()
E = open(os.path.join(ROOT, "frontend/src/components/market/EventsList.tsx"), encoding="utf-8").read()
check("asyncio.create_task(compute_sector_analysis())" in M, "٧ D490 شاشةُ القطاعات الفارغةُ تُطلق بناءها بنفسها")
check("ev-strip" not in E and 'className="ev-tag inline-block"' in E, "٨ D491 وسمُ الحدث سطرٌ أعلى الاسم لا شريطٌ طوليّ، والعنوانُ ينتهي بتاريخه")
print(f"{'FAIL' if fail else 'PASS'} D488 · D489 — EBITDA تداول وشعاراتُها")
sys.exit(fail)
