"""«نجوم تاسي» منذ 2015 (D546) — اختبارٌ تاريخيٌّ شهريٌّ بالبيانات المنشورة في وقتها.

قال المالك: «وقائعُ التاريخ وفهمُ الحاضر تجعلك تتوقّع المستقبل». فيُعاد بناءُ السلّة
آخرَ كلّ شهرٍ منذ ديسمبر 2014 بما كان معلوماً يومئذٍ وحده، ويُقاس الشهرُ التالي:

  · الأسعار: إغلاقٌ شهريٌّ من ياهو (range=max · تعديلُ التجزئة والمنح) وتوزيعاتُه.
  · تاسي: الإغلاقُ اليوميُّ الرسميّ من «تداول» (2007 →) آخرَ كلّ شهر.
  · القوائم: ملفّاتُ XBRL من «تداول» لا تدخل إلا بعد نشرها — السنويةُ بعد 90 يوماً
    من نهاية السنة، والربعيةُ بعد 45 — فلا يُرى رقمٌ قبل صدوره.
  · العائلاتُ الثماني نفسُها (stars_factors) بما يُقاس تاريخياً؛ وعائلةٌ بلا قياسٍ
    في شهرٍ ما محايدة (0.5) كما في الترتيب الحيّ.
  · العائدُ عائدُ سعرٍ بلا توزيعات، مقابلَ تاسي السعريّ — مقارنةٌ بالمثل.

والمعاييرُ مفاتيحُ تُطفأ (`off`): التصفيةُ الشرعية، والشركاتُ الكبيرة، وكلُّ عائلةٍ
من الثماني. وحدودُه المعلومة: الكونُ هو المدرَجُ اليوم (لا بيانات لمن شُطب)،
والحكمُ الشرعيُّ حكمُ اليوم، والقوائمُ قبل 2023 قليلة — فعائلاتُها محايدةٌ غالباً
فيما قبلها ويحمل الزخمُ والقطاعُ والتوزيعاتُ الترتيب.
"""
from __future__ import annotations

import asyncio
import statistics
from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone

AST = timezone(timedelta(hours=3))     # شمعةُ ياهو الشهرية مختومةٌ بمنتصف ليل الرياض (21:00 بتوقيت غرينتش)

from loguru import logger

DATA_KEY = "stars:bt:data"
START = "2014-12"                       # أوّلُ بناءٍ آخرَ ديسمبر 2014 · أوّلُ شهرٍ مقيس يناير 2015
SIZE = 20
LARGE_N = 100
LAG_ANNUAL, LAG_QUARTER = 90, 45
REFRESH_DAYS = 6
FILTERS = ("sharia", "large")
FAMILY_KEYS = ("financial", "multiples", "momentum", "efficiency", "profit_trend", "debt", "industry", "corporate")
_running: asyncio.Task | None = None


def _n(v):
    return float(v) if isinstance(v, (int, float)) else None


def _ym_add(ym: str, k: int) -> str:
    y, m = int(ym[:4]), int(ym[5:7]) - 1 + k
    return f"{y + m // 12:04d}-{m % 12 + 1:02d}"


def _month_end(ym: str) -> date:
    return date.fromisoformat(_ym_add(ym, 1) + "-01") - timedelta(days=1)


def clean_months(months: list) -> list:
    """السلسلةُ الشهريةُ بعد آخر قفزةٍ مستحيلة (D549).

    قِيس (كاشف bonus_door): ياهو يسجّل منحَ الأسهم السعودية تجزئةً ويعدّل بها، لكنّ
    بياناتِه في 2010–2012 فيها أشهرٌ منفردةٌ بسعرٍ أربعةَ أضعافٍ ثمّ يعود (الراجحي
    ‎0.224 في 2010-05 · الدريس ‎0.317 · سابك ‎0.762) — فخرج للراجحي «أقصى تراجع −83.8٪»
    وعائدٌ سالبٌ منذ 2010. فالسعرُ لا ينصف ولا يتضاعف في شهرٍ واحدٍ بلا سبب: تبدأ
    السلسلةُ بعد آخر شهرٍ يتغيّر فيه السعرُ بأكثرَ من الضعف أو دون النصف."""
    ms = [tuple(x) for x in months or [] if x and x[1]]
    cut = 0
    for i in range(1, len(ms)):
        r = ms[i][1] / ms[i - 1][1]
        if r < 0.5 or r > 2.0:
            cut = i
    return ms[cut:]


