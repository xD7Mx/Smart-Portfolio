#!/usr/bin/env python3
"""كاشفُ رسم التقرير المرجعيّ (‏D753) — قارئٌ فقط.
المالك: «الرسمُ مثلُ الذي في تقرير الجزيرة كابيتال — يستخدمون تريدنق فيو بخمسة مؤشّرات، ثلاثةٌ أعلى واثنان أسفل». فلا يُبنى من الذاكرة:
تُستخرج صورُ الرسوم من أحدث تقريرٍ يوميٍّ منشور، ويقرؤها القارئُ البصريّ: كلُّ مؤشّرٍ باسمه وإعداداته ولونه ولوحته، وما رُسم عليها من
مستوياتٍ وخطوط، وكيف تُشتقّ المستوياتُ في النصّ. لا يكتب في أيّ مخزن، والملفُّ المؤقّت يُحذف."""
import asyncio, base64, json, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")

PROMPT = """This is a TradingView chart image from a Saudi broker's daily technical report. Describe it precisely as JSON only:
{"timeframe": "...", "price_type": "candles|bars|line", "candle_colors": {"up": "#hex", "down": "#hex"},
 "overlays_on_price": [{"name": "exact legend text e.g. SMA 10 close", "period": 10, "color": "#hex", "style": "line|dashed"}],
 "drawings_on_price": [{"type": "fibonacci extension|fibonacci retracement|trendline|horizontal|channel|text", "levels": ["127.2%", "161.8%"], "color": "#hex", "anchors": "which swing (from low/high, dates if visible)"}],
 "lower_panes": [{"name": "exact legend text e.g. RSI 14 close", "params": "...", "lines": [{"name": "...", "color": "#hex"}], "levels": [30, 70], "fill": "#hex or null", "histogram": "colors or null"}],
 "volume": "shown? where? colors",
 "right_axis_labels": "what value tags appear on the price axis",
 "background": "#hex", "grid": "visible?", "watermark_or_title": "...", "other": "anything else notable"}
Read the legend texts literally. Count panes exactly."""


async def main():
    import fitz
    from app.services import research_desk as RD
    from app.services.research_reports import _ajc
    items = sorted([i for i in await _ajc() if i.get("kind") == "تقرير يوميّ"], key=lambda i: i.get("date") or "", reverse=True)
    it = items[0]
    print("التقرير:", it["date"], it["title"])
    path = await RD._download(it)
    try:
        doc = fitz.open(path)
        n = 0
        for pno in range(min(doc.page_count, 5)):
            for img in doc[pno].get_images(full=True):
                pix = fitz.Pixmap(doc, img[0])
                if pix.width < 300 or pix.height < 150:
                    continue
                if pix.n - pix.alpha >= 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                png = pix.tobytes("png")
                n += 1
                print(f"\n══ صورة {n} · صفحة {pno + 1} · {pix.width}×{pix.height} ══")
                obj = await RD._gemini([{"inline_data": {"mime_type": "image/png", "data": base64.b64encode(png).decode()}}, {"text": PROMPT}],
                                       max_tokens=2500, temperature=0.0)
                print(json.dumps(obj, ensure_ascii=False)[:2400] if obj else "تعذّرت القراءة")
                if n >= 3:
                    break
            if n >= 3:
                break
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


asyncio.run(main())
