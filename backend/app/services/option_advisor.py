"""السلسلةُ باليونانيات و«التحليلُ الذكيّ» للعقود (‏D761 · بأمر المالك 2026-11-17).

قال المالك: «زرٌّ في أعلى جدول العقود: تحليلٌ ذكيّ — يقوم مقامي، يقرأ التذبذبَ والدلتا والثيتا واليونانياتِ كاملةً ويعرف الأنسب،
ويعرف الخطورة… ولديه امتناع: لو اختير عقدٌ خاطئٌ غيرُ منطقيّ يمتنع عنه. وأقول له أبغى بسعر كذا فيقول لي إن كان مناسباً أو أن هذه
الشركة لا تجمّلني بهذا السعر — مثلاً 150 دولاراً لا تأخذه على SPX، تأخذه على SPY».

كلُّ رقمٍ من مصدره أو من معادلته (لا اختلاق):
  · السعرُ والسلسلة: ‏options_chain (ياهو، متأخّرة)؛ والتذبذبُ يُستخرج من سعر العقد نفسِه (‏option_picks.quote).
  · اليونانيات: بلاك-شولز بلا توزيعات — الدلتا والغاما والثيتا (يومياً، بالدولار للعقد) والفيغا (لكلّ نقطة تذبذب) واحتمالُ الانتهاء
    في النقود واحتمالُ الربح عند الانتهاء.
  · المسارُ والأخبار: ‏option_picks.trend_of وread_news (العناوين وحدها)؛ والتذبذبُ التاريخيُّ عشرون جلسة؛ وموعدُ الأرباح من الاقتباس الحيّ؛
    والأحداثُ الاقتصاديةُ المهمّةُ قبل الانتهاء من ‏econ_calendar.
والحكمُ قواعدُ مكتوبةٌ تُعرض أسبابُها: «مناسب» · «بحذر» · «أمتنع».
"""
from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone

from loguru import logger

from app.services import option_picks as OP

ALT = {"^SPX": "SPY", "SPX": "SPY", "^GSPC": "SPY", "^NDX": "QQQ", "NDX": "QQQ", "^IXIC": "QQQ", "^RUT": "IWM", "RUT": "IWM", "^DJI": "DIA", "^XSP": "SPY"}
VERDICT = {"ok": "مناسب", "warn": "بحذر", "no": "أمتنع"}


def _npdf(x: float) -> float:
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def greeks(S: float, K: float, T: float, iv: float, call: bool, r: float = OP.RATE) -> dict:
    """الدلتا والغاما والثيتا (للسهم يومياً) والفيغا (لكلّ نقطة تذبذب) واحتمالُ الانتهاء في النقود."""
    sq = iv * math.sqrt(T)
    d1 = (math.log(S / K) + (r + iv * iv / 2) * T) / sq
    d2 = d1 - sq
    disc = K * math.exp(-r * T)
    gamma = _npdf(d1) / (S * sq)
    th = -S * _npdf(d1) * iv / (2 * math.sqrt(T)) + (-r * disc * OP._ncdf(d2) if call else r * disc * OP._ncdf(-d2))
    return {"delta": OP._ncdf(d1) if call else OP._ncdf(d1) - 1, "gamma": gamma, "theta": th / 365, "vega": S * _npdf(d1) * math.sqrt(T) / 100,
            "itm": OP._ncdf(d2) if call else OP._ncdf(-d2)}


def hv20(bars: list[dict]) -> float | None:
    """التذبذبُ التاريخيُّ السنويّ من عوائد آخر عشرين جلسة."""
    cl = [float(b["close"]) for b in bars if isinstance(b.get("close"), (int, float)) and b["close"] > 0][-21:]
    if len(cl) < 21:
        return None
    rets = [math.log(cl[i] / cl[i - 1]) for i in range(1, len(cl))]
    m = sum(rets) / len(rets)
    return math.sqrt(sum((x - m) ** 2 for x in rets) / (len(rets) - 1)) * math.sqrt(252)


