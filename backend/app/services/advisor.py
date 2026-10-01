"""مستشارُ المحفظة (D567) — صقرٌ يجيب كما يجيب المستشارُ الماليّ، من ملفِّ قرارٍ يُبنى تلقائياً.

قال المالك: «بدلاً من أن أسألك كلَّ مرّة، أجعل التطبيقَ يجاوبني مثلك … مديرٌ استشاريٌّ للمحفظة
ومساعدٌ استثماريٌّ من الطراز الأول يقرأ الملفّات بصرياً … والدفعاتُ تتغيّر مع الوقت وبعضُها يكتمل
والبعضُ لا — يجب أن يكون متواكباً مع الزمن والمحفظة والتفاصيل الجديدة».

فالمستشارُ طبقتان:
  · **ملفُّ القرار** (حتميّ) — ما جمعتُه يدوياً في الإجابات: مركزُ المالك ووزنُه من رأس المال
    (القيمةُ السوقية + السيولة) وهدفُه والمتبقّي، ومشترياتُه الأخيرة، والقرارُ والسعرُ العادل
    والفنيّ، ونموذجُ الأبحاث، وما قرأه القارئُ البصريُّ من الملفّات، والريتُ بصافي أصوله
    وأقرانه، ومؤتمراتُ المحلّلين، وموعدُ النتائج القادمة.
  · **الموقف** (حتميّ) — الإجراءُ والدفعاتُ وشروطُها محسوبةٌ هنا بالقواعد، من الحالة **الآن**:
    المتبقّي يُعاد حسابُه من المركز الحيّ، فما نُفّذ من دفعاتٍ يُطرح وحده، وما لم يُنفَّذ يبقى.
  · ثمّ **الصياغة** — النموذجُ يكتب بصوت المستشار من الملفّ والموقف، ويُمنع من مخالفة أرقامهما.
    وإن تعذّر النموذجُ كُتب الجوابُ من الموقف نفسِه بلا صياغةٍ أدبية — فلا يصمت المستشار.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta

from loguru import logger

# ── النيّة: سؤالُ قرارٍ لا سؤالُ معلومة ─────────────────────────────────────
_ACT = ("اضخ", "أضخ", "اضيف", "أضيف", "اضف", "أضف", "اشتري", "أشتري", "اشتر", "أشتر", "ابيع", "أبيع",
        "اخفف", "أخفف", "خفف", "استبدل", "أستبدل", "ابدل", "أبدل", "بدل", "اغير", "أغير", "اغيره", "أغيره",
        "انتظر", "أنتظر", "احتفظ", "أحتفظ", "احذف", "أحذف", "اعزز", "أعزز", "ادخل", "أدخل",
        "ماذا افعل", "ماذا أفعل", "وش اسوي", "ايش اسوي", "شو اسوي", "نصيحتك", "تنصحني", "رايك", "رأيك",
        "هل يجوز", "يستاهل", "مستشار", "توصيتك", "قرارك", "اضخ فيه", "ضخ")


def intent(question: str) -> bool:
    """أهو سؤالُ قرارٍ استثماريّ (أضخّ/أبيع/أستبدل/أنتظر/ماذا أفعل)؟"""
    q = (question or "").replace("ـ", "")
    return any(w in q for w in _ACT)


_ASK = ("؟", "?", "هل ", "ام ", "أم ", "او ", "أو ", "ماذا", "وش ", "ايش", "شو ", "رايك", "رأيك", "تنصح",
        "نصيحتك", "يجوز", "يستاهل", "افضل", "أفضل", "اسوي", "أسوي")


def asks(question: str) -> bool:
    """سؤالُ رأيٍ (هل/أم/ماذا/؟) — لا أمرُ تنفيذ («بِع لي»)."""
    q = f" {question or ''} "
    return any(w in q for w in _ASK)


def companies(question: str, ctx: dict, limit: int = 2) -> list[dict]:
    """الشركاتُ المذكورة — الحيازاتُ أوّلاً ثمّ السوق، بلا تكرارٍ ولا تداخل (لمقارنة «أ أم ب»)."""
    from app.services.ai_chat import _mentions
    from app.services.ai_chat_rules import _n
    q = _n(question or "")
    found: dict[str, dict] = {}

    def score(name):
        key = _n(str(name or ""))
        return len(key) + 100 if key and key in q else max(
            [len(t) for t in key.split() if len(t) >= 4 and t in q] or [0])

    for h in ((ctx.get("المحفظة") or {}).get("المراكز") or []):
        s, n = str(h.get("الرمز") or ""), h.get("الشركة")
        if s and _mentions(question, n, s):
            found[s] = {"symbol": s, "name": n, "score": score(n) + 5}
    try:
        from app.services.market_screener import get_cached_screener
        for r in get_cached_screener() or []:
            s, n = str(r.get("symbol") or ""), r.get("name")
            if s and s not in found and _mentions(question, n, s):
                found[s] = {"symbol": s, "name": n, "score": score(n)}
    except Exception:                                             # noqa: BLE001
        pass
    for m in re.findall(r"\b(\d{4})\b", question or ""):
        found.setdefault(m, {"symbol": m, "name": m, "score": 200})
    out = sorted(found.values(), key=lambda x: -x["score"])
    return out[:limit]


# ── ملفُّ القرار ───────────────────────────────────────────────────────────
def _f(x):
    try:
        return None if x is None else float(x)
    except (TypeError, ValueError):
        return None


def results_due(as_of: str | None, today: date | None = None) -> str | None:
    """موعدُ إعلان النتائج القادمة: الأوّليةُ خلال 30 يوماً من نهاية الربع، والسنويةُ خلال 90 (هيئة السوق)."""
    today = today or date.today()
    try:
        q = date.fromisoformat(str(as_of)[:10])
    except (TypeError, ValueError):
        return None
    due = q + timedelta(days=90 if q.month == 12 else 30)
    return due.isoformat() if due >= today - timedelta(days=5) else None


async def dossier(db, symbol: str, name: str = "") -> dict:
    """كلُّ ما يعرفه التطبيقُ عن الشركة وعن مركز المالك فيها — مسطّحاً، وكلُّ مصدرٍ بحارسه."""
    sym = str(symbol).replace(".SR", "").strip()
    f: dict = {"symbol": sym, "name": name or sym}

    # مركزُ المالك ووزنُه — من بطاقة التوزيع النسبي نفسِها (القيمةُ السوقية + السيولة)
    try:
        from app.api.v1.endpoints.allocation import get_allocation
        res = await get_allocation(db)
        d = (json.loads(res.body) if hasattr(res, "body") else res)["data"]
        f["capital"] = d.get("investable")
        f["cash"] = d.get("available_cash")
        for it in d.get("items") or []:
            if str(it.get("symbol")) == sym:
                f.update({"held": True, "value": it.get("market_value"), "weight": it.get("current_weight"),
                          "target": it.get("target_weight") or None, "remaining": it.get("total_amount"),
                          "name": it.get("name") or f["name"]})
    except Exception as e:                                        # noqa: BLE001
        logger.debug("advisor alloc {}: {}", sym, e)
    try:
        from sqlalchemy import select
        from app.models.portfolio import Company, Holding
        from app.models.transaction import Transaction
        row = (await db.execute(select(Holding.quantity, Holding.average_cost, Holding.invested_amount,
                                       Holding.unrealized_profit_pct, Holding.total_dividends_received, Company.id)
                                .join(Company, Holding.company_id == Company.id)
                                .where(Company.symbol == sym))).first()
        if row:
            f.update({"held": True, "qty": _f(row[0]), "avg_cost": _f(row[1]), "invested": _f(row[2]),
                      "pnl_pct": _f(row[3]), "divs": _f(row[4])})
            since = datetime.now() - timedelta(days=120)
            tx = (await db.execute(select(Transaction.executed_at, Transaction.transaction_type,
                                          Transaction.quantity, Transaction.price)
                                   .where(Transaction.company_id == row[5], Transaction.executed_at >= since)
                                   .order_by(Transaction.executed_at.desc()))).all()
            f["recent"] = [{"date": str(t[0])[:10], "type": getattr(t[1], "value", str(t[1])),
                            "qty": _f(t[2]), "price": _f(t[3])} for t in tx][:8]
    except Exception as e:                                        # noqa: BLE001
        logger.debug("advisor holding {}: {}", sym, e)

    # محرّكاتُ التطبيق
    try:
        from app.services.analysis import analyze_company
        a = await analyze_company(f"{sym}.SR", f["name"], db=db) or {}
        fu, t = a.get("fundamentals") or {}, a.get("technical") or {}
        dec = a.get("decision") or {}
        f.update({"price": _f(a.get("price")), "decision": dec.get("label"), "decision_reason": dec.get("reason"),
                  "fv": _f(a.get("fair_value")), "fv_conf": a.get("fair_value_conf"), "upside": _f(a.get("fair_value_upside_pct")),
                  "fin": (a.get("financial") or {}).get("score"), "fin_verdict": (a.get("financial") or {}).get("verdict"),
                  "rsi": _f(t.get("rsi")), "support": _f(t.get("support")), "resistance": _f(t.get("resistance")),
                  "trend": t.get("trend"), "sma200": _f(t.get("mean_basis")), "vs_sma200": _f(t.get("pct_from_avg")),
                  "pe": _f(fu.get("pe_ratio")), "dy": _f(fu.get("dividend_yield")), "roe": _f(fu.get("roe")),
                  "eps_g": _f(fu.get("earnings_growth")), "w52_low": _f(fu.get("week52_low")),
                  "w52_high": _f(fu.get("week52_high")), "sharia": a.get("sharia_status") or None})
        f["name"] = a.get("name") or f["name"]
    except Exception as e:                                        # noqa: BLE001
        logger.debug("advisor analysis {}: {}", sym, e)

    # نموذجُ الأبحاث — النموُّ ونطاقُ المكرّر وتوقّعُ الربع وتاريخُ السهم
    try:
        from app.services.research_model import note
        n = note(sym, f.get("price")) or {}
        g, p, pb = n.get("growth") or {}, n.get("price") or {}, n.get("pe_band") or {}
        f.update({"rev_cagr": g.get("rev_cagr"), "ni_cagr": g.get("ni_cagr"), "years": g.get("years"),
                  "price_cagr": p.get("cagr"), "tasi_cagr": p.get("tasi_cagr"), "max_dd": p.get("max_dd"),
                  "div_hist": p.get("div"), "pe_band": {k: pb.get(k) for k in ("low", "median", "high", "current")} if pb else None})
        fc = (n.get("forecast") or {}).get("net_income_parent") or (n.get("forecast") or {}).get("bank_nfi")
        if fc:
            f["next_q"] = {"as_of": fc.get("as_of"), "net_income": fc.get("value"), "mape": fc.get("mape")}
            f["results_due"] = results_due(fc.get("as_of"))
    except Exception as e:                                        # noqa: BLE001
        logger.debug("advisor research {}: {}", sym, e)

    # ما قرأه القارئُ البصريّ من ملفّات الشركة
    try:
        from app.services.file_reader import coverage, knowledge
        f["files"] = knowledge(sym, 14)
        f["files_cov"] = coverage(sym)
    except Exception:                                             # noqa: BLE001
        f["files"] = []

    # الريت: صافي الأصول والتوزيعات، وأقرانُه
    try:
        from app.services.statement_merge import archetype_of
        if archetype_of(sym) == "reit":
            f["is_reit"] = True
            from app.services.reit_advisor import cached, summarize
            raw = cached(sym)
            if raw:
                r = summarize(raw["dists"], raw.get("vals") or [], f.get("price"))
                f["reit"] = {k: r.get(k) for k in ("nav", "nav_date", "nav_change", "premium", "ttm", "yield",
                                                   "cadence_days", "next_expected", "overdue", "last_amount", "trend")}
                f["reit"]["nav_history"] = (r.get("nav_history") or [])[-6:]
            f["peers"] = _reit_peers(sym)
    except Exception as e:                                        # noqa: BLE001
        logger.debug("advisor reit {}: {}", sym, e)

    try:
        from app.services.investor_calls import lines
        f["calls"] = lines(sym)
    except Exception:                                             # noqa: BLE001
        f["calls"] = []
    return f


def _reit_peers(sym: str) -> list[dict]:
    from app.services import lastgood
    from app.services.reit_advisor import STORE, summarize
    from app.services.tadawul_market import row_for
    out = []
    for k in lastgood.keys_with_prefix("reit:"):
        s = k.split(":", 1)[1]
        raw = lastgood.load(k) or {}
        if not raw.get("dists"):
            continue
        px = (row_for(s) or {}).get("price")
        r = summarize(raw["dists"], raw.get("vals") or [], px)
        if r.get("nav") and r.get("premium") is not None and (date.today() - date.fromisoformat(r["nav_date"])).days <= 460:
            out.append({"symbol": s, "premium": r["premium"], "yield": r.get("yield"), "nav_change": r.get("nav_change"),
                        "self": s == sym})
    return sorted(out, key=lambda x: x["premium"])


# ── الموقف: الإجراءُ والدفعاتُ وشروطُها — بالقواعد، من الحالة الآن ───────────
def signals(f: dict) -> dict:
    files = " ".join(f.get("files") or [])
    reit = f.get("reit") or {}
    # الريتُ يُحكم بتوزيعه وصافي أصوله لا بصافي ربحه: ربحُه يتأرجح بإعادة تقييم العقار ومخصّصاته
    # (الراجحي ريت: ربحُ 2025 −21٪ والتوزيعُ مستقرٌّ صاعد وصافي الأصول +2.6٪)
    profit_down = ((reit.get("trend") == "هابط") or (reit.get("nav_change") is not None and reit["nav_change"] <= -5)) \
        if f.get("is_reit") else \
        ((f.get("eps_g") is not None and f["eps_g"] <= -15)
         or bool(re.search(r"(تراجع|انخفض|هبط)[^.]{0,20}صافي الربح", files)))
    s = {
        "profit_down": profit_down,
        "trend_down": f.get("trend") == "هابط",
        "oversold": f.get("rsi") is not None and f["rsi"] < 30,
        "overbought": f.get("rsi") is not None and f["rsi"] > 70,
        "at_low": bool(f.get("price") and f.get("w52_low") and f["price"] <= f["w52_low"] * 1.02),
        "pe_cheap": bool((f.get("pe_band") or {}).get("current") is not None and (f.get("pe_band") or {}).get("low") is not None
                         and f["pe_band"]["current"] <= f["pe_band"]["low"]),
        "app_buy": "شراء" in str(f.get("decision") or ""),
        "app_avoid": any(w in str(f.get("decision") or "") for w in ("تجنّب", "تجنب", "بيع", "رفض")),
        "auditor_flag": bool(re.search(r"متحفّظ|متحفظ|لفت انتباه|استمرارية", files)) and "غير متحفظ" not in files,
        "reit_deep_discount": bool((f.get("reit") or {}).get("premium") is not None and f["reit"]["premium"] <= -15),
        "reit_overdue": bool((f.get("reit") or {}).get("overdue")),
    }
    return s


def _shares(amount: float, price: float | None) -> int:
    return int(math.floor(amount / price)) if price and amount > 0 else 0


def stance(f: dict) -> dict:
    """الإجراءُ (أضف/انتظر/احتفظ/خفّف/راقب) والدفعاتُ بمبالغها وأسهمها وشروطها."""
    sg = signals(f)
    px = f.get("price")
    cap = f.get("capital") or 0
    noise = max(px or 0, cap * 0.002)
    rem = f.get("remaining")
    target_amt = (f.get("target") or 0) / 100 * cap if f.get("target") else None
    out: dict = {"signals": sg, "tranches": [], "stop_rules": []}
    due = f.get("results_due")
    res_cond = (f"بعد إعلان النتائج القادمة (متوقَّعةٌ حتى {due})" if due else "بعد إعلان النتائج القادمة") + \
        (" إن صمد التوزيعُ وصافي الأصول" if f.get("is_reit") else
         " إن توقّف تراجعُ الربح أو جاء عند توقّع التطبيق أو فوقه")

    if not f.get("held") and not f.get("target"):
        out["action"] = "راقب"
        out["why"] = "لا تملكها ولا وزنَ مستهدفاً لها — حدِّد وزنها في التوزيع النسبي أوّلاً إن أردت دخولها"
        return out
    if target_amt is not None and f.get("value") is not None and f["value"] - target_amt > noise:
        excess = f["value"] - target_amt
        out.update(action="خفّف", amount=round(excess, 2), shares=_shares(excess, px),
                   why=f"وزنُها {f.get('weight')}٪ فوق هدفها {f.get('target')}٪")
        return out
    if not rem or rem < noise:
        out.update(action="احتفظ", why="بلغت وزنَها المستهدف — لا إضافة")
        if sg["profit_down"]:
            out["stop_rules"].append("إن تكرّر تراجعُ الربح في النتائج القادمة فراجِع الهدفَ نفسَه")
        return out

    gated = sg["profit_down"] or sg["app_avoid"] or sg["auditor_flag"] or sg["reit_overdue"] or not sg["app_buy"]
    if f.get("is_reit"):
        nav = (f.get("reit") or {}).get("nav")
        deep = round(nav * 0.85, 2) if nav else None
        value_cond = f"عند خصمٍ 15٪ على صافي الأصول (نحو {deep})" if deep else "عند خصمٍ أعمق على صافي الأصول"
    else:
        lvl = round(px * 0.9, 2) if px else None
        value_cond = f"إن هبط السعرُ نحو {lvl} (−10٪) دون خفضٍ للتوزيع" if lvl else "عند هبوطٍ أعمق دون خفضٍ للتوزيع"
    reclaim = (f"أو ثبت السعرُ فوق متوسط 200 يوم ({f['sma200']})" if f.get("sma200") else "أو تحسّن الاتجاهُ الفنيّ")

    if gated:
        parts = [(0.34, res_cond), (0.33, "بعد تأكيد التحسّن في الربع التالي " + reclaim), (0.33, value_cond)]
        out["action"] = "انتظر الشرط ثمّ أضف على دفعات"
        out["why"] = "؛ ".join(w for w, on in (
            ("الربحُ يتراجع", sg["profit_down"]), ("قرارُ التطبيق ليس شراءً", not sg["app_buy"]),
            ("تحفّظٌ من المراجع", sg["auditor_flag"]), ("تأخّر توزيعُ الريت", sg["reit_overdue"])) if on)
    else:
        first = "الآن" + (" — السعرُ عند قاع 52 أسبوعاً بتشبّعٍ بيعيّ" if sg["at_low"] and sg["oversold"] else "")
        parts = [(0.5, first), (0.5, res_cond + " " + reclaim if sg["trend_down"] else value_cond + " أو " + res_cond)]
        out["action"] = "أضف على دفعتين"
        out["why"] = "قرارُ التطبيق شراءٌ ولا إشارةَ تحذير" + ("، والاتجاهُ هابطٌ فالتدرّجُ أسلم" if sg["trend_down"] else "")
    left = rem
    for i, (share, cond) in enumerate(parts):
        amt = left if i == len(parts) - 1 else round(rem * share, 2)
        left = round(left - amt, 2)
        out["tranches"].append({"n": i + 1, "amount": round(amt, 2), "shares": _shares(amt, px), "when": cond})
    out["remaining"] = round(rem, 2)
    out["remaining_shares"] = _shares(rem, px)
    out["stop_rules"] += [r for r, on in (
        ("توقّف عن الإضافة إن أُعلن خفضٌ للتوزيع", True),
        ("توقّف إن تكرّر تراجعُ الربح في النتائج القادمة", sg["profit_down"]),
        ("توقّف إن هبط صافي الأصول في التقييم القادم أو تأخّر التوزيع", bool(f.get("is_reit")))) if on]
    return out


def compare(a: dict, b: dict) -> list[dict]:
    """جدولُ المقارنة بين شركتين — الأفضلُ في كلّ بندٍ معلَّم."""
    rows = [("قرار التطبيق", "decision", None), ("العائد على حقوق الملكية٪", "roe", "hi"),
            ("عائد التوزيع٪", "dy", "hi"), ("مكرّر الربحية", "pe", "lo"), ("نموّ الربحية٪", "eps_g", "hi"),
            ("عائد السهم السنوي منذ 2010٪", "price_cagr", "hi"), ("الدرجة المالية", "fin", "hi"),
            ("الفجوة عن السعر العادل٪", "upside", "hi")]
    out = []
    for label, k, better in rows:
        va, vb = a.get(k), b.get(k)
        win = None
        if better and isinstance(va, (int, float)) and isinstance(vb, (int, float)) and va != vb:
            win = a["symbol"] if (va > vb) == (better == "hi") else b["symbol"]
        out.append({"بند": label, a["symbol"]: va, b["symbol"]: vb, "الأفضل": win})
    return out


def switch_cost(a: dict) -> str | None:
    """كلفةُ الاستبدال: بيعُ المركز الحاليّ يثبّت ربحَه أو خسارتَه."""
    if a.get("held") and a.get("pnl_pct") is not None and a.get("value"):
        pnl = a["value"] - (a.get("invested") or a["value"])
        return f"بيعُ {a['name']} يثبّت {'خسارة' if pnl < 0 else 'ربح'} {abs(pnl):,.0f} ريال ({a['pnl_pct']:+.1f}٪)"
    return None


# ── الصياغة ─────────────────────────────────────────────────────────────────
CHARTER = """أنت «صقر»، المستشارُ الماليُّ الخاصّ لمالك هذه المحفظة، بخبرة مدير صندوقٍ استثماريّ. تخاطبه مباشرةً.

