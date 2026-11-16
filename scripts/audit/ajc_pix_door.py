#!/usr/bin/env python3
"""كاشفُ عناصر رسم الجزيرة كابيتال بالبكسل (‏D755) — قارئٌ فقط. لأحدث رسمٍ مخبَّأ: حدودُ اللوحات، وأكثرُ الألوان المشبعة في كلّ لوحةٍ
بقيمها الدقيقة، ومواضعُ الشموع وربطُها بتواريخ جلسات تاسي (آخرُ شمعةٍ = إغلاقُ وسيلة الإيضاح)، ثمّ مكوّناتُ الألوان غير الشموع
(الأسهمُ وخطوطُ التباعد) بإطارها وتاريخ موضعها. لا يستعمل قارئاً بصرياً — حسابٌ على البكسل."""
import asyncio, collections, glob, json, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
sys.stdout.reconfigure(line_buffering=True)
D = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "ajc_charts")
WANT = sys.argv[1] if len(sys.argv) > 1 else None


def comps(mask, W, H, min_px=6):
    seen, out = set(), []
    pts = set(mask)
    for p in mask:
        if p in seen:
            continue
        st, cc = [p], []
        seen.add(p)
        while st:
            x, y = st.pop()
            cc.append((x, y))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in pts and q not in seen:
                        seen.add(q)
                        st.append(q)
        if len(cc) >= min_px:
            xs, ys = [c[0] for c in cc], [c[1] for c in cc]
            out.append({"n": len(cc), "x0": min(xs), "x1": max(xs), "y0": min(ys), "y1": max(ys)})
    return out


async def main():
    from PIL import Image
    from app.services.market_data import market_service as M
    fs = sorted(glob.glob(os.path.join(D, "20*.png")))
    f = [x for x in fs if WANT and WANT in x][0] if WANT else fs[-1]
    im = Image.open(f).convert("RGB")
    W, H = im.size
    px = im.load()
    day = os.path.basename(f)[:10]
    print("الرسم:", day, W, H)
    # فواصلُ اللوحات
    seps = [y for y in range(H) if len({px[x, y] for x in range(0, int(W * 0.85), 7)}) <= 2 and px[10, y] != (255, 255, 255)]
    print("فواصل:", seps)
    bounds = [0] + [s for s in seps] + [H]
    panes = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1) if bounds[i + 1] - bounds[i] > 25]
    print("اللوحات:", panes)
    # محورُ الأسعار: آخرُ عمودٍ فيه شموع
    sat = lambda c: max(c) - min(c)   # noqa: E731
    for k, (y0, y1) in enumerate(panes):
        cnt = collections.Counter(px[x, y] for y in range(y0, y1) for x in range(W) if sat(px[x, y]) > 70)
        print(f"لوحة {k} ({y0}-{y1}):", [(f"#{r:02x}{g:02x}{b:02x}", n) for (r, g, b), n in cnt.most_common(16)])
    # الشموع: أعمدةٌ في اللوحة الأولى فيها لونُ صعودٍ أو هبوطٍ صريح (من أكثر لونين مشبعين في الشموع)
    y0, y1 = panes[0]
    cnt0 = collections.Counter(px[x, y] for y in range(y0, y1) for x in range(W) if sat(px[x, y]) > 120)
    up = max((c for c in cnt0 if c[1] > c[0]), key=lambda c: cnt0[c])
    dn = max((c for c in cnt0 if c[0] > c[1]), key=lambda c: cnt0[c])
    print("لونا الشموع:", up, dn)
    near = lambda a, b, t=12: abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) <= t   # noqa: E731
    cols = []
    for x in range(W):
        hits = sum(1 for y in range(y0, y1) if near(px[x, y], up) or near(px[x, y], dn))
        cols.append(hits)
    runs, x = [], 0
    while x < W:
        if cols[x] >= 2:
            s = x
            while x < W and cols[x] >= 2:
                x += 1
            runs.append((s, x - 1))
        x += 1
    centers = [(a + b) / 2 for a, b in runs]
    gaps = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
    print("شموع:", len(centers), "· أوّل/آخر x:", centers[:2], centers[-2:], "· تباعد وسيط:", sorted(gaps)[len(gaps) // 2] if gaps else None)
    bars = [b for b in (await M.get_bars("^TASI.SR", "1d") or []) if b.get("close")]
    bars = [b for b in bars if str(b["date"])[:10] < day]          # تقريرُ الصباح يرسم إغلاقَ الجلسة السابقة
    print("آخر جلسات تاسي:", [(str(b["date"])[:10], round(b["close"], 2)) for b in bars[-3:]])

    def date_at(xc):
        if not centers:
            return "?"
        k = min(range(len(centers)), key=lambda i: abs(centers[i] - xc))
        back = len(centers) - 1 - k
        return str(bars[-1 - back]["date"])[:10] if back < len(bars) else "?"
    # مكوّناتُ الألوان المميّزة (أخضرُ وأحمرُ وأزرقُ الرسم) بشكلها: سهمٌ مدمج أم خطٌّ رفيع
    KEY = {"أخضر": (74, 175, 79), "أحمر": (239, 56, 70), "أزرق": (70, 102, 176)}
    for k, (y0, y1) in enumerate(panes):
        for nm, col in KEY.items():
            mask = [(x, y) for y in range(y0, y1) for x in range(int(centers[-1]) + 4 if centers else W) if near(px[x, y], col, 40)]
            cs = sorted(comps(mask, W, H, 5), key=lambda c: c["x0"])
            if not cs:
                continue
            desc = []
            for c in cs:
                w, h = c["x1"] - c["x0"] + 1, c["y1"] - c["y0"] + 1
                fill = c["n"] / (w * h)
                kind = "سهم" if 6 <= w <= 20 and 6 <= h <= 22 and fill > 0.3 else "خط" if max(w, h) > 25 and fill < 0.3 else "?"
                desc.append(f"{kind} {c['n']}px {w}x{h} y{c['y0']}-{c['y1']} {date_at(c['x0'])}→{date_at(c['x1'])}")
            print(f"  لوحة {k} {nm} ({len(cs)}):", desc[:24])
    from PIL import Image as _I
    import base64, io
    from app.services import research_desk as RD
    c = im.crop((0, 0, int(W * 0.45), int(H * 0.22)))
    c = c.resize((c.width * 3, c.height * 3), _I.LANCZOS)
    b = io.BytesIO(); c.save(b, "PNG")
    obj = await RD._gemini([{"inline_data": {"mime_type": "image/png", "data": base64.b64encode(b.getvalue()).decode()}},
                            {"text": "Transcribe EXACTLY every line of legend text in this crop, top to bottom, character by character, with the color of each "
                                     "line's main text. Include indicator names, their parameters and current values. JSON only: "
                                     '{"lines": [{"text": "...", "color": "#hex"}]}'}], max_tokens=1200, temperature=0.0)
    print("وسيلةُ الإيضاح:", json.dumps(obj, ensure_ascii=False)[:1200])

asyncio.run(main())
