#!/usr/bin/env python3
"""كاشفُ إشارات رسم الجزيرة كابيتال على سنةٍ كاملة (‏D755) — قارئٌ فقط، حسابٌ على البكسل بلا قارئٍ بصريّ.
المالك: «امسك آخر تقاريرهم لسنةٍ كاملة وشوف المؤشّر كيف يشتغل — يُظهرون نتائجَ بتواريخ يومية فتستنبط كيف يعمل».
لكلّ رسمٍ مخبَّأ (‏storage/ajc_charts): اللوحاتُ والشموعُ وربطُها بجلسات تاسي، ثمّ الأسهمُ الخضراء والحمراء (في لوحة السعر ولوحة المذبذب)
وخطوطُها، بتاريخ موضعها وأوّل تقريرٍ ظهرت فيه (أي كم جلسةً تأخّر ظهورُها). ثمّ تُختبر القواعدُ المرشّحة على شموع تاسي:
تباعدُ RSI 14 على محاور (يسار 5 · يمين 5 · مدى 5–60) كمؤشّر تريدنق فيو المدمج، وعبورُ 30 و70 — ويُطبع التطابق."""
import asyncio, collections, glob, json, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
sys.stdout.reconfigure(line_buffering=True)
D = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "ajc_charts")
GREEN, RED = (74, 175, 79), (239, 56, 70)


def near(a, b, t):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) <= t


def comps(pts):
    pts, seen, out = set(pts), set(), []
    for p in pts:
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
        xs, ys = [c[0] for c in cc], [c[1] for c in cc]
        out.append({"n": len(cc), "x0": min(xs), "x1": max(xs), "y0": min(ys), "y1": max(ys), "cx": sum(xs) / len(xs)})
    return out


def read_chart(path):
    import numpy as np
    from PIL import Image
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()
    A = np.asarray(im, dtype=np.int16)
    dist = lambda col: np.abs(A - np.array(col, dtype=np.int16)).sum(axis=2)   # noqa: E731
    seps = [y for y in range(H) if len({px[x, y] for x in range(0, int(W * 0.85), 7)}) <= 2 and px[10, y] != (255, 255, 255)]
    b = [0] + seps + [H]
    panes = [(b[i], b[i + 1]) for i in range(len(b) - 1) if b[i + 1] - b[i] > 25]
    if len(panes) < 2:
        return None
    y0, y1 = panes[0]
    up, dn = (33, 171, 148), (239, 84, 81)
    cm = (dist(up) <= 14) | (dist(dn) <= 14)
    cols = cm[y0:y1].sum(axis=0).tolist()
    runs, x = [], 0
    while x < W:
        if cols[x] >= 2:
            s = x
            while x < W and cols[x] >= 2:
                x += 1
            runs.append((s, x - 1))
        x += 1
    centers = [(a + c) / 2 for a, c in runs]
    if len(centers) < 50:
        return None
    xmax = int(centers[-1]) + 6
    ev = []
    for k, (p0, p1) in enumerate(panes):
        for nm, col in (("g", GREEN), ("r", RED)):
            m = dist(col) <= 18
            ys, xs = np.nonzero(m[p0:p1, :xmax])
            pts = list(zip((xs).tolist(), (ys + p0).tolist()))
            for c in comps(pts):
                w, h = c["x1"] - c["x0"] + 1, c["y1"] - c["y0"] + 1
                if c["n"] < 20:
                    continue
                fill = c["n"] / (w * h)
                kind = "arrow" if w <= 22 and h <= 24 and fill > 0.25 else "line" if max(w, h) > 24 else "blob"
                ki = min(range(len(centers)), key=lambda i: abs(centers[i] - c["cx"]))
                ka = min(range(len(centers)), key=lambda i: abs(centers[i] - c["x0"]))
                kb = min(range(len(centers)), key=lambda i: abs(centers[i] - c["x1"]))
                rel = (c["y0"] - p0) / (p1 - p0)
                ev.append({"pane": k, "col": nm, "kind": kind, "back": len(centers) - 1 - ki, "back_a": len(centers) - 1 - ka,
                           "back_b": len(centers) - 1 - kb, "rel": round(rel, 2), "w": w, "h": h, "slope_up": None})
    return {"n": len(centers), "panes": len(panes), "ev": ev}


def rsi(cl, n=14):
    out = [None] * len(cl)
    g = [max(0, cl[i] - cl[i - 1]) for i in range(1, len(cl))]
    l = [max(0, cl[i - 1] - cl[i]) for i in range(1, len(cl))]
    ag, al = sum(g[:n]) / n, sum(l[:n]) / n
    out[n] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n, len(g)):
        ag, al = (ag * (n - 1) + g[i]) / n, (al * (n - 1) + l[i]) / n
        out[i + 1] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def tv_div(bars, osc, lbL=5, lbR=5, lo=5, hi=60):
    """مؤشّرُ تريدنق فيو المدمج «RSI Divergence Indicator» كما في شيفرته: محورٌ على المذبذب (يسار 5 · يمين 5)، والمقارنةُ بالمحور السابق
    إن كان بين 5 و60 شمعة؛ صاعدٌ منتظم: المذبذبُ قاعٌ أعلى والسعرُ قاعٌ أدنى · هابطٌ منتظم: المذبذبُ قمّةٌ أدنى والسعرُ قمّةٌ أعلى."""
    n, out = len(bars), []
    pl, ph = [], []
    for c in range(lbL, n - lbR):
        v = osc[c]
        if v is None or any(osc[j] is None for j in range(c - lbL, c + lbR + 1)):
            continue
        L, R = [osc[j] for j in range(c - lbL, c)], [osc[j] for j in range(c + 1, c + lbR + 1)]
        if all(v < x for x in L) and all(v <= x for x in R):
            pl.append(c)
        if all(v > x for x in L) and all(v >= x for x in R):
            ph.append(c)
    for arr, bull in ((pl, True), (ph, False)):
        for a, b in zip(arr, arr[1:]):
            if not (lo <= b - a <= hi):
                continue
            if bull and osc[b] > osc[a] and bars[b]["low"] < bars[a]["low"]:
                out.append({"i": b, "side": "bull", "from": a, "kind": "regular"})
            if bull and osc[b] < osc[a] and bars[b]["low"] > bars[a]["low"]:
                out.append({"i": b, "side": "bull", "from": a, "kind": "hidden"})
            if not bull and osc[b] < osc[a] and bars[b]["high"] > bars[a]["high"]:
                out.append({"i": b, "side": "bear", "from": a, "kind": "regular"})
            if not bull and osc[b] > osc[a] and bars[b]["high"] < bars[a]["high"]:
                out.append({"i": b, "side": "bear", "from": a, "kind": "hidden"})
    return out, pl, ph


