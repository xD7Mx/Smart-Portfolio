#!/usr/bin/env python3
"""كاشفُ ورقة التقرير الحيّة (‏D753): يقرأ أحدثَ تقريرٍ محفوظ لكلّ محفظةٍ ويرسم ورقتَه كاملةً كما تراها الشاشةُ ويصل ملفُّه —
ثمّ يقول: كم صفحة، وهل رسمُ «مؤشّر الأبحاث» فيها بمتوسّطيه وفيبوناتشي وRSI، وهل التوصياتُ (نظرتُنا للمراكز واختياراتُنا) في الورقة نفسِها،
ومستوياتُ المقاومة والدعم بأسمائها. قارئٌ فقط — لا يكتب شيئاً."""
import os, re, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
from app.services import research_desk as RD   # noqa: E402
from app.services import research_paper as RP   # noqa: E402

for pid in (0, 1, 2):
    r = RD.load_report(pid, None)
    if not r:
        print(f"محفظة {pid}: لا تقرير")
        continue
    html = RP.render(r, "all")
    pages = html.count('class="pg')
    daily = (r.get("market") or {}).get("daily") or []
    ri = RP.ri_of(r["market"]) if r.get("market") else None
    print(f"محفظة {pid}: {r['date']} · صفحات≈{pages} · شموع يومية {len(daily)} · حجم {len(html):,}")
    print(f"  الرسم: SMA20={'20 SMA' in html or 'SMA 20' in html} · فيبوناتشي1.618={'1.618' in html} · RSI={'RSI' in html} · "
          f"إشارات={len((ri or {}).get('signals') or [])} · خطّا اتجاه={[k for k, v in ((ri or {}).get('trend') or {}).items() if v]}")
    if ri:
        lv = ri["levels"]
        print("  المستويات: " + " · ".join(f"{k}={lv[k]:.2f} {lv.get(k + '_name', '')}" for k in ("s3", "s2", "s1", "p", "r1", "r2", "r3") if k in lv))
        if ri.get("fib"):
            print("  فيبوناتشي: " + " · ".join(f"{x['k']}={x['p']:.2f}" for x in ri["fib"]["levels"]))
    heads = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", html)
    print("  العناوين: " + " | ".join(re.sub("<[^>]+>", "", h)[:40] for h in heads[:30]))
    print(f"  التوصيات في الورقة: مراكز={len(r.get('positions') or r.get('portfolio') or [])} · اختيارات={len(r.get('picks') or [])} · "
          f"نظرتنا={'نظرتنا' in html} · أفضل اختياراتنا={'اختيارات' in html}")
