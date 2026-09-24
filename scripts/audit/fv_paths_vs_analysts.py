#!/usr/bin/env python3
"""دقّةُ كلّ مسارٍ من مسارات السعر العادل مقابل أهداف المحلّلين — بالنمط. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fv_paths_vs_analysts.py

قال المالك: «أريد السعرَ العادل منافساً لهدف المحللين ولمحرّك إنفستنق برو».
فيُقاس لكلّ مسار — خصمٌ · دخلٌ متبقٍّ · مضاعفُ قطاع · صافي أصول — وسيطُ
نسبته إلى الهدف ووسيطُ خطئه المطلق (لوغاريتمياً)، بكلّ نمط. وتُقترح أوزانٌ
تتناسب عكساً مع الخطأ — مقياسٌ يُبنى عليه لا رقمٌ يُنسخ.
"""
import asyncio, collections, math, statistics, sys
sys.path.insert(0, "/app")


async def main():
    from app.services.market_screener import get_cached_screener
    from app.services.analysis import analyze_company
    from app.services.statement_merge import archetype_of
    rows = [r for r in (get_cached_screener() or [])
            if isinstance(r.get("analyst_target"), (int, float)) and r["analyst_target"] > 0]
    err = collections.defaultdict(lambda: collections.defaultdict(list))
    ratio = collections.defaultdict(lambda: collections.defaultdict(list))
    fin = collections.defaultdict(list)
    for r in rows:
        s = r["symbol"]; at = r["analyst_target"]
        an = await analyze_company(f"{s}.SR", allow_supplement=False) or {}
        d = an.get("fair_value_detail") or {}
        a = archetype_of(s) or "?"
        for m in d.get("methods") or []:
            v = m.get("value")
            if isinstance(v, (int, float)) and v > 0:
                err[a][m["name"]].append(abs(math.log(v / at)))
                ratio[a][m["name"]].append(v / at)
        fv = an.get("fair_value")
        if isinstance(fv, (int, float)) and fv > 0:
            fin[a].append(fv / at)
    print(f"أوراقٌ لها هدفُ محلّلين: {len(rows)}")
    allq = [x for v in fin.values() for x in v]
    if allq:
        print(f"السعرُ العادلُ المنشور: وسيطُ النسبة {statistics.median(allq):.2f} · ضمن ±25٪ "
              f"{sum(.75 <= x <= 1.25 for x in allq)}/{len(allq)} · ضمن ±15٪ {sum(.85 <= x <= 1.15 for x in allq)}/{len(allq)}")
    for a in sorted(err, key=lambda k: -sum(len(v) for v in err[k].values())):
        print(f"\n═ {a} · منشور: n={len(fin[a])} وسيط={statistics.median(fin[a]) if fin[a] else float('nan'):.2f}")
        inv = {}
        for name, es in sorted(err[a].items()):
            med_e = statistics.median(es)
            inv[name] = 1 / max(med_e, 0.05)
            print(f"   {name:<32} n={len(es):>3} · وسيطُ النسبة={statistics.median(ratio[a][name]):.2f}"
                  f" · وسيطُ الخطأ={math.exp(med_e) - 1:.0%}")
        tot = sum(inv.values())
        print("   أوزانٌ مقترحة (عكسُ الخطأ):", {k: round(v / tot, 2) for k, v in inv.items()})
    return 0

sys.exit(asyncio.run(main()))
