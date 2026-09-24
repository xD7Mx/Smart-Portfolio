#!/usr/bin/env python3
"""D7M مقابلَ تريدنق فيو على 4001 (D465). قارئٌ فقط.

تريدنق فيو (لقطةُ المالك، 4001 أسبوعي، 24-09-2026):
  الشمعةُ الجارية: فتح 4.67 · أعلى 4.67 · أدنى 4.38 · إغلاق 4.38
  فيبوناتشي: 0 = 5.75 · 1 = 12.50 (1.1 = 13.18 · 0.5 = 9.13 · 0.618 = 9.92 · −0.618 = 1.58)
  اللوحة: 1D هبوط · 4H صعود · 1H هبوط · 15M هبوط · القرار محايد

يقرأ ما يقرؤه التطبيقُ نفسُه: `get_history(…, "5y")` و`/market/frames`، ثمّ
يُعيد حسابَ الزجزاج (نسخةٌ مطابقةٌ لـ`d7m.ts`) ليُقارَن الرقمُ بالرقم.

    docker exec sp_backend python /app/scripts/audit/d7m_vs_tradingview.py
"""
import asyncio, sys
sys.path.insert(0, "/app")


def atr(b, n=10):
    tr = [x["high"] - x["low"] if i == 0 else max(x["high"] - x["low"], abs(x["high"] - b[i-1]["close"]), abs(x["low"] - b[i-1]["close"])) for i, x in enumerate(b)]
    out, prev = [], None
    for i, t in enumerate(tr):
        prev = t if prev is None else (prev * (n - 1) + t) / n
        out.append(prev)
    return out


def zigzag(b, mult=3, depth=7):
    a, half, piv = atr(b), max(1, depth // 2), []
    for i in range(half, len(b) - half):
        isH = all(b[k]["high"] <= b[i]["high"] for k in range(i - half, i + half + 1) if k != i)
        isL = all(b[k]["low"] >= b[i]["low"] for k in range(i - half, i + half + 1) if k != i)
        dev = a[i] / b[i]["close"] * 100 * mult
        for ok, price, hi in ((isH, b[i]["high"], True), (isL, b[i]["low"], False)):
            if not ok:
                continue
            if not piv:
                piv.append([i, price, hi]); continue
            last = piv[-1]
            if last[2] == hi:
                if (price > last[1]) if hi else (price < last[1]):
                    piv[-1] = [i, price, hi]
                continue
            if abs(price - last[1]) / last[1] * 100 >= dev:
                piv.append([i, price, hi])
    return piv


def ema(v, n):
    k, out, prev = 2 / (n + 1), [], None
    for i, x in enumerate(v):
        if i < n - 1:
            out.append(None); continue
        prev = sum(v[:n]) / n if prev is None else x * k + prev * (1 - k)
        out.append(prev)
    return out


def session_up(m, g):
    pv = v = s = n = 0
    for k in range(0, len(m), g):
        ch = m[k:k + g]
        tp = (max(x["high"] for x in ch) + min(x["low"] for x in ch) + ch[-1]["close"]) / 3
        vol = sum(x["volume"] for x in ch)
        pv += tp * vol; v += vol; s += tp; n += 1
    return m[-1]["close"] > (pv / v if v else s / n)


async def main():
    try:
        from app.services.market_data import market_service
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); return 0
    from app.services import cache
    for k in ("hist:yahoo:4001.SR:5y:v5",):
        try: cache.delete(k)
        except Exception: pass
    w = await market_service.get_history("4001.SR", "5y") or []
    print(f"أسبوعي 5y: {len(w)} شمعة · الأخيرتان: {w[-2:]}")
    p = zigzag(w)
    if len(p) >= 2:
        s, e = p[-2], p[-1]
        start, end = e[1], s[1]
        h = (-1 if start > end else 1) * abs(start - end)
        lv = {x: round(start + h * x, 2) for x in (0, 1, 1.1, -0.1, 0.5, 0.618, -0.5, -0.618)}
        print(f"فيبوناتشي التطبيق: ضلعٌ {s[1]}@{w[s[0]]['date']} → {e[1]}@{w[e[0]]['date']} · {lv}")
        print("تريدنق فيو:       0=5.75 · 1=12.50 · 1.1=13.18 · -0.1=5.08 · 0.5=9.13 · 0.618=9.92 · -0.5=2.38 · -0.618=1.58")
    from app.api.v1.endpoints.market import get_d7m_frames
    r = await get_d7m_frames("4001")
    import json
    body = r if isinstance(r, dict) else json.loads(getattr(r, "body", b"{}"))
    d = body.get("data") or {}
    daily, m15 = d.get("daily") or [], d.get("m15") or []
    e = ema([x["close"] for x in daily], 200)
    up1d = e[-1] is not None and daily[-1]["close"] > e[-1]
    rows = {"1D": up1d}
    if m15:
        rows.update({"4H": session_up(m15, 16), "1H": session_up(m15, 4), "15M": session_up(m15, 1)})
    print(f"يوميّ {len(daily)} · 15د {len(m15)} (جلسة {m15[0]['day'] if m15 else '—'})")
    print("لوحة التطبيق: " + " · ".join(f"{k} {'صعود' if v else 'هبوط'}" for k, v in rows.items()))
    print("تريدنق فيو:   1D هبوط · 4H صعود · 1H هبوط · 15M هبوط")
    return 0

sys.exit(asyncio.run(main()))
