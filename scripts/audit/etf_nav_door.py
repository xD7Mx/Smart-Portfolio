#!/usr/bin/env python3
"""بابُ صافي أصول الورقة المؤشِّرة — يُقاس ولا يُفترَض (D389).

    docker exec sp_backend python /app/scripts/audit/etf_nav_door.py

قال المالك: «لنضع معياراً مختصّاً لقطاع الصناديق المتداولة». ومعيارُها
مختلفٌ عن الشركة اختلافاً جوهرياً: قيمةُ الشركة **تُقدَّر** بخصم
تدفّقٍ أو مضاعفات، وقيمةُ الورقة المؤشِّرة **تُقرأ**: صافي أصولها
للوحدة (‏NAV) يُنشَر دوريّاً، والفرصةُ فيها **العلاوةُ أو الخصمُ عن
NAV** لا مضاعفُ ربحية.

فلا يُبنى المعيارُ قبل أن يوجَد مصدرُ NAV. وقِيس سابقاً أنّ صفحاتها
لا تحمل خدمةَ ملفّاتٍ رسمية (لا XBRL) — لكن ذلك نفيُ صيغةٍ لا نفيُ
نشر. فيُطرَق البابُ حيث يُنشَر فعلاً:

  ١· جدولُ سوق الصناديق في «تداول» (كما وُجد جدولُ «نمو»): تُقرأ
     أعمدتُه بأسمائها — فإن كان فيه عمودُ NAV فالبابُ واحدٌ للجميع.
  ٢· وصفحةُ الورقة نفسِها: تُطبَع كلُّ خدماتها (‏`=NJ…=/`) ويُقاس
     جوابُ كلٍّ: حجمُه وعددُ أرقامه وهل فيه مفردةُ «صافي أصول».
  ٣· ويُطبَع **تاريخُ** ما وصل (‏D368 · D379): صافي أصولٍ بلا تاريخٍ
     لا يُبنى عليه، وتاريخُ رابطٍ لا يُنسَب لجدول.

ولا يُخمَّن عنوانٌ ولا اسمُ خدمة: يُقرأ من الصفحة (طريقةُ الجلب
المسجَّلة في `docs/FETCH_METHOD.md`).
"""
from __future__ import annotations

import asyncio
import re
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

NAV_WORDS = ("net asset value", "nav", "صافي الأصول", "صافي أصول",
             "صافي قيمة الأصول")
_NUM = re.compile(r"-?\d[\d,]*\.?\d*")
_DATE = re.compile(r"20\d{2}-\d{2}-\d{2}")
# صفحاتٌ مرشَّحةٌ لجدول الصناديق — تُجرَّب ويُقال ما ردّ كلٌّ منها
PAGES = (
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/"
    "etfs-market-watch/etfs-trading-information",
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/"
    "etfs-market-watch",
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/"
    "funds-market-watch",
)


