"""حلولُ المستشار (D568) — لا تحليلٌ فقط: بديلٌ أفضل، ومحفظةٌ أقلُّ عدداً تكتفي بالقيادية.

قال المالك: «أريد أن تكون لديه القدرةُ على الحلّ وليس التحليل فقط — مثلاً استبدالُها بشركةٍ أفضل،
أو تقليلُ عدد الشركات في المحفظة والاكتفاءُ بالقيادية».

  · **البديل** — من القطاع نفسِه، شرعيٌّ إن كانت شركتُه شرعية، وقرارُ التطبيق فيه «شراء»، ودرجتُه
    المركّبة أعلى بفارقٍ واضح. والريتُ يُستبدل بريتٍ أعمقَ خصماً على صافي أصوله بعائدٍ لا يقلّ.
  · **التركيز** — يُرتَّب كلُّ مركزٍ بدرجةٍ مركّبة (الجودةُ المالية، وقرارُ التطبيق، والفجوةُ عن
    السعر العادل، والعائد، والحجم). القياديةُ تبقى، والذيلُ (وزنٌ صغيرٌ وجودةٌ أدنى أو قرارٌ غيرُ شراء
    أو غيرُ شرعيّ) يُخرَج حتى العدد المطلوب، وتُوزَّع أوزانُ الخارجين على الباقين بنسبة أوزانهم.
كلُّ ذلك محسوبٌ هنا، والنموذجُ يشرحه ولا يغيّره.
"""
from __future__ import annotations

import re

LEADER_CAP = 10e9          # عشرةُ مليارات ريال فأكثر — قياديةٌ بحجمها


def _dec_score(d) -> float:
    d = str(d or "")
    return 100 if "شراء" in d else 10 if any(w in d for w in ("تجنّب", "تجنب", "بيع", "رفض")) else 55


def quality(r: dict) -> float:
    """درجةٌ مركّبة 0–100 من صفّ الفرز: الجودةُ المالية 45٪، والقرار 25٪، والفجوة 15٪، والعائد 15٪."""
    fin = r.get("finance_score")
    fin = float(fin) if isinstance(fin, (int, float)) else 50.0
    up = r.get("fair_value_upside_pct")
    up = max(-30.0, min(40.0, float(up))) if isinstance(up, (int, float)) else 0.0
    dy = r.get("dividend_yield")
    dy = max(0.0, min(8.0, float(dy))) if isinstance(dy, (int, float)) else 0.0
    return round(0.45 * fin + 0.25 * _dec_score(r.get("decision")) + 0.15 * (up + 30) / 70 * 100 + 0.15 * dy / 8 * 100, 1)


def _sharia_ok(v) -> bool:
    return str(v or "").upper() in ("COMPLIANT", "متوافق", "نقي", "شرعي") or "متوافق" in str(v or "")


def _rows() -> list[dict]:
    try:
        from app.services.market_screener import get_cached_screener
        return get_cached_screener() or []
    except Exception:                                             # noqa: BLE001
        return []


def _cap(sym: str, r: dict) -> float | None:
    try:
        from app.services.tadawul_market import row_for
        from app.services.tasi_stars import _cap as cap
        return cap(sym, row_for(sym) or r)
    except Exception:                                             # noqa: BLE001
        return None


def alternatives(sym: str, rows: list[dict] | None = None, n: int = 3, margin: float = 8.0) -> list[dict]:
    """بدائلُ أفضلُ من القطاع نفسه — شرعيةٌ إن كانت الشركةُ شرعية، و«شراء»، ودرجتُها أعلى بـ`margin`."""
    rows = rows if rows is not None else _rows()
    me = next((r for r in rows if str(r.get("symbol")) == str(sym)), None)
    if not me or not me.get("sector"):
        return []
    q0 = quality(me)
    halal = _sharia_ok(me.get("sharia"))
    out = []
    for r in rows:
        s = str(r.get("symbol"))
        if s == str(sym) or r.get("sector") != me.get("sector") or "شراء" not in str(r.get("decision") or ""):
            continue
        if halal and not _sharia_ok(r.get("sharia")):
            continue
        q = quality(r)
        if q >= q0 + margin:
            out.append({"symbol": s, "name": r.get("name"), "price": r.get("price"), "decision": r.get("decision"),
                        "fin": r.get("finance_score"), "upside": r.get("fair_value_upside_pct"),
                        "dy": r.get("dividend_yield"), "pe": r.get("pe_ratio") or r.get("pe"), "roe": r.get("roe"),
                        "quality": q, "vs": round(q - q0, 1)})
    return [{**x, "base_quality": q0} for x in sorted(out, key=lambda x: -x["quality"])[:n]]


def reit_alternatives(own: dict, peers: list[dict], n: int = 3) -> list[dict]:
    """ريتٌ أعمقُ خصماً (15 نقطةً فأكثر) بعائدٍ لا يقلّ ولا هبوطٍ في صافي أصوله."""
    prem, y = own.get("premium"), own.get("yield") or 0
    if prem is None:
        return []
    c = [p for p in peers if not p.get("self") and p["premium"] <= prem - 15 and (p.get("yield") or 0) >= y
         and (p.get("nav_change") is None or p["nav_change"] >= -2)]
    return sorted(c, key=lambda p: p["premium"])[:n]


def swap(value: float, alt_price: float | None) -> dict:
    """مبلغُ البيع يُنقل كاملاً إلى البديل — بأسهمٍ صحيحة."""
    import math
    return {"amount": round(value, 2), "shares": int(math.floor(value / alt_price)) if alt_price else 0}


