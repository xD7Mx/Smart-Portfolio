"""كاشف D699 (قراءةٌ فقط · بأمر المالك 2026-10-13): «أريد كلَّ رقمٍ يظهر في التطبيق محلَّ ثقة… نماذجُ لها القدرةُ للحكم على
شركةٍ ثمّ يتبيّن أنّ توقّعاتها كانت ناجحة».

كانت ثقةُ السعر العادل («مرتفعة/متوسطة/منخفضة») قاعدةً داخلية: اتّفاقُ النماذج وعددُها وحداثةُ القوائم (analysis.confidence_of)،
ومعايرةُ الرقم كانت على أهداف المحلّلين (D623) — لا على ما حدث فعلاً. فهنا يُقاس المحرّكُ بالنتائج:

  · لكلّ نهاية ربعٍ منذ 2023 ولكلّ شركة، يُعاد حسابُ السعر العادل **بما كان معلوماً يومها وحده**: القوائمُ بعد نشرها
    (السنويةُ بعد 90 يوماً من نهاية السنة والربعيةُ بعد 45 — كاختبار النجوم)، والسعرُ إغلاقُ ذلك الشهر، والأقرانُ بأسعارهم
    وقوائمهم يومها، والتوزيعاتُ حتى يومها، ومضاعفاتُ الشركة التاريخيةُ حتى يومها. والدالّةُ نفسُها التي تحسب رقمَ اليوم
    (`fair_value_models.gather` ثمّ `value` ثمّ `blend`) — تُبدَّل أبوابُ مدخلاتها فقط.
  · ثمّ يُقاس ما حدث بعد 6 و12 شهراً: عائدُ السهم ناقصاً عائدَ تاسي (السعريّ بالسعريّ).
  · ويُحكم: هل الأرخصُ عند المحرّك تفوّق فعلاً؟ (ارتباطُ الرتبة · الخُمسيّات · نسبةُ الإصابة) — لكلّ درجة ثقةٍ ولكلّ قطاع.
    وهل الهدفُ لاثني عشر شهراً أقربُ إلى السعر الذي تحقّق من «لا تغيُّر»؟

حدودُه المعلومة (تُقال مع النتيجة): الكونُ هو المدرَجُ اليوم · عددُ الأسهم عددُ اليوم مع أسعارٍ معدَّلةٍ للمنح والتجزئة (فالقيمةُ
السوقيةُ يومها صحيحة إلا بعد اكتتابٍ بحقوق) · بيتا القطاع وتصنيفُه وأرقامُ القوائم المعادُ عرضُها من اليوم · لا مكرّرَ
صفحة «تداول» ولا إعلاناتِ نتائج (لا تاريخَ لهما عندنا) — فتمتنع الماليةُ التي توقّفت ملفّاتُها كما كانت ستمتنع.

    docker exec sp_backend python /app/scripts/audit/fv_backtest_d699.py
"""
import asyncio
import base64
import gzip
import hashlib
import json
import math
import os
import statistics as st
import sys
from datetime import date, timedelta

# ‏D700: يقيس أيَّ شيفرة — `SP_CODE_ROOT` جذرُ الأساس المجمَّد (مهمّةُ candidate_ab) أو الإنتاجُ (‏/app) — على البيانات نفسِها
_ROOT = os.environ.get("SP_CODE_ROOT") or "/app"
sys.path.insert(0, _ROOT)
import app as _app   # noqa: E402,F401
sys.path.insert(1, "/app/scripts/audit")


def _fp(root: str) -> str | None:
    try:
        from engine_freeze_d635 import FILES, ROOT as FR
    except Exception:                                              # noqa: BLE001
        return None
    h = hashlib.sha1()
    for f in FILES:
        rel = f.relative_to(FR).as_posix()
        h.update(rel.encode())
        q = os.path.join(root, rel[len("backend/"):]) if rel.startswith("backend/") else os.path.join(root, rel)
        h.update(open(q, "rb").read() if os.path.exists(q) else b"<missing>")
    return h.hexdigest()[:12]

H = (6, 12)
FIRST = "2023-03"
STEP = 3