async def main():
    from app.services.market_data import market_service as M
    bars = [b for b in (await M.get_bars("^TASI.SR", "1d") or []) if b.get("close")]
    dates = [str(b["date"])[:10] for b in bars]
    print("شموعُ تاسي:", len(bars), dates[0], "→", dates[-1])
    fs = sorted(glob.glob(os.path.join(D, "20*.png")))
    events = {}
    seen_n = collections.Counter()
    for f in fs:
        day = os.path.basename(f)[:10]
        r = read_chart(f)
        if not r:
            continue
        last = max(i for i, d in enumerate(dates) if d < day)          # تقريرُ الصباح يرسم الجلسةَ السابقة
        seen_n[r["n"]] += 1
        for e in r["ev"]:
            if e["kind"] == "blob":
                continue
            i = last - e["back"]
            if i < 0:
                continue
            key = (e["pane"], e["col"], e["kind"], dates[i] if e["kind"] == "arrow" else (dates[last - e["back_a"]], dates[last - e["back_b"]]))
            if key not in events:
                events[key] = {"first": day, "lag": last - i, "count": 0, "rel": e["rel"], "w": e["w"], "h": e["h"], "i": i}
            events[key]["count"] += 1
    print("عددُ الشموع في الرسوم:", seen_n.most_common(4))
    stable = {k: v for k, v in events.items() if v["count"] >= 3}
    print("أحداثٌ ثابتة (ظهرت في 3 تقارير فأكثر):", len(stable), dict(collections.Counter((k[0], k[1], k[2]) for k in stable)))
    cl = [b["close"] for b in bars]
    R = rsi(cl)
    div, pl, ph = tv_div(bars, R)
    reg = {(d["i"], d["side"]) for d in div if d["kind"] == "regular"}
    hid = {(d["i"], d["side"]) for d in div if d["kind"] == "hidden"}
    piv = {(i, "bull") for i in pl} | {(i, "bear") for i in ph}
    print("\nالأسهم (لوحة · لون · تاريخ · أوّلُ ظهور · تأخّر · ارتفاعُها في اللوحة · RSI يومَها · أقربُ محورٍ/تباعد):")
    rows = []
    for (pane, col, kind, d), v in sorted(stable.items(), key=lambda kv: str(kv[0][3])):
        if kind != "arrow":
            continue
        i = v["i"]
        side = "bull" if col == "g" else "bear"
        near_piv = min((abs(j - i) for (j, s) in piv if s == side), default=99)
        near_reg = min((abs(j - i) for (j, s) in reg if s == side), default=99)
        near_hid = min((abs(j - i) for (j, s) in hid if s == side), default=99)
        cr = next((j - i for j in range(i - 3, i + 4) if 0 < j < len(R) and R[j] and R[j - 1] and
                   ((side == "bull" and R[j - 1] < 30 <= R[j]) or (side == "bear" and R[j - 1] > 70 >= R[j]))), None)
        rows.append((pane, col, near_piv, near_reg, near_hid))
        print(f"  {pane} {col} {d} · أوّل {v['first']} · تأخّر {v['lag']} · y {v['rel']} · RSI {R[i]:.1f} · محور ±{near_piv} · منتظم ±{near_reg}"
              f" · خفيّ ±{near_hid} · عبور30/70 {cr} · {v['count']} تقرير")
    for pane in sorted({r[0] for r in rows}):
        rr = [r for r in rows if r[0] == pane]
        print(f"لوحة {pane}: {len(rr)} سهماً · على محور RSI (±1): {sum(1 for r in rr if r[2] <= 1)} · تباعدٌ منتظم (±1): {sum(1 for r in rr if r[3] <= 1)}"
              f" · خفيّ (±1): {sum(1 for r in rr if r[4] <= 1)}")
    print("\nالخطوط (لوحة · لون · من→إلى · تقارير):")
    for (pane, col, kind, d), v in sorted(stable.items(), key=lambda kv: str(kv[0][3])):
        if kind == "line":
            print(f"  {pane} {col} {d[0]}→{d[1]} · {v['w']}x{v['h']} · أوّل {v['first']} · {v['count']}")
    start = os.path.basename(fs[0])[:10]
    print("\nتباعدُ تريدنق فيو المنتظم على السنة نفسِها:", [(dates[d["i"]], d["side"]) for d in div if d["kind"] == "regular" and dates[d["i"]] >= start][:60])
    print("محاورُ RSI (قيعان):", [dates[i] for i in pl if dates[i] >= start][:60])
    print("محاورُ RSI (قمم):", [dates[i] for i in ph if dates[i] >= start][:60])


asyncio.run(main())
