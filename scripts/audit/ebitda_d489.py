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
from app.services import lastgood as _LG, dividend_yield as _DY
_LG.save("div:tadawul:0001", {"rows": [{"amount": 1.0, "eligibility": "2019-01-01"}]})
_z = _DY.resolve("0001", 10.0, {}, {})
_MK = open(os.path.join(ROOT, "backend/app/api/v1/endpoints/market.py"), encoding="utf-8").read()
check(_z == (0.0, "تداول · لا توزيعَ في 12 شهراً") and "_tadawul_changes().get(sym)" in MS and "rows = _sector_dividends_fill(rows)" in _MK,
      "٢٠ D505 لا خليةَ فارغة بلا سبب: عائدُ من لم يوزّع صفرٌ من تداول، والتغيّرُ من لقطة تداول، وتوزيعاتُ القطاع من صفوف الفرز", str(_z))
from app.services import maqasid as _MQ
from app.services.content_engine import clean_events as _CE
_ce = _CE([{"title": 'Saudi Exchange announces <span class="sar-symbol">^</span>14.52'}, {"title": "توزيع <b>1.5</b>"}])
_UI = open(os.path.join(ROOT, "frontend/src/components/common/UI.tsx"), encoding="utf-8").read()
check((_MQ.rating("1050") or {}).get("status") == "NON_COMPLIANT" and (_MQ.rating("1120") or {}).get("status") == "COMPLIANT"
      and _ce == [{"title": "توزيع 1.5"}] and "if (!tone) return null;" not in _UI,
      "٢١ D506 هلالُ الشرعية لكلّ السوق (المصرفُ التقليديّ بفحص النشاط، والمجهولُ رماديّ) ولا عنوانَ إنجليزيّاً ولا وسمَ HTML في الإفصاحات", str(_ce))
from app.services import forecasts as _FC
_ev = open(os.path.join(ROOT, "frontend/src/components/market/EventsList.tsx"), encoding="utf-8").read()
_fp = _FC.pick_forecasts([{"headline": "الراجحي المالية ترفع السعر المستهدف لسهم المراعي", "url": "u"},
                          {"headline": "المراعي تعتمد التقرير السنوي", "url": "x"}, {"headline": "ارتفاع مؤشر السوق", "url": "y"}])
check(len(_fp) == 1 and _fp[0]["kind"] == "سعرٌ مستهدف" and 'onClick={() => setView("fc")}>التوقعات</button>' in _ev
      and "subscription" not in open(os.path.join(ROOT, "backend/app/services/forecasts.py"), encoding="utf-8").read().split('"""')[2],
      "٢٢ D507 «التوقعات» تبويبٌ ثالثٌ في مفكرة السوق من مصادرَ عامّةٍ مقيسة (لا صفحاتِ المشتركين) — وما ليس توقّعاً لا يدخله", str(_fp))
from app.services import content_engine as _C
_st = {k: {"symbol": "2280", "date": "2026-09-28", "type": "dividend", "title": t, "source": src}
       for k, t, src in (("a", "x", "Google"), ("b", "y", "تداول"), ("c", "z", "أرقام"))}
_o1, _o2 = _C._cal_load_store, _C._universe_pairs
_C._cal_load_store, _C._universe_pairs = (lambda: _st), (lambda: [("2280", "المراعي")])
try:
    _src = [e["source"] for e in _aio.run(_C.market_wide_events())]
finally:
    _C._cal_load_store, _C._universe_pairs = _o1, _o2
_CEs = open(os.path.join(ROOT, "backend/app/services/content_engine.py"), encoding="utf-8").read()
check(_src == ["تداول"] and _CEs.find("real += await fetch_argaam_news()") < _CEs.find("real += _google"),
      "٢٣ D508 المصادرُ بترتيب المالك: تداول ← أرقام ← غيرُهما — الحدثُ المكرَّر بنسخة الأعلى رتبة، وأخبارُ أرقام قبل Google", str(_src))