# ══ البيانات ═══════════════════════════════════════════════════════════════
async def _yahoo_monthly(client, sym: str) -> dict | None:
    for host in ("query1", "query2"):
        try:
            r = await client.get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{sym}.SR"
                                 "?range=max&interval=1mo&events=div")
            if r.status_code != 200:
                continue
            res = (r.json().get("chart", {}).get("result") or [None])[0]
            if not res:
                continue
            ts = res.get("timestamp") or []
            cl = ((res.get("indicators", {}).get("quote") or [{}])[0]).get("close") or []
            m: dict[str, float] = {}
            for t, c in zip(ts, cl):
                if c:
                    m[datetime.fromtimestamp(t, tz=AST).date().isoformat()[:7]] = round(float(c), 4)
            divs = [[datetime.fromtimestamp(d["date"], tz=AST).date().isoformat(), round(float(d["amount"]), 4)]
                    for d in ((res.get("events") or {}).get("dividends") or {}).values()
                    if d.get("date") and d.get("amount")]
            return {"m": sorted(m.items()), "div": sorted(divs)}
        except Exception:                                         # noqa: BLE001
            continue
    return None


async def _tasi_monthly() -> dict[str, float]:
    import json
    from app.services import tasi_history as TH
    from app.services.tadawul_http import fetch
    st, body = await fetch(TH.URL_DAILY)
    pts = TH.daily_candles(json.loads(body)) if st == 200 and body else []
    out: dict[str, float] = {}
    for p in pts:
        out[p["date"][:7]] = p["close"]
    return out


def _universe() -> dict[str, dict]:
    """المرشّحون: أسهمُ السوق الرئيسة (لا صناديق) من صفوف الفرز — بقطاعها وحكمها وأسهمها."""
    from app.services.market_screener import get_cached_screener
    from app.services.tasi_stars import _cap, _main_share
    try:
        from app.services.tadawul_market import usable_rows
        snap = usable_rows()[0] or {}
    except Exception:                                             # noqa: BLE001
        snap = {}
    out = {}
    for r in get_cached_screener() or []:
        s = str(r.get("symbol") or "")
        if not s or not _main_share(s):
            continue
        # ‏D546: صفوفُ الفرز بلا قيمةٍ سوقية — فتُقرأ كما يقرؤها الترتيبُ الحيّ (لقطةُ «تداول»
        # أو السعرُ × الأسهمِ المنشورة)، وإلا صار حجمُ كلّ سهمٍ صفراً فخلا الكونُ.
        v = snap.get(s) or {"price": r.get("price")}
        px, cap = _n(v.get("price")) or _n(r.get("price")), _n(r.get("market_cap")) or _cap(s, v)
        out[s] = {"sector": r.get("sector") or "", "sharia": r.get("sharia"),
                  "shares": (cap / px) if cap and px else None}
    return out


