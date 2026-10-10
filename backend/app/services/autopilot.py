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


# ‏D679: ما يقرؤه المستشارُ عن كلّ مركز — المصدرُ الواحد للرأي والحوار
POS_KEYS = ("name", "symbol", "sector", "price", "avg_cost", "fair_value", "fair_value_conf", "quality", "stability",
            "decision", "current_weight", "target_weight", "need", "weekly", "monthly", "daily_liquidity", "last_result",
            "upcoming", "disclosures", "material_events", "analysts", "red_lines", "warnings")
# ونبضُ السوق من لقطة refresh_market_brief بمفاتيحها هي
MARKET_KEYS = ("summary", "phase", "tasi", "brent", "flow", "headlines", "generated_at")


def _f(x):
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


MODES = {"investor": "مستثمر", "trader": "مضارب"}


def judge(pos: dict) -> dict:
    """‏D590: الحكمُ على الشركة واحد — للمستثمر والمضارب معاً (بأمر المالك: «مصلحتُهما واحدة، والفرقُ مدّةُ توظيف رأس المال»).

    قِيس: كان للمضارب قواعدُ مستقلّة (دعمٌ أسبوعيٌّ وسيولة)، فيقول «فرصة» عن شركةٍ نتائجُها سيئةٌ ومسارُها هابط
    وهو نفسُه يقول للمستثمر «لا». فصار الحكمُ واحداً، ولا يملك الوضعُ نقضَه:
      · لا شراءَ إن كان قرارُ التطبيق تجنّباً، أو آخرُ ربعٍ خاسراً، أو الشهريُّ هابطاً والقرارُ ليس شراء،
        أو السعرُ عند مقاومةٍ أسبوعيةٍ أو شهرية، أو فوق قيمته العادلة **حين تكون ثقتُها متوسطةً فأعلى**
        (السعرُ العادلُ بثقةٍ منخفضة لا يحجب ولا يجيز وحدَه — قِيس: 193 تقديراً من 267 ثقتُها منخفضة).
      · ولا تعديلَ متوسّطٍ في شركةٍ شهريُّها هابطٌ وقرارُها ليس شراء."""
    p, c, fv = _f(pos.get("price")), _f(pos.get("avg_cost")), _f(pos.get("fair_value"))
    conf = str(pos.get("fair_value_conf") or "")
    fv_ok = bool(fv) and conf in ("متوسطة", "مرتفعة")
    dec = str(pos.get("decision") or "")
    W, M = pos.get("weekly") or {}, pos.get("monthly") or {}
    buy, avoid = "شراء" in dec, any(w in dec for w in ("تجنب", "تجنّب", "بيع"))
    lr = pos.get("last_result") or {}
    q_loss = isinstance(lr.get("net_income_q"), (int, float)) and lr["net_income_q"] < 0
    m_down = M.get("state") == "هابط"
    at_res = [n for n, x in (("أسبوعية", W), ("شهرية", M)) if x.get("where") in ("داخل منطقة المقاومة", "فوق المقاومة")]
    blocks, notes = [], []
    if avoid:
        blocks.append(f"قرار التطبيق {dec}")
    if q_loss:
        blocks.append(f"آخر ربعٍ خاسر ({lr.get('as_of')})")
    if m_down and not buy:
        blocks.append(f"الشهري هابط والقرار {dec or 'غير متوفّر'}")
    if at_res:
        blocks.append("السعر عند مقاومة " + " و".join(at_res))
    if fv_ok and p and p > fv:
        blocks.append(f"السعر {p:.2f} فوق قيمته العادلة {fv:.2f}")
    elif fv and not fv_ok:
        notes.append("قيمتُه العادلة بثقةٍ منخفضة — لا يُبنى عليها وحدَها")
    can_buy = buy and not blocks
    return {"can_buy": can_buy, "blocks": blocks, "notes": notes, "buy": buy, "avoid": avoid, "m_down": m_down,
            "fv_ok": fv_ok, "q_loss": q_loss}