def enrich_rows(rows: list[dict], S: float, dte: int, call: bool, now: float | None = None) -> None:
    """يضيف لكلّ عقدٍ تذبذبَه من سعره ويونانياتِه — في مكانه؛ والعقدُ بلا سعرٍ صالحٍ تبقى يونانياتُه فارغة."""
    T = max(dte, 0.5) / 365
    for o in rows:
        q = OP.quote(o, S, T, call, now) if o.get("strike") else None
        if not q:
            o["g"] = None
            continue
        g = greeks(S, o["strike"], T, q["iv"], call)
        px = q["px"]
        be = o["strike"] + px if call else o["strike"] - px
        o["g"] = {"iv": round(q["iv"] * 100, 1), "delta": round(g["delta"], 3), "gamma": round(g["gamma"], 4), "theta": round(g["theta"] * 100, 2),
                  "vega": round(g["vega"] * 100, 2), "itm": round(g["itm"] * 100, 1), "pop": round(OP.prob_beyond(S, be, T, q["iv"], call) * 100, 1),
                  "px": px, "src": q["src"], "spread": round(q["spread"] * 100, 1) if q["spread"] is not None else None, "be": round(be, 2)}


def stats(ch: dict, S: float, dte: int) -> dict:
    """رأسُ الجدول: تذبذبُ النقود والحركةُ المتوقّعةُ حتى الانتهاء ونسبةُ البيع إلى الشراء (كمّيةً وعقوداً مفتوحة) وألمُ الحدّ الأقصى."""
    T = max(dte, 0.5) / 365
    ref = OP.atm_iv(ch, S, T)
    calls, puts = ch.get("calls") or [], ch.get("puts") or []
    sv = lambda rows, k: sum((r.get(k) or 0) for r in rows)        # noqa: E731
    cv, pv, coi, poi = sv(calls, "volume"), sv(puts, "volume"), sv(calls, "oi"), sv(puts, "oi")
    strikes = sorted({r["strike"] for r in calls + puts if r.get("strike")})
    pain = None
    if strikes and (coi or poi):
        def loss(x):
            return sum(max(0, x - r["strike"]) * (r.get("oi") or 0) for r in calls) + sum(max(0, r["strike"] - x) * (r.get("oi") or 0) for r in puts)
        pain = min(strikes, key=loss)
    return {"atm_iv": round(ref * 100, 1) if ref else None, "move": round(S * ref * math.sqrt(T), 2) if ref else None,
            "move_pct": round(ref * math.sqrt(T) * 100, 1) if ref else None,
            "pcr_vol": round(pv / cv, 2) if cv else None, "pcr_oi": round(poi / coi, 2) if coi else None,
            "vol": {"call": cv, "put": pv}, "oi": {"call": coi, "put": poi}, "max_pain": pain}


async def _context(sym: str) -> dict:
    """المسارُ والتذبذبُ التاريخيُّ من الشموع اليومية، والأخبار، وموعدُ الأرباح، والأحداثُ الاقتصادية — مخبّأةٌ ربعَ ساعة."""
    from app.services import cache
    from app.services.market_data import market_service as M
    ck = f"optadv:ctx:{sym}"
    hit = cache.get(ck)
    if hit is not None:
        return hit
    base = sym.lstrip("^")
    try:
        bars = await asyncio.wait_for(M.get_bars(sym, "1d"), 25) or []
    except Exception:                                             # noqa: BLE001
        bars = []
    tr = OP.trend_of(bars)
    news = None
    if tr:
        try:
            news = (await OP.read_news({base: tr})).get(base)
        except Exception:                                         # noqa: BLE001
            news = None
    earn = None
    try:
        from app.services.live_quote import live
        earn = ((await live(sym)) or {}).get("earnings")
    except Exception:                                             # noqa: BLE001
        pass
    events = []
    try:
        from app.services.econ_calendar import shape, raw_week
        events = shape(await raw_week(), impacts=("High",))
    except Exception:                                             # noqa: BLE001
        pass
    out = {"trend": tr, "hv": hv20(bars), "news": news, "earnings": earn, "events": events}
    cache.set(ck, out, 900)
    return out


