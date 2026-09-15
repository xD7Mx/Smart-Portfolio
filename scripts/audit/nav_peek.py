"""أين تُذكر «الصفقات الخاصة» في موقع «تداول»؟ — قياسٌ لا تخمين."""
import asyncio
import re
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")   # ويعمل من جذر المستودع أيضاً


async def main():
    from app.services.ownership import _text
    from app.services.tadawul_http import fetch

    HOME = "https://www.saudiexchange.sa/wps/portal/saudiexchange/home"
    try:
        status, html = await fetch(HOME)
    except Exception as e:                                        # noqa: BLE001
        print(f"تعذّر الجلب: {type(e).__name__}: {e}")
        return
    print(f"الرئيسة: HTTP {status} · {len(html or '')} حرفاً")
    html = html or ""

    # ١ · كلُّ وسمِ رابطٍ — بأيّ نوعِ اقتباس
    anchors = re.findall(r"""<a\b[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>""",
                         html, re.S | re.I)
    print(f"روابطُ الصفحة: {len(anchors)}")

    # ٢ · ما نصُّه يذكر صفقةً — أو مسارُه يذكر deal
    hits = [(h, _text(t)) for h, t in anchors
            if "صفق" in _text(t) or re.search(r"deal", h, re.I)]
    print(f"روابطٌ تذكر الصفقات: {len(hits)}")
    for h, t in hits[:25]:
        print(f"   «{t[:45]}» → {h[:130]}")

    # ٣ · وإن لم يكن في الروابط: أين تُذكر العبارةُ نصّاً؟
    for m in list(re.finditer("الصفقات الخاصة", html))[:5]:
        a, b = max(0, m.start() - 220), m.end() + 220
        print("\n── سياقٌ نصّيّ ──")
        print(re.sub(r"\s+", " ", html[a:b]))

    # ٤ · وكلُّ مسارٍ في الصفحة يذكر deal (حتى في السكربت)
    paths = sorted({p for p in re.findall(r"""["'](/[^"']{6,160})["']""", html)
                    if re.search(r"deal", p, re.I)})
    print(f"\nمساراتٌ تذكر deal: {len(paths)}")
    for p in paths[:20]:
        print("   " + p)

asyncio.run(main())
