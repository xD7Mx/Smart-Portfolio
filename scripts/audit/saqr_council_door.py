#!/usr/bin/env python3
"""كاشفُ مجلس صقر (‏D786) على الخادم — قياسُ كلّ مصدرٍ قبل أن يُبنى عليه حكم (قراءةٌ لا تكتب إلا خبءَ القراءة):

قال المالك (2026-11-22): «التحليلُ الفنيّ خطوةٌ من بين الخطوات… يقرأ ويحلّل مثل الصفة البشرية: المسار والمستويات، والشركةُ رابحةٌ أو خاسرة،
وهل هذا ثاني ربعٍ خسارةٍ متواصلة أو ثاني ربعٍ ربحٍ متتالٍ، والأخبار (رئيسُ إنفيديا أُقيل فهبطت رغم نتائجها)، والأحداثُ الاقتصاديةُ والعالمية،
وسلوكُ المستثمرين وانطباعُهم، والصفقاتُ غير الاعتيادية، والحيتان أين يتمركزون… ويربط بينها».

  ١ النتائجُ الربعيةُ المتتالية للسعوديّ: فتراتُ XBRL الربعية (هل الربعُ ثلاثةُ أشهرٍ أم تراكميّ؟) ونتيجةُ «أرقام».
  ٢ نتائجُ ياهو الربعية (‏earnings · earningsHistory · financialData) للسعوديّ والأمريكيّ: الإيرادُ والربحُ ربعياً، ومفاجأةُ السهم، ورأيُ المحللين.
  ٣ أخبارُ الشركة نفسِها: «جوجل نيوز» بالعربية للسعوديّ، وعناوينُ ياهو للأمريكيّ.
  ٤ الصفقاتُ الخاصة (السعوديّ) وآراءُ بيوت الخبرة.
  ٥ تدفّقُ الخيارات (الأمريكيّ): أحجامُ الشراء والبيع، والعقودُ غيرُ الاعتيادية (حجمٌ فوق الاهتمام المفتوح)، وجدرانُ الاهتمام المفتوح.
  ٦ الأحداثُ الاقتصاديةُ القادمة للسوقين.
  ٧ إفصاحاتُ «أرقام» الرسميةُ للشركة السعودية في ثلاثين يوماً (لم تُقس قبل البناء) — عددُها وأحدثُها.
  ٨ المجلسُ على المسح المحفوظ بعد النشر: الحكمُ لكلّ فرصة، وتغطيةُ كلّ عضو (كم «غيرُ متوفّر»)، والمستبعَدُ بسببه، و«الرابط».

    docker exec sp_backend python /app/scripts/audit/saqr_council_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")
SA = [("2222", "أرامكو السعودية"), ("1120", "مصرف الراجحي"), ("2010", "سابك"), ("7010", "الاتصالات السعودية"), ("4030", "البحري"), ("1325", "")]
US = ["NVDA", "AAPL", "TSLA", "ARDT"]


def short(v, n=90):
    s = json.dumps(v, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + "…"


async def main():
    from app.services.market_data import market_service as M
    y = M._yahoo()
    # ١
    print("══ ١ النتائجُ الربعية للسعوديّ (XBRL · أرقام):")
    from app.services import tadawul_xbrl as X
    from app.services import argaam_results as AR
    for sym, _ in SA:
        try:
            q = X.for_symbol(sym, "quarterly")
        except Exception as e:                                    # noqa: BLE001
            print(f"  {sym}: تعذّر {type(e).__name__}")
            continue
        print(f"  {sym}: {len(q)} فترة · مفاتيح آخرها: {sorted((q[-1] if q else {}).keys())[:24]}")
        for p in q[-6:]:
            print(f"     {p.get('as_of')} · فترة {p.get('period') or p.get('months') or p.get('kind') or '?'} · صافي {p.get('net_income')} · الإيراد {p.get('revenue')}"
                  f" · ربحُ السهم {p.get('eps')}")
        print(f"     أرقام: {short((AR.for_symbol(sym) or {}).get('quarter'), 160)}")
    # ٢
    print("══ ٢ ياهو — النتائجُ الربعية ورأيُ المحللين:")
    for sym in ["2222.SR", "1120.SR"] + US:
        try:
            r = await y._quote_summary(sym, "earnings,earningsHistory,financialData,recommendationTrend")
        except Exception as e:                                    # noqa: BLE001
            print(f"  {sym}: تعذّر {type(e).__name__}")
            continue
        if not r:
            print(f"  {sym}: لا نتيجة")
            continue
        fq = (((r.get("earnings") or {}).get("financialsChart") or {}).get("quarterly")) or []
        eh = ((r.get("earningsHistory") or {}).get("history")) or []
        fd = r.get("financialData") or {}
        rt = ((r.get("recommendationTrend") or {}).get("trend")) or []
        print(f"  {sym}: ربعيّ {[(x.get('date'), (x.get('revenue') or {}).get('raw') if isinstance(x.get('revenue'), dict) else x.get('revenue'), (x.get('earnings') or {}).get('raw') if isinstance(x.get('earnings'), dict) else x.get('earnings')) for x in fq]}")
        print(f"     مفاجآت: {[(x.get('quarter'), x.get('epsActual'), x.get('epsEstimate'), x.get('surprisePercent')) for x in eh][-4:]}")
        print(f"     المحللون: {fd.get('recommendationKey')} · المستهدف {fd.get('targetMeanPrice')} · عدد {fd.get('numberOfAnalystOpinions')} · السعر {fd.get('currentPrice')}"
              f" · نموُّ الأرباح {fd.get('earningsGrowth')} · الإيراد {fd.get('revenueGrowth')}")
        print(f"     اتجاهُ التوصيات: {short(rt[:2], 220)}")
    # ٣
    print("══ ٣ أخبارُ الشركة:")
    from app.services import news_fetcher as NF
    for sym, name in SA[:5]:
        try:
            items = await NF._collect([f'"{name}" سهم'], "أسواق", max_age_days=10, tags=[sym], count=10)
        except Exception as e:                                    # noqa: BLE001
            print(f"  {sym}: تعذّر {type(e).__name__}")
            continue
        print(f"  {sym} {name}: {len(items)} عنواناً")
        for it in items[:3]:
            print(f"     [{str(it.get('published'))[:10]}] {it.get('headline')} ({it.get('source')})")
    from app.services import option_picks as OP
    for sym in US[:3]:
        try:
            h = await OP.headlines(sym)
        except Exception as e:                                    # noqa: BLE001
            print(f"  {sym}: تعذّر {type(e).__name__}")
            continue
        print(f"  {sym}: {len(h)} عنواناً · " + " | ".join(f"[{x['at']}] {x['title'][:70]}" for x in h[:2]))
    # ٤
    print("══ ٤ الصفقاتُ الخاصة وآراءُ بيوت الخبرة:")
    from app.services import special_deals as SD
    from app.services import analyst_opinions as AO
    rd = SD.reading() or {}
    deals = rd.get("deals") or []
    print(f"  الصفقات: {len(deals)} · محفوظةٌ {rd.get('at')} · مثالٌ: {short(deals[:2], 260)}")
    by = {}
    for d in deals:
        by[d["symbol"]] = by.get(d["symbol"], 0) + (d.get("value") or 0)
    print(f"  أكبرُها قيمةً: {sorted(by.items(), key=lambda kv: -kv[1])[:6]}")
    st = AO.stored() or {}
    print(f"  آراءُ البيوت: {len(st)} شركة · {sum(len(v) for v in st.values())} رأياً")
    for sym, _ in SA[:4]:
        rows = AO.for_symbol(sym)
        print(f"  {sym}: {len(rows)} رأياً · " + " | ".join(f"{r['date']} {r['house']} {r['rating']} → {r.get('target')}" for r in rows[:3]))
    # ٥
    print("══ ٥ تدفّقُ الخيارات (الأمريكيّ):")
    from app.services.options_chain import chain
    for sym in US[:3]:
        base = await chain(sym)
        if not base:
            print(f"  {sym}: لا سلسلة")
            continue
        S = base.get("price")
        exps = (base.get("expirations") or [])[:3]
        cv = pv = coi = poi = 0
        unusual, walls_c, walls_p = [], {}, {}
        for e in exps:
            ch = base if e["t"] == base.get("expiry") else await chain(sym, e["t"])
            if not ch:
                continue
            for side, rows in (("C", ch["calls"]), ("P", ch["puts"])):
                for o in rows:
                    v, oi = o.get("volume") or 0, o.get("oi") or 0
                    if side == "C":
                        cv += v
                        coi += oi
                        walls_c[o["strike"]] = walls_c.get(o["strike"], 0) + oi
                    else:
                        pv += v
                        poi += oi
                        walls_p[o["strike"]] = walls_p.get(o["strike"], 0) + oi
                    if v >= 500 and v > 1.5 * max(oi, 1):
                        unusual.append((o["contract"], v, oi, o.get("last")))
        unusual.sort(key=lambda x: -x[1])
        wc = sorted(((k, v) for k, v in walls_c.items() if S and k and k >= S), key=lambda kv: -kv[1])[:2]
        wp = sorted(((k, v) for k, v in walls_p.items() if S and k and k <= S), key=lambda kv: -kv[1])[:2]
        print(f"  {sym} @ {S}: آجال {[e['date'] for e in exps]} · حجمُ الشراء {cv:,} والبيع {pv:,} (نسبة {pv / max(cv, 1):.2f}) · اهتمامٌ {coi:,}/{poi:,}")
        print(f"     غيرُ اعتياديّ: {unusual[:4]}")
        print(f"     جدرانُ الشراء فوق السعر {wc} · جدرانُ البيع تحته {wp}")
    # ٦
    print("══ ٦ الأحداثُ الاقتصاديةُ القادمة:")
    from app.services import econ_calendar as EC
    for m in ("sa", "us"):
        try:
            w = await EC.week(with_reading=False, market=m)
        except Exception as e:                                    # noqa: BLE001
            print(f"  {m}: تعذّر {type(e).__name__}")
            continue
        ev = [e for e in w.get("events") or [] if not e.get("past")]
        hi = [e for e in ev if e.get("impact") == "High"]
        print(f"  {m}: {len(ev)} قادمة · عاليةُ الأثر {len(hi)}: " + " | ".join(f"{e.get('at', '')[:16]} {e.get('ar') or e.get('title')}" for e in hi[:5]))
        if ev:
            print(f"     مفاتيح الحدث: {sorted(ev[0].keys())}")

    # ٧
    print("══ ٧ إفصاحاتُ «أرقام» للشركة (ثلاثون يوماً):")
    from datetime import datetime, timedelta, timezone
    from app.services.argaam_calendar import fetch_company_page
    floor = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    for sym, _ in SA:
        try:
            pg = await asyncio.wait_for(fetch_company_page(sym), 25)
        except Exception as e:                                    # noqa: BLE001
            print(f"  {sym}: تعذّر {type(e).__name__}")
            continue
        ds = (pg or {}).get("disclosures") or []
        rec = [d for d in ds if str(d.get("date") or "") >= floor]
        print(f"  {sym}: {len(ds)} إفصاحاً في الصفحة · {len(rec)} في ثلاثين يوماً · بلا تاريخ {sum(1 for d in ds if not d.get('date'))}")
        for d in rec[:3]:
            print(f"     [{d.get('date')}] {str(d.get('title'))[:90]}")
    # ٨
    print("══ ٨ مجلسُ صقر على المسح المحفوظ:")
    from app.services import chart_scan as CS
    for m in ("sa", "us"):
        d = CS.load(m) or {}
        items, rej = d.get("items") or [], d.get("rejected") or []
        print(f"  {m}: محفوظٌ {d.get('at')} في {d.get('secs')} ث · المجال {d.get('universe')} · رسومٌ {d.get('read')} · مقبولة {len(items)} · مستبعَدة {len(rej)}")
        if items and not any(x.get("council") for x in items):
            print("     المسحُ سبق المجلس — لا حكمَ فيه بعد")
            continue
        cov = {}
        for x in items:
            for mm in (x.get("council") or {}).get("members") or []:
                cov.setdefault(mm["role"], {}).setdefault(mm["v"], 0)
                cov[mm["role"]][mm["v"]] += 1
        print("     تغطيةُ الأعضاء في المقبول: " + " · ".join(f"{r} {v}" for r, v in cov.items()))
        vv = {}
        for x in items:
            k = (x.get("council") or {}).get("verdict")
            vv[k] = vv.get(k, 0) + 1
        print(f"     الأحكام: {vv}")
        for x in items[:8]:
            c, lk = x.get("council") or {}, x.get("link") or {}
            print(f"     {x['symbol']} {x.get('name') or ''} · {x['setup']} {x['quality']} · المجلس {c.get('verdict')} {c.get('score')}"
                  + (f" · الرابط {lk.get('decision')}/{lk.get('confidence')}: {str(lk.get('link'))[:110]}" if lk else ""))
            for mm in c.get("members") or []:
                print(f"        {mm['role']} ({mm['v']}): {mm['say'][:120]}")
        why = {}
        for r in rej:
            k = (r.get("why") or ["?"])[0].split(":")[0]
            why[k] = why.get(k, 0) + 1
        print(f"     أسبابُ الاستبعاد (العضوُ الرافض): {why}")
        for r in rej[:6]:
            print(f"     ✘ {r['symbol']} {r.get('name') or ''} · {r['setup']} {r['quality']} — {' · '.join(r.get('why') or [])[:150]}")

asyncio.run(main())
