#!/usr/bin/env python3
"""كاشفُ D720 — درجةُ الجودة المالية إشارةً إشارة (بلاغُ المالك 2026-10-14: «أرقامٌ ظالمة لا تنمّ عن صدق القوائم») — قارئٌ فقط.

لكلّ شركة: آخرُ سنةٍ في القوائم، وكلُّ إشارةٍ بقيمتها الخام ودرجتها ووزنها، والدرجةُ المنشورة — ومعها قراءةُ محرّك القواعد (الجودة ·
السلامة) التي تعرضها النافذةُ نفسُها، ليُرى أين يفترقان."""
import asyncio, os, sys, time
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
SYMS = ["4340", "2270", "2020", "7010", "4164", "1150", "7202", "2222", "1120", "2280", "4190", "2010", "4013", "1180"]


async def main():
    from app.services.market_data import market_service
    from app.services import scores as S
    from app.services.statement_merge import archetype_of
    for s in SYMS:
        try:
            d = await market_service.get_financials(f"{s}.SR")
            ps = (d or {}).get("periods") or []
            if not ps:
                print(f"{s}: لا قوائم"); continue
            L, P = ps[-1], (ps[-2] if len(ps) > 1 else {})
            g = lambda k, p=L: p.get(k)                                     # noqa: E731
            fin = S.governed_finance_score(ps, f"{s}.SR")[0]
            ni, ni0 = g("net_income"), g("net_income", P)
            nig = (ni - ni0) / abs(ni0) * 100 if ni is not None and ni0 else None
            roe = ni / g("equity") * 100 if ni is not None and g("equity") else None
            rev = [p.get("revenue") for p in ps if p.get("revenue")]
            cagr = ((rev[-1] / rev[0]) ** (1 / (len(rev) - 1)) - 1) * 100 if len(rev) >= 3 and rev[0] > 0 and rev[-1] > 0 else None
            f = lambda v, n=1: "—" if v is None else f"{v:.{n}f}"           # noqa: E731
            print(f"{s} [{archetype_of(s + '.SR')}] {len(ps)} سنوات حتى {str(g('period') or g('date') or '?')[:10]} · الدرجة {fin}"
                  f" · نموُّ الربح سنةً {f(nig)}% · ROE {f(roe)}% · نموُّ الإيراد المركّب {f(cagr)}%"
                  f" · الدين/الأصول {f(g('debt_ratio'), 2)} · تغطية {f(g('interest_coverage'))}"
                  f" · OCF/NI {f((g('operating_cash_flow') or 0) / ni if ni else None, 2)}")
        except Exception as e:                                             # noqa: BLE001
            print(f"{s}: ✘ {type(e).__name__}: {str(e)[:120]}")
    print("الأوزانُ المنشورة:", S.FINANCE_WEIGHTS)


asyncio.run(main())
