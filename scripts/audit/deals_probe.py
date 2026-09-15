#!/usr/bin/env python3
"""مسبارُ الصفقات الخاصة — يقيس على الخادم ما حُجب عن حاويتي (D273 · D296).

    docker exec sp_backend python /app/scripts/audit/deals_probe.py
    docker exec sp_backend python /app/scripts/audit/deals_probe.py --days=7
    docker exec sp_backend python /app/scripts/audit/deals_probe.py --apply
    docker exec sp_backend python /app/scripts/audit/deals_probe.py --dump

يمشي **بطريقة نشر المصدر نفسِها** مرحلةً مرحلةً فيُرى أين ينقطع الخيط:
قائمةُ «أرقام» ← فهرسُ الوسم ← مقالاتُه المؤرَّخة ← جدولُ كلٍّ منها. ثمّ
طبقةُ «تداول» بعدها. ولا يكتب شيئاً إلا بـ`--apply`.

و`--dump` يحفظ **البايتاتَ الخام** التي وصلت (الصفحاتُ كما جاءت) في
`/app/_deals_dump.tar.gz` — أي `backend/_deals_dump.tar.gz` على الخادم،
لأن `./backend` مربوطٌ بالحاوية. والسببُ صريح: «أرقام» محجوبةٌ عن بيئة
التطوير بسياسة الخروج، فالمستخرِجُ لا يُكتب على تخمينِ شكلٍ بل على
الصفحة الحقيقية. يُرسَل الملفُّ مرّةً واحدةً فيُكتب القارئُ على واقعه.
"""
from __future__ import annotations

import asyncio
import json
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")


def _days() -> int:
    for a in sys.argv[1:]:
        if a.startswith("--days="):
            try:
                return max(1, int(a.split("=", 1)[1]))
            except ValueError:
                pass
    return 30


