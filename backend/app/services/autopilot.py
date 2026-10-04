"""‏D587: الطيارُ الآليّ للمحفظة — مستشارٌ يرى المحفظةَ كلَّها ويحميها من قراراتها.

بأمر المالك: «كما أنّ للطائرة أوتو بايلوت أريد للمحفظة أوتو مستشاراً ماليّاً يحمي المستثمر من قراراته الخاطئة».
  · يرى: الأهداف (المليون وزمنُ الوصول بالعائد المركّب الفعليّ)، والمملوكَ ومتوسّطَ تكلفته، والمتبقّي من التوزيع،
    ولكلّ شركة: قرارَ التطبيق وقيمتَها العادلة وجودتَها، وD7M الشهريَّ والأسبوعيَّ (الحكم) واليوميَّ (السيولة)،
    وآخرَ نتائجها المعلنة وإفصاحاتِها.
  · يحمي بقواعد حتميةٍ لا يملك النموذجُ نقضَها: لا شراءَ فوق القيمة العادلة ولا عند مقاومةٍ أسبوعيةٍ أو شهرية،
    ولا تعديلَ متوسّطٍ في شركةٍ كُسر اتجاهُها الشهريّ وقرارُها ليس شراء، وتخفيفُ التركّز، وأفضلُ دخولٍ عند دعمٍ
    أسبوعيٍّ أو شهريٍّ يخفض المتوسّط، وتصفيةٌ جزئيةٌ عند مقاومةٍ شهريةٍ والسعرُ فوق قيمته.
  · ويتعلّم من المكتبة: مبادئُها بأسماء كتبها وصفحاتها.
والنموذجُ يصوغ ولا يحكم: الحكمُ من القواعد، وما لا مصدرَ له لا يُقال.
"""
from __future__ import annotations

import asyncio
import json
import math
from datetime import date

from loguru import logger


def _f(x):
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


MODES = {"investor": "مستثمر", "trader": "مضارب"}


def rules(pos: dict, mode: str = "investor") -> dict:
    """قواعدُ الحماية لمركزٍ واحد — حتمية. يعيد {action, level, why[], blocks[]}.

    ‏D588 بأمر المالك — مفتاحُ «مستثمر / مضارب»:
      · المستثمر: الشهريُّ ثمّ الأسبوعيّ للحكم، يصبر على القيمة، ويصفّي عند مقاومةٍ شهريةٍ والسعرُ فوق قيمته.
      · المضارب: الأسبوعيُّ للحكم، وسيولةُ اليوميّ للتوقيت (لا دخولَ في انهيارٍ أو تصريف)، ويأخذ الربحَ عند
        المقاومة الأسبوعية ولو لم يتجاوز السعرُ قيمتَه."""
    if mode == "trader":
        return _rules_trader(pos)
    p, c, fv = _f(pos.get("price")), _f(pos.get("avg_cost")), _f(pos.get("fair_value"))
    dec = str(pos.get("decision") or "")
    W, M = pos.get("weekly") or {}, pos.get("monthly") or {}
    cw, tw = _f(pos.get("current_weight")) or 0, _f(pos.get("target_weight")) or 0
    buy, avoid = "شراء" in dec, any(w in dec for w in ("تجنب", "تجنّب", "بيع"))
    blocks, why = [], []
    at_res = any(x.get("where") in ("داخل منطقة المقاومة", "فوق المقاومة") for x in (W, M) if x)
    at_sup = any(x.get("where") == "داخل منطقة الدعم" for x in (W, M) if x)
    m_down = M.get("state") == "هابط"
    if fv and p and p > fv:
        blocks.append(f"لا شراء: السعر {p:.2f} فوق قيمته العادلة {fv:.2f}")
    if at_res:
        blocks.append("لا شراء: السعر عند مقاومة " + ("شهرية" if M.get("where", "").find("المقاومة") >= 0 else "أسبوعية"))
    if c and p and p < c * 0.9 and m_down and not buy:
        blocks.append(f"لا تعديل متوسط: الشهري هابط والقرار {dec or 'غير متوفّر'}")
    action, level = "احتفظ", None
    if p and fv and p >= fv * 1.05 and (at_res or M.get("where") == "فوق المقاومة"):
        action = "صفِّ جزئياً"
        r = (M.get("resistance") or W.get("resistance"))
        level = r
        why.append(f"السعر فوق قيمته العادلة بـ{(p / fv - 1) * 100:.0f}% وعند مقاومة")
    elif cw > tw + 5 and tw > 0:
        action = "خفّف"
        why.append(f"وزنه {cw:.1f}% فوق هدفه {tw:.1f}%")
    elif buy and not blocks:
        zone = (W.get("support") if W.get("where") != "تحت الدعم" else None) or M.get("support")
        if at_sup or (zone and p and p <= zone[1] * 1.03):
            action, level = "اشترِ الآن", zone
            why.append("السعر داخل منطقة دعم D7M والقرار شراء")
        else:
            action, level = "اشترِ عند الدعم", zone
            why.append("القرار شراء، والدخولُ الأفضل عند الدعم لا الآن")
        need = _f(pos.get("need")) or 0
        q = _f(pos.get("quantity")) or 0
        if level and c and q and need > 0:
            mid = (level[0] + level[1]) / 2
            new_avg = (q * c + need) / (q + need / mid)
            if new_avg < c:
                why.append(f"الشراء بـ{need:,.0f} ريال عند {mid:.2f} يخفض متوسطك من {c:.2f} إلى {new_avg:.2f}")
            else:
                why.append(f"الشراء عند {mid:.2f} يرفع متوسطك من {c:.2f} إلى {new_avg:.2f} — مبرَّرٌ بالقرار لا بالمتوسط")
    elif avoid:
        action = "لا تُضِف"
        why.append(f"قرار التطبيق {dec}")
    return {"action": action, "level": level, "why": why, "blocks": blocks}


