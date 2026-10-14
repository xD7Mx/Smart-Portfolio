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
import re
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
    try:
        from engine_freeze_d635 import LATER
    except ImportError:
        LATER = frozenset()
    h = hashlib.sha1()
    for f in FILES:
        rel = f.relative_to(FR).as_posix()
        q = os.path.join(root, rel[len("backend/"):]) if rel.startswith("backend/") else os.path.join(root, rel)
        if not os.path.exists(q) and rel in LATER:                # ‏D674: أُضيف بعد التجميد وغائبٌ في الأساس
            continue
        h.update(rel.encode())
        h.update(open(q, "rb").read() if os.path.exists(q) else b"<missing>")
    return h.hexdigest()[:12]

H = (3, 6, 12)          # ‏D706 (بأمر المالك): 90 و180 و365 يوماً — التاريخُ جوهرُ التوقّع، فلا يُنتظر المستقبلُ ليُحكم
# ‏D701: «محرّكٌ شاملٌ للسوق الرئيسي» — مع هذا المفتاح يُسجَّل لكلّ شركةٍ في كلّ تاريخٍ كلُّ ما يُعرف يومها (كلُّ نموذجٍ بنسبته إلى السعر
# ولو امتنع المحرّك · المضاعفاتُ الخام · النموُّ والعائدُ على الحقوق · الزخمُ · التوزيع · الحجم) ومعه ما حدث — ليُبنى لكلّ نمطٍ
# ما يثبت بالنتيجة. يضبطه `fv_universe_d701.py`.
UNIVERSE = os.environ.get("SP_BT_UNIVERSE") == "1"
# ‏D706: أوّلُ تاريخٍ يُقاس — 2023 افتراضاً (مقاييسُ حارس التجميد)، ويمتدّ بـ‎SP_BT_FIRST إلى ما تسمح به البيانات (‏history_ab)
_FIRST_ENV = os.environ.get("SP_BT_FIRST") or ""
FIRST = _FIRST_ENV if re.fullmatch(r"20[12]\d-(03|06|09|12)", _FIRST_ENV) else "2023-03"
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
    if hasattr(F, "_monthly_closes"):                              # ‏D702: الزخمُ بأسعار ما قبل التاريخ
        F._monthly_closes = lambda sym: {ym: c for ym, c in (PX.get(str(sym).replace(".SR", "")) or {}).items() if ym < ctx["ym"]}
        F._month_now = lambda: ctx["ym"]
    F._hist_multiples = hist_pit
    TD.read = div_pit
    SW.factor_after = lambda *a, **k: 1.0
    try:                                                           # ‏D674: أحداثُ رأس المال اليوم ليست ما كان معلوماً يومها
        from app.services import capital_events as _CE
        _CE.kind_after = lambda *a, **k: None
    except ImportError:                                            # الشاهدُ المجمَّد قبل D674
        pass
    TF.page_pe = lambda *a, **k: None
    RA.latest = lambda *a, **k: None
    C.get, C.set = cget, cset

    last_full = ym_add(date.today().isoformat()[:7], -1)
    anchors, ym = [], FIRST
    while ym_add(ym, H[0]) <= last_full:
        anchors.append(ym)
        ym = ym_add(ym, STEP)
    obs, fobs, uobs = [], [], []

    def _fwd(o, s, t, p0):
        for h in H:
            t2 = ym_add(t, h)
            p2 = PX[s].get(t2)
            if t2 <= last_full and p2 and t in tasi and t2 in tasi:
                o[f"r{h}"] = round(p2 / p0 - 1, 5)
                o[f"x{h}"] = round(p2 / p0 - tasi[t2] / tasi[t], 5)

    def _urow(s, t, i, p0):
        """صفُّ الشركة يومها: كلُّ ما يُعرف — للبحث عمّا يتنبّأ في كلّ نمط (‏D701)."""
        n = F._n
        m = PX[s]
        o = {"s": s, "t": t, "a": uni[s]["arch"], "sec": uni[s]["sector"], "p0": round(p0, 4)}
        c1, c12, c3 = m.get(ym_add(t, -1)), m.get(ym_add(t, -12)), m.get(ym_add(t, -3))
        if c1 and c12:
            o["mom"] = round(c1 / c12 - 1, 4)                         # ‏12−1: زخمُ سنةٍ بلا الشهر الأخير
        if c3:
            o["mom3"] = round(p0 / c3 - 1, 4)
        if c1:
            o["rev1"] = round(p0 / c1 - 1, 4)
        mc = p0 * uni[s]["shares"]
        o["size"] = round(math.log(mc), 3) if mc > 0 else None
        if i:
            ttm, bal = i.ttm or {}, i.balance or {}
            ni, rev, eq = n(ttm.get("net_income")), n(ttm.get("revenue")), n(bal.get("equity"))
            ebit, ocf = n(ttm.get("ebit")), n(ttm.get("operating_cash_flow"))
            debt, cash = n(bal.get("total_debt")) or 0.0, n(bal.get("ending_cash")) or 0.0
            ev = mc + debt - cash
            o.update({"ey": round(ni / mc, 5) if ni is not None else None, "bp": round(eq / mc, 5) if eq else None,
                      "sp": round(rev / mc, 5) if rev else None, "cp": round(ocf / mc, 5) if ocf is not None else None,
                      "ebit_ev": round(ebit / ev, 5) if ebit is not None and ev > 0 else None,
                      "dy": round(i.dps_ttm / p0, 5) if i.dps_ttm else 0.0, "lev": round(debt / mc, 4),
                      "stale": i.stale_days, "sig": fin_signals(X_pit(s, "annual"))})
            try:
                bs = F.base_of(i)
                every = (F.cashflow_models(i, bs) + F.equity_models(i, bs) + F.multiple_models(i, bs)) if bs else \
                    ((F._equity_only(i) or {}).get("models") or [])
                o["m"] = {x["key"]: round(x["value"] / p0, 4) for x in every
                          if isinstance(x.get("value"), (int, float)) and x["value"] > 0}
            except Exception as e:                                 # noqa: BLE001
                o["m_err"] = type(e).__name__
        _fwd(o, s, t, p0)
        return o

    pending: list = []

    def _record(s, t, i, res) -> int:
        p0 = rows_now[s]["price"]
        res.setdefault("archetype", i.archetype)
        conf = confidence_of(res)
        if uni[s]["sector"] in V1_UNCALIBRATED:
            conf = "منخفضة"
        up = res["value"] / p0 - 1
        shown = not (conf == "منخفضة" and abs(up) > 0.60)          # ‏D628: البعيدُ المتباينُ لا يُنشر
        o = {"s": s, "t": t, "p0": round(p0, 4), "fv": res["value"], "mv": res.get("model_value"),
             "lo": res.get("low"), "hi": res.get("high"), "tg": res.get("target_12m"), "c": conf, "sh": shown,
             "n": res.get("count"), "sec": uni[s]["sector"], "a": uni[s]["arch"],
             # كلُّ نموذجٍ بنسبته إلى السعر — الداخلُ والمستبعَد — ليُعرف أيُّها يتنبّأ فعلاً
             "m": {m["key"]: round(m["value"] / p0, 4) for m in (res.get("models") or []) + (res.get("excluded") or [])
                   if isinstance(m.get("value"), (int, float)) and m["value"] > 0},
             "u": [m["key"] for m in res.get("models") or []], "wk": res.get("weights_kind"),
             "rz": res.get("rel_z"), "rseg": (res.get("rel") or {}).get("seg"), "rpart": res.get("rel_part")}
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
        return 1

    rows_now: dict = {}
    for t in anchors:
        ctx.update(cut=month_end(t), ym=t, peer={})
        rows_t = {}
        for s, u in uni.items():
            p = PX[s].get(t)
            if p:
                rows_t[s] = {"price": p, "market_cap": p * u["shares"], "sector_en": u["sector_en"]}
        TM.usable_rows = lambda _r=rows_t: (_r, False, None)
        rows_now.clear()
        rows_now.update(rows_t)
        n_val = 0
        # ‏D700: الدرجةُ المالية بالدالّة نفسِها التي تعرضها البطاقة (`governed_finance_score`) على القوائم المنشورة يومها
        for s in sorted(rows_t):
            fs = fin_score(s, X_pit(s, "annual"))
            if fs is None:
                continue
            fo = {"s": s, "t": t, "fs": fs, "sec": uni[s]["sector"], "sig": fin_signals(X_pit(s, "annual"))}
            for h in H:
                t2 = ym_add(t, h)
                p2 = PX[s].get(t2)
                if t2 <= last_full and p2 and t in tasi and t2 in tasi:
                    fo[f"x{h}"] = round(p2 / rows_t[s]["price"] - tasi[t2] / tasi[t], 5)
            fobs.append(fo)
        for s in sorted(rows_t):
            try:
                i = await F.gather(s)
                if i:
                    an, qu = X_pit(s, "annual"), X_pit(s, "quarterly")
                    last = max((_end(x) for x in (qu[-1:] + an[-1:])), default=None)
                    i.stale_days = (ctx["cut"] - date.fromisoformat(last)).days if last else None
                if UNIVERSE:
                    _uo = _urow(s, t, i, rows_t[s]["price"])
                    uobs.append(_uo)
                if not i:
                    continue
                res = F.value(i)
                if UNIVERSE and res:
                    _uo["fv"] = round(res["value"] / rows_t[s]["price"], 4) if res.get("value") else None
                    _uo["why"] = None if res.get("value") else str(res.get("reason") or "")[:40]
                dy = (i.dps_ttm / i.price) if (i.dps_ttm and i.price) else None
                if res and res.get("rel") and hasattr(F, "apply_relative"):
                    pending.append((s, i, res, dy))                 # ‏D701 · D702: الجولةُ الثانية بعد أن يُعرف الأقران
                    continue
                if not res or not res.get("value"):
                    continue
                res = F.blend(res, None, i.archetype, dy)
            except Exception as e:                                 # noqa: BLE001
                print(f"   {t} {s} تعذّر: {type(e).__name__}: {str(e)[:80]}")
                continue
            n_val += _record(s, t, i, res)
        # ‏D701: جداولُ الأقران لهذا التاريخ من الجولة الأولى، ثمّ المقارنةُ بها — كما تفعل المسحة
        tables = {}
        for s, i, res, dy in pending:
            tables.setdefault(res["rel"]["seg"], {})[s] = res["rel"]["sig"]
        for s, i, res, dy in pending:
            rv = F.apply_relative(s, res, rows_t[s]["price"], tables.get(res["rel"]["seg"]))
            if rv and rv.get("value"):
                rv.setdefault("archetype", i.archetype)
                n_val += _record(s, t, i, F.blend(rv, None, i.archetype, dy))
        n_rel = sum(1 for o in obs if o["t"] == t and o.get("wk") == "peer_relative")
        pending.clear()
        print(f"   {t}: مسعَّرة {len(rows_t)} · قُيّمت {n_val} (بالمقارنة بالأقران {n_rel}) · كاشُ الأقران {len(ctx['peer'])} قطاعاً")

    XB.for_symbol, F._shares_of, C.get, C.set = real_X, real_shares, real_get, real_set
    report(obs, anchors)
    print(f"@@ENGINE_FP@@ {_fp(_ROOT)}")
    om = outcome_metrics(obs, anchors)
    om.update(fs_report(fobs, anchors))
    print("@@METRICS@@ " + json.dumps(om, ensure_ascii=False))
    print("@@TRACK@@ " + json.dumps(track_table(obs), ensure_ascii=False))
    for tag, rows in (("OBS", obs),) + ((("UNI", uobs),) if UNIVERSE else ()):
        blob = base64.b64encode(gzip.compress(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode())).decode()
        parts = [blob[i:i + 60000] for i in range(0, len(blob), 60000)]
        for j, b in enumerate(parts):
            print(f"@@{tag}@@ {j + 1}/{len(parts)} {b}")



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