def rules(pos: dict, mode: str = "investor") -> dict:
    """‏D591 (بأمر المالك — حُذف مفتاحُ مستثمر/مضارب): يفكّر على المدى البعيد كمستثمر، ويدخل بحذر المضارب.
    «اشترِ» قرارٌ مدعومٌ بقناعةٍ صحيحة لا هلوسة — لا تُقال إلا إن اجتمعت شروطُ القناعة كلُّها، وإلا «انتظر» بالناقص منها:
      ١ الحكمُ على الشركة يجيز الشراء (judge: القرار شراء، لا ربعَ خاسر، لا مقاومة، لا سعرَ فوق قيمةٍ موثوقة)
      ٢ الشهريُّ غيرُ هابط
      ٣ السعرُ داخلَ منطقة الدعم الأسبوعية
      ٤ سيولةُ اليوم ليست جفافاً ولا تصريفاً ولا انهياراً
      ٥ هامشُ أمانٍ موثوق: قيمةٌ عادلةٌ بثقةٍ متوسطةٍ فأعلى فوق السعر بـ10% — أو جودةٌ ماليةٌ 70 فأعلى حين لا تُوثَق القيمة
    والهدفُ أفقُ مستثمر (القيمةُ العادلة أو المقاومةُ الشهرية)، ووقفُ الخسارة حذرُ مضارب (تحت الدعم الأسبوعيّ)."""
    j = judge(pos)
    p, c, fv = _f(pos.get("price")), _f(pos.get("avg_cost")), _f(pos.get("fair_value"))
    W, M = pos.get("weekly") or {}, pos.get("monthly") or {}
    q = _f(pos.get("quantity")) or 0
    cw, tw = _f(pos.get("current_weight")) or 0, _f(pos.get("target_weight")) or 0
    liq = str(pos.get("daily_liquidity") or "")
    quality = _f(pos.get("quality"))
    why = list(j["notes"])
    blocks = [f"لا شراء: {b}" for b in j["blocks"]]
    # ── التصفية ──
    if j["avoid"] and q:
        return {"action": "خفّف", "level": None, "why": why + [f"قرار التطبيق {pos.get('decision')}"], "blocks": blocks, "conviction": []}
    if cw > tw + 5 and tw > 0:
        return {"action": "خفّف", "level": None, "why": why + [f"وزنه {cw:.1f}% فوق هدفه {tw:.1f}%"], "blocks": blocks, "conviction": []}
    if q and c and p and M.get("where") in ("داخل منطقة المقاومة", "فوق المقاومة") and j["fv_ok"] and p >= fv * 1.05:
        return {"action": "صفِّ جزئياً", "level": M.get("resistance"), "blocks": blocks, "conviction": [],
                "why": why + [f"مقاومةٌ شهرية والسعر فوق قيمته العادلة بـ{(p / fv - 1) * 100:.0f}%"]}
    # ── شروطُ القناعة ──
    zone = W.get("support")
    upside = (fv / p - 1) * 100 if (fv and p) else None
    margin_ok = (j["fv_ok"] and upside is not None and upside >= 10) or (not j["fv_ok"] and quality is not None and quality >= 70)
    checks = [
        ("الحكم يجيز الشراء", j["can_buy"], "؛ ".join(j["blocks"]) or f"القرار {pos.get('decision') or 'غير متوفّر'}"),
        ("الشهري غير هابط", M.get("state") not in ("هابط", None, "غير متوفّر"), f"الشهري {M.get('state') or 'غير متوفّر'}"),
        ("السعر في الدعم الأسبوعي", bool(zone and p and zone[0] * 0.99 <= p <= zone[1] * 1.03),
         f"الدعم {zone[0]:.2f}–{zone[1]:.2f}" if zone else "لا دعم محسوب"),
        ("السيولة تدعم الدخول", liq not in ("جفاف سيولة", "تصريف بيعي", "انهيار بيعي", ""), f"سيولة اليوم {liq or 'غير متوفّرة'}"),
        ("هامش أمان موثوق", bool(margin_ok),
         (f"القيمة العادلة {fv:.2f} (+{upside:.0f}%)" if j["fv_ok"] and upside is not None else f"الجودة {quality if quality is not None else 'غير متوفّرة'}")),
    ]
    ok = [n for n, v, _ in checks if v]
    missing = [f"{n}: {d}" for n, v, d in checks if not v]
    if not j["can_buy"]:
        return {"action": "لا تُضِف" if j["blocks"] else "احتفظ", "level": None, "why": why, "blocks": blocks, "conviction": ok}
    if missing:
        return {"action": "انتظر", "level": zone, "blocks": blocks, "conviction": ok,
                "why": why + ["الناقص من القناعة — " + " · ".join(missing)]}
    why.append("القناعة مكتملة: " + " · ".join(ok))
    tgt = fv if (j["fv_ok"] and fv and zone and fv > zone[1]) else (M.get("resistance") or [None])[0]
    if tgt and zone and tgt > zone[1]:
        why.append(f"الهدف {'القيمة العادلة' if tgt == fv else 'المقاومة الشهرية'} {tgt:.2f}، ووقف الخسارة تحت {zone[0] * 0.97:.2f}")
    need = _f(pos.get("need")) or 0
    if c and q and need > 0 and zone:
        mid = (zone[0] + zone[1]) / 2
        new_avg = (q * c + need) / (q + need / mid)
        why.append(f"الشراء بـ{need:,.0f} ريال عند {mid:.2f} " + (f"يخفض متوسطك من {c:.2f} إلى {new_avg:.2f}" if new_avg < c
                   else f"يرفع متوسطك من {c:.2f} إلى {new_avg:.2f} — مبرَّرٌ بالحكم لا بالمتوسط"))
    return {"action": "اشترِ الآن", "level": zone, "why": why, "blocks": blocks, "conviction": ok}


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


_AR_NUM = {"سنة": 1, "سنتين": 2, "سنتان": 2, "ثلاث": 3, "أربع": 4, "اربع": 4, "خمس": 5, "ست": 6, "سبع": 7,
           "ثمان": 8, "تسع": 9, "عشر": 10}


def years_in(question: str) -> int | None:
    """‏D606: «خلال أربع سنوات» · «في 5 سنين» · «بعد سنتين» ← عددُ السنوات المطلوبة للهدف."""
    import re
    q = question or ""
    m = re.search(r"(\d{1,2})\s*(?:سنوات|سنة|سنين|أعوام|عام|سنه)", q)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= 30 else None
    for w, n in _AR_NUM.items():
        if re.search(rf"{w}\S*\s*(?:سنوات|سنين|أعوام)", q) or (w in ("سنتين", "سنتان") and w in q):
            return n
    return None