def _rules_trader(pos: dict) -> dict:
    p, c, fv = _f(pos.get("price")), _f(pos.get("avg_cost")), _f(pos.get("fair_value"))
    dec = str(pos.get("decision") or "")
    W = pos.get("weekly") or {}
    liq = str(pos.get("daily_liquidity") or "")
    cw, tw = _f(pos.get("current_weight")) or 0, _f(pos.get("target_weight")) or 0
    blocks, why = [], []
    w_res = W.get("where") in ("داخل منطقة المقاومة", "فوق المقاومة")
    w_sup = W.get("where") == "داخل منطقة الدعم"
    if liq in ("انهيار بيعي", "تصريف بيعي"):
        blocks.append(f"لا دخول: سيولة اليوم {liq}")
    elif liq == "جفاف سيولة":
        blocks.append("انتظر دخول السيولة: اليوميُّ جافّ")
    if w_res:
        blocks.append("لا دخول: السعر عند مقاومة أسبوعية")
    if any(w in dec for w in ("تجنب", "تجنّب", "بيع")):
        blocks.append(f"لا مضاربة على سهمٍ قراره {dec}")
    action, level = "احتفظ", None
    if w_res and c and p and p > c:
        action, level = "خذ الربح", W.get("resistance")
        why.append(f"السعر عند مقاومة أسبوعية وفوق متوسطك {c:.2f} بـ{(p / c - 1) * 100:.0f}%")
    elif W.get("state") == "هابط" and c and p and p < c * 0.93:
        action, level = "اخرج عند الارتداد", W.get("resistance")
        why.append("الاتجاه الأسبوعي هابط والسعر دون متوسطك بأكثر من 7%")
    elif cw > tw + 5 and tw > 0:
        action = "خفّف"
        why.append(f"وزنه {cw:.1f}% فوق هدفه {tw:.1f}%")
    elif not blocks and w_sup:
        action, level = "ادخل الآن", W.get("support")
        why.append("السعر في دعم أسبوعي" + (f" والسيولة {liq}" if liq else ""))
    elif not blocks and W.get("support"):
        action, level = "ادخل عند الدعم", W.get("support")
        why.append("الدخول الأنسب عند الدعم الأسبوعي")
    if level and action.startswith("ادخل"):
        tgt = W.get("target_1_618")
        if not (tgt and tgt > level[1]):                          # الضلعُ الأخير هابط ⇒ هدفُه تحت الدخول؛ فالمقاومةُ هي الهدف
            tgt = (W.get("resistance") or [None, None])[0]
        if tgt and tgt > level[1]:
            why.append(f"هدفه الأسبوعي {tgt:.2f} (+{(tgt / ((level[0] + level[1]) / 2) - 1) * 100:.0f}%)")
    return {"action": action, "level": level, "why": why, "blocks": blocks}


