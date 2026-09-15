#!/usr/bin/env python3
"""مسبارُ الصفقات الخاصة — يقيس على الخادم ما حُجب عن حاويتي (D273 · D296).

    docker exec sp_backend python /app/scripts/audit/deals_probe.py
    docker exec sp_backend python /app/scripts/audit/deals_probe.py --days=7
    docker exec sp_backend python /app/scripts/audit/deals_probe.py --apply

يمشي **بطريقة نشر المصدر نفسِها** مرحلةً مرحلةً فيُرى أين ينقطع الخيط:
قائمةُ «أرقام» ← فهرسُ الوسم ← مقالاتُه المؤرَّخة ← جدولُ كلٍّ منها. ثمّ
طبقةُ «تداول» بعدها. ولا يكتب شيئاً إلا بـ`--apply`.
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


async def main() -> int:
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