منهجك (ملزم):
• ناقدٌ لا مجامل: قل ما لا يحبّ سماعه إن كانت الأرقامُ تقوله. افصل جودةَ الشركة عن جاذبية سهمها عند سعره.
• حجمُ المركز قبل «اشترِ»: انظر وزنه من رأس المال (القيمةُ السوقية + السيولة) مقابل هدفه والمتبقّي.
• «الموقف» المرفقُ محسوبٌ بقواعد التطبيق: **الإجراءُ والمبالغُ وعددُ الأسهم والشروطُ منه حرفياً** — لا تغيّرها ولا تخترع غيرها. مهمّتك أن تشرحها وتعلّلها من الملفّ.
• استند إلى ما قرأه التطبيقُ من ملفّات الشركة (بفتراتها) إن وُجد: ما الذي تغيّر، ولماذا، وهل التوزيعُ مغطّى. وإن لم يُقرأ شيءٌ فقل ذلك ولا تدّعِ قراءته.
• إن كانت المشترياتُ الأخيرة في الملفّ فاذكرها: ما نُفّذ وما بقي — الخطةُ تتواكب مع ما فعله.
• إن قارن بين شركتين فاحكم صريحاً، واذكر كلفةَ الاستبدال إن وُجدت.
• لا رقمَ من خارج الملفّ. ما لا تعرفه قُل «غير متوفّر».
• لا تحفيز ولا تهويل ولا عبارات تنصّل طويلة.