def goal_eta(current: float, target: float, cagr_pct: float | None) -> dict:
    if not target or target <= 0:
        return {"status": "لا هدف"}
    if current >= target:
        return {"status": "تحقّق", "pct": 100.0}
    pct = round(current / target * 100, 1)
    if not cagr_pct or cagr_pct <= 0:
        return {"status": "غير متوفّر", "pct": pct, "why": "العائد المركّب غير متوفّر بعد (يحتاج تسعين يوماً) أو سالب"}
    years = math.log(target / current) / math.log(1 + cagr_pct / 100)
    return {"status": "على المسار", "pct": pct, "years": round(years, 1), "cagr": round(cagr_pct, 2),
            "note": "بالعائد المركّب الفعليّ، ودون إيداعاتٍ جديدة"}


async def _events(sym: str) -> list[dict]:
    """مفكرةُ الشركة القادمة (المخزَّنةُ المجهَّزة) — أقربُ حدثين."""
    from app.api.v1.endpoints import market as M
    r = await M.get_company_events(sym, "")
    rows = (json.loads(r.body) if hasattr(r, "body") else r).get("data") or []
    today = date.today().isoformat()
    up = sorted([e for e in rows if str(e.get("date") or "")[:10] >= today], key=lambda e: str(e.get("date")))
    return [{"date": str(e.get("date"))[:10], "title": str(e.get("title") or e.get("type") or "")[:90]} for e in up[:2]]


async def _disclosures(sym: str) -> list[dict]:
    """آخرُ ثلاثة إفصاحاتٍ في «تداول» بعناوينها وتواريخها."""
    from app.services import tadawul_disclosure as D
    items = await D.list_for(sym, size=5)
    return [{"date": i.get("date"), "title": str(i.get("title") or "")[:110]} for i in (items or [])[:3]]


