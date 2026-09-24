#!/usr/bin/env python3
"""مجموعةُ نماذج كلّ قطاع بالقياس — لكلّ مجموعاتِ «تداول» وللسوق كلّه بلا تفضيل. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fvm_sector_fit.py

لكلّ قطاعٍ أوراقُه التي لها هدفُ محلّلين: خطأُ المجموعة القائمة، وخطأُ النموذج الكامل،
وخطأُ كلّ نموذجٍ منفرداً، ثمّ اختيارٌ أماميٌّ جشِع (يُضاف النموذجُ الذي يخفض الوسيطَ أكثر،
ويُتوقَّف حين لا يتحسّن). والعيّنةُ الصغيرة (< 5) تُعلَّم فلا يُبنى عليها وحدها.
"""
import asyncio, collections, math, statistics, sys
sys.path.insert(0, "/app")


def err(xs):
    return math.exp(statistics.median(abs(math.log(x)) for x in xs)) - 1 if xs else float("nan")


def within(xs):
    return sum(.75 <= x <= 1.25 for x in xs) / len(xs) if xs else 0


async def main():
    from app.services import fair_value_models as F
    from app.services.market_screener import get_cached_screener
    rows = [x for x in (get_cached_screener() or [])
            if isinstance(x.get("analyst_target"), (int, float)) and x["analyst_target"] > 0]
    by = collections.defaultdict(list)
    for x in rows:
        try:
            i = await F.gather(x["symbol"])
        except Exception as e:                                     # noqa: BLE001
            print(f"✗ {x['symbol']}: {e}")
            continue
        if i:
            by[i.sector or "?"].append((x, i))
    orig = F.model_set

    def ratios(items, keys):
        if keys is not None:
            F.model_set = lambda s, a: ("قياس", keys)
        out = []
        for x, i in items:
            try:
                r = F.value(i)
            except Exception:                                      # noqa: BLE001
                r = None
            if r and isinstance(r.get("value"), (int, float)) and r["value"] > 0:
                out.append(r["value"] / x["analyst_target"])
        F.model_set = orig
        return out

    def fit(items):
        cur = ratios(items, None)
        full = ratios(items, set(F._ALL))
        single = {k: ratios(items, {k}) for k in sorted(F._ALL)}
        single = {k: v for k, v in single.items() if len(v) >= max(2, len(items) // 2)}
        chosen, best = set(), float("inf")
        while True:
            cand = None
            for k in F._ALL - chosen:
                rs = ratios(items, chosen | {k})
                if len(rs) < max(2, len(items) * 0.8):
                    continue
                e = err(rs)
                if e < best - 0.005:
                    best, cand = e, k
            if not cand:
                break
            chosen.add(cand)
        return cur, full, single, chosen, best

    allitems = [p for v in by.values() for p in v]
    print(f"أوراقٌ لها هدف: {len(allitems)} في {len(by)} قطاعاً\n")
    for sec, items in sorted(by.items(), key=lambda kv: -len(kv[1])) + [("══ السوقُ كلُّه", allitems)]:
        cur, full, single, chosen, best = fit(items)
        tag = "  ⚠ عيّنةٌ صغيرة" if len(items) < 5 else ""
        name = orig(sec, items[0][1].archetype)[0] if not sec.startswith("══") else sec
        print(f"═ {sec} · n={len(items)}{tag} · {name}")
        print(f"   القائمة  خطأ {err(cur):.0%} · ±25٪ {within(cur):.0%} · مغطّاة {len(cur)}")
        print(f"   الكاملة  خطأ {err(full):.0%} · ±25٪ {within(full):.0%} · مغطّاة {len(full)}")
        print(f"   الأفضلُ قياساً ({len(chosen)}): {sorted(chosen)} · خطأ {best:.0%}")
        print("   منفردة: " + " · ".join(f"{k} {err(v):.0%}" for k, v in sorted(single.items(), key=lambda kv: err(kv[1]))))
        print()
    return 0

sys.exit(asyncio.run(main()))