async def ensure_data(force: bool = False) -> dict:
    """يجمع الأسعارَ الشهرية وتوزيعاتِها لكلّ مرشّحٍ وتاسي — مرّةً كلّ أسبوع."""
    from app.services import lastgood
    old = lastgood.load(DATA_KEY) or {}
    at = old.get("at")
    if not force and at and (date.today() - date.fromisoformat(at)).days < REFRESH_DAYS and old.get("px"):
        return old
    import httpx
    uni = _universe()
    if not uni:
        return old
    px: dict = dict(old.get("px") or {})
    sem = asyncio.Semaphore(6)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
        async def one(s):
            async with sem:
                d = await _yahoo_monthly(client, s)
                if d and d["m"]:
                    px[s] = d
        await asyncio.gather(*(one(s) for s in uni))
    try:
        tasi = await _tasi_monthly()
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"backtest tasi: {type(e).__name__}: {e}")
        tasi = {}
    tasi = tasi or dict(old.get("tasi") or {})
    rec = {"at": date.today().isoformat(), "px": px, "tasi": tasi}
    if px and tasi:
        lastgood.save(DATA_KEY, rec)
    logger.info(f"⭐ اختبارُ النجوم: أسعارُ {len(px)} سهماً · تاسي {len(tasi)} شهراً")
    return rec


def kick() -> None:
    """يبدأ جمعَ البيانات في الخلفية إن لم يكن جارياً — لا يؤخّر الطلب."""
    global _running
    if _running and not _running.done():
        return
    try:
        _running = asyncio.get_running_loop().create_task(ensure_data())
    except RuntimeError:
        pass


# ══ القوائمُ بتاريخ نشرها ═════════════════════════════════════════════════
def _statements(symbols) -> dict[str, list[tuple[str, dict]]]:
    """لكلّ رمز: (تاريخُ صيرورتها معلومةً، السنةُ) — السنويةُ وحدها، الأقدمُ أوّلاً."""
    from app.services import tadawul_xbrl
    out = {}
    for s in symbols:
        try:
            ann = tadawul_xbrl.for_symbol(s, "annual") or []
        except Exception:                                         # noqa: BLE001
            ann = []
        rows = []
        for p in ann:
            try:
                known = date.fromisoformat(str(p.get("as_of"))[:10]) + timedelta(days=LAG_ANNUAL)
            except ValueError:
                continue
            rows.append((known.isoformat(), p))
        out[s] = sorted(rows, key=lambda x: x[0])
    return out


def _known(rows: list[tuple[str, dict]], cut: str, back: int = 0) -> dict | None:
    k = bisect_right([r[0] for r in rows], cut) - 1 - back
    return rows[k][1] if k >= 0 else None


