#!/usr/bin/env python3
"""المرشَّح 2.3 — قياسٌ قبل أيّ تعديل (قارئٌ فقط): هل يُسقط حذفُ النماذج المنحازة بالنمط التشتّتَ ويُصغّر الخطأ معاً؟

القاعدةُ مسجَّلةٌ قبل القياس (docs/ENGINES_V2.md · المرشَّح ٦):
  · القائمةُ المغلقة للحذف بالنمط: لا شيء · EPV · نماذجُ قيمة المنشأة الثلاثة · كلاهما · خصمُ التوزيعات المستقرّ · الثلاثة معاً.
    ولا يُحذف ما يُنزل النماذجَ تحت ثلاثة (يبقى الأصل).
  · الاختيار: تحقّقٌ متقاطعٌ بإسقاط ورقةٍ واحدة داخل النمط (يُختار الحذفُ على البقية ويُقاس على الساقطة).
  · الاعتماد للنمط: عيّنةٌ ≥ 5 لها هدفُ محلّلين، وخطأُ التحقّق المتقاطع أصغرُ من خطأ اليوم بنقطةٍ مئويةٍ كاملةٍ على الأقلّ.
  · الثقة: «مرتفعة» = تشتّتٌ ≤ 14٪ وثلاثةُ نماذج فأكثر، رابحةٌ غيرُ متأخّرة، قطاعٌ معايَر — ويُشترط أن يبقى خطأُ
    المرتفعة ≤ 12٪ (معنى الكلمة اليوم · D625)، وإلّا لا تُعتمد.
"""
import asyncio, collections, statistics, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market, is_nomu
from app.services.market_screener import get_cached_screener
from app.services.analysis import V1_UNCALIBRATED

uni = {s: m for s, m in main_market(MARKET_UNIVERSE).items() if not is_nomu(s)}
EV = {"peer_ev_ebit", "peer_ev_ebitda", "peer_ev_sales"}
OPTS = {"لا شيء": set(), "EPV": {"epv"}, "قيمةُ المنشأة": EV, "EPV+المنشأة": EV | {"epv"},
        "التوزيعُ المستقرّ": {"ddm_stable"}, "الثلاثة": EV | {"epv", "ddm_stable"}}
med = statistics.median


def sim(x, drop):
    kept = [v for k, v in x["mods"] if k not in drop]
    if len(kept) < 3:
        kept = [v for _, v in x["mods"]]
    mv = statistics.fmean(kept)
    v = x["px"] * (mv / x["px"]) ** x["k"]
    m = med(kept)
    disp = med([abs(z / m - 1) for z in kept]) if m else 9
    return v, disp, len(kept)


def high(x, disp, n):
    return (n >= 3 and disp <= 0.14 and not x["loser"] and not x["stale"] and not x["reit"]
            and x["sec"] not in V1_UNCALIBRATED)


