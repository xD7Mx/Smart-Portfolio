#!/usr/bin/env python3
"""كاشفُ مصادر التقرير اليوميّ وسلسلة الخيارات — قارئٌ فقط (‏D746 · D747).

قبل أن يُبنى جدولٌ في التقرير يُقاس مصدرُه: أيُّ رموز الأسواق الإقليمية والعالمية والسلع والعملات يعطي تاريخاً يومياً،
وما في خدمة مؤشّر «تداول» من مفاتيح (أفيها مؤشّراتُ القطاعات؟)، وما في لقطة السوق، وسلسلةُ خيارات SPY ورسمُ عقدٍ منها،
وبحثُ الرموز الأمريكية. لا يكتب في أيّ مخزن."""
import asyncio, json, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")

CANDS = {
    "إقليمي": ["^TASI.SR", "^DFMGI", "DFMGI.AE", "^FTFADGI", "FADGI.FGI", "^BKP", "^BKA", "^QSI", "^GNRI", "^MSI", "^MSX30", "^BAX", "^BHSE", "^CASE30", "^EGX30"],
    "عالمي": ["^DJI", "^IXIC", "^GSPC", "^FTSE", "^GDAXI", "^FCHI", "^N225", "^BVSP", "^HSI", "^KS11", "000001.SS", "^AXJO", "^BSESN", "EEM", "URTH"],
    "سلع": ["BZ=F", "CL=F", "NG=F", "GC=F", "SI=F", "HG=F", "ALI=F", "SB=F", "TIO=F", "HRC=F"],
    "عملات": ["DX-Y.NYB", "EURUSD=X", "JPY=X", "GBPUSD=X", "CAD=X", "CHF=X", "AUDUSD=X", "CNY=X", "INR=X", "BTC-USD", "ETH-USD", "XRP-USD", "SAR=X"],
    "فائدة": ["^IRX", "^TNX", "^FVX"],
}


