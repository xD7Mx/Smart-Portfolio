"""«نجوم تاسي 20» — سلّةُ عشرين شركةً بقاعدة المالك (D522).

قال المالك: «المعيارُ الأساسيّ هو التفوّقُ على تاسي، وأن يكون توقّعُه
لاثني عشر شهراً القادمة قويّاً وذا مصداقيةٍ استثماريةٍ فذّة».

فالقاعدةُ ثلاثُ بوّابات، كلُّها من حقولٍ لها مصدرٌ في التطبيق، ثمّ ترتيب:

  ١· **التفوّقُ على تاسي**: عائدُ السهم في اثني عشر شهراً أعلى من عائد تاسي
     في المدّة نفسِها (من التاريخ اليوميّ الواحد `market_service.get_history`).
  ٢· **توقّعٌ قويّ للاثني عشر شهراً**: سعرُنا العادلُ فوق السعر بـ‎15٪ فأكثر
     (`fair_value_upside_pct` من المحرّك الواحد).
  ٣· **مصداقيةٌ فذّة**: ثقةُ التقييم ليست «منخفضة»، والدرجةُ المالية ‎70 فأكثر،
     ولا خطَّ أحمر، وآخرُ قوائم منشورةٌ خلال ‎270 يوماً (قاعدةُ الأشهر التسعة)،
     وليست «غيرَ متوافقة» شرعاً.

ثمّ يُرتَّب الناجون بمجموعٍ متساوي الأجزاء: الفجوةُ إلى العادل (سقفُها ‎50٪)
والتفوّقُ على تاسي (سقفُه ‎50 نقطة) والدرجةُ المالية — ويؤخذ الأعلى عشرون.
الأوزانُ متساوية (الافتراضيّ إلى أن يقرّر المالكُ غيرَه).

والسلّةُ **تُثبَّت** بتاريخ بنائها وأسعارِه، ويُقاس أداؤها منذئذٍ مقابلَ تاسي؛
وتُعاد **شهرياً** مع ربط المؤشّر بالفترة السابقة — فلا يُعاد اختيارُ الرابحين
بأثرٍ رجعيٍّ فيُجمَّل الأداء.

ومن نمط InvestingPro (صورُ المالك · «نجوم تاسي» عندهم): الشركاتُ الكبيرة وحدَها
(أكبرُ ‎100 بالقيمة السوقية من لقطة «تداول»)، وإعادةُ التوازن شهرية، وبطاقةُ
أداءٍ بمنحنى مقابلَ تاسي ومكرّرِ ربحيةٍ لكلّ عضو. أمّا «الاختبارُ التاريخيّ منذ
2015» فلا يُحاكى: لا سعرَ عادلاً تاريخياً في التطبيق لكلّ شهر، ومحاكاتُه
بأرقام اليوم انحيازُ نظرٍ للخلف يُجمّل العائد. فالسجلُّ حيٌّ من يوم التثبيت.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from loguru import logger

STORE_KEY = "stars:tasi20"
SIZE = 20
MIN_UPSIDE = 15.0
MIN_SCORE = 70.0
MAX_STMT_DAYS = 270
REBALANCE_DAYS = 30
LARGE_N = 100            # «شركاتٌ كبيرة»: أكبرُ مئةٍ بالقيمة السوقية
CAP_UPSIDE = 50.0
CAP_EXCESS = 50.0


def _ret_12m(points: list | None) -> float | None:
    pts = [p for p in (points or []) if isinstance(p, dict) and p.get("close")]
    if len(pts) < 20:
        return None
    # ‏D525: تاريخُ تاسي من «تداول» أقلُّ نقاطاً من ياهو — فيُقاس امتدادُ التاريخ لا عددُ نقاطه.
    try:
        span = (date.fromisoformat(str(pts[-1].get("date"))[:10]) - date.fromisoformat(str(pts[0].get("date"))[:10])).days
    except ValueError:
        span = 365 if len(pts) >= 200 else 0
    if span < 330:
        return None
    return (pts[-1]["close"] / pts[0]["close"] - 1) * 100


def _main_share(sym) -> bool:
    """سهمٌ في السوق الرئيسة لا «نمو» ولا صندوق — من المصنّف الواحد."""
    from app.data.universe import is_etf, is_main
    return is_main(sym) and not is_etf(sym)


WATCH = 10               # ‏D539: المرتبةُ 21–30 تحت المراقبة
WEIGHTS = {"excess": 0.50, "upside": 0.25, "quality": 0.15, "confidence": 0.10}   # (قبل D540 — متروكٌ للتوثيق)
CONF = {"مرتفعة": 1.0, "متوسطة": 0.6, "منخفضة": 0.2}


def eligible(r: dict) -> bool:
    """شروطُ الأمان وحدها ملزمة (D539): الشرعيةُ · القوائمُ خلال 9 أشهر · بلا خطٍّ
    أحمر · سعرٌ عادلٌ فوق السعر · درجةٌ مالية. والباقي ترتيبٌ لا شرط."""
    up, fs = r.get("fair_value_upside_pct"), r.get("finance_score")
    age = r.get("stmt_age_days")
    # ‏D542: تقييمٌ يزيد على ضعف السعر بثقةٍ منخفضة شاذٌّ لا يُختار عليه نجم
    # (صافولا +194٪ · ساسكو +223٪ · الدواء +146٪ — مضاعفُ مبيعاتِ الأقران على هامشٍ منخفض).
    if isinstance(up, (int, float)) and up > 100 and r.get("fair_value_conf") in (None, "منخفضة"):
        return False
    return (isinstance(up, (int, float)) and up > 0
            and isinstance(fs, (int, float))
            and not (r.get("red_lines") or 0)
            and isinstance(age, (int, float)) and age <= MAX_STMT_DAYS
            and r.get("sharia") != "NON_COMPLIANT"
            and _main_share(r.get("symbol")))


def _pct_rank(vals: list[float]) -> list[float]:
    """الرتبةُ المئوية (0–1) لكلّ قيمةٍ بين أقرانها — الأعلى 1."""
    n = len(vals)
    if n <= 1:
        return [1.0] * n
    # المتساويان في القيمة متساويان في الرتبة (متوسطُ مواضعهما) — لا يُفضَّل أحدُهما بترتيب الإدخال.
    order = sorted(range(n), key=lambda i: vals[i])
    out = [0.0] * n
    k = 0
    while k < n:
        j = k
        while j + 1 < n and vals[order[j + 1]] == vals[order[k]]:
            j += 1
        for q in range(k, j + 1):
            out[order[q]] = ((k + j) / 2) / (n - 1)
        k = j + 1
    return out


def _cap(sym: str, v: dict) -> float | None:
    """القيمةُ السوقية من «تداول»، وإن غابت خارجَ الجلسة: السعرُ × الأسهمِ المنشورة."""
    c = (v or {}).get("market_cap")
    if isinstance(c, (int, float)) and c > 0:
        return c
    px = (v or {}).get("price")
    try:
        from app.services import tadawul_xbrl
        rows = tadawul_xbrl.for_symbol(sym, "annual") or tadawul_xbrl.for_symbol(sym, "quarterly")
        sh = next((p.get("shares_outstanding") for p in reversed(rows or []) if p.get("shares_outstanding")), None)
    except Exception:                                             # noqa: BLE001
        sh = None
    return px * sh if isinstance(px, (int, float)) and isinstance(sh, (int, float)) and px > 0 and sh > 0 else None


def large_caps(snap: dict[str, dict]) -> set[str]:
    caps = sorted(((_cap(k, v) or 0, k) for k, v in (snap or {}).items() if _main_share(k)), reverse=True)
    return {k for c, k in caps[:LARGE_N] if c > 0}


async def bonus_symbols() -> set[str]:
    """رموزُ من أعلنت منحةَ أسهمٍ في سنتين (D540) — من أحداث السوق المحفوظة."""
    try:
        from sqlalchemy import select as _sel
        from app.core.database import AsyncSessionLocal
        from app.models.market import MarketEvent, MarketEventType
        since = datetime.now(timezone.utc) - timedelta(days=730)
        async with AsyncSessionLocal() as db:
            res = await db.execute(_sel(MarketEvent.company_symbol).where(
                MarketEvent.event_type == MarketEventType.BONUS, MarketEvent.event_date >= since))
            return {str(x).replace(".SR", "") for x in res.scalars().all() if x}
    except Exception:                                             # noqa: BLE001
        return set()


def rank(rows: list[dict], rets: dict[str, float], tasi_ret: float,
         large: set[str] | None = None, snap: dict | None = None, bonus: set[str] | None = None) -> list[dict]:
    """الترتيبُ الكامل بنموذج العائلات الثماني (D540) — دالّةٌ نقيّةٌ يقيسها الحارس."""
    from app.services.stars_factors import score_all
    cands = []
    for r in rows or []:
        s = str(r.get("symbol") or "")
        if not eligible(r) or rets.get(s) is None or (large and s not in large):
            continue
        cands.append({**r, "ret_12m": rets[s]})
    if not cands:
        return []
    scores = score_all(cands, bonus)
    out = []
    for r in cands:
        s = str(r["symbol"])
        sc = scores.get(s) or {"score": 0, "families": {}}
        out.append({"symbol": s, "name": r.get("name"), "sector": r.get("sector"),
                    "price": r.get("price"), "fair_value": r.get("fair_value"),
                    "upside": r["fair_value_upside_pct"], "ret_12m": round(r["ret_12m"], 1),
                    "excess": round(r["ret_12m"] - tasi_ret, 1), "finance_score": r["finance_score"],
                    "confidence": r.get("fair_value_conf"), "sharia": r.get("sharia"),
                    "score": sc["score"], "families": sc["families"],
                    "pe": r.get("pe_ratio") or ((snap or {}).get(s) or {}).get("pe_ratio"),
                    "market_cap": _cap(s, (snap or {}).get(s) or {})})
    out.sort(key=lambda x: -x["score"])
    for k, m in enumerate(out, 1):
        m["rank"] = k
    return out


def select(rows: list[dict], rets: dict[str, float], tasi_ret: float,
           large: set[str] | None = None, snap: dict | None = None, bonus: set[str] | None = None) -> list[dict]:
    return rank(rows, rets, tasi_ret, large, snap, bonus)[:SIZE]


def _load() -> dict | None:
    from app.services import lastgood
    rec = lastgood.load(STORE_KEY)
    return rec if isinstance(rec, dict) and rec.get("members") else None


async def build(force: bool = False) -> dict:
    """يبني السلّةَ إن لم توجد أو شاخت ربعاً — وإلا يُبقيها كما هي."""
    from app.services import lastgood
    from app.services.market_data import market_service
    from app.services.market_screener import get_cached_screener

    old = _load()
    today = date.today()
    if old and not force and (today - date.fromisoformat(old["since"])).days < REBALANCE_DAYS:
        return old
    rows = get_cached_screener() or []
    tasi_pts = await market_service.get_history("^TASI.SR", "1y")
    tasi_ret = _ret_12m(tasi_pts)
    if tasi_ret is None:
        # ‏D538: حصّةُ ياهو اليومية نفدت — فيُقرأ تاريخُ تاسي بالنداء المباشر الذي
        # يقرأ به الفرزُ تاريخَ الأسهم، ويُقصّ على آخر سنة.
        try:
            raw = await market_service._yahoo()._fetch_chart_points("^TASI.SR", "2y", "1d")
            cut = (date.today() - timedelta(days=366)).isoformat()
            tasi_pts = [p for p in raw or [] if str(p.get("date"))[:10] >= cut]
            tasi_ret = _ret_12m(tasi_pts)
        except Exception:                                         # noqa: BLE001
            tasi_ret = None
    if tasi_ret is None or not rows:
        return old or {"error": "تاريخُ تاسي أو صفوفُ الفرز غيرُ متوفّرة"}
    from app.services.tadawul_market import usable_rows
    snap = usable_rows()[0] or {}
    large = large_caps(snap) or None
    rets: dict[str, float] = {}
    for r in rows:
        if eligible(r) and (large is None or str(r["symbol"]) in large):
            v = r.get("ret_12m")
            if not isinstance(v, (int, float)):
                v = _ret_12m(await market_service.get_history(f"{r['symbol']}.SR", "1y"))
            if v is not None:
                rets[str(r["symbol"])] = v
    ranked = rank(rows, rets, tasi_ret, large, snap, await bonus_symbols())
    members = ranked[:SIZE]
    if not members:
        return old or {"error": "لا شركةَ تجتاز القاعدةَ اليوم"}
    # ربطُ المؤشّر: مستوى السلّة السابقة يُحمَل فلا يبدأ كلُّ ربعٍ من الصفر.
    level, tlevel = 100.0, 100.0
    history = list((old or {}).get("history") or [])
    if old and old.get("since") == today.isoformat():
        history = [h for h in history if h.get("since") != h.get("until")]   # D542: بناءٌ ثانٍ في اليوم نفسِه لا يُسجَّل فترة
        old = {**old, "_same_day": True}
    if old and not old.get("_same_day"):
        perf = performance(old, rows, tasi_pts[-1]["close"])
        if perf.get("level") is not None:
            level = perf["level"]
            tlevel = perf.get("tasi_level") or tlevel
            history.append({"since": old["since"], "until": today.isoformat(),
                            "ret": perf["ret"], "tasi_ret": perf.get("tasi_ret")})
    rec = {"since": today.isoformat(), "level_start": level, "tasi_level_start": tlevel,
           "inception": (old or {}).get("inception") or today.isoformat(),
           "track": list((old or {}).get("track") or [])[-800:],
           "weighting": "متساوية", "rebalance": "شهرياً", "universe": f"أكبرُ {LARGE_N} بالقيمة السوقية",
           "tasi_start": tasi_pts[-1]["close"], "tasi_ret_12m": round(tasi_ret, 1),
           "members": [{**m, "start_price": m["price"]} for m in members],
           "watch": ranked[SIZE:SIZE + WATCH],
           "history": history[-20:],
           "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    lastgood.save(STORE_KEY, rec)
    logger.info(f"⭐ نجوم تاسي: {len(members)} شركةً · تاسي 12ش {tasi_ret:.1f}٪")
    return rec


def performance(rec: dict, rows: list[dict], tasi_now) -> dict:
    """عائدُ السلّة بأوزانٍ متساوية منذ بنائها، مقابلَ تاسي."""
    px = {str(r.get("symbol")): r.get("price") for r in rows or []}
    rs = []
    for m in rec.get("members") or []:
        p, p0 = px.get(m["symbol"]), m.get("start_price")
        if isinstance(p, (int, float)) and isinstance(p0, (int, float)) and p0 > 0:
            rs.append((p / p0 - 1) * 100)
    if not rs:
        return {"ret": None, "level": None}
    ret = sum(rs) / len(rs)
    t0 = rec.get("tasi_start")
    tret = ((tasi_now / t0 - 1) * 100) if isinstance(tasi_now, (int, float)) and t0 else None
    tl = ((rec.get("tasi_level_start") or 100) * (1 + tret / 100)) if tret is not None else None
    return {"ret": round(ret, 2), "tasi_ret": round(tret, 2) if tret is not None else None,
            "level": round((rec.get("level_start") or 100) * (1 + ret / 100), 2),
            "tasi_level": round(tl, 2) if tl is not None else None,
            "priced": len(rs)}


async def get() -> dict:
    from app.services.market_screener import get_cached_screener
    from app.services.tadawul_market import index_quote
    rec = await build()
    if not rec.get("members"):
        return rec
    rows = get_cached_screener() or []
    q = None
    try:
        q = (await index_quote() or {}).get("price")
    except Exception:                                             # noqa: BLE001
        q = None
    live = {str(r.get("symbol")): r for r in rows}
    members = [{**m, "price": (live.get(m["symbol"]) or {}).get("price", m.get("price")),
                "fair_value": (live.get(m["symbol"]) or {}).get("fair_value", m.get("fair_value"))}
               for m in rec["members"]]
    perf = performance(rec, rows, q)
    # ══ السجلُّ الحيّ: نقطةٌ يوميةٌ واحدة (المستوى والتاسي بأساس 100) ══
    today = date.today().isoformat()
    if perf.get("level") is not None and perf.get("tasi_level") is not None:
        track = [t for t in (rec.get("track") or []) if t.get("d") != today]
        track.append({"d": today, "s": perf["level"], "t": perf["tasi_level"]})
        rec["track"] = track[-800:]
        from app.services import lastgood
        lastgood.save(STORE_KEY, {k: v for k, v in rec.items() if k != "perf"})
    lv, tl = perf.get("level"), perf.get("tasi_level")
    summary = {"total": round(lv - 100, 2) if lv is not None else None,
               "tasi_total": round(tl - 100, 2) if tl is not None else None}
    summary["excess"] = (round(summary["total"] - summary["tasi_total"], 2)
                         if None not in (summary["total"], summary["tasi_total"]) else None)
    # ══ القادمةُ والخارجةُ هذا الشهر (D539) — ترتيبٌ حيٌّ يوميّ مقابلَ السلّة المثبَّتة ══
    entering, exiting, watch = [], [], rec.get("watch") or []
    try:
        from app.services.tadawul_market import usable_rows
        snap = usable_rows()[0] or {}
        rets = {str(r.get("symbol")): r["ret_12m"] for r in rows if isinstance(r.get("ret_12m"), (int, float))}
        tr = rec.get("tasi_ret_12m")
        if rets and isinstance(tr, (int, float)):
            live = rank(rows, rets, tr, large_caps(snap) or None, snap, await bonus_symbols())
            top = {m["symbol"] for m in live[:SIZE]}
            mem = {m["symbol"] for m in rec["members"]}
            entering = [m for m in live[:SIZE] if m["symbol"] not in mem]
            exiting = [m for m in members if m["symbol"] not in top]
            watch = [m for m in live[SIZE:SIZE + WATCH] if m["symbol"] not in mem]
    except Exception:                                             # noqa: BLE001
        pass
    nxt = (date.fromisoformat(rec["since"]) + timedelta(days=REBALANCE_DAYS)).isoformat()
    return {**rec, "members": members, "perf": perf, "summary": summary,
            "entering": entering, "exiting": exiting, "watch": watch, "next_rebalance": nxt}