from app.services import tadawul_market as _TM
import time as _time
_LG.save(_TM.STORE_KEY, {"rows": {"2222": {"price": 25.5, "change_pct": -1.2}}, "at": __import__("datetime").datetime.fromtimestamp(_time.time() - 2 * 86400, __import__("datetime").timezone.utc).isoformat()})
check(_TM.snapshot() == {} and MSm._tadawul_changes().get("2222") == -1.2,
      "٢٤ D509 تغيّرُ آخر جلسةٍ يُقرأ بعد الإغلاق من آخر قراءةٍ محفوظة — لا من اللقطة اللحظية الصارمة الفارغة", str(MSm._tadawul_changes()))
from app.core.config import settings as _S
from app.services.market_data import SahmakAdapter as _SA
from app.services import sahmak_library as _SL
_S.SAHMAK_API_KEY = "test-key"
_calls = []
class _NoNet:
    def __init__(self, *a, **k): _calls.append(1)
    async def __aenter__(self): raise RuntimeError("شبكة")
    async def __aexit__(self, *a): return False
_oh = _SL.httpx.AsyncClient
_SL.httpx.AsyncClient = _NoNet
try:
    _lib = _aio.run(_SL.company_library())
finally:
    _SL.httpx.AsyncClient = _oh
check(_S.SAHMAK_ENABLED is False and _SA().api_key is None and not _calls,
      "٢٥ D510 «سهمك» موقوفٌ كلُّه بمفتاحٍ واحد — لا نداءَ حتى مع وجود المفتاح (تداول ثمّ أرقام)", f"calls={len(_calls)}")
_S.SAHMAK_API_KEY = None
_ipsets = [v for k, (_n, v) in F.MODEL_SETS.items() if k not in ("Banks", "Insurance", "REITs")]
check(all("peer_yield" not in v and "peer_ev_sales" in v for v in _ipsets),
      "٢٦ D511 مجموعاتُ InvestingPro فيها «مكرّرُ الإيرادات لقيمة المنشأة» لا «عائدُ التوزيع مقابل الأقران» (إكسترا 296.91 على سعر 61.45)",
      str([k for k, (_n, v) in F.MODEL_SETS.items() if "peer_yield" in v]))
_AN = open(os.path.join(ROOT, "backend/app/services/analysis.py"), encoding="utf-8").read()
_AP = open(os.path.join(ROOT, "frontend/src/components/analysis/AnalysisPanel.tsx"), encoding="utf-8").read()
check("_new = await _fvm_for(" in _AN and _AN.find("_new = await _fvm_for(") < _AN.find('"fair_value": _fv.get("value")')
      and "{fvmLoading ? (" in _AP,
      "٢٧ D512 سعرٌ عادلٌ واحدٌ من محرّكٍ واحد: التحليلُ والفرزُ من محرّك InvestingPro، ولا رقمَ يُرسم قبل جوابه ثمّ يُستبدَل")
from app.services import tadawul_xbrl as _XB
_fd = _XB._fill_depreciation([{"as_of": "2025-12-31", "revenue": 4e9, "ebit": 8e8}],
                             {"quarterly": [{"as_of": "2025-06-30", "revenue": 2e9, "depreciation": 1.2e8}]})
check(_fd[0].get("depreciation") == 2.4e8 and _fd[0].get("ebitda") == 1.04e9 and "مشتقٌّ" in (_fd[0].get("depreciation_source") or "")
      and "adjustments for depreciation expense" in _XB.LABELS["_dep_ppe"],
      "٢٨ D514 سنةٌ من استكمال PDF بلا إهلاك تأخذه بنسبته إلى الإيراد من أقرب فترةٍ منشورة (موسوماً مشتقّاً) — وصياغاتُ معادن وكيان والشمالية بالحرف", str(_fd))
