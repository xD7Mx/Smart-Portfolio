"""مجالُ صقر الأمريكيّ الكامل — الأساسُ قبل الفنّ (‏D766 · بأمر المالك 2026-11-18).

«هل صقر يغطّي كاملَ شركات السوق الأمريكيّ التي تتوفّر فيها عقودُ خيارات أم شركاتٍ محدودة؟ يجب أن تكون التغطيةُ كاملة، ويختار شركاتٍ ذاتَ
أساسٍ ماليٍّ ممتاز — ليست ركيكةً ولا عليها شطبٌ أو مشاكل — حتى لا يكون العقدُ خطراً من هذه الناحية؛ لأنّ التحليلَ الفنيَّ يجب أن يكون بعد
التحليل الأساسيّ». وكان مجالُه نحو 130 رمزاً (الأسيلُ + أنشطُ اليوم) بلا فرزٍ أساسيّ.

قيس على الخادم (‏scripts/audit/us_universe_door.py · 2026-11-18):
  · «سيبوي» (‏Cboe) تنشر دليلَ كلِّ ورقةٍ أمريكيةٍ لها عقودُ خيارات: ‏5,408 رمزاً في ثانية — المصدرُ الرسميّ للتغطية.
  · مُصفّي TradingView يعيد السوقَ كلَّه (‏3,392 سهماً وصندوقاً سائلاً) في 0.6 ثانية بحقولٍ أساسيةٍ وفنيةٍ معاً، وكلُّ الحقول الاثنين والسبعين صالحة:
    ‏Altman Z (خطرُ الإفلاس) · Piotroski F (المتانة) · الدينُ إلى الحقوق · السيولةُ الجارية · الربحُ والتدفّقُ الحرّ · الهوامش · النموّ ·
    موعدُ الأرباح القادم · المتوسّطاتُ وأداءُ الفترات وقممُها وقيعانُها.
فالمجالُ = دليلُ سيبوي ∩ السوقُ السائل؛ ثمّ **الأساسُ أوّلاً** (يُستبعد الضعيفُ بسببه، ويُرتّب الباقي بدرجة متانة)، ثمّ المسارُ الفنيّ من الحقول
نفسِها — فيُقرأ السوقُ كلُّه في كلّ دورةٍ بنداءٍ واحد، ولا تُطلب الشموعُ إلا لما يدخل الفحصَ العميق."""
import asyncio
import csv
import io
import json
import re

from loguru import logger

CBOE_URL = "https://www.cboe.com/us/options/symboldir/equity_index_options/?download=csv"
COLS = ["name", "description", "type", "subtype", "exchange", "is_primary", "sector", "industry", "close", "change", "Value.Traded",
        "average_volume_10d_calc", "market_cap_basic", "SMA50", "SMA200", "EMA20", "Perf.3M", "price_52_week_high", "price_52_week_low",
        "High.3M", "Low.3M", "High.6M", "Low.6M", "net_income_ttm", "free_cash_flow_ttm", "net_margin", "return_on_equity", "debt_to_equity",
        "current_ratio", "piotroski_f_score_ttm", "altman_z_score_ttm", "total_revenue_yoy_growth_ttm", "earnings_release_next_date"]