def goal_plan(wealth: float, target: float, years: int, cagr_pct: float | None) -> dict:
    """‏D606: الهدفُ في موعدٍ يحدّده المالك — ما العائدُ المطلوب بلا ضخّ، وما الضخُّ الشهريّ المطلوب بعائده الحاليّ.
    بأمر المالك: «لا أريد بعد كم سنة يأتي الهدف — أريد الوصول خلال أربع سنوات: ماذا أفعل وأغيّر؟»"""
    if not wealth or wealth <= 0 or not target or years <= 0:
        return {}
    need = ((target / wealth) ** (1 / years) - 1) * 100
    r = (cagr_pct or 0) / 100
    grown = wealth * (1 + r) ** years
    gap = max(0.0, target - grown)
    if gap <= 0:
        monthly = 0.0
    elif r > 0:
        mr = (1 + r) ** (1 / 12) - 1
        monthly = gap * mr / ((1 + mr) ** (years * 12) - 1)
    else:
        monthly = gap / (years * 12)
    realism = ("في متناول المحفظة" if need <= 12 else "طموحٌ يحتاج انضباطاً وضخّاً" if need <= 20
               else "غيرُ واقعيٍّ بالعائد وحده — الضخُّ هو الطريق")
    return {"السنوات": years, "العائد_المطلوب_بلا_ضخ٪": round(need, 1), "عائدك_الحالي٪": round(cagr_pct, 1) if cagr_pct else None,
            "ما_تبلغه_بعائدك_الحالي": round(grown), "الفجوة": round(gap), "الضخ_الشهري_المطلوب": round(monthly),
            "الحكم": realism}


async def _events(sym: str) -> list[dict]:
    """مفكرةُ الشركة القادمة (المخزَّنةُ المجهَّزة) — أقربُ حدثين."""
    from app.api.v1.endpoints import market as M
    r = await M.get_company_events(sym, "")
    rows = (json.loads(r.body) if hasattr(r, "body") else r).get("data") or []
    # ‏D680: صفُّ المفكرة {headline, published, kind, date_kind} — وكان يُقرأ بـ«date/title» فلا قادمَ أبداً (قِيس: 0/14)
    today = date.today().isoformat()
    when = lambda e: str(e.get("published") or e.get("date") or "")[:10]   # noqa: E731
    up = sorted([e for e in rows if when(e) >= today], key=when)
    return [{"date": when(e), "title": str(e.get("headline") or e.get("title") or e.get("kind") or "")[:90]} for e in up[:2]]


async def _disclosures(sym: str) -> list[dict]:
    """آخرُ ثلاثة إفصاحاتٍ في «تداول» بعناوينها وتواريخها."""
    from app.services import tadawul_disclosure as D
    items = await D.list_for(sym, size=5)
    return [{"date": i.get("date"), "title": str(i.get("title") or "")[:110]} for i in (items or [])[:3]]


def _analysts(sym: str, price) -> dict | None:
    """‏D679: آراءُ بيوت الخبرة المرخّصة خلال سنة (أرقام · D664) — إجماعُ أهدافها وآخرُ توصية، كما في «التوقعات»."""
    import statistics
    from datetime import timedelta
    from app.services.analyst_opinions import for_symbol as _ops
    cut = (date.today() - timedelta(days=365)).isoformat()
    rows = [r for r in _ops(sym) if str(r.get("date") or "") >= cut]
    if not rows:
        return None
    tg = [r["target"] for r in rows if isinstance(r.get("target"), (int, float)) and r["target"] > 0]
    med = statistics.median(tg) if tg else None
    px = _f(price)
    last = rows[0]
    return {"آراء": len(rows), "بيوت": len({r.get("house") for r in rows}),
            "وسيط_الهدف": round(med, 2) if med else None,
            "المسافة_إلى_الوسيط٪": round((med / px - 1) * 100, 1) if (med and px) else None,
            "آخر_توصية": {"الجهة": last.get("house"), "التوصية": last.get("rating"), "الهدف": last.get("target"),
                          "التاريخ": last.get("date")}}


async def _stability(sym: str, sector: str | None) -> str | None:
    """‏D680: ثباتُ الأرباح من محرّك الحوكمة — المنتِجُ الذي تعرضه نافذتُها (‏D675) وبمفتاح ذاكرتها نفسِه (القطاعُ من الشركة)؛
    وكان يُطلب من «financial» في تحليل الشركة ولا يحمله، فغاب عن كلّ المراكز (قِيس: 0/14)."""
    from app.services.governance_engine import evaluate_company
    from app.api.v1.endpoints.holdings import yahoo_symbol
    g = await evaluate_company(yahoo_symbol(sym), sector=sector) or {}
    return (g.get("confidence") or {}).get("stability_label")


