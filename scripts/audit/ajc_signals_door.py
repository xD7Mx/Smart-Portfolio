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
    gaps = sorted(centers[i + 1] - centers[i] for i in range(len(centers) - 1))
    sp = gaps[len(gaps) // 2]
    for i in range(len(centers) - 1):
        if centers[i] > W * 0.6 and centers[i + 1] - centers[i] > 4 * sp:
            centers = centers[:i + 1]
            break
    xmax = int(centers[-1]) + 6
    ev = []
    for k, (p0, p1) in ((0, panes[0]), (len(panes) - 1, panes[-1])):
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


def pivot_k(vals, i, hi, upto):
    """كم شمعةً يساراً ويميناً (حتى `upto`) تبقى فيها الشمعةُ ‏i قمّةً (أو قاعاً)."""
    kl = 0
    while i - kl - 1 >= 0 and (vals[i - kl - 1] < vals[i] if hi else vals[i - kl - 1] > vals[i]):
        kl += 1
    kr = 0
    while i + kr + 1 <= upto and (vals[i + kr + 1] <= vals[i] if hi else vals[i + kr + 1] >= vals[i]):
        kr += 1
    return kl, kr


async def main():
    from app.services.market_data import market_service as M
    bars = [b for b in (await M.get_bars("^TASI.SR", "1d") or []) if b.get("close")]
    dates = [str(b["date"])[:10] for b in bars]
    print("شموعُ تاسي:", len(bars), dates[0], "→", dates[-1])
    fs = sorted(glob.glob(os.path.join(D, "20*.png")))
    raw = collections.defaultdict(list)          # (لوحة، لون) ← [(تاريخ التقرير، آخرُ شمعة، الشمعة)]
    nn = collections.Counter()
    for f in fs:
        day = os.path.basename(f)[:10]
        r = read_chart(f)
        if not r:
            continue
        last = max(i for i, d in enumerate(dates) if d < day)
        nn[r["n"]] += 1
        for e in r["ev"]:
            if e["kind"] != "arrow":
                continue
            raw[("price" if e["pane"] == 0 else "rsi", e["col"])].append((day, last, last - e["back"], e["rel"]))
    print("شموعُ الرسوم:", nn.most_common(3))
    H = [b["high"] for b in bars]
    L = [b["low"] for b in bars]
    R = rsi([b["close"] for b in bars])
    out = {}
    for key, obs in raw.items():
        # تجميعٌ على ±1 شمعة عبر التقارير: لكلّ سهمٍ تاريخُه الأكثرُ تكراراً وأوّلُ تقريرٍ ظهر فيه
        cnt = collections.Counter(i for _, _, i, _ in obs)
        evs = []
        for i, n in sorted(cnt.items()):
            if evs and i - evs[-1]["i_max"] <= 1:
                evs[-1]["i_max"] = i
                evs[-1]["votes"][i] = n
            else:
                evs.append({"i_max": i, "votes": {i: n}})
        res = []
        for e in evs:
            i = max(e["votes"], key=e["votes"].get)
            n = sum(e["votes"].values())
            if n < 3:
                continue
            first = min((day, last) for day, last, j, _ in obs if abs(j - i) <= 1)
            res.append({"i": i, "n": n, "first": first[0], "lag": first[1] - i})
        out[key] = res
    for key in sorted(out):
        hi = key[1] == "r"
        src = H if hi else L
        print(f"\n══ {key[0]} · {'أحمر' if hi else 'أخضر'} · {len(out[key])} سهماً ══")
        lags = collections.Counter()
        for e in out[key]:
            i = e["i"]
            last_at_first = i + e["lag"]
            pk = pivot_k(src, i, hi, last_at_first)
            rk = pivot_k([x or 0 for x in R], i, hi, last_at_first)
            lags[e["lag"]] += 1
            print(f"  {dates[i]} · ظهر {e['first']} (بعد {e['lag']}) · سعرٌ يسار/يمين {pk} · RSI {R[i]:.1f} يسار/يمين {rk} · {e['n']} تقرير")
        print("  توزيعُ التأخّر:", sorted(lags.items()))

asyncio.run(main())
