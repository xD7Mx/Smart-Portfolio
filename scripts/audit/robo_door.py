#!/usr/bin/env python3
"""كاشفُ أوامر المستشار الآليّ (‏D750 · D754 خطّةُ الصفقة وحمايةُ المراكز ولوحةُ المخاطر): يبني أوامرَ اليوم لكلّ محفظةٍ كما يفعل المجدولُ بعد رأي الطيار — بلا إشعار — ويطبعها.
يكتب في سجلّ الأوامر وحده (‏robo/) — لا يمسّ المحفظةَ ولا أرقامَها، ولا ينفّذ صفقة."""
import asyncio, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")


async def main():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.portfolio_scope import reset_scope, set_scope
    from app.models.portfolio import Portfolio
    from app.services import robo_orders as R
    async with AsyncSessionLocal() as db:
        ps = (await db.execute(select(Portfolio.id).where(Portfolio.is_archived.is_(False)).order_by(Portfolio.id))).scalars().all()
    for pid in ps:
        set_scope(pid, False)
        try:
            async with AsyncSessionLocal() as db:
                v = await R.refresh(db, notify=False)
        finally:
            reset_scope()
        print(f"محفظة {pid}: أوامر {len(v['orders'])} · مؤجّلة {len(v['held'])} · موقوف {v['paused']} · سجلّ {v['record']}")
        print(f"  المخاطر: {v.get('risk')}")
        for o in v["orders"]:
            print(f"  {o['side']} {o['shares']} {o['symbol']} {o.get('type')} {o['price']} = {o['amount']:,.0f} · وقف {o.get('stop')} · هدف {o.get('target')}"
                  f" · 1:{o.get('rr')} · مخاطرة {o.get('risk')} ({o.get('risk_pct')}٪) · الحجم: {o.get('sizing')} · ثقة {o.get('confidence')} · "
                  + " ".join(("✓" if c["ok"] else "✗") + c["k"] for c in o["checks"]))
        for r in v.get("protect") or []:
            print(f"  حماية {r['symbol']} {r['name']}: سعر {r['price']} · وقف {r['stop']} ({r['stop_basis']}) {r['d_stop']}٪ · هدف {r['target']}"
                  f" ({r['target_basis']}) {r['d_target']}٪ · {r['state']} · مخاطرة {r['risk']}")
        for h in v["held"][:12]:
            print(f"  مؤجّل {h['symbol']}: {h['why']}")

asyncio.run(main())
