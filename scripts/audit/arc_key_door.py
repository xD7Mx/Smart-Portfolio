#!/usr/bin/env python3
"""أين تضع صفحةُ بحوث الراجحي مفتاحَ واجهتها العامّ؟ (‏D733) — قارئٌ فقط. يبحث في الصفحة وكلِّ سكربتاتها (ومنها ما يذكره
‏_buildManifest) عن النداء ‎graph/edge‎ وعن صيغة GUID قريبةٍ من «key»، ويطبع السياقَ والمفتاحُ مقنَّع."""
import asyncio, os, re, sys, time
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
G = r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}"


def mask(s):
    return re.sub(G, lambda m: m.group(0)[:4] + "…", s)


async def main():
    from app.services import research_reports as R
    from app.services.tadawul_http import smart_fetch
    st, page = await smart_fetch(R.ARC_PAGE, warm=R.ARC + "/ar", timeout=40)
    srcs = re.findall(r"<script[^>]+src=[\"']([^\"']+\.js)[\"']", page or "")
    bm = next((s for s in srcs if "_buildManifest" in s), None)
    if bm:
        _, man = await smart_fetch(R.ARC + bm, timeout=30)
        more = ["/_next/" + x for x in re.findall(r"\"(static/chunks/[^\"]+\.js)\"", man or "")]
        srcs += [m for m in more if m not in srcs]
    print("الصفحة", st, len(page or ""), "· سكربتات:", len(srcs))
    texts = [("page", page or "")]
    for s in srcs[:80]:
        st2, js = await smart_fetch(R.ARC + s if s.startswith("/") else s, referer=R.ARC_PAGE, timeout=30)
        texts.append((s, js or ""))
    for name, t in texts:
        hits = []
        for m in re.finditer(r"(?i)apikey|sc_apikey|graph/edge|SearchAndReports", t):
            hits.append(mask(t[max(0, m.start() - 90): m.end() + 120]).replace("\n", " "))
        if hits:
            print(f"\n══ {name[:90]} ({len(t)}): {len(hits)} موضعاً")
            for h in hits[:6]:
                print("   ", h)
    print("\narc_discover على الكلّ:", {k: v[:6] + "…" for k, v in R.arc_discover([t for _, t in texts]).items()})


asyncio.run(main())
