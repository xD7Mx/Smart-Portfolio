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
SA = open(os.path.join(ROOT, "backend/app/services/sector_analysis.py"), encoding="utf-8").read()
DY = open(os.path.join(ROOT, "backend/app/services/dividend_yield.py"), encoding="utf-8").read()
check("_dps_tadawul(sym) or" in SA and DY.find("_dps_tadawul(base)") < DY.find('src.get("dividend_yield")'), "١٠ D493 تداولُ أوّلاً والمخزنُ احتياط — في القطاعات والأسهم")
check("_dps_tadawul(sym)" in SA and 'r.get("eligibility")' in SA, "٩ D492 عائدُ توزيع القطاع من جدول تداول حين يغيب من الأساسيات")
MS = open(os.path.join(ROOT, "backend/app/services/market_screener.py"), encoding="utf-8").read()
check("_t = _tadawul_ratios(sym" in MS and '_t.get("pe_ratio") if' in MS, "١١ D494 أعمدةُ الفرز (المكرّر · الدفترية · العائد على الحقوق) من قوائم تداول أوّلاً")
from app.services import market_screener as MSm
check(MSm._tadawul_ratios("0000", 10) == {}, "١١ب ورمزٌ بلا قوائم يعود فارغاً فيملؤه الاحتياط")
NC = open(os.path.join(ROOT, "frontend/src/components/analysis/NativeChart.tsx"), encoding="utf-8").read()
check('"year" in tm' in NC and "marketApi.saveDrawings(symbol, d)" in NC and '@router.put("/drawings/{symbol}"' in M,
      "١٢ D496 الرسمُ يُحفظ بزمن الشمعة لا بكائن المكتبة، وعلى الخادم لكلّ شركةٍ حتى يُمسح")
_A = [{"year": y, "as_of": f"{y}-12-31", "revenue": 2e10, "net_income": 0.22 * 24.08e9, "equity": 24.08e9, "eps": 5.3} for y in (2023, 2024, 2025)]
_i = F.Inputs(symbol="X", price=64.75, shares=1e9, annual=_A, ttm=dict(_A[-1]), balance={"equity": 24.08e9},
              ttm_source="t", archetype="bank", sector="Banks", peers={"pe": [10] * 5, "pb": [1.08] * 5, "ps": [3.19] * 5})
_v = {m["key"]: m["value"] for m in F.value(_i)["models"]}
check(abs(_v.get("peer_pb", 0) - 68.5) < 1.5 and abs(_v.get("peer_pe", 0) - 68.5) < 1.5,
      "١٣ D497 المضاعفُ المبرَّر (طريقةُ InvestingPro): مصرفٌ عائدُه 22٪ ودفتريته 24.08 ← ~68.5 (InvestingPro للراجحي 67.78–69.72) لا 26 بوسيط القطاع", str(_v))
FV = open(os.path.join(ROOT, "backend/app/services/fair_value_models.py"), encoding="utf-8").read()
check("or (beta_for(_ar) if _ar else None)" in FV, "١٤ D498 بيتا القطاع تُبحث بالاسم العربيّ أيضاً — لا كلفةَ حقوقٍ ثابتة 10٪ للجميع")
_A2 = [{"year": y, "as_of": f"{y}-12-31", "revenue": 2e10, "net_income": 1e9, "equity": 8e9, "eps": 1.0} for y in (2023, 2024, 2025)]
_i2 = F.Inputs(symbol="X", price=20, shares=1e9, annual=_A2, ttm=dict(_A2[-1]), balance={"equity": 8e9}, ttm_source="t",
               sector="Energy", hist={"pe": [25, 27, 30]}, peers={})
_v2 = {m["key"]: m["value"] for m in F.value(_i2)["models"]}
check(abs(_v2.get("peer_pe", 0) - 27.0) < 0.01 and "await _hist_multiples(sym" in FV,
      "١٥ D500 المكرّرُ من مضاعف الشركة التاريخيّ أوّلاً (وسيط 27× × ربحية 1 = 27) — طريقةُ InvestingPro", str(_v2))
_rd = MS[MS.find("async def refresh_derived"):]
check("_tadawul_ratios(sym.replace" in _rd, "١٦ D501 مضاعفاتُ تداول في الفرز عند كلّ طلبٍ لا في المسحة الليلية وحدها")
_rd2 = _rd[:_rd.find("_tadawul_prices().get(sym)")]
check("pd = None" in _rd2[-200:] and "_movers_changes().get(sym)" in _rd,
      "١٧ D502 التغيّرُ اليوميّ لا يسقط حين يأتي السعرُ من تداول (كان pd غيرَ معرَّف) ويُقرأ من مسح المحرّكين")
import asyncio as _aio
from app.services import market_data as _MD
class _Y:
    async def _fetch_chart_points(self, *a, **k):
        return [{"date": f"{y}-12-31", "close": 20.0} for y in (2021, 2022, 2023, 2024, 2025)]
_orig = _MD.market_service._yahoo
_MD.market_service._yahoo = lambda: _Y()
try:
    _A3 = [{"year": y, "as_of": f"{y}-12-31", "net_income": 1e9, "equity": 1e10, "revenue": 5e9,
            "shares_outstanding": 1e6} for y in (2021, 2022, 2023, 2024, 2025)]   # بالآلاف
    _h = _aio.run(F._hist_multiples("X", _A3, 1e9))
finally:
    _MD.market_service._yahoo = _orig
check(_h.get("pe") and abs(_h["pe"][0] - 20.0) < 0.01 and abs(_h["pb"][0] - 2.0) < 0.01,
      "١٨ D503 المضاعفُ التاريخيّ بعدد الأسهم الحاليّ مع أسعارٍ معدَّلة — لا عددَ القوائم القديم (كان 0.02× لدار الأركان)", str(_h))
_A4 = [{"year": y, "as_of": f"{y}-12-31", "revenue": 2e10, "net_income": 2.46e9, "equity": 20.82e9, "eps": 2.46,
        "operating_income": 3.1e9, "ocf": 4e9, "capex": 2e9} for y in (2023, 2024, 2025)]
_i4 = F.Inputs(symbol="X", price=43.22, shares=1e9, annual=_A4, ttm=dict(_A4[-1]), balance={"equity": 20.82e9},
               ttm_source="t", sector="Food & Beverages", dps_ttm=1.15, peers={})
_d = {m["key"]: m for m in F.value(_i4)["models"]}
_g = next((float(x[1].rstrip("%")) for x in (_d.get("ddm_stable") or {}).get("assumptions", []) if x[0] == "النموُّ المستدام"), 0)
check(_g > 3.6 and (_d.get("ddm_stable") or {}).get("value", 0) > 30,
      "١٩ D504 خصمُ التوزيعات بطريقة InvestingPro: النموُّ العائدُ × الاحتجاز بلا سقف 3.5٪ (المراعي ~62 لا 20.7)", str({k: _d[k]["value"] for k in _d if k.startswith("ddm")}) + f" g={_g}")
print(f"{'FAIL' if fail else 'PASS'} D488 · D489 — EBITDA تداول وشعاراتُها")
sys.exit(fail)
