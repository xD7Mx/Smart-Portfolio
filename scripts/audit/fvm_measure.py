#!/usr/bin/env python3
"""المحرّكُ متعدّدُ النماذج (D468) مقابل المحللين والمحرّك القائم و«InvestingPro». قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fvm_measure.py

· العثيم 4001 نموذجاً نموذجاً (InvestingPro: 6.06 · 3.68–8.49 · المحللون 5.48 · 4.00–7.00)
· ثمّ كلُّ ورقةٍ لها هدفُ محلّلين: وسيطُ النسبة وحصّةُ ما يقع ضمن ±15٪/±25٪،
  للمحرّك الجديد وللقائم، ولكلّ عائلةٍ ونموذجٍ — فتُعايَر الأوزانُ بالقياس.
"""
import asyncio, collections, math, statistics, sys
sys.path.insert(0, "/app")


def stat(xs):
    if not xs:
        return "—"
    return (f"n={len(xs)} · وسيطُ النسبة {statistics.median(xs):.2f} · ±15٪ {sum(.85<=x<=1.15 for x in xs)/len(xs):.0%}"
            f" · ±25٪ {sum(.75<=x<=1.25 for x in xs)/len(xs):.0%} · وسيطُ الخطأ {math.exp(statistics.median(abs(math.log(x)) for x in xs))-1:.0%}")


async def main():
    from app.services import fair_value_models as F
    r = await F.for_symbol("4001") or {}
    print(f"═ 4001: {r.get('value')} ({r.get('low')}–{r.get('high')}) · عدمُ اليقين {r.get('uncertainty')} · نماذج {r.get('count')} · أقران {r.get('peers')}")
    for m in r.get("models") or []:
        print(f"   {m['name'][:44]:46} {m['value']:7.2f}  ({m['low']:.2f}–{m['high']:.2f})")
    for e in r.get("excluded") or []:
        print(f"   ✗ {e['name']} {e['value']} — {e['excluded']}")
    print("   العائلات:", [(f['name'], f['value'], f['weight']) for f in r.get('families') or []])
    print("   ملاحظات:", r.get("notes"), r.get("rates"), r.get("ttm_source"))

    from app.services.market_screener import get_cached_screener
    from app.services.statement_merge import archetype_of
    rows = [x for x in (get_cached_screener() or [])
            if isinstance(x.get("analyst_target"), (int, float)) and x["analyst_target"] > 0]
    new, old = collections.defaultdict(list), collections.defaultdict(list)
    per_model, per_fam = collections.defaultdict(list), collections.defaultdict(list)
    fam_arch = collections.defaultdict(lambda: collections.defaultdict(list))
    worst = []
    pairs = collections.defaultdict(list)          # (جديد، قائم، هدف، ke، عائدُ توزيع)
    for x in rows:
        s, at = x["symbol"], x["analyst_target"]
        a = archetype_of(s) or "?"
        v = await F.for_symbol(s) or {}
        if isinstance(v.get("value"), (int, float)) and v["value"] > 0:
            new[a].append(v["value"] / at); new["*"].append(v["value"] / at)
            worst.append((abs(math.log(v["value"] / at)), s, v["value"], at, x.get("fair_value")))
            for m in v.get("models") or []:
                per_model[m["key"]].append(m["value"] / at)
            for f in v.get("families") or []:
                per_fam[f["family"]].append(f["value"] / at)
                fam_arch[a][f["family"]].append(f["value"] / at)
        fv = x.get("fair_value")
        if isinstance(fv, (int, float)) and fv > 0:
            old[a].append(fv / at); old["*"].append(fv / at)
        if isinstance(v.get("value"), (int, float)) and v["value"] > 0 and isinstance(fv, (int, float)) and fv > 0:
            ke = (v.get("rates") or {}).get("ke") or 0.10
            dy = (x.get("dividend_yield") or 0) / 100 if (x.get("dividend_yield") or 0) > 1 else (x.get("dividend_yield") or 0)
            pairs[a].append((v["value"], fv, at, ke, dy))
    print(f"\nأوراقٌ لها هدف: {len(rows)}")
    print("الجديد الكلّ:", stat(new["*"]))
    print("القائم الكلّ:", stat(old["*"]))
    for a in sorted(k for k in new if k != "*"):
        print(f"  {a:20} جديد {stat(new[a])}\n  {'':20} قائم {stat(old[a])}")
    print("\nالعائلات:")
    for k, v in per_fam.items():
        print(f"  {k:12} {stat(v)}")
    print("النماذج:")
    for k, v in sorted(per_model.items()):
        print(f"  {k:16} {stat(v)}")
    print("\nأوزانٌ مقترحة لكلّ نمط (عكسُ وسيط الخطأ لكلّ عائلة):")
    for a, fams in sorted(fam_arch.items()):
        inv = {f: 1 / max(statistics.median(abs(math.log(x)) for x in xs), 0.05) for f, xs in fams.items() if len(xs) >= 3}
        tot = sum(inv.values()) or 1
        print(f"  {a:20} " + " · ".join(f"{f}={inv[f]/tot:.2f} (وسيط {statistics.median(fams[f]):.2f})" for f in inv))
    def err(xs):
        return statistics.median(abs(math.log(x)) for x in xs) if xs else float("nan")
    print("\nالمزيج α·جديد + (1−α)·قائم — وسيطُ الخطأ لكلّ α (والهدفُ لاثني عشر شهراً = القيمة × (1+ke−عائد)):")
    allp = [p for ps in pairs.values() for p in ps]
    for a, ps in sorted(pairs.items(), key=lambda kv: -len(kv[1])) + [("*الكلّ", allp)]:
        row = []
        for al in (0, .25, .5, .75, 1):
            row.append(f"α={al}: {math.exp(err([(al*n+(1-al)*o)/t for n, o, t, k, d in ps]))-1:.0%}")
        best = min((0, .25, .5, .75, 1), key=lambda al: err([(al*n+(1-al)*o)/t for n, o, t, k, d in ps]))
        tgt = [((best*n+(1-best)*o)*(1+k-d))/t for n, o, t, k, d in ps]
        within = sum(.75 <= x <= 1.25 for x in tgt) / len(tgt)
        print(f"  {a:20} n={len(ps):3} · " + " · ".join(row) + f" · الأفضل α={best} · هدفُ 12 شهراً: وسيطُ النسبة {statistics.median(tgt):.2f} · خطأ {math.exp(err(tgt))-1:.0%} · ±25٪ {within:.0%}")
    print("\nأبعدُ عشرةٍ عن المحللين (رمز · جديد · هدف · قائم):")
    for e, s, v, at, fv in sorted(worst, reverse=True)[:10]:
        print(f"  {s} · {v:.2f} · {at:.2f} · {fv}")
    return 0

sys.exit(asyncio.run(main()))
