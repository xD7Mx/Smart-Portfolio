#!/usr/bin/env python3
"""نصُّ الإفصاح من «تداول» أوّلاً (D467) — قياسٌ قبل البناء. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/tadawul_announcement_text.py
"""
import asyncio, collections, json, re, sys
sys.path.insert(0, "/app")
_SVC = re.compile(r"p0/[A-Za-z0-9_=]*=NJ([A-Za-z][A-Za-z0-9_]{3,60})=/")
O = "https://www.saudiexchange.sa"
PAGE = O + "/wps/portal/saudiexchange/newsandreports/issuer-news/issuer-announcements?locale=ar"


def blocks(h):
    """أكبرُ الكتل النصّية في الصفحة (بلا سكربت/نمط) — لإيجاد المتن."""
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h or "", flags=re.S)
    out = []
    for m in re.finditer(r"<(div|td|p|section|article)[^>]*>(.*?)</\1>", h, re.S):
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
        if len(t) > 80 and not re.search(r"تسجيل الدخول|السوق مغلق|Log in", t):
            out.append((len(t), m.group(0)[:160], t))
    return sorted(out, reverse=True)[:4]


async def main():
    try:
        from app.api.v1.endpoints.market import get_company_events, get_announcement_text
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); return 0
    tot = collections.Counter()
    for sym in ("4001", "2080", "2222"):
        r = await get_company_events(sym, "")
        d = (r if isinstance(r, dict) else json.loads(r.body)).get("data") or []
        d = d if isinstance(d, list) else (d.get("events") or [])
        for e in [x for x in d if isinstance(x, dict) and x.get("url")][:10]:
            t = (e.get("title") or e.get("headline") or "")
            q = await get_announcement_text(symbol=sym, title=t, date=str(e.get("date") or ""), u=e["url"], name=e.get("company_name") or "")
            v = (q if isinstance(q, dict) else json.loads(q.body)).get("data") or {}
            src = v.get("source") or "لا نصّ"
            tot[src] += 1
            print(f"{sym} · {str(e.get('date'))[:10]} · {src:6} · {len(v.get('text') or ''):5} · {t[:60]} → {(v.get('text') or '')[:70]!r}")
    print("المجموع:", dict(tot))
    return 0


sys.exit(asyncio.run(main()))