MIN_PRICE = 5.0                  # دون خمسة دولارات منطقةُ الشطب والعقودِ الرقيقة
MIN_CAP = 2e9                    # شركاتٌ صغيرةٌ أهشّ — الممتازُ لا يقلّ عن ملياري دولار
MIN_VOL = 300_000
Z_DISTRESS = 1.81                # ‏Altman: دون 1.81 منطقةُ الضيق (للشركات غير المالية)
F_WEAK = 4                       # ‏Piotroski: أربعةٌ فأقلّ ضعفٌ أو وسط — الممتازُ خمسةٌ فأكثر (قيس: 4 مرّ بدرجة 75)
MAX_DE, MIN_CR = 3.0, 0.8
MIN_SCORE = 65                   # درجةُ المتانة الدنيا للدخول (من 100)
ETF_MIN_TRADED = 2e8             # الصندوقُ العميقُ وحده: قيمةُ تداوله اليوميّ ≥ 200 مليون دولار (المؤشّراتُ والقطاعاتُ والسلعُ الكبرى)
ETF_BAD = re.compile(r"YIELDMAX|OPTION INCOME|COVERED CALL|INCOME STRATEGY|BUYWRITE|SINGLE STOCK|DAILY TARGET|\bOPTION\b", re.I)
LEVERED = re.compile(r"\b(2X|3X|-1X|-2X|-3X|ULTRA|LEVERAGED|INVERSE|BEAR|BULL|DAILY)\b", re.I)
FIN_SECTORS = ("Finance",)


def canon(sym: str) -> str:
    """رمزٌ واحدُ الصيغة بين المصادر: ‏BRK.B · BRK/B · BRK-B ⇐ BRK-B."""
    return re.sub(r"[./ ]", "-", str(sym or "").strip().upper())


async def cboe_symbols() -> set[str] | None:
    """دليلُ سيبوي لكلّ ورقةٍ لها عقودُ خيارات — مخبّأٌ يوماً (يُحفظ على القرص)؛ وتعذّرُه None."""
    from app.services import cache
    hit = cache.get("saqr:cboe")
    if hit:
        return set(hit)

    def blocking() -> list[str]:
        from curl_cffi import requests as cr
        with cr.Session(impersonate="chrome") as s:
            r = s.get(CBOE_URL, timeout=25)
        if r.status_code != 200:
            return []
        rows = list(csv.reader(io.StringIO(r.text or "")))
        out = []
        for row in rows[1:]:
            if len(row) > 1 and row[1].strip():
                out.append(canon(row[1]))
        return out
    try:
        syms = await asyncio.to_thread(blocking)
    except Exception as e:                                        # noqa: BLE001
        logger.debug("صقر/سيبوي: {}", type(e).__name__)
        syms = []
    if len(syms) < 1000:
        return None
    cache.set("saqr:cboe", sorted(set(syms)), 24 * 3600)
    return set(syms)


