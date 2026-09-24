#!/usr/bin/env python3
"""مجموعةُ نماذج المصارف: أيُّها أقربُ للمحللين؟ قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fvm_bank_sets.py

«InvestingPro» يقوّم المصرفَ بثلاثة (السعر/الأرباح · السعر/المبيعات · السعر/الدفترية).
نقيس المجموعةَ القائمة وبدائلها على كلّ مصرفٍ له هدفُ محلّلين، قبل المزج وبعده.
"""
import asyncio, math, statistics, sys
sys.path.insert(0, "/app")

VARIANTS = {
    "القائمة": None,
    "InvestingPro الثلاثة": {"peer_pe", "peer_ps", "peer_pb"},
    "الأرباح والدفترية": {"peer_pe", "peer_pb"},
    "الحقوق + الأرباح + الدفترية": {"residual_income", "peer_pe", "peer_pb"},
    "الحقوق + الأرباح + الدفترية + التوزيع": {"residual_income", "peer_pe", "peer_pb", "ddm_stable"},
    "بلا عائد الأقران": {"residual_income", "peer_pe", "peer_pb", "ddm_stable", "ddm_two_stage"},
}


def stat(xs):
    if not xs:
        return "—"
    e = math.exp(statistics.median(abs(math.log(x)) for x in xs)) - 1
    return (f"n={len(xs):2} · وسيطُ النسبة {statistics.median(xs):.2f} · ±15٪ {sum(.85<=x<=1.15 for x in xs)/len(xs):.0%}"
            f" · ±25٪ {sum(.75<=x<=1.25 for x in xs)/len(xs):.0%} · وسيطُ الخطأ {e:.0%}")


async def main():
    from app.services import fair_value_models as F
    from app.services.market_screener import get_cached_screener
    rows = [x for x in (get_cached_screener() or [])
            if isinstance(x.get("analyst_target"), (int, float)) and x["analyst_target"] > 0]
    banks = []
    for x in rows:
        i = await F.gather(x["symbol"])
        if i and (i.sector or "").startswith("Banks"):
            banks.append((x, i))
    print(f"مصارفُ لها هدف: {len(banks)}")
    orig = F.MODEL_SETS["Banks"]
    for name, keys in VARIANTS.items():
        F.MODEL_SETS["Banks"] = orig if keys is None else (orig[0], keys)
        raw, bl, per = [], [], []
        for x, i in banks:
            at = x["analyst_target"]
            r = F.value(i)
            if not r or not r.get("value"):
                continue
            raw.append(r["value"] / at)
            dy = (i.dps_ttm / i.price) if (i.dps_ttm and i.price) else None
            b = F.blend(dict(r), F._calibrated(x["symbol"]), i.archetype, dy)
            if b and b.get("value"):
                bl.append(b["value"] / at)
            per.append(f"{x['symbol']}:{r['value']:.2f}/{at:.2f}({r.get('count')})")
        print(f"\n═ {name}\n  النماذج وحدها {stat(raw)}\n  بعد المزج     {stat(bl)}")
        print("  " + " · ".join(per))
    F.MODEL_SETS["Banks"] = orig
    return 0

sys.exit(asyncio.run(main()))
