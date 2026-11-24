"""الفوليوم بروفايل — حجمُ التداول على محور السعر لا الزمن (‏D818 · بأمر المالك 2026-11-24).

قال المالك: «الثيتا والتآكلُ الزمنيّ في العقود المحرّكُ الرئيسيّ لخسارة تسعين بالمئة من الناس… ولزيادة نسبة النجاح أفكّر بإضافة أحد معايير
اختيار السترايكات: الفوليوم بروفايل»، ثمّ: «التكاملُ بين السوقين والخبراتُ التي نبنيها بتحسين الفرص قوّةٌ لنا ولصقر». فهذا حسابٌ واحدٌ للسوقين:

  · نقطةُ التحكّم (‏POC): السعرُ الذي تداول عنده أكبرُ حجم — «القيمةُ العادلة» الأكثرُ قبولاً.
  · منطقةُ القيمة (‏VAL–VAH): النطاقُ الذي جرى فيه 70٪ من التداول، يُبنى من نقطة التحكّم إلى الجانب الأكثف كلَّ خطوة.
  · عُقدُ الحجم الكثيف (‏HVN): قممُ الحجم — يتباطأ عندها السعرُ أو يرتدّ (جدارٌ أمام الصفقة، أو دعمٌ تحتها).
  · عُقدُ الحجم الضعيف (‏LVN): فراغاتٌ عبرها السعرُ سريعاً — إن دخلها يميل إلى العبور السريع نحو العقدة التالية.

**البياناتُ تقريبية ويُقال ذلك:** لا نملك كلَّ صفقةٍ بسعرها؛ فحجمُ كلّ شمعةٍ يوزَّع على مداها (من أدناها إلى أعلاها) بالتساوي — الطريقةُ المعتادة
حين تغيب بيانات الصفقات، ودقّتُها تكفي لمستوياتٍ بعرض أسعار التنفيذ. و**مزادُ الإغلاق في «تداول»** يجمع حجماً كبيراً عند سعرٍ واحد في آخر شمعة
اليوم فيضخّم البروفايلَ عند الإغلاقات اصطناعياً؛ فآخرُ شمعةٍ في كلّ يومٍ سعوديٍّ يُقصّ حجمُها إلى ضعف وسيط شموع يومها. والأسهمُ قليلةُ السيولة
بروفايلُها ضعيفُ الدلالة فيُعلَم ذلك (‏thin) ولا يُبنى عليه حكم.

والنافذةُ تتبع الأفقَ: العقدُ القريبُ (أسبوعان فأقلّ) من شموع 15 دقيقة لنحو عشرين جلسة، والشهريُّ من شموع الساعة لنحو ثلاثة أشهر، والأبعدُ من
اليوميّ لستّة أشهر؛ والسهمُ السعوديُّ من شموع الساعة لنحو ثلاثة أشهر.
"""
from __future__ import annotations

import statistics
from typing import Any

N_BINS = 40
VA_SHARE = 0.70
HVN_K, LVN_K = 1.25, 0.6            # قمّةٌ ≥ 1.25 من وسيط الحجم = عقدةٌ كثيفة · قاعٌ ≤ 0.6 منه = فراغ
MIN_BARS = 30


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and v == v else None


def _clean(bars: list[dict]) -> list[dict]:
    out = []
    for b in bars or []:
        h, l, c, v = _num(b.get("high")), _num(b.get("low")), _num(b.get("close")), _num(b.get("volume"))
        if h is None or l is None or c is None or not v or v <= 0 or h < l:
            continue
        out.append({"d": str(b.get("date") or b.get("time") or "")[:10], "h": h, "l": l, "c": c, "v": v})
    return out


def _cap_auction(rows: list[dict]) -> list[dict]:
    """مزادُ إغلاق «تداول»: آخرُ شمعةٍ في كلّ يومٍ يُقصّ حجمُها إلى ضعف وسيط شموع يومها الأخرى."""
    by: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        by.setdefault(r["d"], []).append(i)
    for idx in by.values():
        if len(idx) < 3:
            continue
        med = statistics.median(rows[i]["v"] for i in idx[:-1])
        last = idx[-1]
        rows[last] = {**rows[last], "v": min(rows[last]["v"], 2 * med)}
    return rows


