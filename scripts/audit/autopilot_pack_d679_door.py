"""كاشف D679: ما يشربه المستشارُ الآليّ فعلاً في الإنتاج — لكلّ مفتاحٍ من POS_KEYS كم مركزاً امتلأ به، ونبضُ السوق
وانتباهُ الحوكمة للمحفظة الافتراضية، بزمن البناء. قراءةٌ فقط (لا يكتب الذاكرة).

    docker exec sp_backend python /app/scripts/audit/autopilot_pack_d679_door.py
"""
import asyncio
import json
import sys
import time

sys.path.insert(0, "/app")


def _full(v):
    return v not in (None, "", [], {})


async def main():
    from app.core.portfolio_scope import install_scope_listeners, set_scope, reset_scope
    try:
        install_scope_listeners()
    except Exception:                                             # noqa: BLE001
        pass
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Portfolio
    from app.services.autopilot import pack, POS_KEYS, MARKET_KEYS
    async with AsyncSessionLocal() as db:
        ps = (await db.execute(select(Portfolio).execution_options(skip_portfolio_scope=True))).scalars().all()
    pid = next((p.id for p in ps if p.is_default), ps[0].id if ps else None)
    set_scope(pid, False)
    try:
        t0 = time.perf_counter()
        async with AsyncSessionLocal() as db:
            pk = await pack(db)
        s = round(time.perf_counter() - t0, 1)
    finally:
        reset_scope()
    pos = pk.get("positions") or []
    n = len(pos)
    print(f"═ مراكز {n} · بُنيت في {s} ث")
    for k in POS_KEYS:
        c = sum(1 for p in pos if _full(p.get(k)))
        print(f"   {k:<16} {c}/{n}")
    m = pk.get("market") or {}
    print(f"═ نبضُ السوق: {sorted(m)} (من {list(MARKET_KEYS)})")
    if m.get("summary"):
        print("   " + str(m["summary"])[:200])
    att = pk.get("attention") or []
    print(f"═ انتباهُ الحوكمة {len(att)}: " + json.dumps(att, ensure_ascii=False)[:600])
    ex = next((p for p in pos if _full(p.get("analysts")) or _full(p.get("material_events"))), None)
    if ex:
        print("═ مثال: " + json.dumps({k: ex.get(k) for k in ("symbol", "sector", "stability", "analysts",
                                                              "material_events", "red_lines", "warnings")},
                                     ensure_ascii=False, default=str)[:1500])


asyncio.run(main())