import json as _json
_dir = _json.load(open(os.path.join(ROOT, "backend/app/data/saudi_directory.json"), encoding="utf-8"))
_fe = open(os.path.join(ROOT, "frontend/src/data/saudiCompanies.ts"), encoding="utf-8").read()
check(all(k in _dir and f'symbol: "{k}"' in _fe for k in ("4328", "6022", "9537")),
      "٢٩ D515 كلُّ شركةٍ في لقطة «تداول» في دليلنا باسمها العربيّ (أرماح 6022 كانت تظهر بالإنجليزية)")
_orig_fr, _orig_min = _TM.fetch_rows, _TM.MIN_ROWS
async def _fake_rows(page=None):
    if page == _TM.ETF_PAGE:   # D518: الصفحةُ قد تعيد أسهمَ الرئيسيّ معها — لا تُعدّ صناديق
        return [{"companyRef": "9405", "lastTradePrice": 21.91, "precentChange": -2.32},
                {"companyRef": "2222", "lastTradePrice": 25.5}], None
    if page == _TM.NOMU_PAGE:
        return [], "لا نمو"
    return [{"companyRef": "2222", "lastTradePrice": 25.5, "precentChange": 0.4}], None
_TM.fetch_rows, _TM.MIN_ROWS = _fake_rows, 1
try:
    _rf = _aio.run(_TM.refresh())
    _rows = (_LG.load(_TM.STORE_KEY) or {}).get("rows") or {}
finally:
    _TM.fetch_rows, _TM.MIN_ROWS = _orig_fr, _orig_min
_bd = (_LG.load(_TM.STORE_KEY) or {}).get("boards") or {}
check("9405" in _rows and _rows["9405"].get("price") == 21.91 and "2222" in _rows and _bd.get("main") == 1 and _bd.get("etf") == 1,
      "٣٠ D517 صناديقُ المؤشرات (94xx) في لقطة «تداول» من صفحة etfs-market-watch — كانت «بلا بيانات»", str(sorted(_rows)) + f" boards={_bd}")
_A5 = [{"year": y, "as_of": f"{y}-12-31", "revenue": None, "net_income": 3.5e8, "equity": 9.5e8} for y in (2023, 2024, 2025)]
_i5 = F.Inputs(symbol="X", price=8.65, shares=1.01e8, annual=_A5, ttm=dict(_A5[-1]), balance={"equity": 9.5e8},
               ttm_source="t", sector="Food & Beverages", hist={"pb": [1.0, 1.2, 1.4], "pe": [3, 4, 5]}, peers={})
_r5 = F.value(_i5)
_i5.stale_days = 900
check(_r5.get("value") and _r5.get("weights_kind") == "equity_only" and F.value(_i5).get("value") is None,
      "٣١ D519 شركةٌ بلا إيرادٍ منشور تُقدَّر بالدفترية والربحية وحدهما (5 شركاتٍ كانت بلا سعرٍ عادل) — والقديمةُ تبقى محجوبة", str(_r5.get("value")))
from app.services import tadawul_sync as _TS
async def _fake_ar(page=None, locale="en"):
    if locale != "ar":
        return [], "بلا عربية"
    if page == _TM.NOMU_PAGE:
        return [{"companySymbol": "9532", "companyName": "شركة مصنع مياه الجوف الصحية"},
                {"companySymbol": "9999", "companyName": "شركة ليست في الدليل"}], None
    return ([{"companySymbol": "4130", "companyName": "شركة درب السعودية الأستثمارية"},
             {"companySymbol": "4083", "companyName": "الشركة المتحدة الدولية القابضة"}]
            + [{"companySymbol": str(5000 + i), "companyName": f"شركة س{i}"} for i in range(_TS.MIN_OFFICIAL)]), None
_TM.fetch_rows = _fake_ar
_ov0 = _TS.overlay(); _ov0["9998"] = {"name": "مزروعةٌ خطأً", "name_src": "تداول"}; _TS._save_overlay(_ov0)
try:
    _so = _aio.run(_TS.sync_official())
