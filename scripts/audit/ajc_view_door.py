#!/usr/bin/env python3
"""كاشفُ رسم الجزيرة كابيتال للعين (‏D755) — قارئٌ فقط: يطبع أحدثَ رسمٍ مخبَّأٍ (‏storage/ajc_charts) صورةً مصغّرةً مرمَّزة،
وقراءةً حرفيةً مكبَّرةً لوسائل إيضاح لوحاته، وألوانَ ما رُسم فيه بعددها — ليُستنبط المؤشّرُ من رسمهم لا من الذاكرة."""
import asyncio, base64, collections, glob, io, json, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
sys.stdout.reconfigure(line_buffering=True)
D = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "ajc_charts")
OCR = ("Transcribe EXACTLY every text visible in this cropped chart legend, character by character, keeping order and spacing. "
       'Also give the color of each colored text token. JSON only: {"lines": [{"text": "...", "tokens": [{"t": "...", "color": "#hex"}]}]}')


async def main():
    from PIL import Image
    from app.services import research_desk as RD
    fs = sorted(glob.glob(os.path.join(D, "20*.png")))
    f = fs[-1]
    im = Image.open(f).convert("RGB")
    W, H = im.size
    print("الرسم:", os.path.basename(f), W, H, "· المخبَّأ:", len(fs))
    # الألوانُ المشبعة بعددها (ما ليس رمادياً)
    px = im.load()
    cnt = collections.Counter()
    for y in range(0, H, 1):
        for x in range(0, W, 1):
            r, g, b = px[x, y]
            if max(r, g, b) - min(r, g, b) > 60:
                cnt[(r // 8 * 8, g // 8 * 8, b // 8 * 8)] += 1
    print("الألوانُ المشبعة:", [(f"#{r:02x}{g:02x}{b:02x}", n) for (r, g, b), n in cnt.most_common(14)])
    # فواصلُ اللوحات: صفوفٌ شبهُ متجانسة
    rows = []
    for y in range(H):
        vals = [px[x, y] for x in range(0, int(W * 0.85), 5)]
        if len(set(vals)) <= 2 and vals[0] != (255, 255, 255) and sum(vals[0]) < 720:
            rows.append(y)
    print("صفوفٌ فاصلة محتملة:", rows[:40])
    for name, box in (("أعلى اليسار", (0, 0, int(W * 0.55), int(H * 0.11))),):
        c = im.crop(box).resize((int((box[2] - box[0]) * 3), int((box[3] - box[1]) * 3)), Image.LANCZOS)
        b = io.BytesIO(); c.save(b, "PNG")
        obj = await RD._gemini([{"inline_data": {"mime_type": "image/png", "data": base64.b64encode(b.getvalue()).decode()}}, {"text": OCR}],
                               max_tokens=1500, temperature=0.0)
        print(f"وسيلةُ الإيضاح ({name}):", json.dumps(obj, ensure_ascii=False)[:1500])
    sm = im.resize((760, int(760 * H / W)), Image.LANCZOS)
    b = io.BytesIO(); sm.save(b, "JPEG", quality=52, optimize=True)
    print("IMG64", len(b.getvalue()))
    print(base64.b64encode(b.getvalue()).decode())


asyncio.run(main())