def judge(k: dict, call: bool, S: float, dte: int, ctx: dict, expiry_iso: str) -> tuple[str, list[str], list[str]]:
    """حكمُ عقدٍ واحد: (المستوى، أسبابُ القبول، أسبابُ الحذر أو الامتناع)."""
    g = k.get("g")
    if not g:
        return "no", [], ["لا سعرَ صالحاً لهذا العقد الآن (لا طلبَ ولا عرضَ ولا صفقةً حديثة) — لا يُبنى عليه."]
    pros, cons, lvl = [], [], "ok"

    def down(to, why):
        nonlocal lvl
        cons.append(why)
        if to == "no" or (to == "warn" and lvl == "ok"):
            lvl = to
    px, oi, vol = g["px"], k.get("oi") or 0, k.get("volume") or 0
    if g["spread"] is not None and g["spread"] > 25:
        down("no", f"الفارقُ بين العرض والطلب {g['spread']:.0f}٪ من السعر — تخسره عند الدخول والخروج.")
    if oi < 50 and vol < 10:
        down("no", f"لا سيولة: العقودُ المفتوحة {oi} والكمّيةُ اليوم {vol} — قد لا تجد من يشتري منك.")
    if g["pop"] < 12:
        down("no", f"احتمالُ الربح عند الانتهاء نحو {g['pop']:.0f}٪ فقط — أقربُ إلى اليانصيب.")
    if dte <= 2 and abs(g["delta"]) < 0.2:
        down("no", f"ينتهي خلال {max(dte, 0)} يوم والدلتا {g['delta']:+.2f} — عقدٌ بعيدٌ عن السعر يتبخّر غالباً قبل أن يتحرّك السهم.")
    burn = -g["theta"] / (px * 100) if px > 0 and g["theta"] < 0 else 0
    if burn > 0.12:
        down("no", f"التآكلُ اليوميّ {-g['theta']:.2f} دولار للعقد = {burn * 100:.0f}٪ من قيمته كلَّ يوم — يذوب العقدُ في أيامٍ إن لم يتحرّك السهمُ فوراً.")
    elif burn > 0.05:
        down("warn", f"التآكلُ اليوميّ {-g['theta']:.2f} دولار للعقد = {burn * 100:.0f}٪ من قيمته كلَّ يوم.")
    tr, news = ctx.get("trend"), ctx.get("news")
    side, note = OP.direction(tr, news) if tr else (None, "")
    want = "call" if call else "put"
    if tr:
        if side and side != want:
            down("no" if (news or {}).get("strength", 0) >= 2 else "warn",
                 f"العقدُ {'شراء' if call else 'بيع'} والمسارُ {tr['state']}" + (f" والأخبارُ {news.get('impact')}" if news and news.get("impact") not in (None, "محايد") else "") + " — عكسُ الاتجاه.")
        elif side == want:
            pros.append(f"مع الاتجاه: المسارُ {tr['state']}" + (f" والخبرُ {news.get('impact')}" if news and news.get("impact") not in (None, "محايد") else "") + ".")
        else:
            down("warn", "المسارُ عرضيّ بلا اتجاه — الشراءُ المكشوف يخسر بالتآكل إن لم يتحرّك السهم.")
    hv = ctx.get("hv")
    if hv and g["iv"] / 100 > hv * 1.4:
        earn = ctx.get("earnings")
        if earn and earn[:10] <= expiry_iso:
            down("warn", f"التذبذبُ الضمنيّ {g['iv']:.0f}٪ فوق التاريخيّ {hv * 100:.0f}٪ والأرباحُ ({earn[:10]}) قبل الانتهاء — يهبط التذبذبُ بعدها فيخسر العقدُ ولو صدق الاتجاه.")
        else:
            down("warn", f"العقدُ غالٍ: تذبذبُه الضمنيّ {g['iv']:.0f}٪ فوق التاريخيّ {hv * 100:.0f}٪.")
    ev = [e for e in ctx.get("events") or [] if not e["past"] and e["at"][:10] <= expiry_iso]
    if ev and dte <= 7:
        down("warn", f"قبل الانتهاء حدثٌ اقتصاديٌّ عالي الأثر: {ev[0]['title']} ({ev[0]['day']} {ev[0]['riyadh'][-5:]} بتوقيت الرياض).")
    if 0.3 <= abs(g["delta"]) <= 0.65:
        pros.append(f"دلتا {g['delta']:+.2f}: يتحرّك مع السهم بقوّةٍ معقولة دون كلفةِ العقد العميق.")
    if dte >= 30:
        pros.append(f"أمامه {dte} يوماً — تآكلُه بطيء ويمنح السهمَ وقتاً.")
    if g["pop"] >= 35:
        pros.append(f"احتمالُ الربح عند الانتهاء نحو {g['pop']:.0f}٪ (تقديراً من التذبذب الضمنيّ).")
    return lvl, pros, cons