async def pack(db, mode: str = "investor") -> dict:
    from sqlalchemy import select
    from app.api.v1.endpoints.allocation import get_allocation
    from app.models.portfolio import Company, Holding
    from app.models.market import Goal
    from app.services.analysis import analyze_company
    from app.services import d7m
    from app.services.results_announcements import latest as latest_result
    from app.services.portfolio_return import compute_cagr_pct
    from app.services.library_wisdom import principles

    res = await get_allocation(db)
    d = (json.loads(res.body) if hasattr(res, "body") else res)["data"]
    hold = {str(s): (float(q or 0), float(ac or 0)) for s, q, ac in (await db.execute(
        select(Company.symbol, Holding.quantity, Holding.average_cost).join(Holding, Holding.company_id == Company.id))).all()}
    items = [it for it in d.get("items") or [] if float(it.get("market_value") or 0) > 0 or float(it.get("target_weight") or 0) > 0]
    investable = float(d.get("investable") or 0)

    async def one(it):
        sym = str(it["symbol"]).replace(".SR", "")
        a, t, ev, dis = await asyncio.gather(asyncio.wait_for(analyze_company(f"{sym}.SR", None, db=None), timeout=20),
                                             asyncio.wait_for(d7m.read(sym), timeout=30),
                                             asyncio.wait_for(_events(sym), timeout=15),
                                             asyncio.wait_for(_disclosures(sym), timeout=15), return_exceptions=True)
        a = a if isinstance(a, dict) else {}
        t = t if isinstance(t, dict) else {}
        q, ac = hold.get(sym) or hold.get(sym + ".SR") or (0.0, 0.0)
        tw = float(it.get("target_weight") or 0)
        mv = float(it.get("market_value") or 0)
        need = max(0.0, tw / 100 * investable - mv)
        r = latest_result(sym) or {}
        pos = {"symbol": sym, "name": it.get("name"), "price": a.get("price") or t.get("price"),
               "quantity": q, "avg_cost": ac or None, "market_value": mv, "current_weight": it.get("current_weight"),
               "target_weight": tw, "need": round(need, 2), "decision": (a.get("decision") or {}).get("label"),
               "fair_value": a.get("fair_value"), "quality": (a.get("financial") or {}).get("score"),
               "weekly": t.get("weekly"), "monthly": t.get("monthly"), "daily_liquidity": (t.get("daily_liquidity") or {}).get("state"),
               "last_result": ({"as_of": r.get("as_of"), "net_income_q": (r.get("quarter") or {}).get("net_income"),
                                "revenue_q": (r.get("quarter") or {}).get("revenue")} if r else None),
               "upcoming": ev if isinstance(ev, list) else [], "disclosures": dis if isinstance(dis, list) else []}
        pos["autopilot"] = rules(pos, mode)
        return pos

    sem = asyncio.Semaphore(4)

    async def guarded(it):
        async with sem:
            try:
                return await one(it)
            except Exception as e:                                # noqa: BLE001
                logger.warning(f"الطيار الآليّ {it.get('symbol')}: {type(e).__name__}")
                return None
    positions = [p for p in await asyncio.gather(*(guarded(it) for it in items)) if p]
    cagr = None
    try:
        cagr = await compute_cagr_pct(db)
    except Exception:                                             # noqa: BLE001
        pass
    wealth = investable
    goals = []
    try:
        # أهدافُ التطبيق المدمجة (المليون والدخل السنويّ) من مصدرها الواحد — الثروةُ كما تعرضها أشرطةُ الأهداف
        from app.api.v1.endpoints.goals import get_builtin_goals
        bg = await get_builtin_goals(db)
        bg = (json.loads(bg.body) if hasattr(bg, "body") else bg).get("data") or {}
        m = bg.get("million") or {}
        if m.get("target"):
            wealth = float(m.get("current") or wealth)
            goals.append({"name": "المليون", "target": float(m["target"]), **goal_eta(wealth, float(m["target"]), cagr)})
        inc = bg.get("income") or {}
        if inc.get("target"):
            goals.append({"name": f"دخل {inc.get('year')}", "target": float(inc["target"]),
                          "current": inc.get("current"), "pct": round(float(inc.get("pct") or 0), 1), "status": "سنويّ"})
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"الطيار الآليّ — الأهداف المدمجة: {type(e).__name__}")
    for g in (await db.execute(select(Goal))).scalars().all():
        if (g.target_type or "AMOUNT") == "AMOUNT" and str(getattr(g.status, "value", g.status)) == "ACTIVE":
            goals.append({"name": g.goal_name, "target": float(g.target_value), **goal_eta(wealth, float(g.target_value), cagr)})
    cash = float(d.get("available_cash") or 0)
    flags = []
    top = max(positions, key=lambda x: float(x.get("current_weight") or 0), default=None)
    if top and float(top.get("current_weight") or 0) > 25:
        flags.append(f"تركّز: {top['name']} {float(top['current_weight']):.1f}% من المحفظة")
    buys = [p for p in positions if p["autopilot"]["action"].startswith(("اشترِ", "ادخل"))]
    if investable and cash / investable > 0.15 and buys:
        flags.append(f"سيولة معطّلة {cash:,.0f} ريال ({cash / investable * 100:.0f}%) وأمامها {len(buys)} {'فرص' if 2 <= len(buys) <= 10 else 'فرصة'} شراء")
    return {"date": date.today().isoformat(), "wealth": round(wealth, 2), "cash": round(cash, 2), "cagr_pct": cagr,
            "goals": goals, "flags": flags, "positions": positions, "principles": principles(24), "mode": mode}