def ym_add(ym: str, k: int) -> str:
    y, m = int(ym[:4]), int(ym[5:7]) - 1 + k
    return f"{y + m // 12:04d}-{m % 12 + 1:02d}"


def month_end(ym: str) -> date:
    return date.fromisoformat(ym_add(ym, 1) + "-01") - timedelta(days=1)


def ranks(xs):
    o = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and xs[o[j + 1]] == xs[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(a, b):
    if len(a) < 8:
        return None
    ra, rb = ranks(a), ranks(b)
    ma, mb = st.fmean(ra), st.fmean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else None


async def main():
    from app.services import cache as C, lastgood as LG, tadawul_xbrl as XB, tadawul_market as TM
    from app.services import fair_value_models as F, stars_backtest as B, split_watch as SW
    from app.services import tadawul_dividends as TD, tadawul_financials as TF, results_announcements as RA
    from app.services.analysis import confidence_of, V1_UNCALIBRATED
    from app.services.statement_merge import archetype_of
    from app.data.market_universe import MARKET_UNIVERSE as MU
    from app.data.universe import main_market

    # ══ قراءةٌ فقط: لا يُكتب في مخزنٍ ولا كاش ══
    C._flush = lambda *a, **k: None
    LG.save = lambda *a, **k: None

    data = LG.load(B.DATA_KEY) or {}
    if not data.get("px") or not data.get("tasi"):
        print("@@BT@@ لا بياناتِ أسعارٍ تاريخية (stars:bt:data) — لا حكم")
        return
    tasi = data["tasi"]
    PX = {s: dict(B.clean_months(d.get("m"))) for s, d in data["px"].items()}
    DIV = {s: sorted(d.get("div") or []) for s, d in data["px"].items()}
    rows_today = TM.usable_rows()[0] or {}
    main = main_market(MU)
    uni = {}
    for s in main:
        r = rows_today.get(s) or rows_today.get(s + ".SR") or {}
        p, mc = F._n(r.get("price")), F._n(r.get("market_cap"))
        sh = (mc / p) if (mc and p) else None
        if not sh:
            try:
                sh = TF.issued_shares(s)
            except Exception:                                      # noqa: BLE001
                sh = None
        if not sh or s not in PX or archetype_of(s) == "reit":
            continue
        uni[s] = {"shares": sh, "sector_en": r.get("sector_en"), "sector": (MU.get(s) or {}).get("sector") or "—",
                  "arch": archetype_of(s) or "—"}
    print(f"@@BT@@ الكون {len(uni)} شركة (رئيسيةٌ مدرجةٌ اليوم بسعرٍ تاريخيّ وعددِ أسهم · بلا صناديق)")

    # ══ القوائمُ كما هي اليوم، تُرشَّح لكلّ تاريخٍ بتاريخ نشرها ══
    RAW = {}
    for s in uni:
        try:
            RAW[s] = ([dict(p, _sym=s) for p in (XB.for_symbol(s, "annual") or [])],
                      [dict(p, _sym=s) for p in (XB.for_symbol(s, "quarterly") or [])])
        except Exception:                                          # noqa: BLE001
            RAW[s] = ([], [])

    def _end(p):
        return str(p.get("as_of") or f"{p.get('year')}-12-31")[:10]

    ctx = {"cut": None, "ym": None, "peer": {}}
    real_X, real_shares, real_get, real_set = XB.for_symbol, F._shares_of, C.get, C.set

    def X_pit(symbol, kind="annual"):
        s = str(symbol).replace(".SR", "")
        an, qu = RAW.get(s) or ([], [])
        rows, lag = (an, B.LAG_ANNUAL) if kind == "annual" else (qu, B.LAG_QUARTER)
        cut = ctx["cut"]
        out = []
        for p in rows:
            try:
                if date.fromisoformat(_end(p)) + timedelta(days=lag) <= cut:
                    out.append(p)
            except ValueError:
                continue
        return sorted(out, key=_end)

    def shares_pit(annual, quarterly):
        s = next((p.get("_sym") for p in list(quarterly) + list(annual) if p.get("_sym")), None)
        if s and uni.get(s, {}).get("shares"):
            return uni[s]["shares"]
        return real_shares(annual, quarterly)

    async def div_pit(symbol):
        s = str(symbol).replace(".SR", "")
        cut = ctx["cut"]
        shift = date.today() - cut                      # المحرّكُ يقصّ «آخرَ 365 يوماً» من اليوم — فتُزاح التواريخُ إلى نافذته
        return {"history": [{"date": (date.fromisoformat(d[:10]) + shift).isoformat(), "amount": a}
                            for d, a in DIV.get(s) or [] if date.fromisoformat(d[:10]) <= cut]}

    async def hist_pit(sym, annual, shares):
        m = PX.get(sym) or {}
        closes = sorted((month_end(ym).isoformat(), c) for ym, c in m.items() if ym <= ctx["ym"] and c)
        out = {"pe": [], "pb": [], "ps": []}
        for per in F._same_company(annual[-5:], shares):
            d = str(per.get("as_of") or "")[:10]
            before = [c for dd, c in closes if dd <= d]
            if not d or not before or not shares or shares <= 0:
                continue
            px = before[-1]
            ni, eq, rev = F._n(per.get("net_income")), F._n(per.get("equity")), F._n(per.get("revenue"))
            for k, base, lo, hi in (("pe", ni, 3, 80), ("pb", eq, 0.2, 30), ("ps", rev, 0.1, 40)):
                if base and base > 0:
                    v = px * shares / base
                    if lo < v <= hi:
                        out[k].append(round(v, 3))
        return {k: v for k, v in out.items() if len(v) >= 3}

    def cget(key):
        return ctx["peer"].get(key) if str(key).startswith("fvm:peers") else real_get(key)

    def cset(key, val, ttl):
        if str(key).startswith("fvm:peers"):
            ctx["peer"][key] = val

    XB.for_symbol = X_pit
    F._shares_of = shares_pit
    F._hist_multiples = hist_pit
    TD.read = div_pit
    SW.factor_after = lambda *a, **k: 1.0
    TF.page_pe = lambda *a, **k: None
    RA.latest = lambda *a, **k: None
    C.get, C.set = cget, cset

    last_full = ym_add(date.today().isoformat()[:7], -1)
    anchors, ym = [], FIRST
    while ym_add(ym, H[0]) <= last_full:
        anchors.append(ym)
        ym = ym_add(ym, STEP)
    obs, fobs = [], []
    for t in anchors:
        ctx.update(cut=month_end(t), ym=t, peer={})
        rows_t = {}
        for s, u in uni.items():
            p = PX[s].get(t)
            if p:
                rows_t[s] = {"price": p, "market_cap": p * u["shares"], "sector_en": u["sector_en"]}
        TM.usable_rows = lambda _r=rows_t: (_r, False, None)
        n_val = 0
        # ‏D700: الدرجةُ المالية بالدالّة نفسِها التي تعرضها البطاقة (`governed_finance_score`) على القوائم المنشورة يومها
        for s in sorted(rows_t):
            fs = fin_score(s, X_pit(s, "annual"))
            if fs is None:
                continue
            fo = {"s": s, "t": t, "fs": fs, "sec": uni[s]["sector"]}
            for h in H:
                t2 = ym_add(t, h)
                p2 = PX[s].get(t2)
                if t2 <= last_full and p2 and t in tasi and t2 in tasi:
                    fo[f"x{h}"] = round(p2 / rows_t[s]["price"] - tasi[t2] / tasi[t], 5)
            fobs.append(fo)
        for s in sorted(rows_t):
            try:
                i = await F.gather(s)
                if not i:
                    continue
                an, qu = X_pit(s, "annual"), X_pit(s, "quarterly")
                last = max((_end(x) for x in (qu[-1:] + an[-1:])), default=None)
                i.stale_days = (ctx["cut"] - date.fromisoformat(last)).days if last else None
                res = F.value(i)
                if not res or not res.get("value"):
                    continue
                dy = (i.dps_ttm / i.price) if (i.dps_ttm and i.price) else None
                res = F.blend(res, None, i.archetype, dy)
            except Exception as e:                                 # noqa: BLE001
                print(f"   {t} {s} تعذّر: {type(e).__name__}: {str(e)[:80]}")
                continue
            p0 = rows_t[s]["price"]
            res.setdefault("archetype", i.archetype)
            conf = confidence_of(res)
            if uni[s]["sector"] in V1_UNCALIBRATED:
                conf = "منخفضة"
            up = res["value"] / p0 - 1
            shown = not (conf == "منخفضة" and abs(up) > 0.60)      # ‏D628: البعيدُ المتباينُ لا يُنشر
            o = {"s": s, "t": t, "p0": round(p0, 4), "fv": res["value"], "mv": res.get("model_value"),
                 "lo": res.get("low"), "hi": res.get("high"), "tg": res.get("target_12m"), "c": conf, "sh": shown,
                 "n": res.get("count"), "sec": uni[s]["sector"], "a": uni[s]["arch"],
                 # كلُّ نموذجٍ بنسبته إلى السعر — الداخلُ والمستبعَد — ليُعرف أيُّها يتنبّأ فعلاً
                 "m": {m["key"]: round(m["value"] / p0, 4) for m in (res.get("models") or []) + (res.get("excluded") or [])
                       if isinstance(m.get("value"), (int, float)) and m["value"] > 0},
                 "u": [m["key"] for m in res.get("models") or []], "wk": res.get("weights_kind")}
            o["arch_key"] = i.archetype
            o["b"] = _bucket(o)
            for h in H:
                t2 = ym_add(t, h)
                p2 = PX[s].get(t2)
                if t2 <= last_full and p2 and t in tasi and t2 in tasi:
                    o[f"r{h}"] = round(p2 / p0 - 1, 5)
                    o[f"x{h}"] = round(p2 / p0 - tasi[t2] / tasi[t], 5)
                    if h == 12:
                        o["p12"] = round(p2, 4)
            obs.append(o)
            n_val += 1
        print(f"   {t}: مسعَّرة {len(rows_t)} · قُيّمت {n_val} · كاشُ الأقران {len(ctx['peer'])} قطاعاً")

    XB.for_symbol, F._shares_of, C.get, C.set = real_X, real_shares, real_get, real_set
    report(obs, anchors)
    print(f"@@ENGINE_FP@@ {_fp(_ROOT)}")
    om = outcome_metrics(obs, anchors)
    om.update(fs_report(fobs, anchors))
    print("@@METRICS@@ " + json.dumps(om, ensure_ascii=False))
    print("@@TRACK@@ " + json.dumps(track_table(obs), ensure_ascii=False))
    blob = base64.b64encode(gzip.compress(json.dumps(obs, ensure_ascii=False, separators=(",", ":")).encode())).decode()
    parts = [blob[i:i + 60000] for i in range(0, len(blob), 60000)]
    for j, b in enumerate(parts):
        print(f"@@OBS@@ {j + 1}/{len(parts)} {b}")


def fin_score(sym, annual):
    """الدرجةُ المالية كما تحسبها البطاقة — من السنوات المنشورة حتى التاريخ (نسبةُ المديونية كسراً كما في الفترات)."""
    if not annual:
        return None
    try:
        from app.services.scores import governed_finance_score
    except Exception:                                              # noqa: BLE001
        return None
    per = []
    for p in annual:
        q = dict(p)
        if isinstance(q.get("debt_ratio"), (int, float)):
            q["debt_ratio"] = q["debt_ratio"] / 100
        e, ie = q.get("ebit"), q.get("interest_expense")
        q["interest_coverage"] = (e / abs(ie)) if isinstance(e, (int, float)) and isinstance(ie, (int, float)) and ie else None
        per.append(q)
    try:
        sc = governed_finance_score(per, sym)[0]
    except Exception:                                              # noqa: BLE001
        return None
    return float(sc) if isinstance(sc, (int, float)) else None


def fs_report(fobs, anchors):
    """هل الدرجةُ المالية الأعلى سبقت السوق؟ — ارتباطُ الرتبة والشرائح بعد 6 و12 شهراً."""
    out = {}
    print(f"\n══ الدرجةُ المالية: {len(fobs)} مشاهدة ══")
    for h in H:
        k = f"x{h}"
        ics = []
        for t in anchors:
            g = [o for o in fobs if o["t"] == t and k in o]
            ic = spearman([o["fs"] for o in g], [o[k] for o in g])
            if ic is not None:
                ics.append(ic)
        if ics:
            m, sd = st.fmean(ics), (st.stdev(ics) if len(ics) > 1 else 0)
            print(f"@@FSIC{h}@@ ارتباطُ الرتبة {m:+.3f} · t={(m / sd * math.sqrt(len(ics)) if sd else 0):.2f} · موجبٌ في "
                  f"{sum(x > 0 for x in ics)} من {len(ics)}")
            out[f"o_fs_ic{h}"] = round(m, 4)
    _rel(fobs, 12)
    for nm, lo, hi in (("خطٌّ أحمر (صفر)", -1, 0.5), ("دون 50", 0.5, 50), ("50–70", 50, 70), ("70 فأعلى", 70, 101)):
        g = [o for o in fobs if "q12" in o and lo <= o["fs"] < hi]
        if len(g) >= 10:
            a = [o for o in g if o["t"] <= "2024-06"]
            b = [o for o in g if o["t"] >= "2024-09"]
            hr = lambda z: f"{sum(o['q12'] > 0 for o in z) / len(z) * 100:.0f}٪" if z else "—"   # noqa: E731
            print(f"@@FSB@@ {nm}: {len(g)} · تفوّق على الوسيط {hr(g)} (النصفان {hr(a)} · {hr(b)}) · "
                  f"متوسّط {st.fmean([o['q12'] for o in g]) * 100:+.1f}٪")
    return out


def _rel(obs, h):
    """التفوّقُ على الشركة الوسيطة في التاريخ نفسِه — لا على تاسي وحده (السوقُ بأوزانه يختلف عن الشركة النموذجية)."""
    k, by = f"x{h}", {}
    for o in obs:
        if k in o:
            by.setdefault(o["t"], []).append(o[k])
    med = {t: st.median(v) for t, v in by.items()}
    for o in obs:
        if k in o:
            o[f"q{h}"] = o[k] - med[o["t"]]


def _bucket(o):
    """فئةُ القراءة كما تقرؤها الثقةُ في التطبيق (`fair_value_models.track_bucket`)."""
    try:
        from app.services.fair_value_models import track_bucket
    except Exception:                                              # noqa: BLE001
        return None
    return track_bucket({"model_value": o.get("mv"), "price": o["p0"], "count": o.get("n"), "weights_kind": o.get("wk"),
                         "archetype": o.get("arch_key")})


def track_table(obs):
    """‏D700: لكلّ فئة قراءةٍ نسبةُ إصابتها بعد اثني عشر شهراً — الرخيصُ تفوّق والغالي تخلّف والعادلُ لم يبتعد 15٪."""
    _rel(obs, 12)
    out = {}
    for o in obs:
        b = o.get("b")
        if not b or "q12" not in o or not o["sh"]:
            continue
        side = b.rsplit("_", 1)[-1]
        hit = (o["q12"] > 0) if side in ("cheap", "deep") else (o["q12"] < 0) if side == "dear" else (abs(o["q12"]) <= 0.15)
        r = out.setdefault(b, {"n": 0, "hit": 0, "n1": 0, "hit1": 0})
        r["n"] += 1
        r["hit"] += hit
        if o["t"] <= "2024-06":
            r["n1"] += 1
            r["hit1"] += hit
    return {b: {"n": r["n"], "hit": round(r["hit"] / r["n"] * 100), "n1": r["n1"],
                "hit1": round(r["hit1"] / r["n1"] * 100) if r["n1"] else None,
                "hit2": round((r["hit"] - r["hit1"]) / (r["n"] - r["n1"]) * 100) if r["n"] > r["n1"] else None}
            for b, r in sorted(out.items())}


def outcome_metrics(obs, anchors):
    """مقاييسُ النتيجة لحارس التجميد (‏D700): الأعلى أفضل إلا خطأَ الهدف."""
    m = {}
    for h in H:
        k = f"x{h}"
        ics = []
        for t in anchors:
            g = [o for o in obs if o["t"] == t and k in o and o["sh"]]
            ic = spearman([o["fv"] / o["p0"] for o in g], [o[k] for o in g])
            if ic is not None:
                ics.append(ic)
        m[f"o_ic{h}"] = round(st.fmean(ics), 4) if ics else None
    _rel(obs, 12)
    qs = {0: [], 4: []}
    for t in anchors:
        g = sorted([o for o in obs if o["t"] == t and "q12" in o and o["sh"]], key=lambda o: -(o["fv"] / o["p0"]))
        for j, o in enumerate(g):
            q = min(4, j * 5 // max(1, len(g)))
            if q in qs:
                qs[q].append(o["q12"])
    m["o_spread12"] = round((st.fmean(qs[0]) - st.fmean(qs[4])) * 100, 2) if qs[0] and qs[4] else None
    ch = [o for o in obs if o["sh"] and "q12" in o and o["fv"] / o["p0"] >= 1.05]
    m["o_cheap_hit12"] = round(sum(o["q12"] > 0 for o in ch) / len(ch), 4) if ch else None
    tg = [o for o in obs if o["sh"] and o.get("p12") and o.get("tg")]
    m["o_target_err"] = round(st.median([abs(o["p12"] / o["tg"] - 1) for o in tg]), 4) if tg else None
    return m


def report(obs, anchors):
    print(f"\n@@BT@@ المشاهدات {len(obs)} · التواريخ {len(anchors)} ({anchors[0]} … {anchors[-1]})")
    for h in H:
        k = f"x{h}"
        rows = [o for o in obs if k in o]
        print(f"\n══ بعد {h} شهراً: {len(rows)} مشاهدة ══")
        ics = []
        for t in anchors:
            g = [o for o in rows if o["t"] == t]
            ic = spearman([o["fv"] / o["p0"] for o in g], [o[k] for o in g])
            if ic is not None:
                ics.append(ic)
        if ics:
            m, sd = st.fmean(ics), (st.stdev(ics) if len(ics) > 1 else 0)
            tt = m / sd * math.sqrt(len(ics)) if sd else 0
            print(f"@@IC{h}@@ ارتباطُ الرتبة (الصعودُ إلى العادل ↔ التفوّقُ على تاسي) {m:+.3f} · t={tt:.2f} · "
                  f"موجبٌ في {sum(x > 0 for x in ics)} من {len(ics)} · {' '.join(f'{x:+.2f}' for x in ics)}")
        # الخُمسيّات: الأوّلُ الأرخصُ عند المحرّك
        qs = {q: [] for q in range(5)}
        for t in anchors:
            g = sorted([o for o in rows if o["t"] == t], key=lambda o: -(o["fv"] / o["p0"]))
            for j, o in enumerate(g):
                qs[min(4, j * 5 // max(1, len(g)))].append(o[k])
        line = " · ".join(f"خ{q + 1} {st.fmean(v) * 100:+.1f}٪ (فوزٌ {sum(x > 0 for x in v) / len(v) * 100:.0f}٪)"
                          for q, v in qs.items() if v)
        print(f"@@Q{h}@@ {line}")
        for nm, sel in (("كلّ المعروض", lambda o: o["sh"]),
                        ("مرتفعة", lambda o: o["sh"] and o["c"] == "مرتفعة"),
                        ("متوسطة", lambda o: o["sh"] and o["c"] == "متوسطة"),
                        ("منخفضة", lambda o: o["sh"] and o["c"] == "منخفضة"),
                        ("المحجوب", lambda o: not o["sh"])):
            g = [o for o in rows if sel(o)]
            if len(g) < 10:
                print(f"   {nm}: {len(g)} — قليل")
                continue
            ic = spearman([o["fv"] / o["p0"] for o in g], [o[k] for o in g])
            cheap = [o for o in g if o["fv"] / o["p0"] - 1 > 0.10]
            dear = [o for o in g if o["fv"] / o["p0"] - 1 < -0.10]
            hc = sum(o[k] > 0 for o in cheap) / len(cheap) * 100 if cheap else float("nan")
            hd = sum(o[k] < 0 for o in dear) / len(dear) * 100 if dear else float("nan")
            mc = st.fmean([o[k] for o in cheap]) * 100 if cheap else float("nan")
            md = st.fmean([o[k] for o in dear]) * 100 if dear else float("nan")
            print(f"@@C{h}@@ {nm}: {len(g)} · ارتباط {ic if ic is None else round(ic, 3)} · "
                  f"الرخيصُ (+10٪) {len(cheap)} تفوّق {hc:.0f}٪ بمتوسّط {mc:+.1f}٪ · "
                  f"الغالي (−10٪) {len(dear)} تخلّف {hd:.0f}٪ بمتوسّط {md:+.1f}٪")
    # الهدفُ لاثني عشر شهراً مقابلَ «لا تغيُّر»
    g = [o for o in obs if o.get("p12") and o.get("tg") and o["sh"]]
    if g:
        e_t = st.median([abs(o["p12"] / o["tg"] - 1) for o in g]) * 100
        e_0 = st.median([abs(o["p12"] / o["p0"] - 1) for o in g]) * 100
        e_f = st.median([abs(o["p12"] / o["fv"] - 1) for o in g]) * 100
        dirn = [o for o in g if abs(o["tg"] / o["p0"] - 1) > 0.05]
        hit = sum((o["tg"] > o["p0"]) == (o["p12"] > o["p0"]) for o in dirn) / len(dirn) * 100 if dirn else float("nan")
        inr = [o for o in g if o.get("lo") and o.get("hi")]
        cov = sum(o["lo"] <= o["p12"] <= o["hi"] for o in inr) / len(inr) * 100 if inr else float("nan")
        print(f"\n@@TG@@ الهدفُ لاثني عشر شهراً ({len(g)}): خطؤه الوسيط {e_t:.1f}٪ · العادلُ {e_f:.1f}٪ · «لا تغيُّر» {e_0:.1f}٪ · "
              f"اتّجاهُه صحيحٌ {hit:.0f}٪ من {len(dirn)} · السعرُ بعد سنةٍ داخل النطاق {cov:.0f}٪")
        for c in ("مرتفعة", "متوسطة", "منخفضة"):
            gc = [o for o in g if o["c"] == c]
            if len(gc) >= 10:
                dc = [o for o in gc if abs(o["tg"] / o["p0"] - 1) > 0.05]
                print(f"   {c}: {len(gc)} · خطأ الهدف {st.median([abs(o['p12'] / o['tg'] - 1) for o in gc]) * 100:.1f}٪ · "
                      f"«لا تغيُّر» {st.median([abs(o['p12'] / o['p0'] - 1) for o in gc]) * 100:.1f}٪ · "
                      f"اتّجاه {sum((o['tg'] > o['p0']) == (o['p12'] > o['p0']) for o in dc) / max(1, len(dc)) * 100:.0f}٪")
    # القطاعات (12 شهراً، مجمَّعة)
    print("\n══ القطاعات (بعد 12 شهراً · المعروضُ وحدَه) ══")
    secs = {}
    for o in obs:
        if "x12" in o and o["sh"]:
            secs.setdefault(o["sec"], []).append(o)
    for sec, g in sorted(secs.items(), key=lambda kv: -len(kv[1])):
        ic = spearman([o["fv"] / o["p0"] for o in g], [o["x12"] for o in g])
        cheap = [o for o in g if o["fv"] / o["p0"] - 1 > 0.10]
        hc = sum(o["x12"] > 0 for o in cheap) / len(cheap) * 100 if cheap else float("nan")
        print(f"@@S@@ {sec}: {len(g)} · ارتباط {'—' if ic is None else f'{ic:+.2f}'} · الرخيصُ {len(cheap)} تفوّق {hc:.0f}٪")


asyncio.run(main())