# ══ الاختبار ════════════════════════════════════════════════════════════════
def run(data: dict, uni: dict[str, dict], stm: dict, off: set[str] | None = None,
        start: str = START) -> dict:
    """دالّةٌ نقيّة: البياناتُ ← مسارُ السلّة وتاسي شهرياً وملخّصُها."""
    from app.services.tasi_stars import _pct_rank
    off = set(off or ())
    fams = [f for f in FAMILY_KEYS if f not in off]
    px = {s: dict(clean_months(d.get("m"))) for s, d in (data.get("px") or {}).items() if s in uni}
    divs = {s: d.get("div") or [] for s, d in (data.get("px") or {}).items() if s in uni}
    tasi = data.get("tasi") or {}
    last = date.today().isoformat()[:7]          # الشهرُ الجاري حتى آخر إغلاق — فالمسارُ يبلغ اليوم
    months = []
    ym = start
    while ym <= last:
        months.append(ym)
        ym = _ym_add(ym, 1)
    level, tlevel = 100.0, 100.0
    track = [{"d": start, "s": 100.0, "t": 100.0}]
    pick: list[str] = []
    beat = n_m = 0
    sizes = []
    for t, nxt in zip(months, months[1:] + [None]):
        if nxt is None or t not in tasi or nxt not in tasi:
            continue
        cut = _month_end(t).isoformat()
        rows = []
        for s, m in px.items():
            c, c12 = m.get(t), m.get(_ym_add(t, -12))
            if not c or not c12 or not m.get(nxt):
                continue
            if "sharia" not in off and uni[s].get("sharia") == "NON_COMPLIANT":
                continue
            rows.append(s)
        if "large" not in off:
            caps = sorted(((px[s][t] * (uni[s].get("shares") or 0), s) for s in rows), reverse=True)
            rows = [s for c, s in caps[:LARGE_N] if c > 0]
        if len(rows) < SIZE:
            continue
        raw: dict[str, dict[str, dict]] = {}
        sec_r: dict[str, list[float]] = {}
        for s in rows:
            m = px[s]
            c = m[t]
            r12 = c / m[_ym_add(t, -12)] - 1
            sec_r.setdefault(uni[s]["sector"], []).append(r12)
            last10 = [m.get(_ym_add(t, -k)) for k in range(10)]
            last3 = [m.get(_ym_add(t, -k)) for k in range(3)]
            d10 = c / statistics.fmean([x for x in last10 if x]) - 1
            d3 = c / statistics.fmean([x for x in last3 if x]) - 1
            since12 = _month_end(_ym_add(t, -12)).isoformat()
            since36 = _month_end(_ym_add(t, -36)).isoformat()
            dps = sum(a for d, a in divs[s] if since12 < d <= cut)
            yrs = {d[:4] for d, a in divs[s] if since36 < d <= cut and a > 0}
            a0 = _known(stm.get(s) or [], cut)
            a1 = _known(stm.get(s) or [], cut, 1)
            f = {}
            if a0:
                ni, eq, rev, ta = (_n(a0.get(k)) for k in ("net_income", "equity", "revenue", "total_assets"))
                sh = _n(a0.get("shares_outstanding")) or uni[s].get("shares")
                mc = c * sh if sh else None
                f = {"roe": ni / eq if ni is not None and eq and eq > 0 else None,
                     "margin": ni / rev if ni is not None and rev and rev > 0 else None,
                     "ey": ni / mc if ni is not None and mc else None,
                     "bp": eq / mc if eq and mc else None,
                     "roa": ni / ta if ni is not None and ta and ta > 0 else None,
                     "turn": rev / ta if rev and ta and ta > 0 else None,
                     "low_debt": -_n(a0.get("debt_ratio")) if _n(a0.get("debt_ratio")) is not None else None}
                ocf, capex = _n(a0.get("operating_cash_flow")), _n(a0.get("capex"))
                f["fcf"] = (ocf - (capex or 0)) / ta if ocf is not None and ta and ta > 0 else None
                ni1 = _n((a1 or {}).get("net_income"))
                f["ni_g"] = max(-2.0, min(2.0, (ni - ni1) / abs(ni1))) if ni is not None and ni1 else None
            raw[s] = {"financial": {"roe": f.get("roe"), "margin": f.get("margin")},
                      "multiples": {"ey": f.get("ey"), "bp": f.get("bp")},
                      "momentum": {"r12": r12, "d10": d10, "d3": d3},
                      "efficiency": {"roa": f.get("roa"), "turn": f.get("turn")},
                      "profit_trend": {"ni": f.get("ni_g")},
                      "debt": {"low_debt": f.get("low_debt"), "fcf": f.get("fcf")},
                      "industry": {"sec": None},
                      "corporate": {"dy": dps / c if c else None, "reg": len(yrs) / 3}}
        for s in rows:
            raw[s]["industry"]["sec"] = statistics.fmean(sec_r[uni[s]["sector"]])
        ranks: dict[str, dict[str, float]] = {s: {} for s in rows}
        keys = {(fm, k) for s in rows for fm in fams for k in raw[s][fm]}
        for fm, k in keys:
            groups = {"": rows}
            if (fm, k) == ("debt", "low_debt"):
                groups = {}
                for s in rows:
                    groups.setdefault(uni[s]["sector"], []).append(s)
            for g in groups.values():
                have = [s for s in g if raw[s][fm].get(k) is not None]
                if len(have) < 2:
                    continue
                for s, v in zip(have, _pct_rank([raw[s][fm][k] for s in have])):
                    ranks[s][f"{fm}.{k}"] = v
        score = {}
        for s in rows:
            fv = []
            for fm in fams:
                vs = [v for kk, v in ranks[s].items() if kk.startswith(fm + ".")]
                fv.append(sum(vs) / len(vs) if vs else 0.5)
            score[s] = sum(fv) / len(fv) if fv else 0.5
        pick = sorted(rows, key=lambda s: (-score[s], s))[:SIZE]
        r = statistics.fmean([px[s][nxt] / px[s][t] - 1 for s in pick])
        tr = tasi[nxt] / tasi[t] - 1
        level *= 1 + r
        tlevel *= 1 + tr
        beat += r > tr
        n_m += 1
        sizes.append(len(rows))
        track.append({"d": nxt, "s": round(level, 2), "t": round(tlevel, 2)})
    if n_m == 0:
        return {"track": [], "months": 0}
    yrs_n = n_m / 12
    peak, dd = 100.0, 0.0
    for p in track:
        peak = max(peak, p["s"])
        dd = min(dd, p["s"] / peak - 1)
    years = []
    for y in sorted({p["d"][:4] for p in track[1:]}):
        prev = [p for p in track if p["d"] < f"{y}-01"][-1:] or track[:1]
        end = [p for p in track if p["d"][:4] == y][-1]
        years.append({"y": y, "s": round((end["s"] / prev[0]["s"] - 1) * 100, 1),
                      "t": round((end["t"] / prev[0]["t"] - 1) * 100, 1)})
    return {"start": start, "months": n_m, "track": track,
            "total": round(level - 100, 1), "tasi_total": round(tlevel - 100, 1),
            "excess": round(level - tlevel, 1),
            "cagr": round(((level / 100) ** (1 / yrs_n) - 1) * 100, 1),
            "tasi_cagr": round(((tlevel / 100) ** (1 / yrs_n) - 1) * 100, 1),
            "beat_pct": round(beat / n_m * 100), "max_dd": round(dd * 100, 1),
            "years": years, "universe": round(statistics.fmean(sizes)), "last_pick": pick}


