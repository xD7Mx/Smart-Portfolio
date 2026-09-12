#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D257 — بناءُ البيتا القطاعية على الخادم حيث الشبكةُ والمخزون.
#
#   docker exec sp_backend python /app/scripts/audit/sector_betas_probe.py
#   docker exec sp_backend python /app/scripts/audit/sector_betas_probe.py --apply
#
# بلا `--apply` لا يُكتب شيء: يُطبع الحصادُ وتغطيتُه وجدولُ القطاعات
# المقترَح — ثمّ يُعتمَد بعد النظر. ولا يُعدَّل ملفُّ المعايير: الجدولُ
# يُحفَظ في مخزن الحالة بتاريخه، ويُقرأ منه المحرّك.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import sys

for _p in ("/app", "backend", "."):
    if _p not in sys.path:
        sys.path.insert(0, _p)

APPLY = "--apply" in sys.argv
LIMIT = None
if "--limit" in sys.argv:
    i = sys.argv.index("--limit")
    if i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
        LIMIT = int(sys.argv[i + 1])


async def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    from app.services import sector_betas as sb

    uni = main_market(MARKET_UNIVERSE)
    syms = list(uni)[:LIMIT] if LIMIT else list(uni)
    print(f"الحصاد: {len(syms)} شركةً · تزامنٌ محدود — قد يطول.\n")

    if not APPLY:
        from app.services.argaam_beta import harvest
        betas = await harvest(syms)
        print(f"بيتا مقروءة: {len(betas)} من {len(syms)}")
        raw = sb._params_raw()
        tax, eng = float(raw["tax_rate"]["value"]), raw["engine"]
        from app.services import cache, lastgood
        lev = {}
        for s in betas:
            ck = f"stmt:{s}.SR"
            fund = cache.get(ck)
            if fund is None:
                fund = lastgood.load(ck)
            per = (fund.get("periods") or []) if isinstance(fund, dict) else []
            last = per[-1] if per else {}
            eq, dr = last.get("equity"), last.get("debt_ratio")
            if isinstance(eq, (int, float)) and eq > 0 \
                    and isinstance(dr, (int, float)) and 0 < dr < 100:
                lev[s] = (eq / max(1e-9, 1 - dr / 100.0) - eq, eq)
        print(f"رافعةٌ مقروءةٌ من مخزوننا: {len(lev)} من {len(betas)}")
        table, rep = sb.build_table(
            betas, lev, {s: (uni.get(s) or {}).get("sector") for s in betas},
            tax=tax, floor=float(eng["beta_floor"]), cap=float(eng["beta_cap"]))
        print(f"\nالتقرير: {rep}\n")
        for sec, row in sorted(table.items(), key=lambda kv: -kv[1]["n"]):
            print(f"   · {sec:<32} بيتا {row['beta']:.3f} · {row['n']} شركة")
        print("\nلم يُكتب شيء. للاعتماد: أعد التشغيل بـ‎ --apply")
        return 0

    rec = await sb.refresh(syms)
    print(rec)
    if rec.get("error"):
        return 1
    from app.services.fair_value_engine.params import load_params
    p = load_params(allow_unverified=True, allow_stale=True)
    print(f"✔ الأثر: {p.provenance()}")
    for sec in ("البنوك", "المواد الأساسية", "الطاقة"):
        try:
            print(f"   {sec}: {p.unlevered_beta(sec)}")
        except Exception as e:                                    # noqa: BLE001
            print(f"   {sec}: {type(e).__name__}")
    return 0


raise SystemExit(asyncio.run(main()))
