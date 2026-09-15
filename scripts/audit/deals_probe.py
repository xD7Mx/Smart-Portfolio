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