async def main():
    import httpx
    from app.services.market_data import market_service as M
    from app.services import tadawul_market as TM
    Y = M.primary
    print("══ التاريخ اليوميّ ══")
    for grp, syms in CANDS.items():
        ok, bad = [], []
        for s in syms:
            try:
                pts = await asyncio.wait_for(M.get_history(s, "1y"), 25) or []
            except Exception as e:                                # noqa: BLE001
                pts = []
            last = pts[-1] if pts else None
            (ok if len(pts) > 150 else bad).append(f"{s}:{len(pts)}" + (f"@{last.get('date')}={last.get('close')}" if last and len(pts) > 150 else ""))
        print(f"  {grp} ✔", " ".join(ok))
        print(f"  {grp} ✘", " ".join(bad))

    print("══ خدمةُ مؤشّر تداول ══")
    try:
        from app.services.tadawul_http import fetch
        st, body = await fetch(TM.INDEX_URL, referer="https://www.saudiexchange.sa/wps/portal/saudiexchange/home")
        d = json.loads(body) if st == 200 else {}
        print("  المفاتيح:", sorted(d.keys())[:60])
        for k, v in d.items():
            if isinstance(v, dict):
                print(f"  {k}:", sorted(v.keys())[:30])
            if isinstance(v, list) and v:
                print(f"  {k}[{len(v)}]:", json.dumps(v[0], ensure_ascii=False)[:300])
    except Exception as e:                                        # noqa: BLE001
        print("  تعذّر:", type(e).__name__, str(e)[:120])

    print("══ لقطةُ السوق ══")
    rows, live, at = TM.usable_rows()
    print("  صفوف", len(rows), "حيّة" if live else "آخر إغلاق", at)
    if rows:
        k0 = next(iter(rows))
        print("  مفاتيح", sorted(rows[k0].keys()))
        main = {s: r for s, r in rows.items() if not s.startswith("9")}
        tv = sum(r.get("turnover") or 0 for r in main.values()); vo = sum(r.get("volume") or 0 for r in main.values())
        tr = sum(r.get("trades") or 0 for r in main.values())
        up = sum(1 for r in main.values() if (r.get("change_pct") or 0) > 0); dn = sum(1 for r in main.values() if (r.get("change_pct") or 0) < 0)
        print(f"  الرئيسي {len(main)}: قيمة {tv:,.0f} · كمية {vo:,.0f} · صفقات {tr:,.0f} · ↑{up} ↓{dn}")
        mc = sum(1 for r in main.values() if r.get("market_cap"))
        print("  القيمةُ السوقية في", mc)
    iq = await TM.index_quote()
    print("  المؤشّر:", iq)

    print("══ الفرز ══")
    try:
        from app.services.market_screener import get_cached_screener
        sc = get_cached_screener() or []
        print("  صفوف", len(sc), "مفاتيح", sorted(sc[0].keys()) if sc else None)
        print("  قيمةٌ سوقية في", sum(1 for r in sc if r.get("market_cap")))
    except Exception as e:                                        # noqa: BLE001
        print("  تعذّر", e)

    print("══ تاسي داخل الجلسة ══")
    try:
        b = await M.get_bars("^TASI.SR", "5m") or []
        print("  5m:", len(b), b[-1] if b else None)
        dly = await M.get_bars("^TASI.SR", "1d") or []
        print("  1d:", len(dly), dly[-1] if dly else None)
    except Exception as e:                                        # noqa: BLE001
        print("  تعذّر", e)

    print("══ مفكرةُ السوق ══")
    try:
        from app.services.content_engine import market_wide_events, clean_events
        ev = clean_events(await market_wide_events())
        print("  أحداث", len(ev))
        for e in ev[:4]:
            print("  ", json.dumps({k: e.get(k) for k in list(e)[:9]}, ensure_ascii=False)[:260])
    except Exception as e:                                        # noqa: BLE001
        print("  تعذّر", e)

    print("══ ياهو: البحثُ والخيارات ══")
    crumb = await Y._crumb()
    H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient(timeout=15, headers=H, cookies=(crumb[1] if crumb else {}), follow_redirects=True) as c:
        r = await c.get("https://query2.finance.yahoo.com/v1/finance/search", params={"q": "nvid", "quotesCount": 8, "newsCount": 0})
        print("  بحث", r.status_code, [(q.get("symbol"), q.get("shortname"), q.get("exchange"), q.get("quoteType")) for q in (r.json().get("quotes") or [])][:8] if r.status_code == 200 else r.text[:120])
        p = {"crumb": crumb[0]} if crumb else {}
        r = await c.get("https://query2.finance.yahoo.com/v7/finance/options/SPY", params=p)
        print("  خيارات", r.status_code)
        if r.status_code == 200:
            res = (r.json().get("optionChain", {}).get("result") or [{}])[0]
            ex = res.get("expirationDates") or []
            print("  آجال", len(ex), [time.strftime("%Y-%m-%d", time.gmtime(x)) for x in ex[:6]], "سعر", (res.get("quote") or {}).get("regularMarketPrice"))
            op = (res.get("options") or [{}])[0]
            calls = op.get("calls") or []
            print("  عقود الشراء", len(calls), "البيع", len(op.get("puts") or []))
            if calls:
                mid = calls[len(calls) // 2]
                print("  عيّنة", json.dumps(mid, ensure_ascii=False)[:500])
                cs = mid["contractSymbol"]
                for tf in ("5m", "1h", "1d"):
                    try:
                        bb = await M.get_bars(cs, tf) or []
                        print(f"  رسم {cs} {tf}:", len(bb), bb[-1] if bb else None)
                    except Exception as e:                        # noqa: BLE001
                        print(f"  رسم {tf} تعذّر", type(e).__name__, str(e)[:100])
            if len(ex) > 1:
                r2 = await c.get("https://query2.finance.yahoo.com/v7/finance/options/SPY", params={**p, "date": ex[1]})
                op2 = ((r2.json().get("optionChain", {}).get("result") or [{}])[0].get("options") or [{}])[0] if r2.status_code == 200 else {}
                print("  الأجلُ الثاني", r2.status_code, len(op2.get("calls") or []))
        r = await c.get("https://query2.finance.yahoo.com/v7/finance/options/AAPL", params=p)
        print("  AAPL", r.status_code, len(((r.json().get("optionChain", {}).get("result") or [{}])[0].get("expirationDates") or [])) if r.status_code == 200 else "")


asyncio.run(main())
