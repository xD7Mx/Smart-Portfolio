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


_PORT = ("قلل عدد", "أقلل عدد", "اقلل عدد", "قلّل", "تقليل عدد", "اكتفي", "أكتفي", "الاكتفاء", "القيادية", "القياديه",
         "تخلص", "أتخلص", "اتخلص", "ركز المحفظة", "تركيز المحفظة", "رتب المحفظة", "ترتيب المحفظة", "اعادة هيكلة", "إعادة هيكلة",
         "اضعف شركات", "أضعف شركات", "الشركات الضعيفة")
_ALT = ("بديل", "بدائل", "افضل منها", "أفضل منها", "افضل منه", "أفضل منه", "شركة افضل", "شركة أفضل", "استبدل", "أستبدل", "ابدل", "أبدل")


def portfolio_intent(question: str) -> bool:
    """سؤالٌ عن المحفظة كلِّها: تقليلُ العدد والاكتفاءُ بالقيادية، أو التخلّصُ من الضعيفة."""
    q = (question or "").replace("ـ", "")
    return any(w in q for w in _PORT)


def wants_alternatives(question: str) -> bool:
    q = (question or "").replace("ـ", "")
    return any(w in q for w in _ALT)


def intent(question: str) -> bool:
    """أهو سؤالُ قرارٍ استثماريّ (أضخّ/أبيع/أستبدل/أنتظر/ماذا أفعل)؟"""
    q = (question or "").replace("ـ", "")
    return any(w in q for w in _ACT) or portfolio_intent(q) or wants_alternatives(q)


_ASK = ("؟", "?", "هل ", "ام ", "أم ", "او ", "أو ", "ماذا", "وش ", "ايش", "شو ", "رايك", "رأيك", "تنصح",
        "نصيحتك", "يجوز", "يستاهل", "افضل", "أفضل", "اسوي", "أسوي")


def asks(question: str) -> bool:
    """سؤالُ رأيٍ (هل/أم/ماذا/؟) — لا أمرُ تنفيذ («بِع لي»)."""
    q = f" {question or ''} "
    return any(w in q for w in _ASK)