def build(bars: list[dict], saudi: bool = False, intraday: bool = True, n_bins: int = N_BINS) -> dict | None:
    """البروفايلُ من الشموع ⇐ ‏{poc, val, vah, hvn:[{p,w}], lvn:[p], lo, hi, step, bins, n, from, to, thin} — أو None إن قلّت الشموع."""
    rows = _clean(bars)
    if len(rows) < MIN_BARS:
        return None
    if saudi and intraday:
        rows = _cap_auction(rows)
    lo, hi = min(r["l"] for r in rows), max(r["h"] for r in rows)
    if not hi > lo:
        return None
    step = (hi - lo) / n_bins
    vol = [0.0] * n_bins
    for r in rows:
        a, b = (r["l"] - lo) / step, (r["h"] - lo) / step
        if b - a < 1e-9:
            vol[min(n_bins - 1, int(a))] += r["v"]
            continue
        i0, i1 = int(a), min(n_bins - 1, int(b))
        span = b - a
        for i in range(i0, i1 + 1):
            ov = min(b, i + 1) - max(a, i)
            if ov > 0:
                vol[i] += r["v"] * ov / span
    tot = sum(vol)
    if tot <= 0:
        return None
    poc = max(range(n_bins), key=lambda i: vol[i])
    lo_i = hi_i = poc
    acc = vol[poc]
    while acc < VA_SHARE * tot and (lo_i > 0 or hi_i < n_bins - 1):
        up = vol[hi_i + 1] if hi_i < n_bins - 1 else -1.0
        dn = vol[lo_i - 1] if lo_i > 0 else -1.0
        if up >= dn:
            hi_i += 1
            acc += up
        else:
            lo_i -= 1
            acc += dn
    sm = [(vol[max(0, i - 1)] + vol[i] + vol[min(n_bins - 1, i + 1)]) / 3 for i in range(n_bins)]
    med = statistics.median(sm) or 1e-9
    top = max(sm) or 1e-9
    price = lambda i: lo + (i + 0.5) * step   # noqa: E731
    peaks = [i for i in range(n_bins) if sm[i] >= HVN_K * med and sm[i] >= sm[max(0, i - 1)] and sm[i] >= sm[min(n_bins - 1, i + 1)]]
    hvn: list[int] = []
    for i in peaks:                                               # قمّتان متجاورتان قمّةٌ واحدة — الأكثفُ منهما
        if hvn and i - hvn[-1] <= 2:
            if sm[i] > sm[hvn[-1]]:
                hvn[-1] = i
            continue
        hvn.append(i)
    lvn = [i for i in range(1, n_bins - 1) if sm[i] <= LVN_K * med and sm[i] <= sm[i - 1] and sm[i] <= sm[i + 1]]
    avg_turn = sum(r["v"] * r["c"] for r in rows) / len(rows)
    return {"poc": round(price(poc), 4), "val": round(lo + lo_i * step, 4), "vah": round(lo + (hi_i + 1) * step, 4),
            "hvn": [{"p": round(price(i), 4), "w": round(sm[i] / top, 3)} for i in hvn], "lvn": [round(price(i), 4) for i in lvn],
            "lo": round(lo, 4), "hi": round(hi, 4), "step": round(step, 6), "bins": [round(v / max(vol), 3) for v in vol],
            "n": len(rows), "from": rows[0]["d"], "to": rows[-1]["d"], "thin": avg_turn < (2e5 if saudi else 2e6)}


def window(dte: int | None = None, saudi: bool = False) -> tuple[str, int, str]:
    """(الإطار، عددُ الشموع، الوصف) بحسب أفق الصفقة — العقدُ القريبُ يُقرأ بشموعٍ قصيرة، والبعيدُ بشموعٍ أطول."""
    if saudi:
        return "1h", 5 * 63, "شموعُ الساعة لنحو ثلاثة أشهر"
    if dte is not None and dte <= 14:
        return "15m", 26 * 20, "شموعُ 15 دقيقة لنحو عشرين جلسة"
    if dte is None or dte <= 60:
        return "1h", 7 * 63, "شموعُ الساعة لنحو ثلاثة أشهر"
    return "1d", 126, "الشموعُ اليومية لستّة أشهر"


async def for_symbol(sym: str, dte: int | None = None, saudi: bool | None = None) -> dict | None:
    """بروفايلُ الرمز من مصدر الرسم نفسِه (‏market_service.get_bars — مخبّأ) بنافذة أفقه."""
    from app.services.market_data import market_service as M
    sa = saudi if saudi is not None else str(sym).upper().endswith(".SR") or str(sym).isdigit()
    s = f"{sym}.SR" if sa and str(sym).isdigit() else sym
    tf, n, label = window(dte, sa)
    try:
        bars = await M.get_bars(s, tf) or []
    except Exception:                                             # noqa: BLE001
        return None
    vp = build(bars[-n:], saudi=sa, intraday=tf != "1d")
    if vp:
        vp["window"] = label
        vp["tf"] = tf
    return vp