async def dump() -> int:
    """يحفظ الصفحاتَ الخام كما وصلت — دليلٌ يُقرأ لا وصفٌ يُروى."""
    import io
    import re as _re2
    import pathlib
    import tarfile

    from app.services import special_deals as sd
    from app.services.tadawul_http import fetch, smart_flow

    files: dict[str, bytes] = {}
    man: list[dict] = []

    def keep(name: str, status: int, body: str, url: str) -> None:
        raw = (body or "")[:2_000_000].encode("utf-8", "replace")
        files[name] = raw
        man.append({"file": name, "url": url, "status": status, "bytes": len(raw)})
        print(f"  · {name}: HTTP {status} · {len(raw)} بايت · {url[:80]}")

    def plan():
        status, home = yield {"url": sd.ARGAAM_HOME}
        keep("home.html", status, home, sd.ARGAAM_HOME)
        index = sd._index_from_nav(home or "") if status == 200 else None
        pages = sd._index_pages(index or sd.TAG_INDEX.format(page=1))[:2]
        arts: list[str] = []
        for i, u in enumerate(pages, 1):
            status, body = yield {"url": u, "referer": sd.ARGAAM_HOME}
            keep(f"index_{i}.html", status, body, u)
            for href, _t in sd._index_links(body or ""):
                if href not in arts:
                    arts.append(href)
        # وإن لم يُعطِ الفهرسُ مقالاتٍ: تُجلَب روابطُ المقالات كما وردت في
        # الصفحة بلا مرشِّح عنوان — فالدليلُ أهمُّ من ترشيحنا.
        if not arts:
            import re as _re
            for m in _re.finditer(r'href="([^"]*?/ar/article/articledetail/id/\d+[^"]*)"',
                                  files.get("index_1.html", b"").decode("utf-8", "replace")):
                u = sd._abs(m.group(1))
                if u not in arts:
                    arts.append(u)
        for i, u in enumerate(arts[:4], 1):
            status, body = yield {"url": u, "referer": pages[0]}
            keep(f"article_{i}.html", status, body, u)
        return len(arts)

    print("═ جلبُ الدليل من «أرقام» ═")
    try:
        found = await smart_flow(plan, warm=sd.ARGAAM_HOME)
        print(f"روابطُ مقالاتٍ وُجدت: {found}")
    except Exception as e:                                        # noqa: BLE001
        print(f"خطّةُ الجلب تعذّرت: {type(e).__name__}: {e}")

    # ══ وبالمتصفّح أيضاً ══
    # إن كان الجدولُ يُبنى بجافاسكربت فالجلبُ المنتحِلُ يعود بقشرةٍ صادقةٍ
    # فارغة. فيُحفَظ **ما يراه متصفّحٌ حقيقيٌّ** كذلك — فالدليلُ يحسم أيَّ
    # الطبقتين تُقرأ، ولا يُخمَّن.
    print("═ وبالمتصفّح (إن توفّر على الخادم) ═")
    try:
        from app.services.browser_fetch import BrowserUnavailable, render
        want = [m["url"] for m in man
                if m["file"].startswith(("index_1", "article_1"))]
        pages = await render(want, settle_ms=9000)
        for i, (u, html) in enumerate(pages.items(), 1):
            # لا حالةَ HTTP للمتصفّح: يُكتب صفراً لا 200 مخترَعاً.
            keep(f"browser_{i}.html", 0, html, u)
    except BrowserUnavailable as e:
        print(f"  المتصفّحُ غيرُ متاح: {e}")
    except Exception as e:                                        # noqa: BLE001
        print(f"  تعذّر: {type(e).__name__}: {e}")

    # ══ وصفحةُ «تداول» من قائمتها هي ══ (D311)
    # قِيس أن المسارَ المحفوظَ يُصرَف إلى صفحةٍ أخرى (أساسُها
    # `investing-trading`). فتُقرأ من القائمة بمعرِّفها المولَّد.
    print("═ صفحةُ «تداول» من قائمتها ═")

    def nav_plan():
        status, home = yield {"url": sd.TD_HOME}
        keep("td_home.html", status, home, sd.TD_HOME)
        url = sd.td_page_from_nav(home or "") if status == 200 else None
        print(f"  رابطُ «الصفقات الخاصة» في القائمة: {url or 'لم يوجد'}")
        if not url:
            return None
        status, page = yield {"url": url, "referer": sd.TD_HOME}
        keep("td_deals.html", status, page, url)
        base = sd.td_base(page or "")
        names = sorted(set(_re2.findall(r"=NJ([A-Za-z][A-Za-z0-9_]{3,60})=/",
                                        page or "")))
        print(f"  أساسُ الصفحة: {base or 'لا شيء'}")
        print(f"  أسماءُ خدماتها: {', '.join(names[:10]) or 'لا شيء'}")
        got = sd.rows_from_html(page or "")
        print(f"  صفقاتٌ من جدول الصفحة: {len(got)}")
        for d in got[:4]:
            print("      " + json.dumps(d, ensure_ascii=False))
        return len(got)

    try:
        import re as _re2  # noqa: F811
        await smart_flow(nav_plan, warm=sd.TD_HOME)
    except Exception as e:                                        # noqa: BLE001
        print(f"  تعذّر: {type(e).__name__}: {e}")

    print("═ وصفحةُ «تداول» للصفقات الخاصة ═")
    try:
        status, body = await fetch(sd.PAGE)
        keep("tadawul.html", status, body, sd.PAGE)
    except Exception as e:                                        # noqa: BLE001
        print(f"تعذّر: {type(e).__name__}: {e}")

    # ══ إشارةٌ فوريةٌ في الطرفيّة ══
    # لا يُنتظَر تحليلي: عددُ صفوف الجدول في كلّ صفحةٍ يقول فوراً هل وصل
    # المحتوى أم صفحةُ اعتراض.
    import re as _re2
    print("\n═ صفوفُ الجداول في كلّ صفحة ═")
    for name, raw in files.items():
        html = raw.decode("utf-8", "replace")
        trs = len(_re2.findall(r"<tr\b", html, _re2.I))
        tbl = len(_re2.findall(r"<table\b", html, _re2.I))
        deny = "Access Denied" in html or "غير مصرح" in html
        print(f"  · {name}: {tbl} جدولاً · {trs} صفّاً"
              + ("  ← صفحةُ اعتراض" if deny else ""))

    # ══ اكتشافُ النقطة من حركة الشبكة ══ (D306)
    # صفحةُ «تداول» لا تذكر اسمَ خدمتها في شيفرتها (قِيس: صفرُ أسماء).
    # فيُفتح المتصفّحُ ويُسجَّل **ما تطلبه الصفحةُ فعلاً**.
    print("\n═ نداءاتُ الصفحة كما وقعت (متصفّح) ═")
    for label, u in (("تداول", sd.PAGE), ("أرقام", sd.ARGAAM_MARKET)):
        try:
            from app.services.browser_fetch import BrowserUnavailable, sniff
            res = await sniff(u, settle_ms=9000, max_bodies=12,
                              hosts=("saudiexchange.sa", "argaam.com",
                                     "tadawul.com.sa"))
        except BrowserUnavailable as e:
            print(f"  {label}: المتصفّحُ غيرُ متاح — {e}")
            continue
        except Exception as e:                                    # noqa: BLE001
            print(f"  {label}: تعذّر — {type(e).__name__}: {e}")
            continue
        calls = res.get("calls") or []
        xhr = [c for c in calls if c.get("type") in ("xhr", "fetch")]
        print(f"  {label}: {len(calls)} ردّاً · منها {len(xhr)} نداءَ بيانات")
        for c in xhr[:14]:
            print(f"      {c['method']} {c['status']} {c['url'][:110]}")
        for i, (cu, body) in enumerate((res.get("bodies") or {}).items(), 1):
            looks = bool(_re2.search(r"\b\d{4}\b", body)
                         and _re2.search(r"\d+\.\d{1,2}", body))
            print(f"      جسمٌ {i}: {len(body)} حرفاً"
                  + ("  ← فيه أرقامٌ تشبه بياناتَ صفقات" if looks else "")
                  + f"  ({cu[:80]})")
            keep(f"xhr_{label}_{i}.txt", 0, body, cu)
        if res.get("html"):
            keep(f"rendered_{label}.html", 0, res["html"], u)

    # ══ الترتيبُ جزءٌ من القياس ══ (D309)
    # كانت كتلةُ «شكلُ الصفحات» تعمل **قبل** التسجيل، فلم تُفحَص الصفحةُ
    # المرسومةُ ولا أجسامُ النداءات — وقد سألني المالكُ عنها فلم يكن عندي
    # جوابٌ لأن قياسي سبق البيانات. فصارت بعدها.
    # ══ شكلُ المحتوى يُطبع لا يُخمَّن ══ (D304)
    # قِيس أن الصفحةَ تعود 200 بصفرِ جداولٍ **حتى بالمتصفّح** — وعدُّ
    # `<table>` وحدَه لا يكفي: المواقعُ الحديثةُ ترسم الصفوفَ حاويات.
    # فيُطبع ملخّصٌ يكشف الشكلَ من طرفيّة المالك بلا نقلِ ملفّ:
    #   · هل في الصفحة عنوانُ الميزة؟ وهل فيها علاماتُ اشتراكٍ مدفوع؟
    #   · وكم كتلةً تشبه صفَّ صفقة (رمزٌ + كسرٌ + تاريخ)؟ وما نصُّ أوائلها؟
    #   · وما نداءاتُ البيانات المذكورةُ في سكربتها؟
    # وكلُّ صفحةٍ محفوظةٍ تُفحَص — ومنها **المرسومة**: قِيس أن صفحةَ
    # «تداول» المرسومةَ 846 ألفَ حرفٍ (الخامُ 556) ولم أفحصها (D307).
    for name in [n for n in files if n.endswith(".html")]:
        raw = files.get(name)
        if not raw:
            continue
        html = raw.decode("utf-8", "replace")
        print(f"\n═ شكلُ {name} ═")
        for label, needle in (("عنوانُ الميزة", "الصفقات الخاصة"),
                              ("اشتراكٌ مدفوع", "اشترك"),
                              ("للمشتركين", "للمشتركين"),
                              ("تسجيلُ دخول", "تسجيل الدخول")):
            n = html.count(needle)
            if n:
                print(f"  · {label}: {n} مرّة")
        no_script = _re2.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html,
                             flags=_re2.S | _re2.I)
        from app.services.ownership import _text, blocks
        # القياسُ على **نصّ** الكتلة لا على طول شيفرتها: أوّلُ صياغةٍ
        # رشّحت بطولِ HTML فأسقطت صفوفاً حقيقيةً صنعتُها للتجربة.
        rowish, seen_t = [], set()
        for b in sorted(blocks(no_script), key=len):
            txt = _text(b)
            if not (20 <= len(txt) <= 400):
                continue
            if not (_re2.search(r"\b\d{4}\b", txt)
                    and _re2.search(r"\d+\.\d{1,2}", txt)
                    and _re2.search(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}", txt)):
                continue
            if any(txt in s for s in seen_t):      # كتلةٌ أمٌّ تكرّر ابنَها
                continue
            seen_t.add(txt)
            rowish.append(txt[:200])
        print(f"  · كتلٌ تشبه صفَّ صفقة: {len(rowish)}")
        for x in rowish[:4]:
            print(f"      {x}")
        # نداءاتُ البيانات في السكربت — مسارٌ نسبيٌّ أو مطلقٌ داخل الموقع
        calls = sorted({m for m in _re2.findall(
            r'["\'](/[A-Za-z0-9_\-/]{6,}(?:\?[^"\']{0,60})?)["\']', html)
            if _re2.search(r"deal|shareholder|Data|List|Grid|Get|api", m, _re2.I)})
        if calls:
            print(f"  · نداءاتٌ محتملةٌ في السكربت: {len(calls)}")
            for c in calls[:8]:
                print(f"      {c}")

        # ══ أسماءُ خدمات بوّابة «تداول» ══ (D305)
        # البوّابةُ تُملأ بنداءٍ اسمُه في الصفحة: `p0/…=NJ{اسم}=/`. وهي
        # الطريقةُ التي فتحت الصكوكَ ومراقبةَ السوق (‏D249 · D251). فتُطبع
        # **كلُّ** الأسماء الموجودة — لا ما يطابق تخميني وحدَه، لأنّ
        # تخميني (`getSpecial…`) هو الذي أخفى الاسمَ الحقيقيّ.
        svc = sorted(set(_re2.findall(r"=NJ([A-Za-z][A-Za-z0-9_]{3,60})=/", html)))
        if svc:
            print(f"  · أسماءُ خدماتٍ في الصفحة: {len(svc)}")
            for s in svc:
                print(f"      {s}")
        base = _re2.search(r"<base[^>]+href=[\"']([^\"']+)", html, _re2.I)
        if base:
            print(f"  · أساسُ الصفحة: {base.group(1)}")


    # ══ وعيّنةٌ من كلّ جسمٍ من مضيف المصدر ══
    # جسمٌ طولُه 29 ألفَ حرفٍ لا يُوصَف بأنه «يشبه بياناتٍ»: تُطبع أوّلُ
    # سبع مئة حرفٍ منه فيُقرأ شكلُه (JSON؟ HTML؟ أعمدةٌ ما؟).
    print("\n═ عيّناتُ أجسام النداءات ═")
    for name in sorted(n for n in files if n.startswith("xhr_")):
        raw = files[name]
        if len(raw) < 200:
            continue
        txt = raw.decode("utf-8", "replace")
        u = next((m["url"] for m in man if m["file"] == name), "")
        if not any(h in u for h in ("saudiexchange.sa", "argaam.com")):
            continue
        print(f"\n  ── {name} · {len(raw)} بايت · {u[:90]}")
        print("     " + txt[:700].replace("\n", " ")[:700])

    out = pathlib.Path("/app/_deals_dump.tar.gz")
    if not out.parent.exists():
        out = pathlib.Path("_deals_dump.tar.gz")
    with tarfile.open(out, "w:gz") as tar:
        for name, raw in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))
        blob = json.dumps(man, ensure_ascii=False, indent=2).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(blob)
        tar.addfile(info, io.BytesIO(blob))
    print(f"\n✔ {out} — {out.stat().st_size} بايت · {len(files)} صفحة")
    print("  على الخادم: backend/_deals_dump.tar.gz — أرسله كما هو.")
    return 0


