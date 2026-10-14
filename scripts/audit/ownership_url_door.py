"""كاشفُ D270 (قراءةٌ فقط) — المرحلةُ التي يسقط فيها هيكلُ الملكية. قِيس (‏ownership_endpoints_door · run 38581559987): التغطيةُ 0
وصفحةُ الشركة «0 حرفاً» لأرامكو والراجحي — فلا نداءَ يُبلغ أصلاً. فيطبع لكلّ شركةٍ: هل في لقطة السوق صفّ، ورابطُ الصفحة كما
وصل، وحالةُ جلبها وطولُها، وهل فيها <base> ونداءاتُ ‎NJ؛ ثمّ يجرّب رابطَ ملفّات القوائم (‏tadawul_xbrl) الذي يعمل ليلاً للمقارنة.

    docker exec sp_backend python /app/scripts/audit/ownership_url_door.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_market as TM
    from app.services import tadawul_ownership as TO
    from app.services.tadawul_http import fetch
    import os
    from datetime import datetime
    from app.services import lastgood
    from app.services.market_phase import market_phase
    from zoneinfo import ZoneInfo
    naive, mecca = datetime.now(), datetime.now(ZoneInfo("Asia/Riyadh")).replace(tzinfo=None)
    ph = lambda t: market_phase((t.weekday() + 1) % 7, t.hour * 60 + t.minute)   # noqa: E731
    print(f"@@CLOCK@@ TZ={os.environ.get('TZ')!r} · ساعةُ الحاوية {naive:%a %H:%M} ← {ph(naive)} · مكة {mecca:%a %H:%M} ← {ph(mecca)}")
    rows, live, at = TM.usable_rows()
    print(f"@@SNAP@@ صفوفُ اللقطة {len(rows)} · حيّة {live} · زمنُها {at}")
    if not rows:
        rec = lastgood.load(TM.STORE_KEY) or {}
        rows = rec.get("rows") if isinstance(rec.get("rows"), dict) else {}
        print(f"@@STORED@@ المحفوظُ بلا شرط عمر: {len(rows)} صفّاً · زمنُه {rec.get('at')} — يُكمل الكاشفُ به")
        TM.row_for = lambda s, _r=rows: _r.get(str(s)) or {}
    with_url = sum(1 for r in rows.values() if (r or {}).get("company_url"))
    print(f"@@URLS@@ برابط صفحةٍ {with_url} من {len(rows)}")
    for sym in ("2222", "1120", "2010"):
        r = TM.row_for(sym)
        url = (r or {}).get("company_url")
        print(f"\n══ {sym} · في اللقطة {bool(r)} · الرابط {url!r}")
        if not url:
            continue
        full = "https://www.saudiexchange.sa" + url if url.startswith("/") else url
        for k in (1, 2):
            st, body = await fetch(full)
            mb = TO._BASE_RE.search(body or "")
            names = sorted(set(TO._EP_RE.findall(body or "")))
            print(f"   جلب {k}: حالة {st} · {len(body or '')} حرفاً · <base> {'موجود' if mb else 'غائب'} · نداءات {len(names)}"
                  + (f" · أوّلها {names[:8]}" if names else "")
                  + ("" if body is None or st == 200 else f" · مطلعُ الردّ {(body or '')[:160]!r}"))
            if st == 200 and body:
                break
            await asyncio.sleep(1.5)
        page = await TO.company_page(sym)
        print(f"   company_page: {len(page or '')} حرفاً")
        rec = await TO.read_symbol(sym)
        print(f"   read_symbol: { {k: (v if k in ('error', 'names_seen') else len(v) if isinstance(v, list) else v) for k, v in rec.items()} }")
        await asyncio.sleep(1.0)


asyncio.run(main())
