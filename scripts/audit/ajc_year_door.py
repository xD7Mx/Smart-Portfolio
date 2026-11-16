#!/usr/bin/env python3
"""كاشفُ سنةٍ من تقارير الجزيرة كابيتال اليومية (‏D755) — المالك 2026-11-16: «لا تجتهد من رأسك؛ امسك آخر تقاريرهم لسنةٍ كاملة
وشوف المؤشّر كيف يشتغل… هم يُظهرون نتائج بتواريخ يومية فتستطيع أن تستنبط كيف يعمل».
يُنزّل كلَّ تقريرٍ يوميٍّ منشور، ويحفظ صورةَ رسم المؤشّر العامّ منه في مخبأٍ على الخادم (‏storage/ajc_charts — ليس من بيانات المالك)،
ويجمع ما يقوله نصُّهم الفنّيّ عن المتوسّطات والتباعد والمؤشّرات بأرقامها، ثمّ يقرأ القارئُ البصريّ أحدثَ رسمين حرفياً."""
import asyncio, base64, collections, json, os, re, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
OUT = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "ajc_charts")

LEGEND = """This is a TradingView chart from a Saudi broker's daily report. Transcribe EVERY legend/label text exactly as printed, character by character
(numbers included), for EVERY pane top to bottom. Then describe drawings. JSON only:
{"panes": [{"index": 0, "legend_lines": ["exact text", "..."], "series": [{"legend": "exact", "color": "#hex", "kind": "line|histogram|area|band"}]}],
 "arrows": [{"color": "red|green|other", "position": "above bar|below bar", "approx_date": "from x-axis", "pane": 0}],
 "divergence_lines": [{"pane": 0, "color": "red|green", "from_date": "", "to_date": "", "connects": "highs|lows", "label": "text near it if any"}],
 "other_lines": [{"pane": 0, "type": "trendline|channel|horizontal|fib", "color": "", "note": ""}],
 "x_axis_range": "first and last visible dates", "notes": ""}"""

KEYS = re.compile(r"(تباعد|الانحراف|انحراف|ديفرجنس|divergence|المتوسط|متوسط|EMA|SMA|RSI|القوة النسبية|ماكد|MACD|بولنجر|فيبوناتشي|"
                  r"قناة|خط الاتجاه|اتجاه صاعد|اتجاه هابط|سهم|إشارة)", re.I)


def biggest(doc):
    import fitz
    best = None
    for pno in range(min(doc.page_count, 4)):
        for img in doc[pno].get_images(full=True):
            try:
                pix = fitz.Pixmap(doc, img[0])
            except Exception:                                     # noqa: BLE001
                continue
            if pix.width < 500 or pix.height < 250:
                continue
            a = pix.width * pix.height
            if not best or a > best[0]:
                if pix.n - pix.alpha >= 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                best = (a, pno + 1, pix)
    return best


async def main():
    import fitz
    from app.services import research_desk as RD
    from app.services.research_reports import _ajc
    os.makedirs(OUT, exist_ok=True)
    allit = await _ajc()
    kinds = collections.Counter(i.get("kind") for i in allit)
    print("كلُّ البنود:", len(allit), dict(kinds))
    items = sorted([i for i in allit if i.get("kind") == "تقرير يوميّ"], key=lambda i: i.get("date") or "", reverse=True)
    print("اليومية:", len(items), "من", items[-1]["date"] if items else "-", "إلى", items[0]["date"] if items else "-")
    for i in items[:3] + items[-2:]:
        print("  ", i["date"], i.get("title"), re.sub(r"^https?://[^/]+", "", str(i.get("url")))[:110])
    sem = asyncio.Semaphore(4)
    phrases = collections.Counter()
    meta = {}

    async def one(it):
        d = it["date"]
        async with sem:
            path = await RD._download(it)
        if not path:
            return
        try:
            doc = fitz.open(path)
            txt = "\n".join(doc[p].get_text() for p in range(min(doc.page_count, 4)))
            for line in re.split(r"[\n.،]", txt):
                if KEYS.search(line) and re.search(r"\d", line):
                    phrases[re.sub(r"[\d,.]+", "#", line.strip())[:90]] += 1
            b = biggest(doc)
            if b:
                fn = os.path.join(OUT, f"{d}.png")
                if not os.path.exists(fn):
                    b[2].save(fn)
                meta[d] = {"page": b[1], "w": b[2].width, "h": b[2].height}
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
    t0 = time.time()
    await asyncio.gather(*(one(i) for i in items))
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"))
    print(f"\nحُفظت رسومٌ: {len(meta)} في {time.time() - t0:.0f}ث · الأبعاد: {collections.Counter((m['w'], m['h'], m['page']) for m in meta.values()).most_common(5)}")
    print("\nأكثرُ العبارات الفنية تكراراً (الأرقام #):")
    for p, n in phrases.most_common(45):
        print(f"  {n:4d} · {p}")
    for d in sorted(meta, reverse=True)[:2]:
        png = open(os.path.join(OUT, f"{d}.png"), "rb").read()
        obj = await RD._gemini([{"inline_data": {"mime_type": "image/png", "data": base64.b64encode(png).decode()}}, {"text": LEGEND}],
                               max_tokens=3500, temperature=0.0)
        print(f"\n══ القراءة الحرفية · {d} ══")
        print(json.dumps(obj, ensure_ascii=False)[:3500] if obj else "تعذّرت القراءة")


asyncio.run(main())