def card(k: dict, call: bool, S: float, dte: int, expiry: str, ctx: dict) -> dict:
    lvl, pros, cons = judge(k, call, S, dte, ctx, expiry)
    g = k.get("g") or {}
    return {"contract": k.get("contract"), "type": "call" if call else "put", "strike": k.get("strike"), "expiry": expiry, "dte": dte,
            "cost": round((g.get("px") or 0) * 100, 2), "px_src": g.get("src"), "g": g, "oi": k.get("oi"), "volume": k.get("volume"),
            "verdict": lvl, "verdict_ar": VERDICT[lvl], "pros": pros, "cons": cons,
            "need_pct": round(((g.get("be") or S) / S - 1) * 100 * (1 if call else -1), 1) if g else None}


def _score(c: dict) -> float:
    g = c["g"] or {}
    d = abs(g.get("delta") or 0)
    burden = -(g.get("theta") or 0) / max(c["cost"], 1)
    return (g.get("pop") or 0) + (8 if 0.3 <= d <= 0.65 else 0) + min(c["oi"] or 0, 5000) / 500 + (5 if c["dte"] >= 30 else 0) \
        - burden * 300 - (12 if c["verdict"] == "warn" else 0)


def pick_expiries(exps: list[dict]) -> list[dict]:
    """آجالٌ تمثّل المدى: الأقربُ بعد أسبوع، ونحو شهر، وشهرين، وأربعة، وثمانية، وسنة."""
    out = []
    for target in (7, 30, 60, 120, 240, 365):
        cand = [e for e in exps if e["dte"] >= min(target, 7)]
        if cand:
            e = min(cand, key=lambda x: abs(x["dte"] - target))
            if e not in out:
                out.append(e)
    return out


