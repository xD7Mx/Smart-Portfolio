#!/usr/bin/env python3
"""تصفّحُ «تداول» بمتصفّحٍ حقيقيٍّ حتى تُوجَد الميزةُ بأيّ اسم (D314).

    docker exec sp_backend python /app/scripts/audit/tadawul_explore.py
    docker exec sp_backend python /app/scripts/audit/tadawul_explore.py --word=صفق

## لماذا هذه الأداة

قال المالك: «بإمكانك تشغيلُ تداول بشكلٍ عميقٍ وتبحث عن الميزة أيّاً كان
اسمُها وتعتمدها — لكن بدلاً من ذلك أنت تخمّن». وهو محقّ: بحثتُ في **نصّ**
الصفحة الرئيسة فوجدتُ ٤١٦ رابطاً بلا ذكرٍ للصفقات، وحكمتُ بأن الموقعَ لا
ينشرها. والسببُ أن **القائمةَ يبنيها جافاسكربت**: لا تظهر في المصدر، وتظهر
في الصفحة المرسومة. فكلُّ تخميني بعدها كان مبنياً على قياسٍ ناقص.

## ما تفعله

١· تفتح الرئيسةَ بمتصفّحٍ حقيقيٍّ وتقرأ **روابطَ الصفحة المرسومة** كلَّها
   (مع نصّها) — لا مصدرَها.
٢· تفتح كلَّ قائمةٍ منسدلةٍ بالمرور عليها فتظهر روابطُها المخفيّة.
٣· تُرشِّح ما يذكر المعنى (صفق · خاص · متفاوض · deal · negotiat).
٤· تزور كلَّ مرشَّحٍ وتقيس فيه: صفوفَ جدوله المرسوم، وعيّنةَ نصّها،
   ونداءاتَ الشبكة التي وقعت وأجسامَها من مضيف «تداول».
٥· ثمّ تكتب الحكم: أيُّ صفحةٍ تحمل الجدول، وأيُّ نداءٍ يعطيه.

ولا تكتب في التطبيق شيئاً — أداةُ اكتشافٍ فقط.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

HOME = "https://www.saudiexchange.sa/wps/portal/saudiexchange/home"
MEAN = re.compile(r"صفق|خاص|متفاوض|deal|negotiat", re.I)
HOST = "saudiexchange.sa"
MAX_PAGES = 3          # الموقعُ مقيَّدُ المعدّل: الأهمُّ أوّلاً وقليلاً
SETTLE = 6000

# صفٌّ يشبه صفقةً: رمزٌ رباعيٌّ + رقمٌ كسريٌّ (سعر) + رقمٌ كبير (كمّية)
ROWISH = (re.compile(r"\b\d{4}\b"), re.compile(r"\d+\.\d{1,2}"),
          re.compile(r"\d{3,}"))


def _word() -> re.Pattern:
    for a in sys.argv[1:]:
        if a.startswith("--word="):
            return re.compile(a.split("=", 1)[1], re.I)
    return MEAN


async def main() -> int:
    from app.services.browser_fetch import BrowserUnavailable, _launch_kwargs

    try:
        from playwright.async_api import async_playwright
    except Exception as e:                                        # noqa: BLE001
        print(f"playwright غير متاحة: {e}")
        return 2

    want = _word()
    pw = browser = None
    try:
        pw = await async_playwright().start()
        try:
            browser = await pw.chromium.launch(**_launch_kwargs())
        except Exception as e:                                    # noqa: BLE001
            raise BrowserUnavailable(f"تعذّر تشغيل كروميوم: {e}") from e
        ctx = await browser.new_context(
            locale="ar-SA", viewport={"width": 1400, "height": 1000},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"))
        page = await ctx.new_page()

        # ── ١ · الرئيسةُ مرسومةً ───────────────────────────────────────
        print("═ الرئيسة ═")
        await page.goto(HOME, timeout=40000, wait_until="domcontentloaded")
        await page.wait_for_timeout(SETTLE)

        async def links() -> list[dict]:
            return await page.evaluate("""() => [...document.querySelectorAll('a')]
                .map(a => ({href: a.href || '',
                            text: (a.textContent || '').replace(/\\s+/g,' ').trim(),
                            title: a.getAttribute('title') || ''}))
                .filter(x => x.href)""")

        first = await links()
        print(f"  روابطُ الصفحة المرسومة: {len(first)}")

        # ── ٢ · القوائمُ المنسدلةُ تُفتح بالمرور ───────────────────────
        # قائمةٌ لا تُفتح لا تُظهر روابطَها: يُمرَّر على كلّ عنوانٍ في شريط
        # القوائم ثمّ تُقرأ الروابطُ من جديد.
        try:
            tops = await page.query_selector_all(
                "nav li, .navbar li, [class*='menu'] li, [class*='nav'] li")
            hovered = 0
            for el in tops[:28]:
                try:
                    await el.hover(timeout=1200)
                    await page.wait_for_timeout(180)
                    hovered += 1
                except Exception:                                 # noqa: BLE001
                    continue
            print(f"  قوائمُ فُتحت بالمرور: {hovered}")
        except Exception as e:                                    # noqa: BLE001
            print(f"  المرورُ تعذّر: {type(e).__name__}")

        after = await links()
        print(f"  وبعد فتح القوائم: {len(after)}")

        seen: dict[str, str] = {}
        for x in first + after:
            t = (x["text"] or x["title"] or "").strip()
            if HOST in x["href"]:
                seen.setdefault(x["href"], t)

        cands = [(h, t) for h, t in seen.items()
                 if want.search(t) or want.search(h)]

        # ══ أشقّاءُ المسار ══ (D315)
        # قِيس أن الميزةَ صفحةٌ **لكلّ سوق** بالنمط نفسِه:
        # `ourmarkets/<السوق>-market-watch/issuers-trading-information`.
        # وقائمةُ المرشَّحين جاءت بالمشتقّات والصكوك والصناديق ولم تأتِ
        # بالسوق الرئيسة — وهي المطلوبة. فتُولَّد الأشقّاءُ من النمط
        # المقيس، لا من تخمينٍ: نفسُ المسار بسوقٍ آخر.
        sibs: list[tuple[str, str]] = []
        for h, t0 in list(cands):
            m = re.search(r"/ourmarkets/([a-z\-]+)-market-watch/", h)
            if not m:
                continue
            for mk in ("main", "nomu"):
                u = h.replace(f"/{m.group(1)}-market-watch/",
                              f"/{mk}-market-watch/")
                # لا يُسقَط شقيقٌ لأنه «مرئيٌّ في القائمة»: السوقُ الرئيسة
                # مرئيةٌ بمساراتٍ أخرى، فأسقطها شرطي الأوّل — وهي المطلوبة.
                if all(u != s for s, _ in sibs) and u not in [c for c, _ in cands]:
                    sibs.append((u, f"{t0} — سوقُ {mk}"))
        if sibs:
            print(f"\n═ أشقّاءُ المسار (مولَّدون من النمط): {len(sibs)} ═")
            for u, lab in sibs:
                print(f"   «{lab}» → {u[:120]}")
            # الرئيسةُ أوّلاً ثمّ نمو، ثمّ ما رأته القائمة
            sibs.sort(key=lambda x: 0 if "/main-market-watch/" in x[0] else 1)
            cands = sibs + cands
        print(f"\n═ روابطُ تذكر المعنى: {len(cands)} ═")
        for h, t in cands[:20]:
            print(f"   «{t[:46] or '—'}» → {h[:120]}")
        if not cands:
            # لا يُحكم بالعجز قبل طبع القائمة كلِّها: ربّما الاسمُ غيرُ ما ظننت.
            print("   لا شيء. وهذه عيّناتُ نصوصِ القوائم لتُقرأ بعينك:")
            texts = sorted({t for t in seen.values() if 2 < len(t) < 40})
            for t in texts[:60]:
                print(f"      {t}")

        # ── ٣ · كلُّ مرشَّحٍ يُزار ويُقاس ───────────────────────────────
        best = []
        for h, t in cands[:MAX_PAGES]:
            calls: list[dict] = []
            resp: list = []

            def _on(r) -> None:
                try:
                    calls.append({"u": r.url, "s": r.status,
                                  "k": r.request.resource_type})
                    resp.append(r)
                except Exception:                                 # noqa: BLE001
                    pass

            p2 = await ctx.new_page()
            p2.on("response", _on)
            print(f"\n═ زيارة: «{t[:40]}» ═\n   {h[:130]}")
            try:
                # ══ مهلةٌ أطولُ ومحاولةٌ ثانية ══ (D316)
                # قِيس أن ثلاثاً من أربع صفحاتٍ انتهت مهلتُها عند ٤٠ ثانية،
                # ومخرَجُ المزوّد يقول `rate_limited: true` — فالموقعُ بطيءٌ
                # تحت التوالي. فيُنتظَر أوّلُ بايتٍ (`commit`) لا رسمُ
                # المستند، وتُعاد المحاولةُ مرّةً، ويُمهَل بين الصفحات.
                try:
                    await p2.goto(h, timeout=90000, wait_until="commit")
                except Exception:                                 # noqa: BLE001
                    await p2.wait_for_timeout(4000)
                    await p2.goto(h, timeout=90000, wait_until="commit")
                await p2.wait_for_timeout(SETTLE + 4000)
                # ══ الخلايا لا الصفّ ══
                # `textContent` للصفّ يلصق الخلايا: «الراجحي112092.50…» —
                # فتضيع حدودُ الرمز والسعر ويُحكم بأنه لا يشبه صفقة (وهو
                # العطبُ الذي جعلني أقول «صفرُ صفوف» قبلاً). فتُقرأ الخلايا
                # وتُوصَل بفاصلٍ ظاهر.
                rows = await p2.evaluate("""() => {
                    const cells = (el, sel) =>
                      [...el.querySelectorAll(sel)]
                        .map(c => (c.textContent || '').replace(/\\s+/g,' ').trim())
                        .filter(Boolean).join(' | ');
                    const out = [];
                    for (const tr of document.querySelectorAll('tr')) {
                      const s = cells(tr, 'td,th') ||
                        (tr.textContent || '').replace(/\\s+/g,' ').trim();
                      if (s) out.push(s);
                    }
                    if (out.length === 0) {
                      for (const d of document.querySelectorAll('[class*="row"],[role="row"]')) {
                        const s = cells(d, '[class*="cell"],[role="cell"],div,span') ||
                          (d.textContent || '').replace(/\\s+/g,' ').trim();
                        if (s && s.length < 300) out.push(s);
                      }
                    }
                    return out.slice(0, 40);
                }""")
            except Exception as e:                                # noqa: BLE001
                print(f"   تعذّر فتحُها: {type(e).__name__}: {e}")
                await p2.close()
                continue

            # ══ الجدولُ يُملأ بضغطة ══ (D317)
            # قِيس على السوق الرئيسة: ترويسةُ الجدول صحيحةٌ («التاريخ |
            # الرمز | الشركة | السعر | الكمية المتداولة | القيمة المتداولة
            # | الوقت») وتحتها شروطُ الأهلية، و**صفرُ نداءِ بيانات**. أي
            # أن الشبكةَ لا تُطلَق بمجرّد الفتح: الصفحةُ تنتظر بحثاً.
            # فتُجرَّب الأزرارُ بمعناها (بحث · عرض · تطبيق · Search)،
            # وتُقرأ الصفوفُ والنداءاتُ بعدها.
            if not any(all(rx.search(r) for rx in ROWISH) for r in rows):
                try:
                    btns = await p2.query_selector_all(
                        "button, input[type=submit], input[type=button], a.btn,"
                        " [class*='search'], [class*='btn']")
                    pressed = 0
                    for b in btns[:40]:
                        try:
                            lbl = ((await b.inner_text()) or "").strip()
                            if not lbl:
                                lbl = (await b.get_attribute("value")) or ""
                            if not re.search(r"بحث|عرض|تطبيق|search|submit|go",
                                             lbl, re.I):
                                continue
                            await b.click(timeout=2500)
                            pressed += 1
                            await p2.wait_for_timeout(5000)
                            if pressed >= 2:
                                break
                        except Exception:                         # noqa: BLE001
                            continue
                    print(f"   أزرارٌ ضُغطت بمعناها: {pressed}")
                    if pressed:
                        rows = await p2.evaluate("""() => {
                            const cells = (el, sel) =>
                              [...el.querySelectorAll(sel)]
                                .map(c => (c.textContent || '').replace(/\\s+/g,' ').trim())
                                .filter(Boolean).join(' | ');
                            const out = [];
                            for (const tr of document.querySelectorAll('tr')) {
                              const s = cells(tr, 'td,th') ||
                                (tr.textContent || '').replace(/\\s+/g,' ').trim();
                              if (s) out.push(s);
                            }
                            return out.slice(0, 40);
                        }""")
                except Exception as e:                            # noqa: BLE001
                    print(f"   التفاعلُ تعذّر: {type(e).__name__}")

            dealish = [r for r in rows
                       if all(rx.search(r) for rx in ROWISH)]
            print(f"   صفوفٌ مرسومة: {len(rows)} · منها تشبه صفقةً: {len(dealish)}")
            for r in dealish[:4]:
                print(f"      {r[:150]}")
            if not dealish:
                for r in rows[:8]:
                    print(f"      (صفٌّ لا يشبه صفقة) {r[:130]}")

            xhr = [c for c in calls
                   if c["k"] in ("xhr", "fetch") and HOST in c["u"]]
            print(f"   نداءاتُ بياناتٍ من «تداول»: {len(xhr)}")
            for c in xhr[:8]:
                print(f"      {c['s']} {c['u'][:120]}")
            # ══ نداءُ الصفحة أوّلاً ══ (D315)
            # التقاطي كان بترتيب الوصول، فامتلأ سقفُه بخدمات القالب
            # (`ThemeTASIUtilityServlet` · `TickerServlet`) ولم يبقَ موضعٌ
            # لنداءِ الجدول نفسِه. فيُرتَّب: ما يحمل مسارَ الصفحة قبلَ غيره.
            key = re.sub(r"\?.*$", "", h).rstrip("/").split("/")[-1]
            ordered = sorted(
                resp, key=lambda r: 0 if key and key in getattr(r, "url", "")
                else (1 if "theme.helper" not in getattr(r, "url", "") else 2))
            bodies = []
            for r in ordered:
                if len(bodies) >= 5:
                    break
                try:
                    if r.request.resource_type not in ("xhr", "fetch"):
                        continue
                    if HOST not in r.url:
                        continue
                    b = await r.text()
                except Exception:                                 # noqa: BLE001
                    continue
                if not b:
                    continue
                looks = all(rx.search(b) for rx in ROWISH)
                bodies.append((r.url, len(b), looks, b[:220]))
            for u, n, looks, head in bodies:
                data_ep = '"data"' in head or "issuers-trading" in u
                print(f"      جسمٌ {n} حرفاً"
                      + ("  ← يشبه بياناتِ صفقات" if looks else "")
                      + ("  ★ نداءُ جدولِ الصفحة" if data_ep else "")
                      + f"\n         {u if data_ep else u[:110]}\n         "
                      + re.sub(r"\s+", " ", head if not data_ep else head[:700]))
            if dealish or any(x[2] for x in bodies):
                best.append({"page": h, "title": t, "rows": len(dealish),
                             "bodies": [x[0] for x in bodies if x[2]]})
            await p2.close()
            await page.wait_for_timeout(2500)     # نفَسٌ بين الصفحات

        # ── ٤ · الحكم ──────────────────────────────────────────────────
        print("\n═ الحكم ═")
        if best:
            print("وُجدت. أعتمدها في التطبيق:")
            for b in best:
                print("   " + json.dumps(b, ensure_ascii=False)[:400])
        elif cands:
            print("الروابطُ موجودةٌ وصفحاتُها بلا صفوفِ صفقات — "
                  "فالميزةُ معروضةٌ بشكلٍ آخرَ أو محجوبةٌ عند الحافّة.")
        else:
            print("لا رابطَ يذكر المعنى في القوائم المرسومة. "
                  "اقرأ عيّناتِ النصوص أعلاه: إن رأيتَ اسمَ الميزة فمرّره "
                  "بـ‎--word=<كلمة> ويُعاد البحثُ به.")
        return 0
    except BrowserUnavailable as e:
        print(f"المتصفّحُ غيرُ متاح: {e}")
        return 2
    finally:
        for closer in (getattr(browser, "close", None),
                       getattr(pw, "stop", None)):
            if closer:
                try:
                    await closer()
                except Exception:                                 # noqa: BLE001
                    pass


raise SystemExit(asyncio.run(main()))
