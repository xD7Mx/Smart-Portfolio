#!/usr/bin/env python3
"""طريقةُ تقييم القطاع تُطبَّق فعلاً: النمطُ الرسميّ ومضاعفا السوق (D446).

    python3 scripts/audit/sector_method_applied.py

قال المالك: «لكلّ قطاعٍ طريقةُ تقييمٍ تجعل الموضوع أبسط». والمواصفةُ قائمةٌ
(‏`archetype_spec.VALUATION`) لكنّها لا تُطبَّق: قِيس بكاشف `fv_paths_low.py`
أنّ عيّنةً من عشرة قطاعاتٍ كلَّها «general» — القطاعُ يصل بالإنجليزية من
ياهو فلا يطابق الخريطة — ومسارُ «مضاعف الربحية العادل» غائبٌ لأنّ مضاعفَ
القطاع يُحسب من نظائر المحفظة وحدَها.

والفحصُ سلوكيّ: لقطةُ سوقٍ مصطنعةٌ بمصارفَ ومكرّراتها، وياهو صامت بلا
قطاع، ثمّ يُنادى بناءُ التحليل الحقيقيّ ويُشترط أن يصل المحرّكَ النمطُ
«bank» ووسيطُ مكرّرات النظائر، وأن يظهر مسارُ القطاع.
"""
from __future__ import annotations
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")
import asyncio, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    from app.services import analysis as AN, tadawul_market as TM, fair_value as F
    from app.services.market_data import market_service as MS
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)

PE = {"1010": 10.0, "1020": 12.0, "1030": 11.0, "1060": 13.0, "1080": 9.0, "1120": 18.0}
ROWS = {s: {"price": 20.0, "sector_en": "Banks", "pe_ratio": pe, "price_to_book": 1.4}
        for s, pe in PE.items()}
ROWS["1050"] = {"price": 21.18, "sector_en": "Banks", "pe_ratio": 10.7, "price_to_book": 1.2}
TM.usable_rows = lambda: (ROWS, False, None)
TM.row_for = lambda s: ROWS.get(str(s).replace(".SR", ""), {})
async def _none(*a, **k): return None
async def _price(*a, **k): return {"price": 21.18}
async def _info(*a, **k): return {"eps": 2.0, "book_value": 17.5, "roe": 11.4, "sector": "Basic Materials"}
P = [{"year": y, "net_income": 4.2e9 + i * 5e8, "equity": 4.5e10 + i * 2e9, "eps": 1.7 + i * .15,
      "shares_outstanding": 2.5e9, "total_debt": 1e10, "revenue": 1.3e10}
     for i, y in enumerate((2023, 2024, 2025))]
async def _fin(*a, **k): return {"periods": P}
MS.get_price, MS.get_company_info, MS.get_history, MS.get_financials = _price, _info, _none, _fin

seen = {}
_orig = F.compute
def _spy(info, price, sector_avg_pe=None, sector_avg_pb=None, **kw):
    seen.update(pe=sector_avg_pe, pb=sector_avg_pb, arch=kw.get("archetype"))
    out = _orig(info, price, sector_avg_pe, sector_avg_pb, **kw)
    seen["methods"] = [m.get("name") for m in out.get("methods") or []]
    return out
F.compute = _spy
import app.services.governance_rules as _g2
_got = {}
_o_sc = _g2.scope_for
def _sc(sector, *a, **k):
    _got["sector"] = sector
    return _o_sc(sector, *a, **k)
_g2.scope_for = _sc
try:
    asyncio.run(AN.analyze_company("1050.SR", allow_supplement=False))
except Exception as e:                                            # noqa: BLE001
    print(f"… التحليلُ رفع {type(e).__name__}: {e}")
fail = 0
def check(ok, label, det=""):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))
check(seen.get("arch") == "bank", "١ المحرّكُ يتلقّى نمطَ القطاع الرسميّ لا «general»", str(seen.get("arch")))
check(seen.get("pe") == 11.5, "٢ ومكرّرُ القطاع وسيطُ النظائر من لقطة السوق", str(seen.get("pe")))
check(any("مضاعف" in (n or "") for n in seen.get("methods") or []),
      "٣ ومسارُ مضاعف القطاع حاضرٌ في التقدير", str(seen.get("methods")))
from app.services import governance_rules as G
check(G.archetype_for(_got.get("sector")) == "bank",
      "٤ ومعيارُ درجة الجودة معيارُ المصارف لا العامّ", str(_got.get("sector")))
# ── ٥ · ولقطةٌ بلا مكرّرات — كما قِيست على الخادم (D453) ──
import app.services.tadawul_xbrl as _X
from app.services import sector_multiples as _SM
_BARE = {s: {"price": 20.0, "sector_en": "Banks"} for s in PE}
_X.for_symbol = lambda sym, kind="annual": [{"eps": 20.0 / PE.get(str(sym), 10.0),
                                            "equity": 1.4e10, "shares_outstanding": 1e9}]
_m = _SM.for_symbol("1050", rows=_BARE) or {}
check(_m.get("pe") == 11.5, "٥ ولقطةٌ بلا مكرّرات: يُحسب مكرّرُ القطاع من إفصاح XBRL", str(_m))
print(("FAIL" if fail else "PASS") + " D446 — طريقةُ تقييم القطاع مطبَّقة")
sys.exit(fail)
