#!/usr/bin/env python3
"""كاشفُ جاهزية التسليم — قارئٌ فقط (الكتابةُ في الكاش والمخازن معطَّلةٌ داخل هذه العمليّة).

١ تطابقُ الشاشات: ما تعرضه صفحةُ الشركة (`analyze_company` كما تناديه الصفحة) مقابل ما يعرضه الفرزُ والمختبر
  (مخزنُ المسحة) — السعرُ العادل والثقة — لكلّ شركات السوق الرئيسيّ.
٢ سلامةُ مدخلات البعيدة عن سعرها: عددُ الأسهم مقابل القيمة السوقية، والربحيةُ والدفترية الضمنيّتان، ونماذجُها."""
import asyncio, collections, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None            # لا كتابة
lastgood.save = lambda *a, **k: None
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.services.content_engine import fund_store_load
from app.services.analysis import analyze_company
from app.services import fair_value_models as FM

uni = main_market(MARKET_UNIVERSE)
store = fund_store_load()
deep = lastgood.load("governance:deep") or {}


async def page(sym, sem):
    async with sem:
        try:
            return sym, await asyncio.wait_for(analyze_company(f"{sym}.SR", uni[sym].get("name_ar")), timeout=40)
        except Exception as e:                                     # noqa: BLE001
            return sym, {"_err": f"{type(e).__name__}: {str(e)[:80]}"}


def same(a, b):
    if a is None or b is None:
        return a is None and b is None
    return abs(a / b - 1) <= 0.005 if b else a == b


async def main():
    sem = asyncio.Semaphore(4)
    res = dict(await asyncio.gather(*(page(s, sem) for s in sorted(uni))))
    err = {s: a["_err"] for s, a in res.items() if "_err" in a}
    fv_mis, conf_mis, dec_mis = [], [], []
    for s, a in res.items():
        if "_err" in a or not a:
            continue
        st = store.get(s) or {}
        pv, sv = a.get("fair_value"), st.get("fair_value") if isinstance(st.get("fair_value"), (int, float)) else None
        if not same(pv, sv):
            fv_mis.append((s, pv, sv, a.get("fair_value_conf"), st.get("fair_value_conf"),
                           a.get("fair_value_unavailable_reason") or "", st.get("fair_value_unavailable") or ""))
        elif pv is not None and a.get("fair_value_conf") != st.get("fair_value_conf"):
            conf_mis.append((s, a.get("fair_value_conf"), st.get("fair_value_conf")))
        d = (deep.get(s) or {}).get("decision") if isinstance(deep.get(s), dict) else None
        dl = (d.get("label") if isinstance(d, dict) else d)
        pl = (a.get("decision") or {}).get("label") if isinstance(a.get("decision"), dict) else a.get("decision")
        if dl and pl and dl != pl:
            dec_mis.append((s, pl, dl))
    n = len(res) - len(err)
    print(f"١ تطابقُ الشاشات — قِيست {n} صفحةً (تعذّرت {len(err)})")
    print(f"   السعرُ العادل: الصفحةُ ≠ الفرز في {len(fv_mis)} · الثقةُ وحدها في {len(conf_mis)} · القرارُ في {len(dec_mis)}")
    for s, pv, sv, pc, sc, pr, sr in sorted(fv_mis, key=lambda x: x[0])[:40]:
        print(f"     {s} {uni[s].get('name_ar')} · الصفحة {pv} ({pc}) · الفرز {sv} ({sc})"
              + (f" · سببُ الصفحة: {pr[:60]}" if pv is None else "") + (f" · سببُ الفرز: {sr[:60]}" if sv is None else ""))
    for s, pc, sc in conf_mis[:15]:
        print(f"     ثقة {s} {uni[s].get('name_ar')} · الصفحة {pc} · الفرز {sc}")
    for s, pl, dl in dec_mis[:15]:
        print(f"     قرار {s} {uni[s].get('name_ar')} · الصفحة {pl} · الفرز {dl}")
    for s, e in list(err.items())[:10]:
        print(f"     تعذّر {s}: {e}")

    print("\n٢ سلامةُ مدخلات البعيدة عن سعرها (> 40٪ بثقةٍ متوسطةٍ فأعلى، أو > 60٪)")
    far = []
    for s, st in store.items():
        fv = st.get("fair_value")
        if s not in uni or not isinstance(fv, (int, float)):
            continue
        i = await FM.gather(s)
        if not i or not i.price:
            continue
        g = fv / i.price - 1
        if abs(g) > 0.60 or (abs(g) > 0.40 and st.get("fair_value_conf") in ("مرتفعة", "متوسطة")):
            far.append((s, i, g, st))
    from app.services.tadawul_market import row_for
    for s, i, g, st in sorted(far, key=lambda x: -abs(x[2])):
        v = FM.value(i)
        ni = (i.ttm or {}).get("net_income")
        eq = (i.balance or {}).get("equity")
        mc = (row_for(s) or {}).get("market_cap")
        print(f"   {s} {uni[s].get('name_ar')} ({uni[s].get('sector')}) · {g:+.0%} · ثقة {st.get('fair_value_conf')}")
        print(f"      السعر {i.price} · الأسهم {i.shares / 1e6:,.1f} مليون · القيمةُ السوقية من «تداول» "
              f"{(mc / 1e9 if mc else 0):,.2f} مليار ({(mc / i.price / 1e6 if mc else 0):,.1f} مليون سهم)")
        print(f"      ربحُ 12 شهراً {(ni or 0) / 1e6:,.0f} مليون ({i.ttm_source}) · P/E {(i.price * i.shares / ni) if ni else 0:.1f}"
              f" · الحقوق {(eq or 0) / 1e6:,.0f} مليون · P/B {(i.price * i.shares / eq) if eq else 0:.2f} · عمرُ القوائم {i.stale_days} يوماً")
        print("      النماذج: " + " · ".join(f"{m['key']}={m['value']:.1f}" for m in (v.get("models") or [])))
        notes = [x for x in (v.get("notes") or []) if any(w in x for w in ("تجزئة", "الأسهم", "السوق", "حديث", "قصير"))]
        if notes:
            print("      ملاحظات: " + " | ".join(notes[:4]))


asyncio.run(main())