async def get(off: set[str] | None = None) -> dict | None:
    """الاختبارُ لمجموعة المعايير المفعّلة — مخزَّنٌ اثنتي عشرةَ ساعة."""
    from app.services import cache, lastgood
    key = "stars:bt:v2:" + (",".join(sorted(off or ())) or "all")
    hit = cache.get(key)
    if hit is not None:
        return hit
    data = lastgood.load(DATA_KEY) or {}
    if not data.get("px") or (data.get("at") and (date.today() - date.fromisoformat(data["at"])).days >= REFRESH_DAYS):
        kick()
    if not data.get("px"):
        return None
    uni = _universe()
    res = await asyncio.to_thread(run, data, uni, _statements(list(uni)), off)
    if res.get("track"):
        cache.set(key, res, 12 * 3600)
    return res


# ══ مختبرُ السلّة (D608) ══ بأمر المالك: «خلطةُ شركاتٍ أختارها بنفسي ويريني أداءها حتى أعتمدها لمحفظتي —
# كأنه مختبرُ أبحاثٍ للسوق». البياناتُ نفسُها التي يُختبر بها «نجوم تاسي»: أوزانٌ متساوية تُعاد شهرياً،
# بالسعر وحده (بلا توزيعات — كما في اختبار النجوم)، مقابلَ تاسي. وشركةٌ لم تُدرَج بعد تدخل حين يبدأ سعرُها.
def basket(data: dict, symbols: list[str], start: str = START) -> dict:
    """دالّةٌ نقيّة: سلّةُ المالك ← مسارُها وتاسي شهرياً وملخّصُها، وما ساهم به كلُّ سهم."""
    tasi = data.get("tasi") or {}
    px = {s: dict(clean_months((data.get("px") or {}).get(s, {}).get("m"))) for s in symbols}
    px = {s: m for s, m in px.items() if m}
    missing = [s for s in symbols if s not in px]
    last = date.today().isoformat()[:7]
    months, ym = [], start
    while ym <= last:
        months.append(ym)
        ym = _ym_add(ym, 1)
    level, tlevel = 100.0, 100.0
    track = [{"d": start, "s": 100.0, "t": 100.0}]
    beat = n_m = 0
    contrib = {s: 0.0 for s in px}
    for t, nxt in zip(months, months[1:] + [None]):
        if nxt is None or t not in tasi or nxt not in tasi:
            continue
        live = [s for s, m in px.items() if m.get(t) and m.get(nxt)]
        if not live:
            continue
        rs = {s: px[s][nxt] / px[s][t] - 1 for s in live}
        r = statistics.fmean(rs.values())
        for s, v in rs.items():
            contrib[s] += level * v / len(live)
        tr = tasi[nxt] / tasi[t] - 1
        level *= 1 + r
        tlevel *= 1 + tr
        beat += r > tr
        n_m += 1
        track.append({"d": nxt, "s": round(level, 2), "t": round(tlevel, 2)})
    if n_m == 0:
        return {"track": [], "months": 0, "missing": missing}
    yrs_n = n_m / 12
    peak, dd = 100.0, 0.0
    for p in track:
        peak = max(peak, p["s"])
        dd = min(dd, p["s"] / peak - 1)
    years = []
    for y in sorted({p["d"][:4] for p in track[1:]}):
        prev = [p for p in track if p["d"] < f"{y}-01"][-1:] or track[:1]
        end = [p for p in track if p["d"][:4] == y][-1]
        years.append({"y": y, "s": round((end["s"] / prev[0]["s"] - 1) * 100, 1),
                      "t": round((end["t"] / prev[0]["t"] - 1) * 100, 1)})
    return {"start": track[0]["d"], "months": n_m, "track": track,
            "total": round(level - 100, 1), "tasi_total": round(tlevel - 100, 1), "excess": round(level - tlevel, 1),
            "cagr": round(((level / 100) ** (1 / yrs_n) - 1) * 100, 1),
            "tasi_cagr": round(((tlevel / 100) ** (1 / yrs_n) - 1) * 100, 1),
            "beat_pct": round(beat / n_m * 100), "max_dd": round(dd * 100, 1), "years": years,
            "contrib": sorted(({"symbol": s, "pts": round(v, 1)} for s, v in contrib.items()), key=lambda x: -x["pts"]),
            "missing": missing}