async def _material(sym: str) -> list[dict]:
    """‏D679: الأحداثُ الجوهرية لسنة (‏D644) — العقودُ والاستحواذاتُ والخسائرُ الجسيمة بقيمها كما في صفحة السهم."""
    # ‏D680: من عرض الصفحة نفسِه (‏events_view) — العنوانُ العربيُّ الرسميّ من صفحة الإفصاح، والحدثُ الواحد بندٌ واحد؛
    # وكان يُقرأ الخامُ فوصل المستشارَ عنوانٌ إنجليزيٌّ مُحرَّف («Alghaz Waltsnae Company …»)
    from app.services.events_view import for_display
    d = await for_display(sym, limit=3) or {}
    out = []
    for e in (d.get("events") or [])[:3]:
        x = {"التاريخ": e.get("date"), "النوع": e.get("kind_ar"), "العنوان": str(e.get("title") or "")[:90]}
        if e.get("value"):
            x["القيمة"] = e.get("value")
        out.append(x)
    return out


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
    _rows = (await db.execute(select(Company.symbol, Holding.quantity, Holding.average_cost, Company.sector)
                              .join(Holding, Holding.company_id == Company.id))).all()
    hold = {str(s): (float(q or 0), float(ac or 0)) for s, q, ac, _ in _rows}
    sector_of = {str(s).replace(".SR", ""): sec for s, _, _, sec in _rows}
    items = [it for it in d.get("items") or [] if float(it.get("market_value") or 0) > 0 or float(it.get("target_weight") or 0) > 0]
    investable = float(d.get("investable") or 0)

    async def one(it):
        sym = str(it["symbol"]).replace(".SR", "")
        a, t, ev, dis, me, stb = await asyncio.gather(asyncio.wait_for(analyze_company(f"{sym}.SR", None, db=None), timeout=20),
                                                 asyncio.wait_for(d7m.read(sym), timeout=30),
                                                 asyncio.wait_for(_events(sym), timeout=15),
                                                 asyncio.wait_for(_disclosures(sym), timeout=15),
                                                 asyncio.wait_for(_material(sym), timeout=20),
                                                 asyncio.wait_for(_stability(sym, sector_of.get(sym)), timeout=20),
                                                 return_exceptions=True)
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
               "fair_value": a.get("fair_value"), "fair_value_conf": a.get("fair_value_conf"),
               "quality": (a.get("financial") or {}).get("score"),
               "weekly": t.get("weekly"), "monthly": t.get("monthly"), "daily_liquidity": (t.get("daily_liquidity") or {}).get("state"),
               "last_result": ({"as_of": r.get("as_of"), "net_income_q": (r.get("quarter") or {}).get("net_income"),
                                "revenue_q": (r.get("quarter") or {}).get("revenue")} if r else None),
               "upcoming": ev if isinstance(ev, list) else [], "disclosures": dis if isinstance(dis, list) else []}
        # ‏D679 (بأمر المالك: «قادرٌ على شرب جميع المعلومات والبيانات داخل التطبيق»): ما تعرضه الشاشاتُ الأخرى عن الشركة
        try:
            from app.data.market_universe import MARKET_UNIVERSE
            pos["sector"] = (MARKET_UNIVERSE.get(sym) or {}).get("sector")
        except Exception:                                         # noqa: BLE001
            pass
        pos["stability"] = stb if isinstance(stb, str) else None
        pos["red_lines"] = [str(x.get("label") or x.get("title") or x) if isinstance(x, dict) else str(x)
                            for x in (a.get("red_lines") or [])][:3]
        pos["warnings"] = [str(x.get("label") or x.get("title") or x) if isinstance(x, dict) else str(x)
                           for x in (a.get("warnings") or [])][:3]
        pos["material_events"] = me if isinstance(me, list) else []
        try:
            pos["analysts"] = _analysts(sym, pos.get("price"))
        except Exception:                                         # noqa: BLE001
            pos["analysts"] = None
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
        from app.services.portfolio_return import unified_cagr_pct
        cagr = await unified_cagr_pct(db)                         # D605: الرقمُ نفسُه في المؤشرات المالية
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
    market = None
    try:
        from app.services.ai_content import get_market_brief_snapshot
        _b = get_market_brief_snapshot() or {}
        # مفاتيحُ اللقطة كما يكتبها refresh_market_brief (‏D679: كانت تُقرأ «headline/mood/asof» ولا وجودَ لها)
        market = {k: (_b.get(k)[:5] if k == "headlines" and isinstance(_b.get(k), list) else _b.get(k))
                  for k in MARKET_KEYS if _b.get(k) is not None} or None
    except Exception:                                             # noqa: BLE001
        pass
    attention = []
    try:
        from app.services.governance import get_portfolio_governance
        _g = await asyncio.wait_for(get_portfolio_governance(db), timeout=25) or {}
        attention = [(f"{x.get('name') or x.get('symbol') or ''}: {x.get('message') or ''}".strip(": ")
                      if isinstance(x, dict) else str(x)) for x in (_g.get("attention") or [])][:5]
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"الطيار الآليّ — الحوكمة: {type(e).__name__}")
    flags = []
    top = max(positions, key=lambda x: float(x.get("current_weight") or 0), default=None)
    if top and float(top.get("current_weight") or 0) > 25:
        flags.append(f"تركّز: {top['name']} {float(top['current_weight']):.1f}% من المحفظة")
    buys = [p for p in positions if p["autopilot"]["action"].startswith(("اشترِ", "انتظر السيولة"))]
    if investable and cash / investable > 0.15 and buys:
        flags.append(f"سيولة معطّلة {cash:,.0f} ريال ({cash / investable * 100:.0f}%) وأمامها {len(buys)} {'فرص' if 2 <= len(buys) <= 10 else 'فرصة'} شراء")
    return {"date": date.today().isoformat(), "wealth": round(wealth, 2), "cash": round(cash, 2), "cagr_pct": cagr,
            "goals": goals, "flags": flags, "positions": positions, "principles": principles(24), "mode": mode,
            "market": market, "attention": attention}


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
    n_buy = sum(1 for a in actions if a["action"].startswith(("اشترِ", "انتظر السيولة")))
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
    mode = "investor"                                            # ‏D591: لا مفتاح — رأيٌ واحد
    ck = f"autopilot:v4:{pid}:{date.today().isoformat()}"   # v4: D680 (القادمُ والثباتُ والأحداثُ بعناوينها العربية)
    if not force:
        hit = cache.get(ck)
        if hit:
            return hit
    pk = await pack(db, mode)
    base = render(pk)
    from app.services.ai_content import _generate_obj
    slim = {"الثروة": pk["wealth"], "السيولة": pk["cash"], "العائد المركّب٪": pk["cagr_pct"], "الأهداف": pk["goals"],
            "تنبيهات": pk["flags"], "نبض_السوق": pk.get("market"), "انتباه_الحوكمة": pk.get("attention"),
            "المراكز": [{k: p.get(k) for k in POS_KEYS} | {"قرار_الطيار": p["autopilot"]}
                        for p in pk["positions"]],
            "مبادئ_المكتبة": [f"{x['p']} — «{x['book']}» ص{x['page']}" for x in pk["principles"]]}
    lens = ("بعقل مستثمرٍ بعيد المدى يدخل بحذر مضارب: «اشترِ» لا تُقال إلا بقناعةٍ مكتملة الشروط (conviction)، "
            "وكلُّ «انتظر» يُسمّى ناقصُها.")
    prompt = f"""أنت الطيارُ الآليّ لمحفظة المالك: مستشارٌ ماليٌّ متخرّجٌ من مكتبته. تتكلّم الآن {lens}
هدفُك هدفُه: الوصولُ إلى أهداف المحفظة بأسرع وقتٍ ممكن دون مخاطرةٍ تهدم رأس المال، ومتوسّطُ التكلفة سلاحُك — تشتري عند الدعوم التاريخية وتصفّي عند المقاومات.

المعطياتُ (مصدرك الوحيد — لا رقمَ من خارجها):
{json.dumps(slim, ensure_ascii=False, default=str)}

قواعدُ ملزمة:
- «قرار_الطيار» لكلّ مركز حتميّ صادرٌ عن قواعد الحماية: لا تناقضه ولا تقترح شراءً فيما حُجب شراؤه. مهمّتك أن تشرحه وترتّب الأولويات.
- الإطاران الشهريُّ والأسبوعيُّ لأداة D7M هما الحكمُ الفنيّ، واليوميُّ لقراءة السيولة وحدها.
- استشهد بمبدأين أو ثلاثةٍ من مبادئ المكتبة حيث تنطبق فعلاً، باسم الكتاب ورقم الصفحة كما وردت.
- اقرأ مفكرةَ كلّ شركةٍ (upcoming) وإفصاحاتِها (disclosures) وآخرَ نتائجها: حدثٌ قريبٌ أو إفصاحٌ جوهريٌّ يغيّر التوقيت يُذكر.
- واقرأ لكلّ شركة: آراءَ بيوت الخبرة (analysts: وسيطُ أهدافها وآخرُ توصية)، وأحداثَها الجوهرية (material_events)، وخطوطَها
  الحمراء وتحذيراتِها (red_lines · warnings)، وثباتَ أرباحها (stability) — واذكر منها ما يغيّر الحكم. وثقةُ السعر العادل (fair_value_conf) تُقرأ:
  «منخفضة» لا يُبنى عليها وحدها. ونبضُ السوق وانتباهُ الحوكمة سياقٌ للمحفظة كلّها.
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
        obj = await _generate_obj(prompt, f"ai:autopilot:v4:{pid}:{date.today().isoformat()}:{len(pk['positions'])}", 6 * 3600)
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
    out["conviction"] = {p["symbol"]: p["autopilot"].get("conviction") for p in pk["positions"]}
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


# ══ ‏D589: حوارُ المستشار الآليّ — يخاطبه المالكُ بوجهة نظره، فيردّ بما لديه ══
# بأمر المالك: «سدافكو أفكّر بالخروج منها لأنها في مسارٍ هابط ورأسُ مالي قرض — أريد بديلاً في مسارٍ متوازن».
# فيُقرأ ما ذُكر من شركات (بالاسم المختصر أو الكامل أو الرمز)، ولكلٍّ: موقفُها الحقيقيّ على D7M، وكلفةُ الخروج عليه،
# وبدائلُ من قطاعها شرعيةٌ إن كانت شرعية، في مسارٍ شهريٍّ غير هابط، بجودتها وعائدها — والنموذجُ يحاور ولا يخترع.

def _directory() -> dict:
    import json as _j
    import pathlib
    try:
        p = pathlib.Path(__file__).resolve().parents[1] / "data" / "saudi_directory.json"
        return _j.loads(p.read_text(encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        return {}


_GENERIC = {"الشركة", "شركة", "السعودية", "السعودي", "العربية", "الوطنية", "مصرف", "بنك", "البنك", "صندوق", "مجموعة",
            "للتسويق", "الطبية", "للخدمات", "القابضة", "للتأمين", "التعاوني", "التعاونية", "للتنمية", "للاستثمار", "والأغذية",
            "الأهلية", "المتحدة", "الدولية", "المتقدمة", "للصناعات", "الصناعية", "لمنتجات", "الألبان", "خدمات", "ريت", "المالية"}


def mentioned(question: str, positions: list[dict], limit: int = 3) -> list[str]:
    """الرموزُ المذكورة: الرمزُ نفسُه، أو الاسمُ المختصر في الدليل، أو الاسمُ الكامل — الحيازاتُ أوّلاً."""
    q = " ".join(str(question or "").replace("ـ", "").split())
    found: list[tuple[int, str]] = []
    held = {p["symbol"] for p in positions}
    names = {p["symbol"]: [p.get("name") or ""] for p in positions}
    for sym, v in _directory().items():
        names.setdefault(str(sym), []).append((v or {}).get("name") or "")
    import re as _re

    def has(n: str) -> bool:
        return bool(_re.search(r"(?<![\w])(?:ال|بال|و|ب|ل)?" + _re.escape(n) + r"(?![\w])", q))

    full_hits: list[str] = []                # أسماءٌ كاملةٌ طوبقت — تُسقط ما طابق بكلمةٍ منها وحدها
    token_of: dict[str, str] = {}
    for sym, ns in names.items():
        score = 0
        if _re.search(r"(?<!\d)" + _re.escape(sym) + r"(?!\d)", q):
            score = 300
        for n in ns:
            n = " ".join(str(n).split())
            if len(n) < 3 or not has(n):
                continue
            # اسمٌ قصيرٌ بكلمةٍ واحدة خارجَ المحفظة قد يكون كلمةً عادية («في مسارٍ هابط» ليست شركة «مسار»)
            if sym not in held and " " not in n and len(n) <= 5 and not _re.search(r"(شركة|سهم|أسهم)\s+" + _re.escape(n), q):
                continue
            score = max(score, 200 + len(n))
            full_hits.append(n)
        if not score:
            # الكلمةُ المميِّزةُ من الاسم («جرير» من «جرير للتسويق»، «النهدي» من «النهدي الطبية»)
            for n in ns:
                for tok in str(n).split():
                    t = tok.strip("()،,.")
                    if len(t) >= 4 and t not in _GENERIC and has(t) and (sym in held or len(t) >= 6):
                        score = max(score, 150 + len(t))
                        token_of[sym] = t
        if score:
            found.append((score + (50 if sym in held else 0), sym))
    out = []
    for _, s in sorted(found, reverse=True):
        t = token_of.get(s)
        if t and any(t in fh.split() for fh in full_hits):
            continue                          # «الراجحي» داخلَ «الراجحي ريت» المطابَق كاملاً ⇒ ليست المصرفَ ولا التكافل
        if s not in out:
            out.append(s)
    return out[:limit]


async def _alt_paths(sym: str, n: int = 4) -> list[dict]:
    """بدائلُ من القطاع نفسِه بمسارها على D7M — «متوازن» = الشهريُّ غيرُ هابط والأسبوعيُّ غيرُ هابط."""
    from app.services import advisor_solutions as S
    from app.services import d7m
    rows = S._rows()
    alts = S.alternatives(sym, rows, n=8, margin=0)
    out = []
    for a in alts:
        try:
            t = await asyncio.wait_for(d7m.read(a["symbol"]), timeout=25) or {}
        except Exception:                                         # noqa: BLE001
            t = {}
        M, W = t.get("monthly") or {}, t.get("weekly") or {}
        # متوازنٌ بمسارٍ معلوم: الشهريُّ صاعدٌ أو ضعيف (لا هابط ولا «غير متوفّر») والأسبوعيُّ غيرُ هابط —
        # قِيس: المطاحن الرابعة (إدراجٌ حديث) شهريُّها «غير متوفّر» فعُدّت متوازنةً بلا بيّنة
        balanced = M.get("state") in ("صاعد", "ضعيف") and W.get("state") not in ("هابط", None, "غير متوفّر")
        out.append({"symbol": a["symbol"], "name": a.get("name"), "price": a.get("price"), "decision": a.get("decision"),
                    "quality": a.get("quality"), "dividend_yield": a.get("dy"), "upside": a.get("upside"),
                    "monthly": {k: M.get(k) for k in ("state", "where", "support", "resistance")} if M else None,
                    "weekly": {k: W.get(k) for k in ("state", "where", "support")} if W else None, "balanced": balanced})
    out.sort(key=lambda x: (not x["balanced"], -(x.get("quality") or 0)))
    return out[:n]


async def ask(db, question: str, mode: str = "investor", history: list | None = None) -> dict:
    from app.core.portfolio_scope import active_pid
    from app.services import cache
    mode = "investor"
    pid = active_pid()
    ck = f"autopilot:pack:v4:{pid}:{date.today().isoformat()}"
    pk = cache.get(ck)
    if not pk:
        pk = await pack(db, mode)
        cache.set(ck, pk, 3 * 3600)
    syms = mentioned(question, pk["positions"])
    focus = []
    for s in syms:
        pos = next((p for p in pk["positions"] if p["symbol"] == s), None)
        item = {"symbol": s, "held": bool(pos)}
        if pos:
            q, c, pr = _f(pos.get("quantity")) or 0, _f(pos.get("avg_cost")), _f(pos.get("price"))
            item.update({k: pos.get(k) for k in POS_KEYS + ("quantity",)})
            item["قرار_الطيار"] = pos["autopilot"]
            if q and c and pr:
                item["كلفة_الخروج"] = {"قيمة_البيع": round(q * pr, 2), "المدفوع": round(q * c, 2),
                                       "ربح_أو_خسارة_تُثبَّت": round(q * (pr - c), 2), "النسبة٪": round((pr / c - 1) * 100, 1)}
        else:
            try:
                from app.services import d7m
                from app.services.analysis import analyze_company
                a = await asyncio.wait_for(analyze_company(f"{s}.SR", None), timeout=20) or {}
                t = await asyncio.wait_for(d7m.read(s), timeout=25) or {}
                item.update({"name": a.get("name"), "price": a.get("price"), "decision": (a.get("decision") or {}).get("label"),
                             "fair_value": a.get("fair_value"), "fair_value_conf": a.get("fair_value_conf"),
                             "quality": (a.get("financial") or {}).get("score"),
                             "weekly": t.get("weekly"), "monthly": t.get("monthly"),
                             "daily_liquidity": (t.get("daily_liquidity") or {}).get("state")})
                try:                                              # ‏D679: وما تعرضه الشاشاتُ عنها
                    item["analysts"] = _analysts(s, a.get("price"))
                    item["material_events"] = await asyncio.wait_for(_material(s), timeout=20)
                except Exception:                                 # noqa: BLE001
                    pass
            except Exception:                                     # noqa: BLE001
                pass
        try:
            item["بدائل_من_قطاعها"] = await _alt_paths(s)
        except Exception:                                         # noqa: BLE001
            item["بدائل_من_قطاعها"] = []
        focus.append(item)
    plan = None
    yrs = years_in(question)
    if yrs:
        g = next((x for x in pk["goals"] if x.get("target")), None)
        if g:
            plan = {"الهدف": g["name"], "المبلغ": g["target"], **goal_plan(pk["wealth"], g["target"], yrs, pk["cagr_pct"])}
    ctx = {"الثروة": pk["wealth"], "السيولة": pk["cash"], "العائد_المركّب٪": pk["cagr_pct"], "خطة_الهدف_في_موعد": plan,
           "نبض_السوق": pk.get("market"), "انتباه_الحوكمة": pk.get("attention"),
           "الأهداف": pk["goals"], "تنبيهات": pk["flags"], "الشركات_المذكورة": focus,
           "بقية_المحفظة": [{"name": p["name"], "symbol": p["symbol"], "action": p["autopilot"]["action"],
                              "weight": p.get("current_weight")} for p in pk["positions"] if p["symbol"] not in syms],
           "مبادئ_المكتبة": [f"{x['p']} — «{x['book']}» ص{x['page']}" for x in pk["principles"]]}
    hist = "\n".join(f"{'المالك' if h.get('role') == 'user' else 'المستشار'}: {str(h.get('text'))[:400]}"
                     for h in (history or [])[-6:])
    hist_block = ("المحادثةُ السابقة:\n" + hist) if hist else ""
    lens = "بعقل مستثمرٍ بعيد المدى يدخل بحذر مضارب"
    prompt = f"""أنت المستشارُ الآليّ لمحفظة المالك، تحاوره {lens}. يكلّمك بوجهة نظره، وتردّ كمستشارٍ أمين: توافقه إن صدقت الأرقام، وتخالفه صراحةً إن خالفته — ولا تجامله.