async def main():
    from app.services.fair_value_models import for_symbol, _tuning, MARKET_BLEND_K
    from app.services.statement_merge import archetype_of
    rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
    sem = asyncio.Semaphore(4)

    async def one(s):
        async with sem:
            try:
                return s, await asyncio.wait_for(for_symbol(s), timeout=40)
            except Exception:                                      # noqa: BLE001
                return s, None
    got = dict(await asyncio.gather(*(one(s) for s in sorted(uni))))
    xs = []
    for s, f in got.items():
        if not f or not f.get("value") or not f.get("price"):
            continue
        mods = [(m.get("key"), m["value"]) for m in (f.get("models") or [])
                if isinstance(m.get("value"), (int, float)) and m["value"] > 0]
        if not mods:
            continue
        notes = " ".join(str(n) for n in (f.get("notes") or []))
        at = (rows.get(s) or {}).get("analyst_target")
        xs.append({"s": s, "px": f["price"], "mods": mods, "k": _tuning(s).get("k", MARKET_BLEND_K),
                   "at": at if isinstance(at, (int, float)) and at > 0 else None,
                   "arch": archetype_of(s) or "—", "sec": uni[s].get("sector") or "—",
                   "loser": ("خاسر" in notes or "خسارة" in notes), "stale": "أقدمُ من تسعة أشهر" in notes,
                   "reit": f.get("weights_kind") == "reit_nav"})
    print(f"═ أوراقٌ بنماذج {len(xs)} · لها هدفُ محلّلين {sum(1 for x in xs if x['at'])}")
    err = lambda x, d: abs(sim(x, d)[0] / x["at"] - 1)          # noqa: E731
    choice = {}
    print("\n═ التحقّقُ المتقاطع بالنمط (خطأُ اليوم ← خطأُ الاختيار على أوراقٍ لم يُختر بها)")
    for a in sorted({x["arch"] for x in xs}):
        ref = [x for x in xs if x["arch"] == a and x["at"]]
        base = med([err(x, set()) for x in ref]) if ref else None
        if len(ref) < 5:
            print(f"   {a:<18} n={len(ref):>3} — عيّنةٌ دون خمس، يبقى كما هو")
            continue
        loo = []
        for i, h in enumerate(ref):
            rest = ref[:i] + ref[i + 1:]
            best = min(OPTS, key=lambda o: med([err(x, OPTS[o]) for x in rest]))
            loo.append(err(h, OPTS[best]))
        full = min(OPTS, key=lambda o: med([err(x, OPTS[o]) for x in ref]))
        cv = med(loo)
        ok = cv <= base - 0.01
        choice[a] = full if ok else "لا شيء"
        print(f"   {a:<18} n={len(ref):>3} · اليوم {base:.1%} ← متقاطعٌ {cv:.1%} · الاختيار «{full}» · "
              f"{'يُعتمد' if ok else 'لا يُعتمد'}")
    print("\n═ الأثرُ على الثقة — «مرتفعة» بالقاعدة المسجّلة (ثلاثةُ نماذج فأكثر · تشتّت ≤ 14٪)")
    for lab, pick in (("اليوم (أربعةُ نماذج)", None), ("قاعدةُ الثلاثة وحدها", {}), ("الثلاثة + الحذفُ المعتمد", choice)):
        hi, he, allerr = 0, [], []
        for x in xs:
            d = OPTS[pick.get(x["arch"], "لا شيء")] if pick else set()
            v, disp, n = sim(x, d)
            h = high(x, disp, n) and (n >= 4 if pick is None else True)
            hi += h
            if x["at"]:
                allerr.append(abs(v / x["at"] - 1))
                if h:
                    he.append(abs(v / x["at"] - 1))
        print(f"   {lab:<26} مرتفعة {hi}/{len(xs)} = {hi / len(xs):.0%} · خطؤها {med(he) if he else float('nan'):.1%} "
              f"(n={len(he)}) · خطأُ الكلّ {med(allerr):.1%}")
    print("\n═ القطاعاتُ الأربعةُ غيرُ المعايَرة بعد الحذف المعتمد — خطؤها مقابل خطأ السعر نفسِه")
    for sec in sorted(V1_UNCALIBRATED):
        ref = [x for x in xs if x["sec"] == sec and x["at"]]
        if not ref:
            continue
        e0 = med([err(x, set()) for x in ref])
        e1 = med([err(x, OPTS[choice.get(x["arch"], "لا شيء")]) for x in ref])
        ep = med([abs(x["px"] / x["at"] - 1) for x in ref])
        print(f"   {sec:<28} n={len(ref):>3} · اليوم {e0:.1%} · بعد الحذف {e1:.1%} · السعرُ نفسُه {ep:.1%}")
    print("\n═ ما يبقى دون «مرتفعة» بعد الحزمة — بأسبابه")
    why = collections.Counter()
    for x in xs:
        v, disp, n = sim(x, OPTS[choice.get(x["arch"], "لا شيء")])
        if high(x, disp, n):
            continue
        why["خاسرة" if x["loser"] else "متأخّرة" if x["stale"] else "ريت" if x["reit"] else
            "قطاعٌ غيرُ معايَر" if x["sec"] in V1_UNCALIBRATED else "أقلُّ من ثلاثة" if n < 3 else
            "تشتّت 14–30٪" if disp <= 0.30 else "تشتّت > 30٪"] += 1
    print(f"   {why.most_common()}")


asyncio.run(main())