def render(pk: dict) -> dict:
    """الصيغةُ المختصرة من القواعد وحدَها — البديلُ حين يتعذّر النموذج، وسقفُ ما يقوله."""
    pos = pk["positions"]
    acts = [p for p in pos if p["autopilot"]["action"] != "احتفظ"]
    g = (pk.get("goals") or [None])[0]
    goal_line = None
    if g:
        goal_line = (f"هدف {g['target']:,.0f}: أنجزتَ {g.get('pct', 0)}%"
                     + (f"، وتصل بعد {g['years']} سنة بعائدك المركّب {g['cagr']}%." if g.get("years") else f" — {g.get('why') or g['status']}."))
    blocks = [f"{p['name']}: {b}" for p in pos for b in p["autopilot"]["blocks"]]
    actions = []
    for p in acts[:8]:
        ap = p["autopilot"]
        lv = ap.get("level")
        actions.append({"symbol": p["symbol"], "name": p["name"], "action": ap["action"],
                        "level": f"{lv[0]:.2f}–{lv[1]:.2f}" if lv else None, "why": "؛ ".join(ap["why"])[:160]})
    n_buy = sum(1 for a in actions if a["action"].startswith(("اشترِ", "ادخل")))
    n_cut = sum(1 for a in actions if a["action"] in ("خفّف", "صفِّ جزئياً", "خذ الربح", "اخرج عند الارتداد"))
    def cnt(n, one, few, many):
        return f"{one}" if n == 1 else f"{n} {few}" if 2 <= n <= 10 else f"{n} {many}"
    parts = []
    if n_buy:
        parts.append(cnt(n_buy, "فرصةُ شراءٍ واحدة", "فرص شراء", "فرصة شراء") + " بشروطها")
    if n_cut:
        parts.append(cnt(n_cut, "مركزٌ يحتاج تخفيفاً", "مراكز تحتاج تخفيفاً", "مركزاً يحتاج تخفيفاً"))
    if blocks:
        parts.append(cnt(len(blocks), "حمايةٌ مفعّلة", "حمايات مفعّلة", "حمايةً مفعّلة"))
    verdict = ("المحفظة: " + "، و".join(parts) + ".") if parts else "المحفظة على مسارها: لا إجراء الآن."
    return {"verdict": verdict, "goal": goal_line, "flags": pk.get("flags") or [], "actions": actions,
            "protections": blocks[:8], "principles": [], "source": "rules"}