def read(vp: dict | None, S: float | None, side: str = "long", wall_w: float = 0.6) -> dict | None:
    """قراءةُ البروفايل عند السعر وفي جهة الصفقة: المنطقة (فوق القيمة · داخلها · تحتها)، والعقدةُ الكثيفةُ التالية في الجهة (هدفٌ يتباطأ عنده
    السعر)، والجدارُ (أوّلُ عقدةٍ كثيفةٍ ثقيلةٍ أمام السعر)، والدعمُ خلفه (أقربُ عقدةٍ كثيفةٍ أو نقطةُ التحكّم خلف السعر)، وفراغٌ أمامه؟"""
    if not vp or not S or S <= 0:
        return None
    long = side == "long"
    zone = "فوق القيمة" if S > vp["vah"] else "تحت القيمة" if S < vp["val"] else "داخل القيمة"
    ahead = sorted([h for h in vp["hvn"] if (h["p"] > S * 1.005 if long else h["p"] < S * 0.995)], key=lambda h: abs(h["p"] - S))
    behind = sorted([h for h in vp["hvn"] if (h["p"] <= S * 1.005 if long else h["p"] >= S * 0.995)], key=lambda h: abs(h["p"] - S))   # عقدةٌ عند السعر قاعدتُه
    nxt = ahead[0] if ahead else None
    wall = next((h for h in ahead if h["w"] >= wall_w), None)
    sup = behind[0]["p"] if behind else (vp["poc"] if (vp["poc"] <= S if long else vp["poc"] >= S) else None)
    far = nxt["p"] if nxt else (vp["hi"] if long else vp["lo"])
    gap = any((S < p < far) if long else (far < p < S) for p in vp["lvn"])
    pct = lambda p: round((p / S - 1) * 100, 2) if p else None   # noqa: E731
    return {"zone": zone, "poc": vp["poc"], "val": vp["val"], "vah": vp["vah"], "next": nxt["p"] if nxt else None, "next_pct": pct(nxt["p"]) if nxt else None,
            "wall": wall["p"] if wall else None, "wall_pct": pct(wall["p"]) if wall else None, "support": sup, "support_pct": pct(sup) if sup else None,
            "vah_pct": pct(vp["vah"]), "val_pct": pct(vp["val"]), "gap_ahead": gap, "thin": vp.get("thin", False), "window": vp.get("window", "")}


def member(rd: dict | None, side: str = "long") -> dict:
    """شاهدُ «الحجم» عند صقر — يوافق إن كان الطريقُ مفتوحاً من قاعدةِ حجمٍ قريبة، ويتحفّظ أمام جدارٍ قريب أو مطاردةٍ بعيدةٍ عن القيمة،
    و«غير متوفّر» بلا بروفايلٍ أو بسيولةٍ ضعيفة. لا يرفض وحده: هو معيارُ جودةٍ لا بوّابة."""
    from app.services.saqr_council import _m
    if not rd:
        return _m("الحجم", "na", "لا بروفايلَ حجمٍ كافٍ لهذا السهم")
    if rd["thin"]:
        return _m("الحجم", "na", "السيولةُ ضعيفةٌ فبروفايلُ الحجم قليلُ الدلالة")
    long = side == "long"
    f = lambda p: f"{p:,.2f}"   # noqa: E731
    if rd["wall"] is not None and abs(rd["wall_pct"]) <= 3:
        return _m("الحجم", "warn", f"جدارُ حجمٍ كثيفٍ عند {f(rd['wall'])} ({rd['wall_pct']:+.1f}٪) {'فوق' if long else 'تحت'} السعر مباشرة — يُبطئ الحركةَ قبل الهدف")
    base = rd["support_pct"] is not None and abs(rd["support_pct"]) <= 3
    ext = (rd["vah_pct"] < -8) if long else (rd["val_pct"] > 8)            # ابتعد عن منطقة القيمة أكثرَ من 8٪ في جهته
    if ext and not base:
        edge = rd["vah"] if long else rd["val"]
        return _m("الحجم", "warn", f"السعرُ ممتدٌّ بعيداً عن منطقة القيمة ({f(edge)}) — الدخولُ هنا مطاردة")
    out = (long and rd["zone"] == "فوق القيمة") or (not long and rd["zone"] == "تحت القيمة")
    if out and rd["gap_ahead"]:
        tgt = f" نحو {f(rd['next'])}" if rd["next"] else ""
        return _m("الحجم", "ok", f"خرج السعرُ من منطقة القيمة وأمامه فراغُ حجمٍ — الحركةُ عبره أسرع{tgt}")
    if base:
        return _m("الحجم", "ok", f"قريبٌ من قاعدة حجمٍ كثيفةٍ عند {f(rd['support'])} — دخولٌ بمخاطرةٍ قصيرة" + (f"، والعقدةُ التالية {f(rd['next'])}" if rd["next"] else ""))
    return _m("الحجم", "na", f"داخل منطقة القيمة ({f(rd['val'])}–{f(rd['vah'])}) بلا جدارٍ قريبٍ ولا قاعدةٍ لاصقة")


def summary(vp: dict | None) -> dict | Any:
    """ما يُرسَل إلى الواجهة: المستوياتُ وحدها بلا أعمدة البروفايل (تُرسم من ‏bins إن طُلبت)."""
    if not vp:
        return None
    return {k: vp[k] for k in ("poc", "val", "vah", "hvn", "lvn", "lo", "hi", "step", "bins", "window", "thin", "from", "to") if k in vp}
