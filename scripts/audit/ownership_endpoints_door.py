"""كاشفُ D270 (قراءةٌ فقط): لماذا لا يُقرأ هيكلُ الملكية من «تداول»؟ — قِيس (‏open_items_door · run 38553016706): المحفوظُ 0 من 272،
وقراءةُ أرامكو الحيّة بلا بندٍ ولا خطأ. فيطبع لشركتين كلَّ نداءٍ في صفحتها: اسمَه، وهل يطابق تصنيفَ القارئ، وما يعيده (الحالة ·
عددُ الصفوف · مفاتيحُ أوّل صفّ) — لا يكتب شيئاً.

    docker exec sp_backend python /app/scripts/audit/ownership_endpoints_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_ownership as TO
    from app.services.tadawul_http import fetch
    from app.services import lastgood
    print("@@COVER@@", lastgood.load("ownership:coverage"))
    try:
        from app.services.ownership import reading as ar_reading
        from app.data.market_universe import MARKET_UNIVERSE as MU
        from app.data.universe import main_market
        syms = list(main_market(MU))
        print(f"@@ARGAAM@@ محفوظٌ من «أرقام» {sum(1 for s in syms if ar_reading(s))} من {len(syms)}")
    except Exception as e:                                         # noqa: BLE001
        print("@@ARGAAM@@ تعذّر", type(e).__name__, e)
    for sym in ("2222", "1120"):
        body = await TO.company_page(sym)
        print(f"\n══ {sym} · صفحة {len(body or '')} حرفاً")
        if not body:
            continue
        mb = TO._BASE_RE.search(body)
        base = mb.group(1).rstrip("/") if mb else None
        names = sorted(set(TO._EP_RE.findall(body)))
        print(f"@@NAMES@@ {len(names)} نداءً · الأساس {'موجود' if base else 'غائب'}")
        for n in names:
            kind = next((k for k, rx in TO.KINDS.items() if rx.search(n)), "—")
            ep = next(m.group(0) for m in TO._EP_RE.finditer(body) if m.group(1) == n)
            st, raw, rows, keys = None, "", [], []
            if base:
                try:
                    st, raw = await fetch(f"{base}/{ep}", params={"requestLocale": "en"}, referer=base)
                    data = json.loads(raw) if raw else None
                    rows = data.get("data") if isinstance(data, dict) else data
                    rows = rows if isinstance(rows, list) else []
                    keys = sorted(rows[0])[:14] if rows and isinstance(rows[0], dict) else []
                    if not rows and isinstance(data, dict):
                        keys = sorted(data)[:14]
                except Exception as e:                             # noqa: BLE001
                    raw = f"{type(e).__name__}"
            print(f"   {n} · تصنيف {kind} · حالة {st} · {len(raw or '')} حرفاً · صفوف {len(rows)} · مفاتيح {keys}")
            await asyncio.sleep(0.8)


asyncio.run(main())
