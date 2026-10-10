#!/usr/bin/env python3
"""ثقةُ «خلاصة المجلس» (الرقمُ الظاهر «ثقة X٪» في نافذة الحوكمة) — ما يحبسها دون 90؟ قارئٌ فقط.

‏`confidence.py`: الدرجةُ = 0.4 × سنواتُ القوائم (خمسٌ تامّة) + 0.4 × اكتمالُ 18 مؤشّراً أساسياً + 0.2 × مؤشّرُ الثبات.
فيُقاس لكلّ شركةٍ في السوق الرئيسيّ: الدرجةُ وأجزاؤها الثلاثة، وأيُّ المؤشّرات يغيب وفي أيّ نمط — أهو غيابُ بيانٍ
يُجلب، أم مؤشّرٌ لا معنى له في النمط (هامشُ الربح الإجماليّ في مصرف) يُعَدّ عليه ناقصاً وهو غيرُ قابلٍ للتطبيق.
"""
import asyncio, collections, contextvars, statistics, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market, is_nomu
from app.services import confidence as CF

uni = {s: m for s, m in main_market(MARKET_UNIVERSE).items() if not is_nomu(s)}
CUR = contextvars.ContextVar("sym", default=None)
CAP: dict = {}
_orig = CF.compute_confidence


def _cap(features):
    r = _orig(features)
    s = CUR.get()
    if s:
        CAP[s] = (features, r)
    return r

CF.compute_confidence = _cap


def _v(features, k):
    raw = features.get(k)
    return raw.get("value") if isinstance(raw, dict) else raw


async def main():
    from app.services.governance_engine import evaluate_company
    from app.services.statement_merge import archetype_of
    sem = asyncio.Semaphore(4)

    async def one(s):
        async with sem:
            CUR.set(s)
            try:
                await asyncio.wait_for(evaluate_company(f"{s}.SR", sector=uni[s].get("sector_ar")), timeout=60)
            except Exception as e:                                 # noqa: BLE001
                return s, type(e).__name__
            return s, None
    res = await asyncio.gather(*(one(s) for s in sorted(uni)))
    errs = collections.Counter(e for _, e in res if e)
    rows = []
    for s, (f, r) in CAP.items():
        miss = [k for k in CF._CORE_FEATURES if _v(f, k) is None]
        rows.append({"s": s, "score": r.score, "years": r.years_available, "comp": r.completeness_pct,
                     "cons": _v(f, "consistency_index"), "miss": miss, "arch": archetype_of(s) or "—"})
    print(f"═ الشركات {len(uni)} · قِيست {len(rows)} · تعذّر {sum(errs.values())} {dict(errs)}")
    sc = sorted(x["score"] for x in rows)
    if not sc:
        return
    print(f"   الدرجة: وسيط {statistics.median(sc):.0f} · ≥95 {sum(1 for x in sc if x >= 95)} · ≥90 {sum(1 for x in sc if x >= 90)}"
          f" · 80–89 {sum(1 for x in sc if 80 <= x < 90)} · 60–79 {sum(1 for x in sc if 60 <= x < 80)} · <60 {sum(1 for x in sc if x < 60)}")
    print(f"   السنوات: {dict(sorted(collections.Counter(x['years'] for x in rows).items()))}")
    cb = collections.Counter(("100" if x["comp"] >= 100 else "90+" if x["comp"] >= 90 else "75+" if x["comp"] >= 75 else "<75")
                             for x in rows)
    print(f"   الاكتمال: {dict(cb)}")
    cons = [x["cons"] for x in rows if isinstance(x["cons"], (int, float))]
    print(f"   الثبات: وسيط {statistics.median(cons):.0f} · غائب {sum(1 for x in rows if x['cons'] is None)} · "
          f"≥50 {sum(1 for x in cons if x >= 50)} · <30 {sum(1 for x in cons if x < 30)}")
    print("\n═ المؤشّراتُ الغائبة بالنمط (عددُ الشركات التي يغيب عنها)")
    by = collections.defaultdict(collections.Counter)
    na = collections.Counter(x["arch"] for x in rows)
    for x in rows:
        for k in x["miss"]:
            by[x["arch"]][k] += 1
    for a, c in sorted(by.items(), key=lambda kv: -na[kv[0]]):
        print(f"   {a:<18} n={na[a]:>3} · " + " · ".join(f"{k} {n}" for k, n in c.most_common(8)))
    print("\n═ ما يحبس الدرجةَ دون 90 — أيُّ جزءٍ لو اكتمل وحده بلغها؟")
    lo = [x for x in rows if x["score"] < 90]
    yrs = lambda x: min(100, x["years"] / 5 * 100)                       # noqa: E731
    cons_c = lambda x: x["cons"] if isinstance(x["cons"], (int, float)) else 50.0   # noqa: E731
    by_y = sum(1 for x in lo if 40 + x["comp"] * .4 + cons_c(x) * .2 >= 90)
    by_c = sum(1 for x in lo if yrs(x) * .4 + 40 + cons_c(x) * .2 >= 90)
    by_yc = sum(1 for x in lo if 80 + cons_c(x) * .2 >= 90)
    print(f"   دون 90: {len(lo)} · تبلغها بخمس سنواتٍ وحدها {by_y} · باكتمالٍ تامّ وحده {by_c} · بالاثنين معاً {by_yc}"
          f" · ولا تبلغها حتى بهما (الثباتُ دون 50) {len(lo) - by_yc}")
    for x in sorted(lo, key=lambda x: x["score"])[:12]:
        print(f"     {x['s']} {uni[x['s']].get('name_ar')} · {x['score']} · سنوات {x['years']} · اكتمال {x['comp']} · "
              f"ثبات {x['cons']} · يغيب {x['miss'][:5]}")


asyncio.run(main())