async def tv_market() -> list[dict]:
    """السوقُ الأمريكيّ السائل كلُّه من مُصفّي TradingView بحقوله الأساسية والفنية — مخبّأٌ عشرَ دقائق."""
    from app.services import cache
    hit = cache.get("saqr:tvmkt")
    if hit is not None:
        return hit

    def blocking() -> list[dict]:
        from curl_cffi import requests as cr
        body = {"filter": [{"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]},
                           {"left": "close", "operation": "greater", "right": MIN_PRICE},
                           {"left": "average_volume_10d_calc", "operation": "greater", "right": MIN_VOL},
                           {"left": "type", "operation": "in_range", "right": ["stock", "fund"]}],
                "columns": COLS, "sort": {"sortBy": "Value.Traded", "sortOrder": "desc"}, "range": [0, 6000]}
        with cr.Session(impersonate="chrome") as s:
            r = s.post("https://scanner.tradingview.com/america/scan", data=json.dumps(body), timeout=25,
                       headers={"Content-Type": "application/json", "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"})
        if r.status_code != 200:
            return []
        return [dict(zip(COLS, row.get("d") or [])) for row in (json.loads(r.text or "{}").get("data") or [])]
    try:
        rows = await asyncio.to_thread(blocking)
    except Exception as e:                                        # noqa: BLE001
        logger.debug("صقر/المُصفّي: {}", type(e).__name__)
        rows = []
    if rows:
        cache.set("saqr:tvmkt", rows, 600)
    return rows


def _n(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


def fundamentals(row: dict) -> tuple[bool, int, str]:
    """(يُقبل؟، درجةُ المتانة من 100، السبب) — الأساسُ قبل الفنّ. الصندوقُ المتداولُ (مؤشّرٌ أو قطاعٌ أو سلعة) مقبولٌ بلا قوائم إن لم يكن
    مرفوعاً أو عكسياً؛ والسهمُ يُستبعد لخطر الشطب أو الضيق أو الضعف أو الخسارة المحترقة أو الدين أو السيولة، ثمّ يُدرَّج."""
    kind, sub = row.get("type"), row.get("subtype")
    desc = str(row.get("description") or "")
    px, cap = _n(row.get("close")), _n(row.get("market_cap_basic"))
    if px is None or px < MIN_PRICE:
        return False, 0, "سعرٌ دون 5 دولارات — منطقةُ الشطب والعقود الرقيقة"
    if kind == "fund":
        if sub != "etf":
            return False, 0, "صندوقٌ مغلقٌ أو وحدة — لا يُتداول بعقوده"
        if LEVERED.search(desc):
            return False, 0, "صندوقٌ مرفوعٌ أو عكسيّ — يتآكل يومياً"
        if ETF_BAD.search(desc):
            return False, 0, "صندوقُ دخلٍ بالعقود أو سهمٍ واحد — بنيتُه تتآكل"
        if (_n(row.get("Value.Traded")) or 0) < ETF_MIN_TRADED:
            return False, 0, "صندوقٌ صغيرُ التداول — لا عمقَ لعقوده"
        return True, 70, "صندوقٌ متداولٌ عميق (مؤشّرٌ أو قطاعٌ أو سلعة)"
    if sub != "common" or row.get("is_primary") is False:
        return False, 0, "ليس سهماً عادياً أساسياً (ممتازٌ أو إدراجٌ ثانويّ)"
    if cap is None or cap < MIN_CAP:
        return False, 0, "قيمةٌ سوقيةٌ دون ملياري دولار — أهشّ من أن يُبنى عليها"
    fin = str(row.get("sector") or "") in FIN_SECTORS
    z, f = _n(row.get("altman_z_score_ttm")), _n(row.get("piotroski_f_score_ttm"))
    ni, fcf = _n(row.get("net_income_ttm")), _n(row.get("free_cash_flow_ttm"))
    de, cr_ = _n(row.get("debt_to_equity")), _n(row.get("current_ratio"))
    if not fin and z is not None and z < Z_DISTRESS:
        return False, 0, f"منطقةُ الضيق المالي (Altman Z ‏{z:.2f} دون 1.81)"
    if f is not None and f <= F_WEAK:
        return False, 0, f"متانةٌ ضعيفة (Piotroski ‏{f:.0f} من 9)"
    if ni is not None and fcf is not None and ni <= 0 and fcf <= 0:
        return False, 0, "خاسرةٌ وتحرق النقد (صافي الربح والتدفّقُ الحرّ سالبان)"
    if not fin and de is not None and (de < 0 or de > MAX_DE):
        return False, 0, f"دينٌ مفرط (الدينُ إلى الحقوق {de:.1f})" if de > 0 else "حقوقُ ملكيةٍ سالبة"
    if not fin and cr_ is not None and cr_ < MIN_CR:
        return False, 0, f"سيولةٌ جاريةٌ ضعيفة ({cr_:.2f})"
    s = 0.0
    s += (f or 0) * 5                                                         # ٤٥ للمتانة
    s += 20 if fin else (20 if (z or 0) >= 3 else 10 if (z or 0) >= Z_DISTRESS else 0)
    s += 10 if (ni or 0) > 0 else 0
    s += 10 if (_n(row.get("return_on_equity")) or 0) >= 10 else 0
    s += 10 if (fcf or 0) > 0 else 0
    s += 5 if (_n(row.get("total_revenue_yoy_growth_ttm")) or 0) > 0 else 0
    sc = int(round(min(s, 100)))
    if sc < MIN_SCORE:
        return False, sc, f"أساسٌ دون الممتاز (درجةُ المتانة {sc} من 100)"
    return True, sc, f"أساسٌ متين (درجة {sc}: Piotroski {f:.0f}" + (f" · Altman {z:.1f}" if z is not None and not fin else "") + ")"


def tv_trend(row: dict) -> dict | None:
    """المسارُ من حقول المُصفّي نفسِها (بلا شموع) بقاعدة ‏option_picks.trend_of نفسِها — فلا تعريفان للمسار في التطبيق: صاعدٌ إن كان متوسّطُ 50 فوق
    200 بأكثر من 1٪ وميلُه صاعدٌ (المتوسّطُ الأسّيّ لعشرين فوقه) والإغلاقُ فوق 200، والهابطُ عكسُه، وما سواهما عرضيّ؛ والارتدادُ إلى ما دون
    متوسّط 50 في مسارٍ قائمٍ لا يلغيه."""
    c, s50, s200, e20, p3 = (_n(row.get(k)) for k in ("close", "SMA50", "SMA200", "EMA20", "Perf.3M"))
    if not (c and s50 and s200 and e20) or p3 is None:
        return None
    if s50 > s200 * 1.01 and e20 > s50 and c > s200:
        state = "صاعد"
    elif s50 < s200 * 0.99 and e20 < s50 and c < s200:
        state = "هابط"
    else:
        state = "عرضي"
    slope = (e20 / s50 - 1) * 100
    strength = abs(slope) + abs(p3) / 4 + abs(c / s200 - 1) * 20
    hi52, lo52 = _n(row.get("price_52_week_high")) or c, _n(row.get("price_52_week_low")) or c
    return {"close": round(c, 2), "sma50": round(s50, 2), "sma200": round(s200, 2), "slope50": round(slope, 2), "ret3m": round(p3, 1),
            "hi52": round(hi52, 2), "lo52": round(lo52, 2), "hi60": round(_n(row.get("High.3M")) or hi52, 2), "lo60": round(_n(row.get("Low.3M")) or lo52, 2),
            "hi120": round(_n(row.get("High.6M")) or hi52, 2), "lo120": round(_n(row.get("Low.6M")) or lo52, 2), "state": state, "strength": round(strength, 2)}


async def universe() -> dict:
    """المجالُ الكامل: ‏{"tr": {رمز: مسار}, "fund": {رمز: (درجة، سبب)}, "meta": {...}} — كلُّ ورقةٍ لها عقودُ خيارات (دليلُ سيبوي) وسائلةٌ، اجتازت
    الأساس؛ ومعه أعدادُ ما استُبعد بسببه. وإن تعذّر دليلُ سيبوي فالسوقُ السائلُ كلُّه (والعقدُ نفسُه يُتحقَّق منه في الفحص العميق)."""
    from app.services import cache
    cboe, rows = await asyncio.gather(cboe_symbols(), tv_market())
    tr, fund, why, names = {}, {}, {}, {}
    seen = 0
    for row in rows:
        sym = canon(row.get("name"))
        if not sym or (cboe is not None and sym not in cboe):
            continue
        seen += 1
        ok, sc, reason = fundamentals(row)
        if not ok:
            key = reason.split(" (")[0].split(" —")[0]
            why[key] = why.get(key, 0) + 1
            continue
        t = tv_trend(row)
        if not t:
            continue
        tr[sym] = t
        fund[sym] = (sc, reason)
        names[sym] = row.get("description")
        cache.set(f"saqr:tr:{sym}", t, 6 * 3600)
    meta = {"cboe": len(cboe) if cboe is not None else None, "market": len(rows), "optionable": seen, "passed": len(tr),
            "excluded": dict(sorted(why.items(), key=lambda kv: -kv[1])),
            "up": sum(1 for t in tr.values() if t["state"] == "صاعد"), "down": sum(1 for t in tr.values() if t["state"] == "هابط")}
    return {"tr": tr, "fund": fund, "names": names, "meta": meta}