المعطياتُ (مصدرك الوحيد — لا رقمَ ولا شركةَ من خارجها):
{json.dumps(ctx, ensure_ascii=False, default=str)}
{hist_block}

كلامُ المالك الآن: {question}

قواعد:
- ابدأ بالحكم في جملةٍ واحدة: هل أوافقه أم لا، ولماذا بالرقم.
- إن ذكر مساراً هابطاً فتحقّق من D7M الشهريّ والأسبوعيّ وقل ما تراه فعلاً. وإن كان السعرُ في دعمٍ فقُل إنّ البيعَ في القاع يثبّت الخسارة، واذكرها من «كلفة_الخروج».
- البدائلُ من «بدائل_من_قطاعها» وحدها؛ قدّم المتوازنةَ (balanced) واذكر لكلٍّ مسارَه وجودتَه وعائدَه. وإن لم يوجد بديلٌ متوازنٌ فقُل ذلك.
- بديلٌ مسارُه الشهريّ «غير متوفّر» (إدراجٌ حديث) لا تصفه بالمتوازن: قل إنّ تاريخه لا يكفي للحكم الشهريّ.
- الخسارةُ قبل البيع غيرُ محقّقة: قل «البيعُ يُثبّت خسارةً قدرها…» لا «خسارةٌ محقّقة». ونسبتُها من كلفة المركز («من كلفتك فيها») لا من رأس المال كلِّه.
- إن ذكر أنّ رأسَ ماله قرضٌ أو دَين: حمايةُ رأس المال أوّلاً، وتفضيلُ الجودة والتوزيع المنتظم، وتجنّبُ ما يحتاج سنواتٍ ليتعافى، ولا رافعةَ فوق القرض.
- «قرار_الطيار» حتميّ: لا تنصح بشراءٍ حجبته الحماية.
- لا تقل «اشترِ» أو «ادخل» إلا لما «قرار_الطيار» فيه «اشترِ الآن» (قناعةٌ مكتملة). وكلُّ ما سواه «انتظر» مع ذكر الناقص من القناعة كما ورد.
- إن ذكر شركةً لا معطياتَ لها فقُل «غير متوفّر» ولا تخمّن.
- آراءُ بيوت الخبرة (analysts) والأحداثُ الجوهرية والخطوطُ الحمراء شواهدُ تُذكر بأرقامها حين تؤيّد كلامَه أو تخالفه.
- إن كانت «خطة_الهدف_في_موعد» حاضرة فهو يسأل: كيف أبلغ الهدف في هذا الموعد؟ فأجب بأرقامها: العائدُ المطلوب بلا ضخّ مقابل عائده الحاليّ،
  والضخُّ الشهريّ المطلوب، وحكمُ الواقعية. ثمّ ما يغيّره عملياً في المحفظة: أيُّ مراكزَ تُعاد إلى أوزانها، وأين يذهب الضخّ (ما «قرار_الطيار» فيه «اشترِ الآن» وحده)،
  وما يُخفَّف. لا تعِد بعائدٍ لم يحقّقه، ولا ترفع المخاطرة لتعويض الوقت.
