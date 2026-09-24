#!/usr/bin/env python3
"""نصُّ الإفصاح من «تداول» أوّلاً (D467) — قياسٌ قبل البناء. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/tadawul_announcement_text.py
"""
import asyncio, collections, re, sys
from urllib.parse import urlparse
sys.path.insert(0, "/app")


async def main():
    try:
        from app.services.tadawul_announcements import fetch_tadawul_announcements
        from app.services.tadawul_http import fetch, smart_fetch
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); return 0
    items = await fetch_tadawul_announcements(force=True)
    print(f"إفصاحاتُ تداول: {len(items)} · بروابط: {sum(1 for x in items if x.get('url'))}")
    print("المضيفات:", dict(collections.Counter(urlparse(x.get('url') or '').hostname or '—' for x in items)))
    dates = sorted(x.get("date") or "" for x in items)
    print(f"المدى: {dates[:1]} … {dates[-1:]}")
    syms = collections.Counter(x.get("symbol") for x in items)
    print("أكثرُ الرموز:", syms.most_common(8))
    for x in items[:3]:
        print("  عيّنة:", {k: (str(v)[:120]) for k, v in x.items()})
    for s in ("4001", "2080"):
        mine = [x for x in items if str(x.get("symbol")) == s]
        print(f"{s}: {len(mine)} → " + " | ".join(f"{m.get('date')} {m.get('title','')[:60]}" for m in mine[:5]))
    tried = 0
    for x in items:
        u = x.get("url")
        if not u or tried >= 3:
            continue
        tried += 1
        try:
            st, h = await fetch(u) if "saudiexchange" in u else await smart_fetch(u, timeout=25)
        except Exception as e:
            print(f"\n— {u[:150]}\n  خطأ {type(e).__name__}: {str(e)[:100]}"); continue
        h = h or ""
        vis = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)))
        t = (x.get("title") or "")[:20]
        i = vis.find(t) if t else -1
        print(f"\n— {u[:150]}\n  HTTP {st} · {len(h)} حرف · العنوانُ في الصفحة: {i >= 0}")
        print(f"  حولَ العنوان: {vis[max(0, i):i + 700] if i >= 0 else vis[:400]}")
        for m in re.finditer(r'(?:href|src)="([^"]*(?:\.pdf|attachment|download|announcementDetails|annoucementDetails)[^"]*)"', h, re.I):
            print(f"  مرفق/تفاصيل: {m.group(1)[:160]}")
            break
    return 0

sys.exit(asyncio.run(main()))
