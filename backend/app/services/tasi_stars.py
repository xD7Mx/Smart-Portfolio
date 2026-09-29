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
وتُعاد كلَّ ربعٍ (‏90 يوماً) مع ربط المؤشّر بالفترة السابقة — فلا يُعاد
اختيارُ الرابحين بأثرٍ رجعيٍّ فيُجمَّل الأداء.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from loguru import logger

STORE_KEY = "stars:tasi20"
SIZE = 20
MIN_UPSIDE = 15.0
MIN_SCORE = 70.0
MAX_STMT_DAYS = 270
REBALANCE_DAYS = 90
CAP_UPSIDE = 50.0
CAP_EXCESS = 50.0


def _ret_12m(points: list | None) -> float | None:
    closes = [p.get("close") for p in (points or []) if isinstance(p, dict) and p.get("close")]
    if len(closes) < 200:
        return None
    return (closes[-1] / closes[0] - 1) * 100


def _main_share(sym) -> bool:
    """سهمٌ في السوق الرئيسة لا «نمو» ولا صندوق — من المصنّف الواحد."""
    from app.data.universe import is_etf, is_main
    return is_main(sym) and not is_etf(sym)


def eligible(r: dict) -> bool:
    """البوّابتان ٢ و٣ — ما لا يحتاج تاريخاً سعرياً."""
    up, fs = r.get("fair_value_upside_pct"), r.get("finance_score")
    age = r.get("stmt_age_days")
    return (isinstance(up, (int, float)) and up >= MIN_UPSIDE
            and r.get("fair_value_conf") not in (None, "منخفضة")
            and isinstance(fs, (int, float)) and fs >= MIN_SCORE
            and not (r.get("red_lines") or 0)
            and isinstance(age, (int, float)) and age <= MAX_STMT_DAYS
            and r.get("sharia") != "NON_COMPLIANT"
            and _main_share(r.get("symbol")))


def score(r: dict, excess: float) -> float:
    return (min(r["fair_value_upside_pct"], CAP_UPSIDE) / CAP_UPSIDE
            + min(excess, CAP_EXCESS) / CAP_EXCESS
            + r["finance_score"] / 100) / 3 * 100


def select(rows: list[dict], rets: dict[str, float], tasi_ret: float) -> list[dict]:
    """البوّابةُ ١ فوق ٢ و٣، ثمّ الترتيب — دالّةٌ نقيّةٌ يقيسها الحارس."""
    out = []
    for r in rows or []:
        s = str(r.get("symbol") or "")
        if not eligible(r) or rets.get(s) is None:
            continue
        excess = rets[s] - tasi_ret
        if excess <= 0:
            continue
        out.append({"symbol": s, "name": r.get("name"), "sector": r.get("sector"),
                    "price": r.get("price"), "fair_value": r.get("fair_value"),
                    "upside": r["fair_value_upside_pct"], "ret_12m": round(rets[s], 1),
                    "excess": round(excess, 1), "finance_score": r["finance_score"],
                    "sharia": r.get("sharia"), "score": round(score(r, excess), 1)})
    out.sort(key=lambda x: -x["score"])
    return out[:SIZE]


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
    if tasi_ret is None or not rows:
        return old or {"error": "تاريخُ تاسي أو صفوفُ الفرز غيرُ متوفّرة"}
    rets: dict[str, float] = {}
    for r in rows:
        if eligible(r):
            v = _ret_12m(await market_service.get_history(f"{r['symbol']}.SR", "1y"))
            if v is not None:
                rets[str(r["symbol"])] = v
    members = select(rows, rets, tasi_ret)
    if not members:
        return old or {"error": "لا شركةَ تجتاز القاعدةَ اليوم"}
    # ربطُ المؤشّر: مستوى السلّة السابقة يُحمَل فلا يبدأ كلُّ ربعٍ من الصفر.
    level = 100.0
    history = list((old or {}).get("history") or [])
    if old:
        perf = performance(old, rows, tasi_pts[-1]["close"])
        if perf.get("level") is not None:
            level = perf["level"]
            history.append({"since": old["since"], "until": today.isoformat(),
                            "ret": perf["ret"], "tasi_ret": perf.get("tasi_ret")})
    rec = {"since": today.isoformat(), "level_start": level, "weighting": "متساوية",
           "tasi_start": tasi_pts[-1]["close"], "tasi_ret_12m": round(tasi_ret, 1),
           "members": [{**m, "start_price": m["price"]} for m in members],
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
    return {"ret": round(ret, 2), "tasi_ret": round(tret, 2) if tret is not None else None,
            "level": round((rec.get("level_start") or 100) * (1 + ret / 100), 2),
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
    return {**rec, "members": members, "perf": performance(rec, rows, q)}