async def main() -> int:
    if "--dump" in sys.argv[1:]:
        return await dump()
    apply = "--apply" in sys.argv[1:]
    days = _days()
    from app.services import special_deals as sd
    from app.services.tadawul_http import smart_flow

    print(f"═ مدى القياس: {days} يوماً ═\n")

    # ── ١ · طريقةُ النشر، مرحلةً مرحلة ─────────────────────────────────
    # تُعاد خطواتُ الخطّة هنا بالطبع، لأن المقصودَ **موضعُ الانقطاع** لا
    # النتيجةُ وحدَها: فهرسٌ لم يُكتشف؟ أم مقالاتٌ لم تُطابق عنواناً؟ أم
    # جدولٌ لم يُقرأ؟ وكلُّ سطرٍ هنا قياسٌ لا ترجيح.
    def plan():
        status, home = yield {"url": sd.ARGAAM_HOME}
        print(f"قائمةُ «أرقام»: HTTP {status} · {len(home or '')} حرفاً")
        index = sd._index_from_nav(home) if status == 200 else None
        print(f"فهرسُ «الصفقات الخاصة»: "
              + (f"من القائمة → {index}" if index else "لم يُوجد في القائمة — يُجرَّب الوسم"))
        index = index or sd.TAG_INDEX.format(page=1)
        status, body = yield {"url": index, "referer": sd.ARGAAM_HOME}
        print(f"صفحةُ الفهرس: HTTP {status} · {len(body or '')} حرفاً")
        direct = sd.rows_from_html(body or "")
        if direct:
            print(f"  · جدولٌ مباشرٌ في الفهرس: {len(direct)} صفقة")
        links = sd._index_links(body or "")
        print(f"مقالاتُ الصفقات في الصفحة: {len(links)}")
        for href, title in links[:5]:
            print(f"  · {title[:70]}")
        if not links:
            return None
        href, title = links[0]
        status, art = yield {"url": href, "referer": index}
        at = sd._article_date(art or "")
        print(f"\nأوّلُ مقالة: HTTP {status} · {len(art or '')} حرفاً · "
              f"تاريخُها {at or 'لم يُفصح عنه'}")
        rows = sd.rows_from_html(art or "", at=at.isoformat() if at else None)
        print(f"صفقاتٌ قُرئت منها: {len(rows)}")
        for d in rows[:5]:
            print("  " + json.dumps(d, ensure_ascii=False))
        if not rows:
            import re
            trs = len(re.findall(r"<tr\b", art or "", re.I))
            print(f"  (جداولُ المقالة: {trs} صفّاً — إن كان صفراً فالجدولُ "
                  "يُبنى بجافاسكربت ويلزم المتصفّح)")
        return True

    try:
        await smart_flow(plan, warm=sd.ARGAAM_HOME)
    except Exception as e:                                        # noqa: BLE001
        print(f"خطّةُ القراءة تعذّرت: {type(e).__name__}: {e}")

    # ── ٢ · والحصيلةُ كما يراها التطبيق ────────────────────────────────
    print("\n═ الحصيلة كما يقرؤها التطبيق ═")
    deals, why = await sd.argaam_deals(days)
    print(f"صفقاتٌ من «أرقام»: {len(deals)}")
    for d in deals[:8]:
        print("  " + json.dumps(d, ensure_ascii=False))
    if why:
        print(f"تعذّر: {why}")

    # ── ٣ · وطبقةُ «تداول» بعدها — مكتوبةٌ تُجرَّب ولا تُنتظَر ─────────
    print("\n═ طبقةُ «تداول» ═")
    rows, why_t = await sd.fetch_rows()
    print(f"صفوفٌ خام: {len(rows)}" if not why_t else f"تعذّر: {why_t}")
    if rows:
        print("أسماءُ الحقول كما وردت:")
        print("  " + ", ".join(sorted(rows[0].keys())))
        got = sd.normalize(rows)
        print(f"صفقاتٌ فُهمت: {len(got)} من {len(rows)}")
        for d in got[:5]:
            print("  " + json.dumps(d, ensure_ascii=False))

    if apply:
        print("\n═ الحفظ ═")
        print(json.dumps(await sd.refresh(days), ensure_ascii=False))
    else:
        print("\n(لم يُكتب شيء. أضف --apply ليُحفَظ ويظهر في التبويب فوراً.)")
    return 0


raise SystemExit(asyncio.run(main()))