البنية (نصٌّ عربيٌّ نظيف، بلا رموز تنسيق ولا نجوم، والتعدادُ بـ«•»):
١) سطرٌ أوّل: القرارُ صريحاً.
٢) مركزك: الكمية والتكلفة والربح أو الخسارة، والوزنُ مقابل الهدف والمتبقّي.
٣) ما يطمئن، ثمّ ما يقلق — بأرقام الملفّ.
٤) الخطة: الدفعاتُ كما في الموقف (المبلغ، الأسهم، متى).
٥) متى يتغيّر رأيي: قواعدُ التوقّف.
واختم بسطرٍ واحد: «رأيٌ تحليليّ من بيانات التطبيق، والقرارُ لك.»"""


def render(fs: list[dict], sts: list[dict], cmp: list[dict] | None = None) -> str:
    """الجوابُ بلا نموذج — من الملفّ والموقف وحدهما (شبكةُ الأمان)."""
    out = []
    for f, st in zip(fs, sts):
        out.append(f"{f['name']} ({f['symbol']}): {st.get('action')} — {st.get('why', '')}")
        if f.get("held"):
            out.append(f"• مركزك: {(f.get('qty') or 0):g} سهماً بتكلفة {f.get('avg_cost')} — "
                       f"{(f.get('pnl_pct') or 0):+.1f}٪، ووزنه {f.get('weight')}٪ مقابل هدف {f.get('target')}٪")
        if f.get("recent"):
            r = f["recent"][0]
            out.append(f"• آخرُ عمليةٍ: {r['type']} {(r.get('qty') or 0):g} سهماً بسعر {r.get('price')} في {r['date']}")
        for t in st.get("tranches") or []:
            out.append(f"• الدفعة {t['n']}: {t['amount']:,.0f} ريال (نحو {t['shares']} سهماً) — {t['when']}")
        for s in st.get("stop_rules") or []:
            out.append(f"• {s}")
        for l in (f.get("files") or [])[:4]:
            out.append(f"• من الملفّات: {l}")
        out.append("")
    if cmp:
        a, b = fs[0]["symbol"], fs[1]["symbol"]
        wins = sum(1 for r in cmp if r["الأفضل"] == a), sum(1 for r in cmp if r["الأفضل"] == b)
        out.append(f"المقارنة: {fs[0]['name']} أفضل في {wins[0]} بنود، و{fs[1]['name']} في {wins[1]}.")
        sc = switch_cost(fs[0])
        if sc:
            out.append(f"• {sc}")
    out.append("رأيٌ تحليليّ من بيانات التطبيق، والقرارُ لك.")
    return "\n".join(out).strip()


async def answer(db, question: str, picked: list[dict], history: list | None = None) -> dict:
    import httpx
    from app.core.config import settings
    from app.services.usage_tracker import can_call, record
    fs = [await dossier(db, p["symbol"], p.get("name") or "") for p in picked]
    sts = [stance(f) for f in fs]
    cmp = compare(fs[0], fs[1]) if len(fs) == 2 else None
    fallback = render(fs, sts, cmp)
    if not settings.AI_API_KEY or not can_call("gemini"):
        return {"reply": fallback, "grounded": True, "source": "advisor-rules"}
    pack = {"ملفّات القرار": fs, "الموقف المحسوب": sts, "اليوم": date.today().isoformat()}
    if cmp:
        pack["المقارنة"] = cmp
        pack["كلفة الاستبدال"] = switch_cost(fs[0])
    convo = "".join(f"\n{'المالك' if m.get('role') == 'user' else 'صقر'}: {m.get('content', '')}"
                    for m in (history or [])[-6:])
    prompt = (f"{CHARTER}\n\n=== ملفّ القرار (مصدرك الوحيد) ===\n"
              f"{json.dumps(pack, ensure_ascii=False, default=str)}\n=== نهاية الملفّ ===\n"
              f"{('المحادثة السابقة:' + convo) if convo else ''}\n\nسؤال المالك: {question}\n\nجوابك:")
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}")
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=40) as c:
            r = await c.post(url, json={"contents": [{"parts": [{"text": prompt}]}],
                                        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 1800}})
        if r.status_code != 200:
            logger.warning("advisor: HTTP {}", r.status_code)
            return {"reply": fallback, "grounded": True, "source": "advisor-rules"}
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = re.sub(r"[٠-٩]", lambda m: str(ord(m.group()) - 0x0660), text)
        from app.services.ai_chat import _strip_markup
        return {"reply": _strip_markup(text), "grounded": True, "source": "advisor"}
    except Exception as e:                                        # noqa: BLE001
        logger.warning("advisor: {}", type(e).__name__)
        return {"reply": fallback, "grounded": True, "source": "advisor-rules"}