async def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.services import tadawul_market as tm
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_http import fetch

    etfs = sorted(s for s, m in MARKET_UNIVERSE.items()
                  if (m or {}).get("sector") == "صناديق المؤشرات المتداولة")
    print(f"═ بابُ صافي الأصول ═ أوراقٌ مؤشِّرةٌ في الدليل: {len(etfs)}"
          f" · {' · '.join(etfs[:8])}{' …' if len(etfs) > 8 else ''}")

    # ── ١ · جدولُ سوق الصناديق ─────────────────────────────────────────
    for pg in PAGES:
        try:
            st, html = await fetch(pg)
        except Exception as e:                                    # noqa: BLE001
            print(f"\n── {pg[-46:]}: تعذّر — {type(e).__name__}")
            continue
        if st != 200 or not html:
            print(f"\n── {pg[-46:]}: HTTP {st}")
            continue
        mb = X._BASE.search(html)
        svcs = {m.group(1): m.group(0) for m in X._NJ.finditer(html)}
        hit = [w for w in NAV_WORDS if w in html.lower()]
        print(f"\n── {pg[-46:]}: HTTP 200 · {len(html)} حرفاً"
              f" · خدماتٌ={len(svcs)} · مفرداتُ NAV في الصفحة={len(hit)}"
              + (f" ({' · '.join(hit[:3])})" if hit else ""))
        if not mb:
            print("   بلا <base> — لا يُبنى نداء")
            continue
        base = mb.group(1).rstrip("/")
        for nm, sp in list(svcs.items())[:8]:
            try:
                s2, b2 = await fetch(f"{base}/{sp}",
                                     params={"requestLocale": "en"},
                                     referer=pg)
            except Exception as e:                                # noqa: BLE001
                print(f"   ⟨{nm}⟩ تعذّر {type(e).__name__}")
                continue
            if s2 != 200 or not b2:
                print(f"   ⟨{nm}⟩ HTTP {s2}")
                continue
            h2 = [w for w in NAV_WORDS if w in b2.lower()]
            ds = sorted(set(_DATE.findall(b2)))
            print(f"   ⟨{nm}⟩ {len(b2)} حرفاً · أرقامٌ={len(_NUM.findall(b2))}"
                  f" · صفوفٌ={len(X._TR.findall(b2))}"
                  f" · **NAV: {len(h2)}**"
                  + (f" ({' · '.join(h2[:2])})" if h2 else "")
                  + (f" · أحدثُ تاريخ={ds[-1]}" if ds else " · بلا تاريخ"))
            if h2:
                # تُطبَع أسماءُ الأعمدة كما هي — لا يُخمَّن موضعُ رقم
                rows = X._TR.findall(b2)[:3]
                for tr in rows:
                    cells = [X._clean(c) for c in X._TD.findall(tr)]
                    if cells:
                        print(f"      صفٌّ: {cells[:8]}")

    # ── ٢ · صفحةُ ورقةٍ مؤشِّرةٍ بعينها ─────────────────────────────────
    for sym in etfs[:2]:
        url = (tm.row_for(sym) or {}).get("company_url")
        print(f"\n════ {sym} ════ رابطُ الصفحة في اللقطة: {url or '—'}")
        if not url:
            continue
        full = X.ORIGIN + url if url.startswith("/") else url
        try:
            st, page = await fetch(full)
        except Exception as e:                                    # noqa: BLE001
            print(f"  تعذّرت — {type(e).__name__}")
            continue
        if st != 200 or not page:
            print(f"  HTTP {st}")
            continue
        mb = X._BASE.search(page)
        svcs = {m.group(1): m.group(0) for m in X._NJ.finditer(page)}
        print(f"  خدماتٌ ({len(svcs)}): {' · '.join(svcs) or 'لا شيء'}")
        _w = [w for w in NAV_WORDS if w in page.lower()]
        print(f"  ومفرداتُ NAV في الصفحة: {len(_w)}"
              + (f" ({' · '.join(_w[:3])})" if _w else ""))
        if not mb:
            continue
        base = mb.group(1).rstrip("/")
        for nm, sp in list(svcs.items())[:8]:
            try:
                s3, b3 = await fetch(f"{base}/{sp}",
                                     params={"requestLocale": "en"},
                                     referer=full)
            except Exception:                                     # noqa: BLE001
                continue
            if s3 != 200 or not b3:
                continue
            h3 = [w for w in NAV_WORDS if w in b3.lower()]
            ds = sorted(set(_DATE.findall(b3)))
            print(f"   ⟨{nm}⟩ {len(b3)} حرفاً · NAV={len(h3)}"
                  + (f" · أحدثُ تاريخ={ds[-1]}" if ds else ""))

    print("\nالحكم: خدمةٌ يظهر في جوابها **مفردةُ صافي الأصول مع رقمٍ"
          " وتاريخ** هي البابُ المطلوب — فتُنقَل أسماءُ أعمدتها بالحرف"
          " ويُبنى عليها معيارُ الورقة المؤشِّرة: قيمتُها = صافي أصولها"
          " للوحدة، والفرصةُ فيها العلاوةُ أو الخصمُ عنه، وجودتُها فرقُ"
          " التتبّع والرسومُ والحجمُ والسيولة. وإن لم يظهر البابُ فيُقال"
          " صريحاً إن NAV غيرُ متوفّرٍ عندنا ولا يُختلَق رقمٌ مكانَه.")
    return 0


raise SystemExit(asyncio.run(main()))