def wanted_count(question: str, default: int = 10) -> int:
    """«أكتفي بثماني شركات» · «قلّلها إلى 8» — وإلا العددُ الافتراضيّ."""
    words = {"خمس": 5, "ست": 6, "سبع": 7, "ثمان": 8, "تسع": 9, "عشر": 10, "احدى عشر": 11, "اثنتي عشر": 12, "اثنا عشر": 12}
    m = re.search(r"\b(\d{1,2})\b", question or "")
    if m and 3 <= int(m.group(1)) <= 30:
        return int(m.group(1))
    for w, v in sorted(words.items(), key=lambda kv: -len(kv[0])):
        if w in (question or ""):
            return v
    return default


def consolidate(items: list[dict], rows: list[dict], keep_n: int, capital: float) -> dict:
    """خطةُ التركيز: من يبقى ومن يخرج، وأوزانُ الباقين الجديدة، وما يُثبَّت من ربحٍ أو خسارة.

    `items`: صفوفُ التوزيع النسبي (symbol, name, market_value, target_weight, current_weight) + invested."""
    by = {str(r.get("symbol")): r for r in rows}
    scored = []
    items = [it for it in items if float(it.get("market_value") or 0) > 0]      # مراكزُ مُغلقة لا تُعدّ
    for it in items:
        s = str(it["symbol"])
        r = by.get(s, {})
        cap = it.get("cap") if it.get("cap") is not None else _cap(s, r)
        q = quality(r) if r else 40.0
        # القياديةُ بحجمها في السوق — لا بقرار التطبيق (قِيس: اشتراطُ «شراء» أخرج الاتصالاتِ والحبيب)
        leader = bool(cap and cap >= LEADER_CAP)
        scored.append({**it, "quality": q, "cap": cap, "leader": leader, "decision": r.get("decision"),
                       "halal": _sharia_ok(r.get("sharia")) if r.get("sharia") is not None else None,
                       "sector": r.get("sector")})
    # الترتيب: غيرُ الشرعيّ أوّلاً للخروج، ثمّ الأدنى درجةً؛ والقياديةُ لا تخرج إلا إن لم يبقَ غيرُها
    order = sorted(scored, key=lambda x: (x["halal"] is not False, x["leader"], x["quality"]))
    exits, keep = [], list(scored)
    for x in order:
        if len(keep) <= keep_n:
            break
        if x["leader"] and any(not k["leader"] for k in keep if k is not x):
            continue
        keep.remove(x)
        exits.append(x)
    for x in exits:
        x["note"] = ("غيرُ شرعية" if x["halal"] is False else
                     "جودتُها عالية لكنها ليست قيادية — خروجُها ثمنُ الاكتفاء بالقيادية" if x["quality"] >= 80 and not x["leader"]
                     else "الأدنى درجةً بين غير القيادية")
    freed_w = sum(float(x.get("target_weight") or 0) for x in exits)
    base_w = sum(float(k.get("target_weight") or 0) for k in keep) or 1.0
    for k in keep:
        tw = float(k.get("target_weight") or 0)
        k["new_target"] = round(tw + freed_w * tw / base_w, 2)
    proceeds = sum(float(x.get("market_value") or 0) for x in exits)
    realized = sum(float(x.get("market_value") or 0) - float(x.get("invested") or x.get("market_value") or 0) for x in exits)
    return {"before": len(items), "after": len(keep), "keep": sorted(keep, key=lambda k: -k["quality"]),
            "exits": exits, "proceeds": round(proceeds, 2), "realized": round(realized, 2),
            "freed_weight": round(freed_w, 2), "sectors_after": sorted({k.get("sector") for k in keep if k.get("sector")})}


def swap_verdict(f: dict, st: dict, held: set[str]) -> dict | None:
    """حكمُ الاستبدال حين يُسأل عن بديل — محسوبٌ لا مستنتج (قِيس: قال النموذجُ «يوجد بديلٌ أفضل» و«ابقَ» معاً).

    يُستبدل إن كانت الشركةُ ضعيفة (الموقفُ «استبدل»)، أو تفوّق البديلُ بـ25 درجةً فأكثر؛ وإلا فالبقاءُ مع شرطٍ يقلب الحكم."""
    alts = f.get("alternatives") or []
    if not alts:
        return {"الحكم": "لا بديلَ أفضلَ في قطاعها بمعايير التطبيق — البقاءُ هو الحلّ", "البديل": None}
    b = alts[0]
    gap = round((b.get("quality") or 0) - (b.get("base_quality") or 0), 1)
    cost = None
    if f.get("held") and f.get("value") and f.get("invested"):
        pnl = f["value"] - f["invested"]
        cost = f"{'خسارة' if pnl < 0 else 'ربح'} {abs(pnl):,.0f} ريال تُثبَّت بالبيع"
    owned = str(b.get("symbol")) in held
    if st.get("action") == "استبدل" or gap >= 25:
        v = f"استبدل: {b.get('name')} أعلى بـ{gap} درجة"
    else:
        v = (f"احتفظ الآن: {b.get('name')} أعلى بـ{gap} درجة، لكنّ الفارق دون حدّ التبديل (25) وقرارُ التطبيق "
             f"لـ{f.get('name')} {f.get('decision') or 'غير متوفّر'}؛ ويصبح التبديلُ هو الحلّ إن خيّبت النتائجُ القادمة")
    return {"الحكم": v, "البديل": {k: b.get(k) for k in ("symbol", "name", "quality", "base_quality", "decision", "fin", "upside", "dy", "pe")},
            "فارق الدرجة": gap, "كلفة التبديل": cost,
            "تملكه أصلاً": ("نعم — رفعُ وزنه يكون بتعديل هدفه في التوزيع النسبي، وتركيزُه يزيد" if owned else "لا")}