def forward(symbols: list[str]) -> dict:
    """النظرةُ القادمة — ما تقوله المحرّكاتُ اليوم لا تنبّؤٌ بالسعر: الصعودُ إلى العادل بثقته، والجودة، والقرار."""
    from app.services.content_engine import fund_store_load
    from app.services.market_screener import get_cached_screener
    store = fund_store_load() or {}
    rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
    out, ups = [], []
    for s in symbols:
        st = store.get(s) or store.get(s + ".SR") or {}
        r = rows.get(s) or {}
        px, fv = _n(r.get("price")), _n(st.get("fair_value"))
        up = round((fv / px - 1) * 100, 1) if px and fv else None
        conf = st.get("fair_value_conf")
        out.append({"symbol": s, "name": r.get("name"), "price": px, "fair_value": fv, "upside": up, "conf": conf,
                    "quality": st.get("finance_score"), "decision": (r.get("decision") or {}).get("label")
                    if isinstance(r.get("decision"), dict) else r.get("decision")})
        if up is not None and conf in ("مرتفعة", "متوسطة"):
            ups.append(up)
    return {"items": out, "upside_reliable": round(statistics.fmean(ups), 1) if ups else None,
            "reliable_n": len(ups), "n": len(symbols)}


async def lab(symbols: list[str], start: str = START) -> dict | None:
    from app.services import lastgood
    syms = list(dict.fromkeys(str(s).replace(".SR", "").strip() for s in symbols if str(s).strip()))[:30]
    data = lastgood.load(DATA_KEY) or {}
    if not data.get("px"):
        kick()
        return None
    res = await asyncio.to_thread(basket, data, syms, start)
    res["forward"] = forward(syms)
    return res
