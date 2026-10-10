#!/usr/bin/env python3
"""كاشفُ تقارير الجهات المرخّصة لتبويب «التوقعات» (المالك: «أريد تقاريرَ للجهات المعتمدة من بنوكٍ
وغيرها لسوق تاسي — حالياً خالية») — قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/research_sources_door.py

لا تُحفظ مساراتٌ مخمَّنة (FETCH_METHOD §٢): تُفتح الصفحةُ الرئيسةُ لكلّ جهةٍ في جلسةٍ منتحِلةٍ
واحدة، وتُكتشف منها روابطُ «الأبحاث/التقارير» بمسارها ونصّها، ثمّ يُقاس كلُّ مرشّح: الحالة · الطول ·
روابطُ PDF · التواريخ · عناوينُ الروابط الطويلة · علاماتُ الرسم بسكربت. فيُبنى القارئُ على الشكل لا الظنّ.
"""
import asyncio, re, sys
from urllib.parse import urljoin, urlparse
sys.path.insert(0, "/app")

HOMES = {
    "الراجحي المالية": "https://www.alrajhi-capital.sa/ar",
    "الجزيرة كابيتال": "https://www.aljaziracapital.com.sa/ar",
    "الرياض المالية": "https://www.riyadcapital.com/ar",
    "الأهلي كابيتال": "https://www.snbcapital.com/ar",
    "البلاد المالية": "https://www.albilad-capital.com/ar",
    "الإنماء للاستثمار": "https://www.alinmainvestment.com/ar",
    "السعودي الفرنسي كابيتال": "https://www.sfc.sa/ar",
    "جدوى للاستثمار": "https://www.jadwa.com/ar",
    "يقين المالية": "https://www.yaqeen.sa/ar",
    "دراية المالية": "https://www.derayah.com/ar",
    "ساب إنفست": "https://www.sabinvest.com/ar",
    "الاستثمار كابيتال": "https://www.icap.com.sa/ar",
    "الخبير المالية": "https://www.alkhabeer.com/ar",
    "العربي المالية": "https://www.anbcapital.com.sa/ar",
    "تداول — التقارير والنشرات": "https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports/reports-publications?locale=ar",
}
_A = re.compile(r'<a\b[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', re.I | re.S)
_HINT = re.compile(r"research|report|publication|insight|analys|outlook|أبحاث|الأبحاث|البحوث|تقارير|التقارير|دراسات|نشرات|تحليل", re.I)
_DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b|\b\d{1,2}/\d{1,2}/20\d\d\b|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d\d\b"
                   r"|(?:يناير|فبراير|مارس|أبريل|إبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)\s+20\d\d", re.I)


def _txt(h):
    return " ".join(re.sub(r"<[^>]+>", " ", h or "").split())


def links(html, base):
    out = []
    for href, label in _A.findall(html or ""):
        u = urljoin(base, href.replace("&amp;", "&").strip())
        if u.startswith("http"):
            out.append((u, _txt(label)))
    return out


def measure(name, url, st, body):
    body = body or ""
    ls = links(body, url)
    pdfs = [(u, t) for u, t in ls if re.search(r"\.pdf($|\?)", u, re.I)]
    long_t = [(u, t) for u, t in ls if len(t) >= 24]
    js = [k for k in ("__NEXT_DATA__", "ng-version", "data-reactroot", "id=\"root\"", "id=\"app\"", "nuxt", "angular") if k in body]
    api = sorted(set(re.findall(r"[\"'](/(?:api|umbraco/api|_api|wp-json)/[^\"' ]{3,80})[\"']", body)))[:6]
    print(f"   · {url[:110]} → {st} · {len(body)} حرفاً · روابط {len(ls)} · PDF {len(pdfs)} · تواريخ {len(_DATE.findall(body))}"
          f" · سكربت {js} · نقاط {api}")
    for u, t in pdfs[:5]:
        print(f"       PDF: {t[:70]!r} ← {u[:130]}")
    for u, t in long_t[:6]:
        if (u, t) not in pdfs:
            print(f"       ع: {t[:80]!r} ← {u[:110]}")
    for d in _DATE.findall(body)[:4]:
        print(f"       ت: {d}")
    return ls


def plan(name, home):
    def gen():
        st, body = yield {"url": home, "timeout": 25}
        host = urlparse(home).netloc.split(":")[0].replace("www.", "")
        ls = measure(name, home, st, body)
        cands, seen = [], set()
        for u, t in ls:
            if host not in urlparse(u).netloc or u in seen:
                continue
            if _HINT.search(u) or _HINT.search(t):
                seen.add(u)
                cands.append((u, t))
        cands.sort(key=lambda x: (0 if re.search(r"research|أبحاث|بحوث", x[0] + x[1], re.I) else 1, len(x[0])))
        print(f"   مرشّحو «الأبحاث» في {name}: {len(cands)} — {[t[:24] for _, t in cands[:8]]}")
        sub = []
        for u, t in cands[:6]:
            st2, b2 = yield {"url": u, "referer": home, "timeout": 25}
            l2 = measure(name, u, st2, b2)
            sub += [(x, y) for x, y in l2 if host in urlparse(x).netloc and x not in seen
                    and re.search(r"equit|compan|sector|macro|daily|weekly|monthly|initiat|update|شرك|قطاع|يومي|أسبوعي|شهري|اقتصاد", x + y, re.I)]
        for u, t in list(dict.fromkeys(sub))[:4]:
            seen.add(u)
            st3, b3 = yield {"url": u, "referer": home, "timeout": 25}
            measure(name, u, st3, b3)
        return None
    return gen


async def one(sem, name, home):
    from app.services.tadawul_http import smart_flow
    async with sem:
        print(f"\n═ {name} — {home}")
        try:
            await asyncio.wait_for(smart_flow(plan(name, home), warm=None, timeout=25), 300)
        except Exception as e:                                     # noqa: BLE001
            print(f"   ✘ {type(e).__name__}: {str(e)[:140]}")


async def main():
    sem = asyncio.Semaphore(1)                                     # تسلسلٌ يُبقي المخرَجَ مقروءاً لكلّ جهة
    for name, home in HOMES.items():
        await one(sem, name, home)


asyncio.run(main())
