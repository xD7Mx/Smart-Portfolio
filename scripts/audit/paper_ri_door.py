#!/usr/bin/env python3
"""كاشفُ ورقة التقرير الحيّة (‏D753 · D756) — قارئٌ فقط: يقرأ أحدثَ تقريرٍ محفوظ لكلّ محفظةٍ ويرسم ورقتَه كاملةً كما تراها الشاشةُ ويصل
ملفُّه، ثمّ يقول: عددُ صفحات الملفّ المطبوع (كلُّ صفحةٍ ورقةٌ واحدة لا تفيض)، ومؤشّرُ دحم في رسمها بمناطقه الثلاث ومتوسّطاته واتجاهه وقناته
وستوكاستيك RSI، والمستوياتُ بأسمائها، والتوصياتُ في الورقة نفسِها. لا يكتب شيئاً."""
import asyncio, os, re, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
from app.services import research_desk as RD   # noqa: E402
from app.services import research_paper as RP   # noqa: E402


async def main():
    for pid in (1, 2):
        r = RD.load_report(pid, None)
        if not r:
            print(f"محفظة {pid}: لا تقرير")
            continue
        html = RP.render(r, "all")
        d = RP.d7m_of(r["market"]) if r.get("market") else None
        npg, nd = html.count('<section class="page"'), len((r.get("market") or {}).get("daily") or [])
        print(f"محفظة {pid}: {r['date']} · صفحات الورقة {npg} · شموع يومية {nd}")
        if d:
            print("  مناطقُ دحم:", {k: [round(v, 2) for v in z] for k, z in d["zones"].items()},
                  "· اتجاه", len(d["trend"]["lines"]), "خطّاً · قناة", "نعم" if d["channel"] else "لا",
                  "· SMA 20/50/200", [round(d[k][-1], 2) if d[k][-1] else None for k in ("sma20", "sma50", "sma200")])
            lv = RP.levels_of(r["market"])
            print("  المستويات: " + " · ".join(f"{k}={lv[k]:.2f} {lv.get(k + '_name', '')}" for k in ("s3", "s2", "s1", "p", "r1", "r2", "r3") if lv.get(k)))
        print("  الرسم: SMA 200 =", "SMA 200" in html, "· Stoch RSI =", "Stoch RSI 3 3 14 14" in html, "· مؤشّر الأبحاث =", "1.618 (" in html)
        pdf = await RP.pdf(r)
        pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf)) if pdf else 0
        print("  الملفّ:", f"{len(pdf):,} بايت · صفحات {pages}" if pdf else "تعذّرت الطباعة")


asyncio.run(main())
