#!/usr/bin/env python3
"""نصُّ الإفصاح من «تداول» أوّلاً (D467) — قياسٌ قبل البناء. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/tadawul_announcement_text.py
"""
import asyncio, json, re, sys
sys.path.insert(0, "/app")
_SVC = re.compile(r"p0/[A-Za-z0-9_=]*=NJ([A-Za-z][A-Za-z0-9_]{3,60})=/")


def vis(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", h or "", flags=re.S)))


async def main():
    try:
        from app.services.tadawul_ownership import company_page
        from app.services.tadawul_http import fetch
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); return 0
    O = "https://www.saudiexchange.sa"
    from app.services import tadawul_market as TM
    if not TM.row_for("4001"):
        await TM.refresh()
    print("رابطُ صفحة 4001:", (TM.row_for("4001") or {}).get("company_url"))
    body = await company_page("4001") or ""
    print(f"صفحةُ 4001: {len(body)} حرف")
    base = (re.search(r"<base[^>]+href=[\"']([^\"']+)", body) or [None, ""])[1].rstrip("/")
    eps = {}
    for m in _SVC.finditer(body):
        eps.setdefault(m.group(1), m.group(0))
    print("الخدمات:", sorted(eps))
    links = sorted(set(re.findall(r'href="([^"]*(?:news-detail|announcement|NewsDetail|newsId)[^"]*)"', body, re.I)))
    print(f"روابطُ إعلاناتٍ في الصفحة: {len(links)}", links[:5])
    for name in [n for n in eps if re.search(r"news|announc|disclos", n, re.I)]:
        for params in ({"symbol": "4001", "language": "ar"}, {"companySymbol": "4001", "requestLocale": "ar"}, {"requestLocale": "ar"}):
            try:
                st, raw = await fetch(f"{base}/{eps[name]}", params=params, referer=base)
            except Exception as e:
                print(f"  {name} {params}: {type(e).__name__}"); continue
            print(f"  {name} {params}: HTTP {st} · {len(raw or '')} · {(raw or '')[:400]!r}")
    # صفحةُ تفاصيل إعلانٍ واحد (رابطُ خدمة الأخبار العامّة المقيسة)
    target = links[0] if links else "/wps/portal/saudiexchange/newsandreports/issuer-news/news-detail-wcm/?newsId=9593&locale=ar"
    u = target if target.startswith("http") else O + target
    st, h = await fetch(u)
    v = vis(h)
    print(f"\nتفاصيل: {u[:140]} · HTTP {st} · {len(h or '')} حرف")
    for kw in ("تعلن", "يعلن", "announces", "Purity", "بيوريتي"):
        i = v.find(kw)
        if i >= 0:
            print(f"  «{kw}»: …{v[max(0,i-150):i+600]}…"); break
    else:
        print(f"  لم يُعثر على المتن · أوّلُ الظاهر: {v[:300]}")
    eps2 = sorted(set(m.group(1) for m in _SVC.finditer(h or "")))
    print("  خدماتُ صفحة التفاصيل:", eps2)
    return 0

sys.exit(asyncio.run(main()))