async def opinion(db, force: bool = False, mode: str = "investor") -> dict:
    from app.core.portfolio_scope import active_pid
    from app.services import cache
    pid = active_pid()
    mode = mode if mode in MODES else "investor"
    ck = f"autopilot:v1:{pid}:{mode}:{date.today().isoformat()}"
    if not force:
        hit = cache.get(ck)
        if hit:
            return hit
    pk = await pack(db, mode)
    base = render(pk)
    from app.services.ai_content import _generate_obj
    slim = {"الثروة": pk["wealth"], "السيولة": pk["cash"], "العائد المركّب٪": pk["cagr_pct"], "الأهداف": pk["goals"],
            "تنبيهات": pk["flags"],
            "المراكز": [{k: p.get(k) for k in ("name", "symbol", "price", "avg_cost", "fair_value", "quality", "decision",
                                               "current_weight", "target_weight", "need", "weekly", "monthly",
                                               "daily_liquidity", "last_result", "upcoming", "disclosures")} | {"قرار_الطيار": p["autopilot"]}
                        for p in pk["positions"]],
            "مبادئ_المكتبة": [f"{x['p']} — «{x['book']}» ص{x['page']}" for x in pk["principles"]]}
    lens = ("بعين المستثمر: الإطاران الشهريُّ والأسبوعيّ، والقيمةُ قبل السعر، والصبرُ على الجودة، وتصفيةٌ عند المقاومة الشهرية."
            if mode == "investor" else
            "بعين المضارب: الإطارُ الأسبوعيّ للحكم وسيولةُ اليوميّ للتوقيت، ودخولٌ عند الدعم وجنيُ ربحٍ عند المقاومة الأسبوعية، ووقفُ خسارةٍ حين يُكسر الاتجاه.")
    prompt = f"""أنت الطيارُ الآليّ لمحفظة المالك: مستشارٌ ماليٌّ متخرّجٌ من مكتبته. تتكلّم الآن {lens}
هدفُك هدفُه: الوصولُ إلى أهداف المحفظة بأسرع وقتٍ ممكن دون مخاطرةٍ تهدم رأس المال، ومتوسّطُ التكلفة سلاحُك — تشتري عند الدعوم التاريخية وتصفّي عند المقاومات.

المعطياتُ (مصدرك الوحيد — لا رقمَ من خارجها):
{json.dumps(slim, ensure_ascii=False, default=str)}

قواعدُ ملزمة:
- «قرار_الطيار» لكلّ مركز حتميّ صادرٌ عن قواعد الحماية: لا تناقضه ولا تقترح شراءً فيما حُجب شراؤه. مهمّتك أن تشرحه وترتّب الأولويات.
- الإطاران الشهريُّ والأسبوعيُّ لأداة D7M هما الحكمُ الفنيّ، واليوميُّ لقراءة السيولة وحدها.
- استشهد بمبدأين أو ثلاثةٍ من مبادئ المكتبة حيث تنطبق فعلاً، باسم الكتاب ورقم الصفحة كما وردت.
- اقرأ مفكرةَ كلّ شركةٍ (upcoming) وإفصاحاتِها (disclosures) وآخرَ نتائجها: حدثٌ قريبٌ أو إفصاحٌ جوهريٌّ يغيّر التوقيت يُذكر.
- لا تذكر توجّهاتٍ أو رؤيةً أو قطاعاتٍ للمملكة إلا إن وردت في المعطيات.
- جملٌ قصيرة (أربع عشرة كلمة على الأكثر)، بصيغة المتكلّم، بلا تحوّطٍ ولا إخلاءِ مسؤولية.

أعد JSON فقط:
{{"verdict": "جملةٌ واحدة: حالُ المحفظة الآن وأهمُّ ما يجب فعله",
  "goal": "جملةٌ واحدة عن الهدف وزمن الوصول كما في المعطيات",
  "points": [{{"t": "جملةٌ قصيرة برقم", "tone": "+|-|="}}],
  "actions": [{{"symbol": "الرمز", "name": "الشركة", "action": "كما في قرار_الطيار", "level": "المنطقة إن وُجدت", "why": "جملةٌ قصيرة"}}],
  "protections": ["جملةٌ قصيرة لكلّ حمايةٍ مفعّلة تمنعك من خطأ"],
  "principles": [{{"p": "المبدأ كما ورد", "book": "الكتاب", "page": 0, "applies": "على أيّ مركزٍ ولماذا"}}]}}
والنقاطُ أربعٌ إلى ستّ، والإجراءاتُ ستٌّ على الأكثر مرتّبةً بالأهمية."""
    obj = None
    try:
        obj = await _generate_obj(prompt, f"ai:autopilot:v1:{pid}:{mode}:{date.today().isoformat()}:{len(pk['positions'])}", 6 * 3600)
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"الطيار الآليّ — النموذج: {type(e).__name__}")
    out = dict(base)
    if isinstance(obj, dict) and obj.get("verdict"):
        allowed = {p["symbol"]: p["autopilot"]["action"] for p in pk["positions"]}
        acts = []
        for a in (obj.get("actions") or [])[:6]:
            s = str(a.get("symbol") or "").replace(".SR", "")
            if s in allowed:
                acts.append({**a, "symbol": s, "action": allowed[s]})        # الإجراءُ من القواعد لا من النموذج
        known = {(x["book"], x["page"]) for x in pk["principles"]}
        prin = [x for x in (obj.get("principles") or []) if (x.get("book"), _int(x.get("page"))) in known][:3]
        out.update({"verdict": obj["verdict"], "goal": obj.get("goal") or base["goal"],
                    "points": (obj.get("points") or [])[:6], "actions": acts or base["actions"],
                    # الحماياتُ من القواعد بأسماء شركاتها — لا عباراتٌ عامةٌ يكتبها النموذج (قِيس: «الالتزام بوقف الخسارة»)
                    "protections": base["protections"], "principles": prin, "source": "ai"})
    out["asof"] = pk["date"]
    out["mode"] = mode
    out["positions"] = [{"symbol": p["symbol"], "name": p["name"], "action": p["autopilot"]["action"],
                         "weekly": (p.get("weekly") or {}).get("where"), "monthly": (p.get("monthly") or {}).get("where"),
                         "liquidity": p.get("daily_liquidity")} for p in pk["positions"]]
    cache.set(ck, out, 6 * 3600)
    return out


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None
