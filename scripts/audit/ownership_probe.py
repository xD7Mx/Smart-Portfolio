#!/usr/bin/env python3
"""مسبارُ هيكل الملكية — يقيس على الخادم ما لا يُقاس من هنا (D270).

    docker exec sp_backend python /app/scripts/audit/ownership_probe.py 1010
    docker exec sp_backend python /app/scripts/audit/ownership_probe.py --market 15 --apply

يطبع: أمتاحٌ المتصفّح؟ · أيُّ تبويبٍ اكتُشف؟ · كم صفّاً فُهم في كلٍّ؟
ولا يكتب شيئاً إلا بـ`--apply`. والصفرُ يُطبَع صفراً — لا يُجمَّل.
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")


async def main() -> int:
    args = [a for a in sys.argv[1:]]
    apply = "--apply" in args
    args = [a for a in args if a != "--apply"]

    from app.services import ownership as ow
    from app.services.browser_fetch import available

    ok, why = await available()
    print(f"المتصفّح: {'متاح' if ok else 'غير متاح'} — {why}")
    if not ok:
        print("لا قياسَ بلا متصفّح. رَكِّب الصورةَ من جديد: docker compose up -d --build")
        return 1

    if args and args[0] == "--market":
        n = int(args[1]) if len(args) > 1 else 10
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        syms = list(main_market(MARKET_UNIVERSE))[:n]
    else:
        syms = args or ["1010"]

    tally = {k: 0 for k in ow.TABS}
    for sym in syms:
        res = await ow.refresh(sym) if apply else await _dry(ow, sym)
        if res.get("error"):
            print(f"{sym}: تعذّر — {res['error']}")
            continue
        got = {k: len(res.get(k) or []) for k in ow.TABS}
        for k, v in got.items():
            tally[k] += 1 if v else 0
        print(f"{sym}: " + " · ".join(f"{k}={v}" for k, v in got.items()))

    print("\nالتغطية من " + str(len(syms)) + " شركة:")
    for k, v in tally.items():
        print(f"  {k}: {v}")
    return 0


async def _dry(ow, sym: str) -> dict:
    """قراءةٌ بلا حفظ — لقياسٍ لا يمسّ مخزنَ الحالة."""
    from app.services.argaam_calendar import BASE, _company_id, _company_url
    from app.services.browser_fetch import BrowserUnavailable, render
    cid = await _company_id(str(sym).replace(".SR", ""))
    if not cid:
        return {"error": "لا معرِّفَ للشركة في «أرقام»"}
    try:
        home = next(iter((await render([_company_url(cid)])).values()), "")
    except BrowserUnavailable as e:
        return {"error": f"المتصفّحُ غيرُ متاح: {e}"}
    links = ow.tab_links(home, BASE)
    if not links:
        return {"error": "لم يُكتشف تبويبٌ بأسماء البنود"}
    pages = await render(list(links.values()))
    out: dict = {"urls": links}
    for k, u in links.items():
        out[k] = ow.parse(pages.get(u, ""))
    return out


raise SystemExit(asyncio.run(main()))
