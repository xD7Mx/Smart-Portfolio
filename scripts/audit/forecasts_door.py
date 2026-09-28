"""كاشفُ مصادر «التوقعات» (بأمر المالك): توقعاتُ البنوك وبيوت الخبرة وتقاريرُ السوق.

قراءةٌ فقط. يكتشف الروابطَ من صفحات «أرقام» نفسِها (لا تخمينَ مسارات) ثمّ يعرض
لكلّ مرشَّحٍ حالتَه وحجمَه وأوّلَ صفوف جداوله وعناوينه — ليُبنى المحلّلُ على
الشكل الحقيقيّ لا على الظنّ (docs/FETCH_METHOD.md).

    docker exec sp_backend python /app/scripts/audit/forecasts_door.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")

import httpx  # noqa: E402

from app.services.argaam_calendar import BASE, UA, _rows_of  # noqa: E402

SEEDS = ["/ar", "/ar/articles", "/ar/company/companies-prices/3"]
PAT = re.compile(r'href="(/ar/[^"#?]*(?:recommend|estimat|forecast|research|report|expect|consensus|target)[^"#?]*)"', re.I)
EXTRA = [
    "/ar/company/recommendations/marketid/3",
    "/ar/research-reports",
    "/ar/company/research-reports/marketid/3",
    "/ar/analyst-recommendations",
    "/ar/estimates",
    "/ar/company/estimates/marketid/3",
]


async def main():
    async with httpx.AsyncClient(timeout=25, follow_redirects=True,
                                 headers={"User-Agent": UA, "Accept-Language": "ar,en;q=0.8"}) as c:
        found: list[str] = []
        for s in SEEDS:
            try:
                r = await c.get(BASE + s)
                hs = sorted(set(PAT.findall(r.text)))
                print(f"═ بذرة {s}: {r.status_code} · {len(r.text)} · روابط مرشّحة {len(hs)}")
                for h in hs[:25]:
                    print("   ", h)
                found += hs
            except Exception as e:                                # noqa: BLE001
                print(f"═ بذرة {s}: خطأ {e}")
        cands = list(dict.fromkeys(EXTRA + found))[:30]
        for u in cands:
            try:
                r = await c.get(BASE + u)
            except Exception as e:                                # noqa: BLE001
                print(f"✖ {u}: {e}")
                continue
            rows = _rows_of(r.text) if r.status_code == 200 else []
            heads = re.findall(r"<h[1-4][^>]*>\s*([^<]{8,120})</h", r.text)[:4]
            links = re.findall(r'<a[^>]+href="(/ar/article[^"]+)"[^>]*>\s*([^<]{12,140})</a>', r.text)[:4]
            print(f"\n── {u}: {r.status_code} · {len(r.text)} بايت · صفوف {len(rows)}")
            for h in heads:
                print("   ع:", " ".join(h.split()))
            for cells in rows[:4]:
                print("   ص:", " | ".join(" ".join(x.split())[:40] for x in cells[:7]))
            for href, t in links:
                print("   م:", " ".join(t.split())[:100], "→", href[:80])


asyncio.run(main())


# ══ الطورُ الثاني: الصفحتان تُحمَّلان بسكربت (صفرُ صفوف في HTML) — فتُقرأ
# نداءاتُهما من حركة الشبكة (FETCH_METHOD §٤ج). ══
async def sniff_pages():
    from app.services.browser_fetch import sniff
    for u in ("/ar/monitors/analyst-estimates", "/ar/monitors/research-articles"):
        try:
            res = await sniff(BASE + u, settle_ms=10000, want=r"(?i)json|estimat|research|article|report|api",
                              max_bodies=4)
        except Exception as e:                                    # noqa: BLE001
            print(f"✖ sniff {u}: {e}")
            continue
        calls = [c for c in (res.get("calls") or []) if c.get("type") in ("xhr", "fetch")]
        print(f"\n═ sniff {u}: نداءات {len(calls)}")
        for c in calls[:25]:
            print(f"   {c.get('status')} {c.get('type')} {str(c.get('url'))[:150]} · {c.get('size')}")
        for k, v in list((res.get("bodies") or {}).items())[:4]:
            print(f"   ⟵ {str(k)[:120]}\n      {str(v)[:700]}")


asyncio.run(sniff_pages())
