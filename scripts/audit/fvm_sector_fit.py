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
    F.MIN_MODELS = 0          # تُقاس المجموعةُ وحدَها — لا يستكملها حدُّ النشر
    from app.services.market_screener import get_cached_screener
    rows = [x for x in (get_cached_screener() or [])
            if isinstance(x.get("analyst_target"), (int, float)) and x["analyst_target"] > 0]
    by = collections.defaultdict(list)
    why = collections.Counter()
    for x in rows:
        try:
            i = await F.gather(x["symbol"])
        except Exception as e:                                     # noqa: BLE001
            print(f"✗ {x['symbol']}: {e}")
            continue
        if not i:
            why["لا مدخلات (gather)"] += 1
            continue
        by[i.sector or "?"].append((x, i))
        r0 = F.value(i)
        if not (r0 or {}).get("value"):
            why[f"{i.sector}: {(r0 or {}).get('reason') or 'لا نموذجَ صالحاً'} · عمرُ القوائم {i.stale_days}"] += 1
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

    # نظريةٌ لا يتجاوزها القياس: المصرفُ والتأمينُ لا تدفّقَ حرٌّ لهما ولا قيمةَ منشأة.
    FIN_BAN = F._DCF | {"epv", "peer_ev_ebit", "peer_ev_sales", "peer_pocf"}
    def pool(sec):
        return F._ALL - FIN_BAN if sec.startswith(("Banks", "Insurance", "Financial")) else set(F._ALL)

    memo = {}
    def r1(x, i, keys):
        k = (x["symbol"], frozenset(keys))
        if k not in memo:
            F.model_set = lambda s, a: ("قياس", keys)
            try:
                r = F.value(i)
            except Exception:                                      # noqa: BLE001
                r = None
            F.model_set = orig
            memo[k] = (r["value"] / x["analyst_target"]) if (r and isinstance(r.get("value"), (int, float)) and r["value"] > 0) else None
        return memo[k]

    def rs(items, keys):
        return [v for v in (r1(x, i, keys) for x, i in items) if v]

    def greedy(items, cand):
        chosen, best = set(), float("inf")
        while cand - chosen:
            scored = []
            for k in cand - chosen:
                v = rs(items, chosen | {k})
                if len(v) >= max(2, len(items) * 0.8):
                    scored.append((err(v), k))
            if not scored:
                break
            e, k = min(scored)
            if len(chosen) >= 3 and e >= best - 0.005:
                break
            chosen.add(k); best = min(best, e) if len(chosen) > 3 else e
        return chosen

    def loo(items, cand):
        out = []
        for j, (x, i) in enumerate(items):
            ks = greedy(items[:j] + items[j + 1:], cand)
            v = r1(x, i, ks) if ks else None
            if v:
                out.append(v)
        return out

    def fit(items, sec, cv=True):
        cur = ratios(items, None)
        full = ratios(items, set(F._ALL))
        single = {k: rs(items, {k}) for k in sorted(F._ALL)}
        single = {k: v for k, v in single.items() if len(v) >= max(2, len(items) // 2)}
        chosen = greedy(items, pool(sec))
        best = err(rs(items, chosen))
        cvr = loo(items, pool(sec)) if cv else []
        return cur, full, single, chosen, best, cvr

    print("أسبابُ غياب القيمة:")
    for k, v in why.most_common():
        print(f"   {v:3} × {k}")
    PROPOSE = {}
    allitems = [p for v in by.values() for p in v]
    print(f"أوراقٌ لها هدف: {len(allitems)} في {len(by)} قطاعاً\n")
    for sec, items in sorted(by.items(), key=lambda kv: -len(kv[1])) + [("══ السوقُ كلُّه", allitems)]:
        cur, full, single, chosen, best, cvr = fit(items, sec, cv=len(items) <= 40)
        tag = "  ⚠ عيّنةٌ صغيرة" if len(items) < 5 else ""
        name = orig(sec, items[0][1].archetype)[0] if not sec.startswith("══") else sec
        print(f"═ {sec} · n={len(items)}{tag} · {name}")
        print(f"   القائمة  خطأ {err(cur):.0%} · ±25٪ {within(cur):.0%} · مغطّاة {len(cur)}")
        print(f"   الكاملة  خطأ {err(full):.0%} · ±25٪ {within(full):.0%} · مغطّاة {len(full)}")
        print(f"   الأفضلُ قياساً ({len(chosen)}): {sorted(chosen)} · خطأ داخل العيّنة {best:.0%}")
        if cvr:
            verdict = "يُعتمد" if (len(items) >= 5 and err(cvr) < err(cur) - 0.02) else "لا يُعتمد — القائمةُ أمتن"
            print(f"   خارج العيّنة (ترك واحد): خطأ {err(cvr):.0%} · ±25٪ {within(cvr):.0%} مقابل القائمة {err(cur):.0%} → {verdict}")
            if verdict == "يُعتمد":
                PROPOSE[sec] = sorted(chosen)
        print("   منفردة: " + " · ".join(f"{k} {err(v):.0%}" for k, v in sorted(single.items(), key=lambda kv: err(kv[1]))))
        print()
    print("المقترح:", PROPOSE)
    return 0

sys.exit(asyncio.run(main()))