async def analyze(symbol: str, budget: float | None = None, expiry: int | None = None, contract: str | None = None,
                  side: str | None = None, with_summary: bool = True) -> dict:
    """التحليلُ الذكيّ: الاتجاهُ والسياق، والأنسبُ في كلّ أجلٍ ضمن الميزانية، وما يُمتنع عنه ولماذا — أو حكمُ عقدٍ بعينه."""
    from app.services.options_chain import chain, parse_option
    sym = str(symbol or "").upper()
    one = parse_option(contract) if contract else None
    if one:
        sym = one["root"]
    base = await chain(sym)
    if not base or not base.get("price"):
        return {"symbol": sym, "error": "لا سلسلةَ خياراتٍ لهذا الرمز."}
    S = float(base["price"])
    ctx = await _context(sym)
    tr, news = ctx.get("trend"), ctx.get("news")
    lean, why = OP.direction(tr, news) if tr else (None, "لا شموعَ كافيةً للحكم على المسار.")
    head = {"symbol": sym, "price": S, "trend": tr, "news": news, "hv": round(ctx["hv"] * 100, 1) if ctx.get("hv") else None,
            "earnings": ctx.get("earnings"), "lean": lean, "lean_note": why,
            "events": [e for e in ctx.get("events") or [] if not e["past"]][:4]}
    exps = base.get("expirations") or []

    # ── حكمُ عقدٍ بعينه ──
    if one:
        e = next((x for x in exps if x["date"] == one["expiry"]), None)
        ch = await chain(sym, e["t"]) if e else None
        row = next((r for r in (ch or {}).get("calls" if one["type"] == "call" else "puts") or [] if abs((r.get("strike") or 0) - one["strike"]) < 1e-6), None)
        if not row:
            return {**head, "contract": None, "error": "العقدُ غيرُ موجودٍ في السلسلة الآن (انتهى أو لا تداولَ عليه)."}
        S1 = float(ch.get("price") or S)
        enrich_rows([row], S1, e["dte"], one["type"] == "call")
        c = card(row, one["type"] == "call", S1, e["dte"], e["date"], ctx)
        if budget and c["cost"] > budget:
            c["cons"].append(f"كلفتُه {c['cost']:,.0f} دولار فوق ميزانيتك {budget:,.0f}.")
            if c["verdict"] == "ok":
                c.update(verdict="warn", verdict_ar=VERDICT["warn"])
        return {**head, "contract": c}

    # ── الأنسبُ في السلسلة ──
    sides = [side] if side in ("call", "put") else ([lean] if lean else ["call", "put"])
    targets = [x for x in exps if x["t"] == expiry] if expiry else pick_expiries(exps)
    chains = await asyncio.gather(*(chain(sym, e["t"]) for e in targets))
    cards = []
    for e, ch in zip(targets, chains):
        if not ch:
            continue
        S1 = float(ch.get("price") or S)
        ref = OP.atm_iv(ch, S1, max(e["dte"], 0.5) / 365)
        for sd in sides:
            rows = [r for r in (ch["calls"] if sd == "call" else ch["puts"]) if r.get("strike") and 0.5 * S1 <= r["strike"] <= 1.6 * S1]
            enrich_rows(rows, S1, e["dte"], sd == "call")
            for r in rows:
                g = r.get("g")
                if not g or (ref and not (OP.IV_BAND[0] * ref <= g["iv"] / 100 <= OP.IV_BAND[1] * ref)) or g["px"] < OP.MIN_PX:
                    continue
                cards.append(card(r, sd == "call", S1, e["dte"], e["date"], ctx))
    usable = [c for c in cards if c["verdict"] != "no"]
    within = [c for c in usable if not budget or c["cost"] <= budget]
    within.sort(key=_score, reverse=True)
    best, seen = [], set()
    for c in within:                                              # أجلٌ واحدٌ لكلّ توصيةٍ — تنويعُ المدى
        if c["expiry"] in seen:
            continue
        seen.add(c["expiry"])
        best.append(c)
        if len(best) >= 3:
            break
    refused = sorted([c for c in cards if c["verdict"] == "no" and (not budget or c["cost"] <= budget)], key=lambda c: -(c["g"] or {}).get("pop", 0))[:3]
    fit = None
    if budget and not within:
        low = min((c["cost"] for c in usable), default=None)
        nm = sym.lstrip("^")
        fit = {"ok": False, "min_cost": low,
               "text": (f"ميزانيةُ {budget:,.0f} دولار لا تكفي لعقدٍ معقولٍ على {nm}: أرخصُ عقدٍ مقبولٍ كلفتُه {low:,.0f} دولار."
                        if low else f"لا عقدَ مقبولاً على {nm} الآن ضمن هذه الشروط.")}
        alt = ALT.get(sym)
        if alt:
            alt_res = await analyze(alt, budget=budget, side=side, with_summary=False)
            if alt_res.get("best"):
                b = alt_res["best"][0]
                fit["alt"] = {"symbol": alt, "card": b, "text": f"تأخذه على {alt}: {b['contract']} بكلفة {b['cost']:,.0f} دولار ({b['verdict_ar']})."}
            else:
                lo2 = (alt_res.get("fit") or {}).get("min_cost")
                fit["alt_none"] = f"ولا تكفي على {alt} أيضاً" + (f": أرخصُ عقدٍ مقبولٍ عليه {lo2:,.0f} دولار." if lo2 else ".")
        if "alt" not in fit:
            lab = (OP.cached(budget) or {}).get("picks") or []
            if lab:
                fit["lab"] = [{"symbol": p["symbol"], "contract": p["contract"], "cost": p["cost"], "pop": p["pop"]} for p in lab[:3]]
    elif budget:
        fit = {"ok": True, "text": f"ميزانيةُ {budget:,.0f} دولار تكفي على {sym.lstrip('^')}."}
    # المسارُ عرضيٌّ بلا خبرٍ يحسمه: النصيحةُ الامتناعُ عن الشراء المكشوف — وما بقي يُعرض «إن أصررت» لا «الأنسب»
    abstain = None if lean or not tr else ("المسارُ عرضيٌّ بلا اتجاهٍ ولا خبرٍ يحسمه — لا أنصح بشراء عقدٍ مكشوفٍ الآن؛ "
                                            "التآكلُ يأكل قيمتَه إن لم يتحرّك السهم. وإن أصررت فهذه أقلُّها سوءاً.")
    if abstain and not best:
        abstain = abstain.split(" وإن أصررت")[0]
    res = {**head, "best": best, "refused": refused, "fit": fit, "budget": budget, "scanned": len(cards), "abstain": abstain,
           "expiries": [e["date"] for e in targets], "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    res["summary"] = await summary(res) if with_summary else None
    return res


SUM = """أنت مستشارُ خياراتٍ أمريكيّ. اكتب للمستثمر خلاصةً عربيةً فصيحةً في ثلاث جملٍ قصيرة من الحقائق أدناه وحدها (لا تضف رقماً ولا خبراً):
ما الاتجاه، وما الأنسبُ ولماذا، وما الخطرُ الأهمّ. إن لم يكن عقدٌ مناسب فقل ذلك صراحةً. نصٌّ فقط بلا عناوين.

"""


async def summary(res: dict) -> str | None:
    """خلاصةُ النموذج من الحقائق المحسوبة وحدها — مخبّأةٌ ربعَ ساعة؛ وNone إن تعذّر (فتكفي الحقائق)."""
    import httpx
    from app.services import cache
    from app.core.config import settings
    facts = {"symbol": res["symbol"], "price": res["price"], "trend": (res.get("trend") or {}).get("state"), "lean": res.get("lean"),
             "news": (res.get("news") or {}).get("event"), "hv": res.get("hv"), "earnings": res.get("earnings"),
             "events": [e.get("title") for e in res.get("events") or []][:2], "budget": res.get("budget"),
             "best": [{k: c[k] for k in ("contract", "cost", "dte", "verdict_ar")} | {"pop": (c["g"] or {}).get("pop"), "delta": (c["g"] or {}).get("delta"),
                      "cons": c["cons"][:2]} for c in res.get("best") or []],
             "refused": [{"contract": c["contract"], "why": c["cons"][:1]} for c in res.get("refused") or []][:2],
             "fit": (res.get("fit") or {}).get("text"), "abstain": res.get("abstain")}
    import hashlib
    import json as _j
    key = "optadv:sum:" + hashlib.md5(_j.dumps(facts, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    hit = cache.get(key)
    if hit is not None:
        return hit
    if not settings.AI_API_KEY:
        return None
    try:
        from app.services.usage_tracker import can_call, record
        if not can_call("gemini"):
            return None
        record("gemini")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}"
        body = {"contents": [{"parts": [{"text": SUM + _j.dumps(facts, ensure_ascii=False)}]}], "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400}}
        async with httpx.AsyncClient(timeout=40) as c:
            r = await c.post(url, json=body)
        if r.status_code != 200:
            return None
        txt = (r.json()["candidates"][0]["content"]["parts"][0]["text"] or "").strip()[:700]
    except Exception as e:                                        # noqa: BLE001
        logger.debug("التحليلُ الذكيّ/الخلاصة: {}", type(e).__name__)
        return None
    cache.set(key, txt, 900)
    return txt
