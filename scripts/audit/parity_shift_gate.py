#!/usr/bin/env python3
"""بوابةُ ثبات رقم اليوم (‏D649) — تجربةٌ مضبوطة: يتحرّك السعرُ 2٪ بعد المسحة (كجلسة تداول)، فهل تبقى الصفحةُ على رقم الفرز؟

قارئٌ فقط، وفي عمليّته وحدها: الأسعارُ تُزاح في الذاكرة، وكاشُ التحليل والنماذج يُفرَّغ داخلها (كأنّ حفظَه انتهى أثناء
الجلسة)، والكتابةُ معطَّلة. لا يُقاس القرارُ هنا — القرارُ يتبع السعرَ الحيّ بحقّ (سقفُ القيمة العادلة)؛ يُقاس الرقم.
  p_fv_drift    صفحاتٌ يبتعد سعرُها العادل عن الفرز > 0.5٪ لأنّ السعرَ تحرّك
  p_conf_drift  صفحاتٌ تتبدّل ثقتُها لأنّ السعرَ تحرّك"""
import asyncio, json, sys
sys.path.insert(0, "/app")
SHIFT = 1.02
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
with cache._lock:
    for k in [k for k in cache._store if k.startswith(("analysis:", "fvm:"))]:
        cache._store.pop(k, None)
from app.services import tadawul_market as TM
_ur, _rf = TM.usable_rows, TM.row_for


def _shift_row(r):
    return {**r, "price": round(r["price"] * SHIFT, 4)} if isinstance(r, dict) and isinstance(r.get("price"), (int, float)) else r


def _usable_rows(*a, **k):
    rows, *rest = _ur(*a, **k)
    return (({s: _shift_row(r) for s, r in rows.items()} if isinstance(rows, dict) else rows), *rest)


TM.usable_rows = _usable_rows
TM.row_for = lambda *a, **k: _shift_row(_rf(*a, **k))
from app.services.market_data import market_service
_gp = market_service.get_price


async def _get_price(*a, **k):
    p = await _gp(*a, **k)
    return _shift_row(p) if isinstance(p, dict) else (p * SHIFT if isinstance(p, (int, float)) else p)
market_service.get_price = _get_price

from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market, is_nomu
from app.services import content_engine
from app.services.analysis import analyze_company

uni = {s: m for s, m in main_market(MARKET_UNIVERSE).items() if not is_nomu(s)}
_pos = lambda v: v if isinstance(v, (int, float)) and v > 0 else None   # noqa: E731


async def main():
    store = content_engine.fund_store_load()
    sem = asyncio.Semaphore(4)

    async def one(s):
        async with sem:
            try:
                return s, await asyncio.wait_for(analyze_company(f"{s}.SR", uni[s].get("name_ar")), timeout=45)
            except Exception as e:                                 # noqa: BLE001
                return s, {"_err": type(e).__name__}
    res = dict(await asyncio.gather(*(one(s) for s in sorted(uni))))
    fvd, cfd, err, n = [], [], [], 0
    for s, a in res.items():
        if not a or "_err" in a:
            err.append(s)
            continue
        st = store.get(s) or {}
        sv = _pos(st.get("fair_value"))
        if "fair_value" not in st or sv is None:
            continue
        n += 1
        pv = _pos(a.get("fair_value"))
        if pv is None or abs(pv / sv - 1) > 0.005:
            fvd.append((s, pv, sv))
        elif a.get("fair_value_conf") != st.get("fair_value_conf"):
            cfd.append(s)
    ok = not fvd
    print(f"{'✔' if ok else '✘'} ٧ ثباتُ رقم اليوم — السعرُ +{SHIFT - 1:.0%} بعد المسحة · لها رقمٌ في الفرز {n} (تعذّرت {len(err)}) · "
          f"ابتعدت الصفحةُ عن الفرز {len(fvd)} · تبدّلت ثقتُها {len(cfd)}")
    for s, pv, sv in fvd[:8]:
        print(f"     {s} {uni[s].get('name_ar')} · الصفحة {pv} · الفرز {sv}")
    print("@@METRICS@@" + json.dumps({"p_fv_drift": len(fvd), "p_conf_drift": len(cfd), "verdict": {"٧ ثباتُ رقم اليوم": ok}},
                                     ensure_ascii=False))


asyncio.run(main())