finally:
    _TM.fetch_rows = _orig_fr
_on = _TS.official_overlay()
_IX = open(os.path.join(ROOT, "frontend/src/index.tsx"), encoding="utf-8").read()
check(_so.get("ok") and _on.get("4130") == "درب السعودية الأستثمارية" and _on.get("4083") == "الشركة المتحدة الدولية القابضة"
      and _on.get("9532") == "مصنع مياه الجوف الصحية" and "9999" not in _TS.overlay() and "9998" not in _TS.overlay() and "applyOfficialNames(" in _IX and "official-names" in open(os.path.join(ROOT, "frontend/src/services/api.ts"), encoding="utf-8").read(),
      "٣٢ D520·D523 الاسمُ الرسميّ من «تداول» يُكتب فوق الدليل لكلّ رمزٍ يعرفه (استبدالاً لا إكمالاً ولا إضافة) ويُقلَع ما زُرع خطأً، وتطبّقه الواجهةُ قبل الرسم", str({k: _on.get(k) for k in ("4130", "4083", "9532")}))
from app.services import tasi_stars as _ST
_base = {"fair_value_upside_pct": 30.0, "fair_value_conf": "متوسطة", "finance_score": 80.0, "red_lines": 0,
         "stmt_age_days": 100, "sharia": "COMPLIANT", "price": 10.0, "fair_value": 13.0}
_rows = [{**_base, "symbol": "1001"},
         {**_base, "symbol": "1002", "fair_value_upside_pct": 10.0},
         {**_base, "symbol": "1003"},
         {**_base, "symbol": "1004", "sharia": "NON_COMPLIANT"},
         {**_base, "symbol": "1005", "fair_value_conf": "منخفضة"},
         {**_base, "symbol": "1006", "stmt_age_days": 400},
         {**_base, "symbol": "1007", "finance_score": 60.0}]
_sel = _ST.select(_rows, {s: (5.0 if s == "1003" else 25.0) for s in ("1001", "1002", "1003", "1004", "1005", "1006", "1007")}, 8.0)
_pf = _ST.performance({"members": [{"symbol": "1001", "start_price": 10.0}, {"symbol": "1002", "start_price": 20.0}], "tasi_start": 100.0, "level_start": 100},
                      [{"symbol": "1001", "price": 11.0}, {"symbol": "1002", "price": 19.0}], 102.0)
from datetime import date as _dt, timedelta as _td
_tp = [{"date": (_dt(2025, 9, 29) + _td(days=7 * i)).isoformat(), "close": 100 + i} for i in range(53)]
_r12 = _ST._ret_12m(_tp)
_sel_l = _ST.select(_rows, {"1001": 25.0}, 8.0, large={"2222"})
_lc = _ST.large_caps({"2222": {"market_cap": 9e12}, "1001": {"market_cap": 1e9}, "9536": {"market_cap": 5e12}})
check([m["symbol"] for m in _sel] == ["1001"] and _sel_l == [] and _r12 is not None and abs(_r12 - 52.0) < 0.01 and _ST._ret_12m(_tp[:10]) is None and "9536" not in _lc and _ST.REBALANCE_DAYS == 30 and _sel[0]["excess"] == 17.0 and _pf["ret"] == 2.5 and _pf["tasi_ret"] == 2.0 and _pf["level"] == 102.5,
      "٣٣ D522 نجوم تاسي: متفوّقٌ على تاسي في 12 شهراً + عادلٌ فوق السعر ≥15٪ + ثقةٌ ودرجةٌ وقوائمُ حديثةٌ وشرعيّ — وأداءٌ متساوي الأوزان مقابلَ تاسي منذ التثبيت", str([m["symbol"] for m in _sel]) + f" {_pf}")
print(f"{'FAIL' if fail else 'PASS'} D488 · D489 — EBITDA تداول وشعاراتُها")
sys.exit(fail)
