#!/usr/bin/env python3
"""شكلُ صفحات الأبحاث المقروءة (بعد research_sources_door) — قارئٌ فقط: بنيةُ البطاقة حول كلّ تقرير قبل كتابة القارئ.

    docker exec sp_backend python /app/scripts/audit/research_shape_door.py

«اقرأ الشكلَ قبل أن تكتب قارئاً» (FETCH_METHOD §٨): لكلّ صفحةٍ أصنافُ ملفّاتها، وسياقُ أوّل بطاقاتها بوسومها، وتواريخُها.
"""
import asyncio, collections, html, re, sys
sys.path.insert(0, "/app")

PAGES = [
    ("الجزيرة كابيتال", "https://www.aljaziracapital.com.sa/ar/insights/research-reports/", "https://www.aljaziracapital.com.sa/ar"),
    ("الراجحي المالية", "https://www.alrajhi-capital.sa/research", "https://www.alrajhi-capital.sa/ar"),
    ("الرياض المالية", "https://www.riyadcapital.com/research-reports", "https://www.riyadcapital.com/ar"),
    ("جدوى", "https://www.jadwa.com/ar/economic-reports", "https://www.jadwa.com/ar"),
    ("الأهلي كابيتال", "https://research.snbcapital.com", "https://www.snbcapital.com/ar"),
]


def squash(s, n):
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r'(class|style|data-[a-z-]+)="[^"]{40,}"', r'\1="…"', s)
    return s[:n]


def vis(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S | re.I)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


async def main():
    from app.services.tadawul_http import smart_fetch
    for name, url, home in PAGES:
        try:
            st, body = await smart_fetch(url, warm=home, referer=home, timeout=40)
        except Exception as e:                                     # noqa: BLE001
            print(f"\n═ {name}: ✘ {type(e).__name__}: {e}"); continue
        body = html.unescape(body or "")
        print(f"\n═ {name} — {url} → {st} · {len(body)}")
        files = re.findall(r'href=["\']([^"\']+\.pdf)', body, re.I)
        kinds = collections.Counter(re.sub(r"[\d_\-]+(ar|en)?\.pdf$", "", f.rsplit("/", 1)[-1].lower()) for f in files)
        print(f"   ملفّات {len(files)} · أصنافُها {kinds.most_common(25)}")
        recent = sorted({f for f in files if re.search(r"2026", f)})[:12]
        for f in recent:
            print(f"   ٢٠٢٦: {f[-110:]}")
        for kw in ("ResearchListing", "research", "تقرير", "documents/"):
            idx = [m.start() for m in re.finditer(re.escape(kw), body)][:3]
            for i in idx:
                print(f"   [{kw}] …{squash(body[max(0, i - 500):i + 300], 800)}")
            if idx:
                break
        for m in list(re.finditer(r"\.pdf", body, re.I))[:2]:
            print(f"   [بطاقة] …{squash(body[max(0, m.start() - 900):m.end() + 200], 1100)}")
        v = vis(body)
        print(f"   نصٌّ مرئيّ ({len(v)}): {v[:900]}")
        apis = sorted(set(re.findall(r"[\"'](/(?:api|o|c|delegate|umbraco|wp-json)/[^\"' ]{3,90})[\"']", body)))[:12]
        print(f"   نداءات: {apis}")


asyncio.run(main())