def fin_signals(annual):
    """مكوّناتُ الدرجة المالية كلٌّ وحدَه — ليُعرف أيُّها يتنبّأ: نموُّ الإيراد · جودةُ الربح (التشغيليّ ÷ الصافي) · هامشُ التدفّق
    الحرّ · العائدُ على الحقوق · المديونية (أدنى أفضل) · تغطيةُ الفوائد · هامشُ الربح · نموُّ الربح."""
    def n(x):
        return float(x) if isinstance(x, (int, float)) else None
    if not annual:
        return {}
    a, b, f = annual[-1], (annual[-2] if len(annual) >= 2 else {}), annual[0]
    out = {}
    r0, r1 = n(f.get("revenue")), n(a.get("revenue"))
    if r0 and r1 and r0 > 0 and r1 > 0 and len(annual) >= 2:
        out["growth"] = (r1 / r0) ** (1 / (len(annual) - 1)) - 1
    q = [n(p.get("operating_cash_flow")) / n(p.get("net_income")) for p in annual
         if n(p.get("operating_cash_flow")) is not None and n(p.get("net_income")) and n(p.get("net_income")) > 0]
    if q:
        out["eq"] = max(-3.0, min(3.0, st.fmean(q)))
    fm = [n(p.get("free_cash_flow")) / n(p.get("revenue")) for p in annual
          if n(p.get("free_cash_flow")) is not None and n(p.get("revenue")) and n(p.get("revenue")) > 0]
    if fm:
        out["fcf_m"] = st.fmean(fm)
    ni, eq_ = n(a.get("net_income")), n(a.get("equity"))
    if ni is not None and eq_ and eq_ > 0:
        out["roe"] = ni / eq_
    if n(a.get("debt_ratio")) is not None:
        out["low_debt"] = -n(a.get("debt_ratio"))
    e, ie = n(a.get("ebit")), n(a.get("interest_expense"))
    if e is not None and ie:
        out["cover"] = max(-20.0, min(50.0, e / abs(ie)))
    if ni is not None and r1 and r1 > 0:
        out["margin"] = ni / r1
    n0 = n(b.get("net_income"))
    if ni is not None and n0:
        out["ni_g"] = max(-2.0, min(2.0, (ni - n0) / abs(n0)))
    return {k: round(v, 5) for k, v in out.items()}


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
    for key in ("growth", "eq", "fcf_m", "roe", "low_debt", "cover", "margin", "ni_g"):
        row = []
        for h in H:
            k, ics = f"x{h}", []
            for t in anchors:
                g = [o for o in fobs if o["t"] == t and k in o and key in (o.get("sig") or {})]
                ic = spearman([o["sig"][key] for o in g], [o[k] for o in g])
                if ic is not None:
                    ics.append(ic)
            if ics:
                m, sd = st.fmean(ics), (st.stdev(ics) if len(ics) > 1 else 0)
                half = [st.fmean(ics[:len(ics) // 2]), st.fmean(ics[len(ics) // 2:])] if len(ics) >= 4 else []
                row.append(f"{h}ش {m:+.3f} (t {m / sd * math.sqrt(len(ics)) if sd else 0:+.1f} · النصفان "
                           + " / ".join(f"{x:+.2f}" for x in half) + ")")
        print(f"@@FSSIG@@ {key}: " + " · ".join(row))
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
                         "archetype": o.get("arch_key"), "rel_z": o.get("rz"), "rel": {"seg": o.get("rseg")},
                         "rel_part": o.get("rpart")})


def track_table(obs):
    """‏D700: لكلّ فئة قراءةٍ نسبةُ إصابتها بعد اثني عشر شهراً — الرخيصُ تفوّق والغالي تخلّف والعادلُ لم يبتعد 15٪."""
    _rel(obs, 12)
    # ‏D701: المصارفُ والمقارنةُ بالأقران تُقاس بأقرانها لا بالسوق كلِّه — قِيس أنّ «المصرفَ الرخيص 93٪» كان أكثرُه تفوّقَ المصارف
    # جميعاً في الفترة (والغالي منها تفوّق 69٪)، فليس مهارةَ التقييم
    seg_of = lambda o: "bank" if o.get("arch_key") == "bank" else (f"rel_{o.get('rseg')}" if o.get("wk") == "peer_relative" else None)   # noqa: E731
    segq: dict = {}
    for o in obs:
        if "q12" in o and seg_of(o):
            segq.setdefault((seg_of(o), o["t"]), []).append(o["q12"])
    segmed = {k: st.median(v) for k, v in segq.items()}
    out = {}
    for o in obs:
        b = o.get("b")
        if not b or "q12" not in o or not o["sh"]:
            continue
        q = o["q12"] - segmed[(seg_of(o), o["t"])] if seg_of(o) else o["q12"]
        side = b.rsplit("_", 1)[-1]
        hit = (q > 0) if side in ("cheap", "deep", "better") else (q < 0) if side in ("dear", "weaker") else (abs(q) <= 0.15)
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
    # ‏D705: السعرُ المستهدف يُقاس بنفسه — ارتباطُ رتبته بالتفوّق بعد سنة (والعادلُ في ‎o_ic12)
    ics = []
    for t in anchors:
        g = [o for o in obs if o["t"] == t and "x12" in o and o["sh"] and o.get("tg")]
        ic = spearman([o["tg"] / o["p0"] for o in g], [o["x12"] for o in g])
        if ic is not None:
            ics.append(ic)
    m["o_tg_ic12"] = round(st.fmean(ics), 4) if ics else None
    horizon_report(obs, anchors)
    return m


def horizon_report(obs, anchors):
    """‏D706: لكلّ أفقٍ (90 · 180 · 365 يوماً) — ارتباطُ العادل والمستهدف بالتفوّق، وإصابةُ «رخيص» و«غالٍ»، وفارقُ الخُمسين، ونصفا
    التاريخ، وكلُّ سنةٍ وحدها — على المشاهدات نفسِها. يُطبع للقراءة ولا يدخل مقاييسَ الحارس إلا ‎o_ic{h}."""
    half = anchors[len(anchors) // 2] if anchors else ""
    for h in H:
        k = f"x{h}"
        _rel(obs, h)
        g_all = [o for o in obs if o["sh"] and k in o]
        if not g_all:
            continue

        def ic_of(rows, key):
            ics = []
            for t in sorted({o["t"] for o in rows}):
                g = [o for o in rows if o["t"] == t and o.get(key)]
                ic = spearman([o[key] / o["p0"] for o in g], [o[k] for o in g])
                if ic is not None:
                    ics.append(ic)
            return (round(st.fmean(ics), 3), sum(x > 0 for x in ics), len(ics)) if ics else (None, 0, 0)
        fv, tg = ic_of(g_all, "fv"), ic_of(g_all, "tg")
        h1, h2 = ic_of([o for o in g_all if o["t"] < half], "fv"), ic_of([o for o in g_all if o["t"] >= half], "fv")
        q = f"q{h}"
        ch = [o for o in g_all if q in o and o["fv"] / o["p0"] >= 1.05]
        de = [o for o in g_all if q in o and o["fv"] / o["p0"] <= 0.95]
        qs = {0: [], 4: []}
        for t in sorted({o["t"] for o in g_all}):
            g = sorted([o for o in g_all if o["t"] == t and q in o], key=lambda o: -(o["fv"] / o["p0"]))
            for j, o in enumerate(g):
                b = min(4, j * 5 // max(1, len(g)))
                if b in qs:
                    qs[b].append(o[q])
        spread = (st.fmean(qs[0]) - st.fmean(qs[4])) * 100 if qs[0] and qs[4] else None
        yrs = {}
        for y in sorted({o["t"][:4] for o in g_all}):
            yrs[y] = ic_of([o for o in g_all if o["t"][:4] == y], "fv")[0]
        print(f"@@HORIZON@@ {h * 30} يوماً · مشاهدات {len(g_all)} · العادل {fv[0]:+.3f} (موجبٌ {fv[1]}/{fv[2]}) · النصفان "
              f"{h1[0]} / {h2[0]} · المستهدف {tg[0]} · إصابةُ «رخيص» {sum(o[q] > 0 for o in ch) / max(1, len(ch)):.0%} ({len(ch)}) · "
              f"«غالٍ» {sum(o[q] < 0 for o in de) / max(1, len(de)):.0%} ({len(de)}) · فارقُ الخُمسين "
              f"{spread if spread is None else round(spread, 1)} نقطة · بالسنة {yrs}")


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
