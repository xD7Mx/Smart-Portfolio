#!/usr/bin/env python3
"""كاشفُ بنية التقرير اليوميّ للجزيرة كابيتال — قارئٌ فقط (‏D746).

بأمر المالك: «أبغى شيئاً طبقَ الأصل من الجزيرة كابيتال… عندهم تقسيماتٌ للمؤشّر وللقطاعات وللإحصاءات وللمعدّل».
فلا يُبنى التصميمُ من الذاكرة: يُنزَّل أحدثُ تقريرٍ يوميٍّ منشور ويُطبع هيكلُه — الصفحات، والكتلُ بمواضعها وأحجام خطوطها
وألوانها، والصورُ، وألوانُ التعبئة الغالبة. لا يكتب في أيّ مخزن، والملفُّ المؤقّت يُحذف."""
import asyncio, os, sys, time   # noqa: E401
from collections import Counter
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")


def _hex(c) -> str:
    if isinstance(c, int):
        return f"#{c:06x}"
    if isinstance(c, (list, tuple)) and len(c) >= 3:
        return "#" + "".join(f"{int(max(0, min(1, v)) * 255):02x}" for v in c[:3])
    return "-"


async def main():
    import fitz
    from app.services import research_desk as RD
    from app.services.research_reports import _ajc
    items = [i for i in await _ajc() if i.get("kind") == "تقرير يوميّ"]
    items.sort(key=lambda i: i.get("date") or "", reverse=True)
    if not items:
        print("لا تقريرَ يوميّاً منشوراً"); return
    it = items[0]
    print("التقرير:", it["date"], it["title"], it["url"])
    path = await RD._download(it)
    if not path:
        print("تعذّر التنزيل"); return
    try:
        doc = fitz.open(path)
        print("الصفحات:", doc.page_count)
        for pno in range(min(doc.page_count, 4)):
            pg = doc[pno]
            W, H = pg.rect.width, pg.rect.height
            print(f"\n══ صفحة {pno + 1} ({W:.0f}×{H:.0f}) ══")
            fills = Counter(_hex(d.get("fill")) for d in pg.get_drawings() if d.get("fill") is not None)
            print("  التعبئة:", fills.most_common(8))
            for im in pg.get_image_info():
                b = im["bbox"]
                print(f"  صورة [{b[0]:.0f},{b[1]:.0f},{b[2]:.0f},{b[3]:.0f}]")
            n = 0
            for blk in pg.get_text("dict")["blocks"]:
                if blk.get("type") != 0:
                    continue
                for ln in blk["lines"]:
                    sp = ln["spans"]
                    txt = " ".join(s["text"].strip() for s in sp if s["text"].strip())
                    if not txt:
                        continue
                    s0 = max(sp, key=lambda s: len(s["text"]))
                    b = ln["bbox"]
                    bold = "B" if (s0["flags"] & 16) else " "
                    print(f"  [{b[0]:.0f},{b[1]:.0f}] {s0['size']:.1f}{bold} {_hex(s0['color'])} {txt[:110]}")
                    n += 1
                    if n >= 170:
                        break
                if n >= 170:
                    print("  …"); break
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


asyncio.run(main())
