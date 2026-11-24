#!/usr/bin/env python3
"""كاشفُ D816 على الخادم — هل يقدر التطبيقُ وحده على التقرير اليوميّ كاملاً لو غاب تقريرا الجزيرة والراجحي؟ (قراءةٌ لا تكتب شيئاً)

قال المالك (2026-11-24): «التقريرُ يستقي معلوماته من الجزيرة والراجحي كمبدأ، ولو حصلت لهما مشكلة يقوم تطبيقُنا بالعمل بنفسه — الأخبارُ
المحلية والعالمية وبقيةُ التقرير كاملاً، وكلُّ معلومةٍ فيه — مع الحفاظ على شكل التقرير».
فيُقاس هنا ما يملكه التطبيقُ بنفسه لكلّ قسمٍ كان يأتي من التقريرين:

  ١ الأخبار: عناوينُ اليوم من الوسائل الموثوقة (محليّةٌ وعالميةٌ واقتصادية)، وإعلاناتُ «تداول» الرسمية.
  ٢ ما يُتابَع: أحداثُ الأسبوع الاقتصاديةُ للسوقين بأثرها.
  ٣ الأسواقُ الإقليمية: رموزٌ مرشّحةٌ لمؤشّرات الخليج ومصر — أيُّها يرسمه المصدرُ فعلاً (لا يُعتمد رمزٌ لم يُقس).
  ٤ أسعارُ الفائدة بين البنوك (سايبور): هل تصل صفحةُ البنك المركزيّ وفيها أرقام.

    docker exec sp_backend python /app/scripts/audit/report_self_door_d816.py
"""
import os
import time

os.environ.setdefault("TZ", "Asia/Riyadh")
time.tzset()

import asyncio  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, "/app")

REGIONAL = {
    "دبي": ["DFMGI.AE", "^DFMGI", "DFMGI"],
    "أبو ظبي": ["^FTFADGI", "FADGI.FGI", "^ADI", "FTFADGI"],
    "الكويت": ["^BKP", "^KWSE", "BKP.KW"],
    "قطر": ["^QSI", "QSI.QA", "^GNRI.QA", "GNRI.QA"],
    "عُمان": ["^MSX30", "^MSM30", "MSX30.OM"],
    "البحرين": ["^BAX", "^BHSE", "BAX.BH"],
    "مصر": ["^CASE30", "EGX30.CA", "^EGX30"],
}
SAIBOR_URLS = ["https://www.sama.gov.sa/en-US/FinExc/Pages/SAIBOR.aspx", "https://www.sama.gov.sa/ar-sa/FinExc/Pages/SAIBOR.aspx",
               "https://www.sama.gov.sa/en-US/Indices/Pages/SAIBOR.aspx"]


async def main():
    from datetime import date, datetime, timedelta, timezone
    from app.services import news_fetcher as NF
    from app.services import research_desk as RD
    print("══ ١ الأخبار من الوسائل الموثوقة (آخرُ 30 ساعة)")
    cut = datetime.now(timezone.utc) - timedelta(hours=30)
    for name, fn in (("محليّ", NF.fetch_market_news), ("عالميّ", NF.fetch_global_news), ("اقتصاديّ", NF.fetch_economic_news)):
        t0 = time.monotonic()
        try:
            items = await fn()
        except Exception as e:                                   # noqa: BLE001
            print(f"   {name}: تعذّر {type(e).__name__}")
            continue
        fresh = [i for i in items if i.get("trusted") and i.get("published") and i["published"] >= cut]
        srcs = sorted({str(i.get("source")) for i in fresh})
        print(f"   {name}: {len(items)} عنواناً · موثوقٌ حديث {len(fresh)} · الوسائل {len(srcs)}: {' · '.join(srcs[:8])} · {time.monotonic() - t0:.1f}ث")
        for i in fresh[:2]:
            print(f"      — {str(i.get('headline'))[:90]}")
    w = await RD.wire_sources(date.today())
    print("   مصادرُ الأخبار المستقلّة للتقرير:", [(x["key"], len(x.get("local_news") or x.get("global_news") or [])) for x in w])
    try:
        from app.services.tadawul_announcements import fetch_tadawul_announcements
        ann = await fetch_tadawul_announcements()
        today = date.today().isoformat()
        recent = [a for a in ann if str(a.get("date") or "")[:10] >= (date.today() - timedelta(days=2)).isoformat()]
        print(f"   إعلاناتُ «تداول» الرسمية: {len(ann)} · آخرُ يومين {len(recent)} · اليوم {sum(1 for a in ann if str(a.get('date') or '')[:10] == today)}")
        for a in recent[:3]:
            print(f"      — {a.get('date')} · {a.get('symbol')} · {str(a.get('title') or a.get('headline') or '')[:70]}")
    except Exception as e:                                       # noqa: BLE001
        print("   إعلاناتُ «تداول»: تعذّر", type(e).__name__)

    print("══ ٢ ما يُتابَع — أحداثُ الأسبوع")
    try:
        from app.services import econ_calendar as EC
        raw = await EC.raw_week()
        for mk in ("sa", "us"):
            ev = EC.shape(raw, market=mk)
            print(f"   {mk}: {len(ev)} حدثاً · " + " | ".join(f"{e.get('when') or e.get('date') or ''} {str(e.get('title_ar') or e.get('title') or '')[:40]}" for e in ev[:3]))
    except Exception as e:                                       # noqa: BLE001
        print("   تعذّر:", type(e).__name__)

    print("══ ٣ الأسواقُ الإقليمية — رموزٌ مرشّحة")
    from app.services.market_data import market_service
    for mk, cands in REGIONAL.items():
        res = []
        for s in cands:
            try:
                b = await asyncio.wait_for(market_service.get_bars(s, "1d"), 30)
            except Exception:                                    # noqa: BLE001
                b = []
            last = (b[-1].get("date") or b[-1].get("time")) if b else None
            res.append(f"{s}={len(b)}{'@' + str(last)[:10] if last else ''}")
        print(f"   {mk}: " + " · ".join(res))

    print("══ ٤ سايبور — صفحةُ البنك المركزيّ")
    import httpx
    for u in SAIBOR_URLS:
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as c:
                r = await c.get(u)
            nums = re.findall(r"\b[0-9]\.[0-9]{3,5}\b", r.text)
            print(f"   {u[-40:]}: {r.status_code} · {len(r.text)}B · أرقامٌ عشرية {len(nums)} · سايبور مذكور={'SAIBOR' in r.text or 'سايبور' in r.text}")
        except Exception as e:                                   # noqa: BLE001
            print(f"   {u[-40:]}: تعذّر {type(e).__name__}")
    print("══ انتهى")


asyncio.run(main())