def companies(question: str, ctx: dict, limit: int = 2) -> list[dict]:
    """الشركاتُ المذكورة — الحيازاتُ أوّلاً ثمّ السوق، بلا تكرارٍ ولا تداخل (لمقارنة «أ أم ب»).

    ‏«الراجحي ريت» لا تعني مصرفَ الراجحي معه: المطابقةُ بكلمتين متتاليتين من الاسم تتقدّم على
    كلمةٍ واحدة، ومن طابق بكلمةٍ تحملها مطابقةٌ أقوى يسقط (قِيس: فُهمت شركتين)."""
    from app.services.ai_chat import _STOP_WORDS
    from app.services.ai_chat_rules import _n
    q = _n(question or "")
    cands: dict[str, dict] = {}

    def consider(sym, name, bonus=0):
        key = _n(str(name or ""))
        toks = key.split()
        if not sym or len(key) < 3:
            return
        sc, hit = 0, set()
        if key in q:
            sc, hit = 300 + len(key), set(toks)
        else:
            for x, y in zip(toks, toks[1:]):
                if f"{x} {y}" in q and not ({x, y} <= _STOP_WORDS):
                    sc, hit = max(sc, 200 + len(x) + len(y)), hit | {x, y}
            if not sc:
                for t in toks:
                    if len(t) >= 4 and t not in _STOP_WORDS and t in q:
                        sc, hit = max(sc, len(t)), hit | {t}
        if not sc and str(sym) in (question or ""):
            sc = 250
        if sc and (sym not in cands or cands[sym]["score"] < sc + bonus):
            cands[sym] = {"symbol": str(sym), "name": name, "score": sc + bonus, "hit": hit}

    for h in ((ctx.get("المحفظة") or {}).get("المراكز") or []):
        consider(str(h.get("الرمز") or ""), h.get("الشركة"), 5)
    try:
        from app.services.market_screener import get_cached_screener
        for r in get_cached_screener() or []:
            consider(str(r.get("symbol") or ""), r.get("name"))
    except Exception:                                             # noqa: BLE001
        pass
    ranked = sorted(cands.values(), key=lambda x: (-len(x["hit"]), -x["score"]))
    out: list[dict] = []
    for c in ranked:
        # كلماتُها كلُّها داخلَ مطابقةٍ أطول لشركةٍ أخرى ⇒ ليست شركةً ثانية
        # (المصرفُ مسجَّلٌ في الفرز باسم «الراجحي» وحده — فيطابق كاملاً وهو جزءٌ من «الراجحي ريت»)
        if c["hit"] and any(len(o["hit"]) > len(c["hit"]) and c["hit"] <= o["hit"] for o in cands.values()):
            continue
        out.append(c)
    out.sort(key=lambda x: -x["score"])
    return [{"symbol": c["symbol"], "name": c["name"], "score": c["score"]} for c in out[:limit]]


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
            _ar = {"BUY": "شراء", "SELL": "بيع", "BONUS": "منحة", "DIVIDEND": "توزيع", "SPLIT": "تجزئة"}
            f["recent"] = [{"date": str(t[0])[:10], "type": _ar.get(str(getattr(t[1], "value", t[1])).upper(), str(getattr(t[1], "value", t[1]))),
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
        if not re.search(r"[\u0600-\u06FF]", str(f.get("name") or "")):   # الاسمُ العربيّ يبقى
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
    # ‏D569: ما نصح به صقرُ من قبل وما جرى له — النصيحةُ تُتابَع لا تُعاد من الصفر
    try:
        from app.services.advisor_memory import recall, summary
        f["advice"] = summary(recall(sym))
    except Exception:                                             # noqa: BLE001
        f["advice"] = None
    # ‏D568: البدائلُ الأفضل — الحلُّ لا التحليلُ وحده
    try:
        from app.services import advisor_solutions as S
        if f.get("is_reit"):
            own = {"premium": (f.get("reit") or {}).get("premium"), "yield": (f.get("reit") or {}).get("yield")}
            f["alternatives"] = S.reit_alternatives(own, f.get("peers") or [])
        else:
            f["alternatives"] = S.alternatives(sym)
    except Exception as e:                                        # noqa: BLE001
        logger.debug("advisor alts {}: {}", sym, e)
        f["alternatives"] = []
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


def reit_facts(f: dict) -> list[str]:
    """جملٌ محسوبةٌ لا يُترك للنموذج استنتاجُها — قِيس: قرأ جدولَ الأقران معكوساً فقال عن الراجحي ريت
    «أفضلُ من معظم أقرانه» وخصمُه من أصغرها (أي أغلاها نسبةً إلى صافي أصوله)."""
    out: list[str] = []
    r, peers = f.get("reit") or {}, [p for p in (f.get("peers") or []) if not p.get("self")]
    prem = r.get("premium")
    if prem is not None and peers:
        deeper = sum(1 for p in peers if p["premium"] < prem)
        med = sorted(p["premium"] for p in peers)[len(peers) // 2]
        out.append(f"خصمُه على صافي الأصول {prem:+.1f}٪ مقابل وسيطِ أقرانه {med:+.1f}٪: "
                   f"{deeper} من {len(peers)} أقرانٍ خصمُهم أعمق — "
                   + ("فهو **أغلى** من أكثرهم نسبةً إلى صافي أصوله" if deeper > len(peers) / 2
                      else "فهو **أرخص** من أكثرهم نسبةً إلى صافي أصوله"))
        ys = sorted(p["yield"] for p in peers if p.get("yield"))
        if r.get("yield") and ys:
            higher = sum(1 for y in ys if y > r["yield"])
            out.append(f"عائدُ توزيعه {r['yield']}٪ مقابل وسيطِ أقرانه {ys[len(ys) // 2]}٪ ({higher} من {len(ys)} عائدُهم أعلى)")
    hist = [h["v"] for h in r.get("nav_history") or []]
    if len(hist) >= 2:
        drops = [(b / a - 1) * 100 for a, b in zip(hist, hist[1:])]
        worst = min(drops)
        if worst <= -5:
            out.append(f"صافي أصوله هبط {abs(worst):.1f}٪ في أحد التقييمات الأخيرة، وتغيّرُه في آخر تقييم {drops[-1]:+.1f}٪")
    return out


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
    out: dict = {"signals": sg, "tranches": [], "stop_rules": [], "facts": reit_facts(f)}
    due = f.get("results_due")
    res_cond = (f"بعد إعلان النتائج القادمة (متوقَّعةٌ حتى {due})" if due else "بعد إعلان النتائج القادمة") + \
        (" إن صمد التوزيعُ وصافي الأصول" if f.get("is_reit") else
         " إن توقّف تراجعُ الربح أو جاء عند توقّع التطبيق أو فوقه")

    if not f.get("held") and not f.get("target"):
        out["action"] = "راقب"
        out["why"] = "لا تملكها ولا وزنَ مستهدفاً لها — حدِّد وزنها في التوزيع النسبي أوّلاً إن أردت دخولها"
        return out
    # ‏D568: الشركةُ الضعيفةُ ذاتُ البديل الأفضل تُستبدل — قبل حسابات الوزن كلِّها
    weak = sg["app_avoid"] or sg["auditor_flag"] or (not sg["app_buy"] and (f.get("fin") or 100) < 55)
    alts = f.get("alternatives") or []
    if f.get("held") and weak and alts and f.get("value"):
        best = alts[0]
        from app.services.advisor_solutions import swap
        out.update(action="استبدل", why="؛ ".join(w for w, on in (
            ("قرارُ التطبيق تجنّب", sg["app_avoid"]), ("تحفّظٌ من المراجع", sg["auditor_flag"]),
            ("جودةٌ ماليةٌ دون 55 وقرارٌ ليس شراءً", not sg["app_buy"] and (f.get("fin") or 100) < 55)) if on),
                   replace_with=best, swap=swap(f["value"], best.get("price")))
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
    # ‏D569: لكلّ شرطٍ صيغةٌ آليّة تراقبها المهمّةُ اليومية (cond) بجانب نصّه للمالك (when)
    after = (f.get("next_q") or {}).get("as_of")
    c_res = {"k": "results", "after": after, "due": due, "nth": 1}
    c_res2 = {"k": "results", "after": after, "due": due, "nth": 2}
    c_rec = {"k": "reclaim", "level": f.get("sma200")} if f.get("sma200") else None
    if f.get("is_reit"):
        nav = (f.get("reit") or {}).get("nav")
        deep = round(nav * 0.85, 2) if nav else None
        value_cond = f"عند خصمٍ 15٪ على صافي الأصول (نحو {deep})" if deep else "عند خصمٍ أعمق على صافي الأصول"
        c_val = {"k": "below", "level": deep} if deep else None
    else:
        lvl = round(px * 0.9, 2) if px else None
        value_cond = f"إن هبط السعرُ نحو {lvl} (−10٪) دون خفضٍ للتوزيع" if lvl else "عند هبوطٍ أعمق دون خفضٍ للتوزيع"
        c_val = {"k": "below", "level": lvl} if lvl else None
    reclaim = (f"أو ثبت السعرُ فوق متوسط 200 يوم ({f['sma200']})" if f.get("sma200") else "أو تحسّن الاتجاهُ الفنيّ")
    any_ = lambda *cs: [c for c in cs if c]

    if gated:
        parts = [(0.34, res_cond, any_(c_res)), (0.33, "بعد تأكيد التحسّن في الربع التالي " + reclaim, any_(c_res2, c_rec)),
                 (0.33, value_cond, any_(c_val))]
        out["action"] = "انتظر الشرط ثمّ أضف على دفعات"
        out["why"] = "؛ ".join(w for w, on in (
            ("الربحُ يتراجع", sg["profit_down"]), ("قرارُ التطبيق ليس شراءً", not sg["app_buy"]),
            ("تحفّظٌ من المراجع", sg["auditor_flag"]), ("تأخّر توزيعُ الريت", sg["reit_overdue"])) if on)
    else:
        first = "الآن" + (" — السعرُ عند قاع 52 أسبوعاً بتشبّعٍ بيعيّ" if sg["at_low"] and sg["oversold"] else "")
        parts = [(0.5, first, [{"k": "now"}]),
                 (0.5, res_cond + " " + reclaim, any_(c_res, c_rec)) if sg["trend_down"]
                 else (0.5, value_cond + " أو " + res_cond, any_(c_val, c_res))]
        out["action"] = "أضف على دفعتين"
        out["why"] = "قرارُ التطبيق شراءٌ ولا إشارةَ تحذير" + ("، والاتجاهُ هابطٌ فالتدرّجُ أسلم" if sg["trend_down"] else "")
    left = rem
    for i, (share, cond, mc) in enumerate(parts):
        amt = left if i == len(parts) - 1 else round(rem * share, 2)
        left = round(left - amt, 2)
        out["tranches"].append({"n": i + 1, "amount": round(amt, 2), "shares": _shares(amt, px), "when": cond, "cond": mc})
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
• ربحُ المركز أو خسارتُه **غيرُ محقّقة** ما لم يُبع — لا تقل «محقّقة».
• حجمُ المركز قبل «اشترِ»: انظر وزنه من رأس المال (القيمةُ السوقية + السيولة) مقابل هدفه والمتبقّي.
• «الحقائق» في الموقف (مقارنةُ الأقران وتاريخُ صافي الأصول) محسوبةٌ — انقلها كما هي ولا تستنتج عكسها.
• «الموقف» المرفقُ محسوبٌ بقواعد التطبيق: **الإجراءُ والمبالغُ وعددُ الأسهم والشروطُ منه حرفياً** — لا تغيّرها ولا تخترع غيرها. مهمّتك أن تشرحها وتعلّلها من الملفّ.
• استند إلى ما قرأه التطبيقُ من ملفّات الشركة (بفتراتها) إن وُجد: ما الذي تغيّر، ولماذا، وهل التوزيعُ مغطّى. وإن لم يُقرأ شيءٌ فقل ذلك ولا تدّعِ قراءته.
• إن كانت المشترياتُ الأخيرة في الملفّ فاذكرها: ما نُفّذ وما بقي — الخطةُ تتواكب مع ما فعله.
• إن قارن بين شركتين فاحكم صريحاً، واذكر كلفةَ الاستبدال إن وُجدت.
• **قدّم حلاً لا تحليلاً فقط.** إن كان الإجراءُ «استبدل» فسمِّ البديلَ ومبلغَ النقل وأسهمَه كما في الموقف، ولماذا هو أفضل
  (بالأرقام: الدرجة المالية، القرار، الفجوة، العائد). وإن سأل عن بديلٍ ووُجدت «البدائل» فاعرض أفضلها بأرقامه،
  وإن لم يوجد بديلٌ أفضل فقل ذلك صراحةً — البقاءُ أحياناً هو الحلّ.
• إن ورد «ما نصحتُ به سابقاً» فابدأ منه: ما الذي نُفّذ، وما الذي تحقّق شرطُه، وما الذي ما زال ينتظر — لا تبدأ من الصفر.
• لا رقمَ من خارج الملفّ. ما لا تعرفه قُل «غير متوفّر».
• لا تحفيز ولا تهويل ولا عبارات تنصّل طويلة.

ابدأ بالقرار مباشرةً بلا تحيّةٍ ولا تعريفٍ بنفسك، ولا تكتب أسماءَ حقولٍ إنجليزية.
• إن ورد «حكم الاستبدال» فهو الحكمُ — انقله صريحاً في السطر الأوّل ولا تخلطه بنقيضه.
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
        if st.get("replace_with"):
            b, sw = st["replace_with"], st.get("swap") or {}
            out.append(f"• الحلّ: استبدلها بـ{b.get('name')} ({b.get('symbol')}) — درجتُها {b.get('quality')} مقابل "
                       f"{b.get('base_quality')}، وقرارُها {b.get('decision')}؛ انقل {sw.get('amount', 0):,.0f} ريال (نحو {sw.get('shares')} سهماً)")
        adv = f.get("advice")
        if adv:
            st_ = " · ".join(f"الدفعة {t['n']}: {t['الحالة']}" for t in adv.get("الدفعات") or [])
            out.append(f"• نصيحتي السابقة ({adv.get('بتاريخ')}): {adv.get('الإجراء')} — {st_}")
        for x in st.get("facts") or []:
            out.append(f"• {x.replace('**', '')}")
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
    # ‏D569: النصيحةُ تُحفظ بدفعاتها وشروطها الآليّة، فتُراقَب وتُتابَع
    try:
        from app.core.portfolio_scope import active_pid
        from app.services.advisor_memory import remember
        for f, st in zip(fs, sts):
            if f.get("held"):
                remember(f, st, active_pid())
    except Exception as e:                                        # noqa: BLE001
        logger.debug("advisor remember: {}", e)
    cmp = compare(fs[0], fs[1]) if len(fs) == 2 else None
    fallback = render(fs, sts, cmp)
    if not settings.AI_API_KEY or not can_call("gemini"):
        return {"reply": fallback, "grounded": True, "source": "advisor-rules"}
    pack = {"ملفّات القرار": fs, "الموقف المحسوب": sts, "اليوم": date.today().isoformat()}
    # ‏D568: سُئل عن بديل ⇒ حكمُ الاستبدال محسوبٌ لا مستنتج
    if wants_alternatives(question):
        try:
            from app.services.advisor_solutions import swap_verdict
            from sqlalchemy import select
            from app.models.portfolio import Company, Holding
            held = {s for s, in (await db.execute(select(Company.symbol).join(Holding, Holding.company_id == Company.id)
                                                  .where(Holding.quantity > 0))).all()}
            pack["حكم الاستبدال"] = [swap_verdict(f, st, held) for f, st in zip(fs, sts)]
            fallback = "\n".join(f"{f['name']}: {v['الحكم']}" + (f" — {v['كلفة التبديل']}" if v.get("كلفة التبديل") else "")
                                 for f, v in zip(fs, pack["حكم الاستبدال"]) if v) + "\n\n" + fallback
        except Exception as e:                                    # noqa: BLE001
            logger.debug("advisor swap verdict: {}", e)
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
        import asyncio
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.25, "maxOutputTokens": 1800}}
        for i in range(2):                                        # ‏503 «مشغول» عارض — محاولةٌ ثانية (قِيس)
            if not can_call("gemini"):
                break
            record("gemini")
            async with httpx.AsyncClient(timeout=40) as c:
                r = await c.post(url, json=body)
            if r.status_code in (429, 500, 503) and i == 0:
                await asyncio.sleep(4)
                continue
            break
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


# ── على مستوى المحفظة: التركيزُ والاكتفاءُ بالقيادية (D568) ─────────────────
PORT_CHARTER = """أنت «صقر»، المستشارُ الماليُّ الخاصّ لمالك المحفظة، بخبرة مدير صندوق. سألك عن هيكلة محفظته كلِّها.
«خطةُ التركيز» المرفقةُ محسوبةٌ بقواعد التطبيق: من يبقى ومن يخرج والأوزانُ الجديدة والمبالغ — **انقلها حرفياً ولا تغيّرها**.
**لا تُخرج شركةً ليست في «يخرج»، ولا تُبقِ شركةً فيه، ولا تصف قرارَ شركةٍ بغير «قرار التطبيق» المكتوب لها.**
وإن كانت «يخرج» فارغةً فقل صراحةً إنّ محفظتك ضمن العدد المطلوب ولا خروجَ تقترحه الخطة.
مهمّتك: احكم صريحاً، ثمّ اشرح لماذا خرج كلُّ خارجٍ (درجتُه، قرارُه، وزنُه، شرعيّتُه) ولماذا بقيت القيادية، وما الذي
يُثبَّت من ربحٍ أو خسارة عند البيع، وأين تذهب المبالغ (الأوزانُ الجديدة للباقين)، وإن وُجد لخارجٍ بديلٌ أفضل في قطاعه فاذكره.
نبّهه أنّ التنفيذ بيده: يُحدَّث الوزنُ المستهدف في «التوزيع النسبي» فيحسب التطبيقُ المبالغ.
ابدأ بالحكم مباشرةً بلا تحيّةٍ ولا تعريفٍ بنفسك. ولا تكتب أسماءَ حقولٍ إنجليزية.
نصٌّ عربيٌّ نظيف بلا رموز تنسيق، والتعدادُ بـ«•»، واختم: «رأيٌ تحليليّ من بيانات التطبيق، والقرارُ لك.»"""


async def portfolio_pack(db, question: str) -> dict:
    from app.api.v1.endpoints.allocation import get_allocation
    from app.services import advisor_solutions as S
    from sqlalchemy import select
    from app.models.portfolio import Company, Holding
    res = await get_allocation(db)
    d = (json.loads(res.body) if hasattr(res, "body") else res)["data"]
    inv = {s: float(v or 0) for s, v in (await db.execute(
        select(Company.symbol, Holding.invested_amount).join(Holding, Holding.company_id == Company.id))).all()}
    # المراكزُ الحيّة وحدها (قِيس: مراكزُ مُغلقةٌ بقيمة صفرٍ عُدّت فخرجت الخطةُ «10 ⇒ 10» بلا خروج)
    items = [{**it, "invested": inv.get(str(it["symbol"]))} for it in d.get("items") or []
             if float(it.get("market_value") or 0) > 0]
    n = len(items)
    asked_n = S.wanted_count(question, default=0)
    keep_n = asked_n or (10 if n > 12 else max(5, n - 3))
    leaders_only = not asked_n and any(w in (question or "") for w in ("القيادية", "القياديه", "القيادي"))
    rows = S._rows()
    # ‏D570: قرارُ كلّ مركزٍ من التحليل الحيّ نفسِه الذي تعرضه صفحةُ السهم — لا من مخزن الفرز
    # (قِيس: الخطةُ قالت عن سدافكو «انتظار» وصفحتُها «شراء»). مهلةٌ قصيرة، والفرزُ احتياط.
    import asyncio
    from app.services.analysis import analyze_company

    async def _live_dec(sym):
        try:
            a = await asyncio.wait_for(analyze_company(f"{sym}.SR", None, db=db), timeout=8)
            return sym, (a or {}).get("decision", {}).get("label"), (a or {}).get("financial", {}).get("score")
        except Exception:                                         # noqa: BLE001
            return sym, None, None
    live = {s: (dl, fs) for s, dl, fs in [await _live_dec(str(it["symbol"])) for it in items]}
    rows = [dict(r) for r in rows]
    for r in rows:
        dl, fs = live.get(str(r.get("symbol")), (None, None))
        if dl and "غير كافية" not in dl and "غير متوفر" not in dl:   # تحليلٌ تعثّر تحت المهلة ⇒ المخزنُ أصدق
            r["decision"] = dl
        if isinstance(fs, (int, float)):
            r["finance_score"] = fs
    plan = S.consolidate(items, rows, keep_n, d.get("investable") or 0, leaders_only=leaders_only)
    for x in plan["exits"]:
        alts = S.alternatives(str(x["symbol"]), rows, n=1)
        x["better_in_sector"] = alts[0] if alts else None
    _AR_K = {"symbol": "الرمز", "name": "الشركة", "market_value": "القيمة", "current_weight": "الوزن الحالي٪",
             "target_weight": "الهدف الحالي٪", "new_target": "الهدف الجديد٪", "quality": "الدرجة", "decision": "قرار التطبيق",
             "leader": "قيادية", "halal": "شرعية", "sector": "القطاع", "invested": "المدفوع", "note": "سبب الخروج",
             "better_in_sector": "بديلٌ أفضل في قطاعها"}
    slim = lambda k: {_AR_K[key]: k.get(key) for key in _AR_K if key in k or key == "new_target"}
    return {"عدد الشركات": f"{plan['before']} ⇒ {plan['after']}", "يبقى": [slim(k) for k in plan["keep"]],
            "يخرج": [slim(x) for x in plan["exits"]], "حصيلة البيع": plan["proceeds"],
            "ربحٌ أو خسارةٌ تُثبَّت": plan["realized"], "وزنٌ يُعاد توزيعه٪": plan["freed_weight"],
            "القطاعات بعد التركيز": plan["sectors_after"], "رأس المال": d.get("investable")}


def render_portfolio(p: dict) -> str:
    out = [f"خطة التركيز: {p['عدد الشركات']} شركات."]
    for x in p["يخرج"]:
        alt = x.get("بديلٌ أفضل في قطاعها")
        out.append(f"• يخرج {x['الشركة']} ({x['الرمز']}) — درجته {x['الدرجة']}، قراره {x.get('قرار التطبيق')}، "
                   f"وزنه {x.get('الوزن الحالي٪')}٪ — {x.get('سبب الخروج')}"
                   + (f"؛ وبديلُه الأفضل في قطاعه {alt['name']} ({alt['symbol']})" if alt else ""))
    for k in p["يبقى"]:
        out.append(f"• يبقى {k['الشركة']} — هدفه الجديد {k.get('الهدف الجديد٪')}٪ (كان {k.get('الهدف الحالي٪')}٪)"
                   + (" — قيادية" if k.get("قيادية") else ""))
    r = p["ربحٌ أو خسارةٌ تُثبَّت"]
    out.append(f"• حصيلةُ البيع {p['حصيلة البيع']:,.0f} ريال، و{'تُثبَّت خسارة' if r < 0 else 'يُثبَّت ربح'} {abs(r):,.0f} ريال.")
    out.append("• التنفيذ بيدك: حدِّث الأوزانَ المستهدفة في «التوزيع النسبي» فيحسب التطبيقُ المبالغ.")
    out.append("رأيٌ تحليليّ من بيانات التطبيق، والقرارُ لك.")
    return "\n".join(out)


async def answer_portfolio(db, question: str, history: list | None = None) -> dict:
    import httpx
    from app.core.config import settings
    from app.services.usage_tracker import can_call, record
    p = await portfolio_pack(db, question)
    fallback = render_portfolio(p)
    if not settings.AI_API_KEY or not can_call("gemini"):
        return {"reply": fallback, "grounded": True, "source": "advisor-rules"}
    prompt = (f"{PORT_CHARTER}\n\n=== خطةُ التركيز (مصدرك الوحيد) ===\n{json.dumps(p, ensure_ascii=False, default=str)}\n"
              f"=== نهاية الخطة ===\n\nسؤال المالك: {question}\n\nجوابك:")
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}")
    try:
        import asyncio
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.25, "maxOutputTokens": 2000}}
        for i in range(2):
            record("gemini")
            async with httpx.AsyncClient(timeout=40) as c:
                r = await c.post(url, json=body)
            if r.status_code in (429, 500, 503) and i == 0:
                await asyncio.sleep(4)
                continue
            break
        if r.status_code != 200:
            return {"reply": fallback, "grounded": True, "source": "advisor-rules"}
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = re.sub(r"[٠-٩]", lambda m: str(ord(m.group()) - 0x0660), text)
        from app.services.ai_chat import _strip_markup
        return {"reply": _strip_markup(text), "grounded": True, "source": "advisor"}
    except Exception as e:                                        # noqa: BLE001
        logger.warning("advisor portfolio: {}", type(e).__name__)
        return {"reply": fallback, "grounded": True, "source": "advisor-rules"}
