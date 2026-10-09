#!/usr/bin/env python3
"""كاشفُ تقرير الشركة مقابل المحرّك (سؤالُ المالك 2026-10-09) — قارئٌ فقط: الكتابةُ في الكاش والمخازن معطَّلة.

لكلّ شركات السوق الرئيسيّ: «السعرُ المستهدف خلال 12 شهراً» في ترويسة تقرير الشركة (`quarter_report.build`) مقابل هدف
صفحة السهم (تفاصيلُ النماذج — `/fair-value-models`)، والسعرُ العادل المعروض في الصفحة مقابل الفرز، وما يعرضه التقريرُ
لشركةٍ حجب المحرّكُ رقمَها."""
import asyncio, json, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market, is_nomu
from app.services.content_engine import fund_store_load
from app.services.quarter_report import build
from app.api.v1.endpoints.market import get_fair_value_models

uni = {s: m for s, m in main_market(MARKET_UNIVERSE).items() if not is_nomu(s)}
store = fund_store_load()
_pos = lambda v: v if isinstance(v, (int, float)) and v > 0 else None   # noqa: E731


def _data(r):
    body = getattr(r, "body", None)
    return (json.loads(body) if body else r).get("data") or {}


async def main():
    sem = asyncio.Semaphore(4)

    async def one(s):
        async with sem:
            try:
                rep = await asyncio.wait_for(build(s), timeout=60)
                page = _data(await get_fair_value_models(s))
                return s, rep, page
            except Exception as e:                                 # noqa: BLE001
                return s, {"_err": f"{type(e).__name__}: {str(e)[:60]}"}, {}
    res = await asyncio.gather(*(one(s) for s in sorted(uni)))
    mis, shown_withheld, fv_mis, err, n = [], [], [], [], 0
    for s, rep, page in res:
        if "_err" in rep:
            err.append((s, rep["_err"]))
            continue
        n += 1
        rt = _pos((rep.get("header") or {}).get("target_12m"))
        pt = _pos(page.get("target_12m")) if _pos(page.get("value")) else None
        if (rt is None) != (pt is None) or (rt and pt and abs(rt / pt - 1) > 0.005):
            mis.append((s, rt, pt))
        if rt and _pos((store.get(s) or {}).get("fair_value")) is None and "fair_value" in (store.get(s) or {}):
            shown_withheld.append((s, rt, (store.get(s) or {}).get("fair_value_unavailable")))
        st = store.get(s) or {}
        rf, sf = _pos((rep.get("header") or {}).get("fair_value")), _pos(st.get("fair_value"))
        if "fair_value" in st and ((rf is None) != (sf is None) or (rf and sf and abs(rf / sf - 1) > 0.005)):
            fv_mis.append((s, rf, sf))
    print(f"تقاريرُ قِيست {n} (تعذّرت {len(err)})")
    print(f"✘ هدفُ التقرير ≠ هدف صفحة السهم: {len(mis)}" if mis else "✔ هدفُ التقرير = هدف صفحة السهم في كلّ الشركات")
    for s, rt, pt in mis[:15]:
        print(f"     {s} {uni[s].get('name_ar')} · التقرير {rt} · الصفحة {pt}")
    print(f"{'✘' if shown_withheld else '✔'} تقاريرُ تعرض هدفاً لشركةٍ حجب المحرّكُ رقمَها: {len(shown_withheld)}")
    for s, rt, why in shown_withheld[:12]:
        print(f"     {s} {uni[s].get('name_ar')} · هدفُ التقرير {rt} · والمحرّكُ: {str(why)[:70]}")
    print(f"{'✘' if fv_mis else '✔'} السعرُ العادل في التقرير ≠ الفرز: {len(fv_mis)}")
    for s, rf, sf in fv_mis[:10]:
        print(f"     {s} {uni[s].get('name_ar')} · التقرير {rf} · الفرز {sf}")
    for s, e in err[:8]:
        print(f"     تعذّر {s}: {e}")
    print("@@REPORT@@" + json.dumps({"n": n, "mismatch": len(mis), "withheld_shown": len(shown_withheld), "fv_mismatch": len(fv_mis), "err": len(err)}))


asyncio.run(main())