- جملٌ قصيرة (أربع عشرة كلمة على الأكثر)، بصيغة المتكلّم، بلا تحوّطٍ ولا إخلاءِ مسؤولية، في ستّة أسطرٍ إلى عشرة.
- اختم بسطرٍ واحد: «ما أفعله لو كنتُ مكانك: …».

اكتب الردّ نصّاً عربياً مباشراً بلا عناوين ولا رموز تنسيق."""
    from app.core.config import settings
    from app.services.usage_tracker import can_call, record
    reply, source = None, "rules"
    if settings.AI_API_KEY and can_call("gemini"):
        import httpx
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.25, "maxOutputTokens": 1400}}
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent"
               f"?key={settings.AI_API_KEY}")
        for i in range(2):
            try:
                record("gemini")
                async with httpx.AsyncClient(timeout=60) as c:
                    r = await c.post(url, json=body)
                if r.status_code in (429, 500, 503) and i == 0:
                    await asyncio.sleep(4)
                    continue
                if r.status_code == 200:
                    reply = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    reply = reply.replace("**", "").replace("##", "")
                    source = "ai"
                break
            except Exception as e:                                # noqa: BLE001
                logger.warning(f"حوار المستشار: {type(e).__name__}")
                break
    if not reply:
        reply = _ask_rules(focus, mode) if focus or not plan else _plan_text(plan)
    return {"reply": reply, "source": source, "mentioned": [{"symbol": f["symbol"], "name": f.get("name")} for f in focus],
            "alternatives": [{"for": f["symbol"], **a} for f in focus for a in (f.get("بدائل_من_قطاعها") or []) if a.get("balanced")][:4]}


def _plan_text(p: dict) -> str:
    """الردُّ من الأرقام وحدها حين يتعذّر النموذج — خطةُ الهدف في موعد."""
    lines = [f"لبلوغ {p.get('الهدف')} ({p.get('المبلغ'):,.0f} ريال) خلال {p['السنوات']} سنوات:",
             f"تحتاج عائداً مركّباً {p['العائد_المطلوب_بلا_ضخ٪']}٪ سنوياً بلا ضخّ — {p['الحكم']}."]
    if p.get("عائدك_الحالي٪") is not None:
        lines.append(f"بعائدك الحاليّ {p['عائدك_الحالي٪']}٪ تبلغ {p['ما_تبلغه_بعائدك_الحالي']:,} ريال.")
    if p.get("الفجوة"):
        lines.append(f"الفجوة {p['الفجوة']:,} ريال، تُسدّ بضخٍّ شهريٍّ نحو {p['الضخ_الشهري_المطلوب']:,} ريال.")
    else:
        lines.append("عائدك الحاليّ يكفي إن ثبت — حافظ على الأوزان ولا ترفع المخاطرة.")
    return "\n".join(lines)


def _ask_rules(focus: list[dict], mode: str) -> str:
    """الردُّ من الأرقام وحدها حين يتعذّر النموذج."""
    if not focus:
        return "لم أتعرّف على شركةٍ في كلامك. اذكر اسمها أو رمزها، وأردّ عليك بأرقامها."
    lines = []
    for f in focus:
        M, W = f.get("monthly") or {}, f.get("weekly") or {}
        lines.append(f"{f.get('name') or f['symbol']}: الشهري {M.get('state') or 'غير متوفّر'} ({M.get('where') or '—'})، "
                     f"والأسبوعي {W.get('state') or 'غير متوفّر'} ({W.get('where') or '—'}).")
        ce = f.get("كلفة_الخروج")
        if ce:
            v = ce["ربح_أو_خسارة_تُثبَّت"]
            lines.append(f"الخروج الآن {'يثبّت خسارة' if v < 0 else 'يثبّت ربحاً'} {abs(v):,.0f} ريال ({ce['النسبة٪']:+.1f}%).")
        ap = f.get("قرار_الطيار")
        if ap:
            lines.append(f"قرار الطيار: {ap['action']}" + (f" — {'؛ '.join(ap['why'])}" if ap.get("why") else "") + ".")
        bal = [a for a in f.get("بدائل_من_قطاعها") or [] if a.get("balanced")]
        if bal:
            lines.append("بدائل متوازنة من قطاعها: " + "، ".join(
                f"{a['name']} (جودة {a.get('quality')}، الشهري {(a.get('monthly') or {}).get('state')})" for a in bal[:3]) + ".")
        else:
            lines.append("لا بديل متوازن في قطاعها بمعايير التطبيق الآن.")
    return "\n".join(lines)
