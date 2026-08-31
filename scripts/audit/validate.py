"""تقريرُ التحقّق — ثلاثةَ عشرَ إثباتاً على السوق الحقيقيّ.

## قبل/بعد من تشغيلةٍ واحدة

العطبُ (‏D134) كان أن `peer_distribution` يجمع مفاتيحَه من المواصفة
القديمة، فتسعةُ مؤشّراتٍ تُحسب ولا تجد مسطرة. ولإثبات أثر الإصلاح على
**الشركات نفسها** لا على الكود، يُبنى التوزيعُ هنا مرّتين:

    القديم = المفاتيحُ التي كان يجمعها قبل الإصلاح (يُعاد إنتاجُ العطب)
    الجديد = بعد الإصلاح

ثم يُدار الخطُّ كاملاً على كلٍّ منهما بالبيانات ذاتها، فيكون الفرقُ
أثرَ الإصلاح وحده — لا أثرَ يومٍ مختلفٍ ولا عيّنةٍ مختلفة.

## ولا يُغيَّر شيء

هذا السكربتُ **يقرأ ولا يكتب**: لا وزنَ يُمَسّ ولا عتبةَ ولا بوّابة.
وتجربةُ حساسية `PB_ROE` تُجرى بقيمٍ مؤقّتةٍ تُعاد بعدها إلى أصلها،
وهي كشفُ هشاشةٍ لا معايرةٌ جديدة.

    docker exec sp_backend python /app/scripts/audit/validate.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter, defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MIN_PEERS = 3
PRICE_BASED = {"p_e", "p_b", "ev_ebitda", "p_ffo", "p_e_normalized",
               "dividend_yield", "fv_discount"}
GROWTH_KEYS = ("revenue_cagr_5y", "eps_cagr_5y", "book_value_cagr_5y",
               "roic_trend", "roe_trend")


def _med(v):
    s = sorted(v)
    if not s:
        return None
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _q(v, f):
    s = sorted(v)
    return s[int(f * (len(s) - 1))] if s else None


def _pearson(xs, ys):
    """ارتباطٌ خطّيّ — على الأزواج المكتملة وحدها."""
    pairs = [(a, b) for a, b in zip(xs, ys)
             if isinstance(a, (int, float)) and isinstance(b, (int, float))]
    n = len(pairs)
    if n < 8:
        return None, n
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    sx = sum((p[0] - mx) ** 2 for p in pairs) ** 0.5
    sy = sum((p[1] - my) ** 2 for p in pairs) ** 0.5
    if sx == 0 or sy == 0:
        return None, n
    cov = sum((p[0] - mx) * (p[1] - my) for p in pairs)
    return round(cov / (sx * sy), 3), n


def _legacy_keys() -> set[str]:
    """المفاتيحُ التي كان `build` يجمعها قبل إصلاح D134."""
    from app.data.archetype_spec import SCORECARDS
    from app.services import governance_pillar
    out: set[str] = set()
    for card in SCORECARDS.values():
        if not card.get("abstain"):
            for k, *_r in card["metrics"]:
                out.add(k)
    return out | set(governance_pillar.METRIC_KEYS)


def _shrink(dist: dict, keep: set[str]) -> dict:
    """نسخةٌ من التوزيع بمفاتيحَ محدودة — لإعادة إنتاج الحال السابقة."""
    out = {"companies": dist.get("companies"), "archetypes": {}}
    if "composite" in dist:
        out["composite"] = dist["composite"]
    for arch, keys in (dist.get("archetypes") or {}).items():
        out["archetypes"][arch] = {k: v for k, v in keys.items() if k in keep}
    return out


async def main(argv: list[str]) -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.economic_models import (COMPONENTS, CONCEPT_OF, model_of)
    from app.services import peer_distribution as pd
    from app.services import investment_score as inv
    from app.services import spec_score, red_lines, risk_gate
    from app.services import model_valuation as mv
    from app.services import investment_readiness as rdy
    from app.services import canonical as cn
    from app.services import absolute_quality as aq
    from app.data.saudi_directory import name_of
    from app.services.four_scores import build_company_features
    from app.services.market_data import market_service

    print("═" * 80)
    print("  تقريرُ التحقّق — بعد إصلاح المسطرة الغائبة (D134)")
    print("═" * 80)

    dist_new = await pd.build()
    dist_old = _shrink(dist_new, _legacy_keys())
    ranked = {k for m in COMPONENTS.values() for c in m.values()
              for k, _l, _w, d in c if k not in PRICE_BASED and d != "discount"}

    # ══ ١ — تغطيةُ الأقران ══
    print("\n" + "═" * 80)
    print("  ١ — تغطيةُ الأقران: أَلِكلّ مؤشّرٍ يُرتَّب مسطرةٌ صالحة؟")
    print("═" * 80)
    print(f"  {'المؤشّر':24}{'أنماطٌ لها توزيع':>18}{'أصغرُ عيّنة':>12}"
          f"{'أكبرُ عيّنة':>12}{'قبل':>7}")
    print("─" * 80)
    archs = sorted(dist_new.get("archetypes") or {})
    for k in sorted(ranked):
        ns = [d["archetypes"][a][k]["n"] for a in archs
              for d in (dist_new,) if k in d["archetypes"].get(a, {})]
        before = sum(1 for a in archs if k in dist_old["archetypes"].get(a, {}))
        print(f"  {k:24}{len(ns):>18}{(min(ns) if ns else 0):>12}"
              f"{(max(ns) if ns else 0):>12}{before:>7}")
    gone = [k for k in sorted(ranked)
            if not any(k in dist_new["archetypes"].get(a, {}) for a in archs)]
    print(f"\n  مؤشّراتٌ تُرتَّب {len(ranked)} · بلا توزيعٍ في أيّ نمط "
          f"{len(gone)}  {'✔' if not gone else '✖ ' + str(gone)}")
    print(f"  حدُّ العيّنة المطبَّق في `peer_distribution`: "
          f"MIN_COHORT = {pd.MIN_COHORT}")
    thin = [(a, k, v["n"]) for a in archs
            for k, v in dist_new["archetypes"][a].items()
            if v["n"] < pd.MIN_COHORT]
    print(f"  توزيعاتٌ نجت بعيّنةٍ دون الحدّ: {len(thin)}"
          f"  {'✔' if not thin else '✖'}")

    # ══ حصادُ السوق مرّةً واحدة ══
    rows: list[dict] = []
    unread: Counter = Counter()
    for sym, meta in MARKET_UNIVERSE.items():
        if sym.startswith("9"):
            unread["NOMU_EXCLUDED"] += 1
            continue
        try:
            data = await market_service.get_financials(f"{sym}.SR",
                                                       allow_supplement=False)
        except Exception:                                         # noqa: BLE001
            unread["API_ERROR"] += 1
            continue
        ps = (data or {}).get("periods") or []
        if len(ps) < 2:
            unread["TOO_FEW_PERIODS" if ps else "NO_PERIODS"] += 1
            continue
        info: dict = {}
        try:
            ci = await market_service.get_company_info(f"{sym}.SR")
            if isinstance(ci, dict):
                info = dict(ci)
        except Exception:                                         # noqa: BLE001
            pass
        try:
            fe, inf, _ = build_company_features(ps, info=info,
                                                sector=meta.get("sector"))
            merged = dict(inf or {}); merged.update(info)
            fe.update(inv.price_features(merged, fe, ps))
            crows, _src = cn.normalize(ps)
            dv = cn.dividends(crows, merged, merged.get("current_price"))
            for k in ("dividend_yield", "dividend_years",
                      "dividend_growth", "payout_ratio"):
                if dv.get(k) is not None:
                    fe[k] = dv[k]
                else:
                    fe.pop(k, None)
        except Exception:                                         # noqa: BLE001
            unread["FEATURE_BUILD_ERROR"] += 1
            continue
        rows.append({"sym": sym, "sector": meta.get("sector"), "ps": ps,
                     "crows": crows, "fe": fe, "inf": merged})

    # وسائطُ القطاع
    bys: dict = defaultdict(lambda: defaultdict(list))
    for r in rows:
        for k in PRICE_BASED - {"fv_discount"}:
            v = inv._val(r["fe"], k)
            if v is not None:
                bys[r["sector"] or ""][k].append(v)
        v = inv._val(r["fe"], "roe")
        if v is not None:
            bys[r["sector"] or ""]["roe"].append(v)
    medians = {s: {k: _med(v) for k, v in ks.items() if len(v) >= MIN_PEERS}
               for s, ks in bys.items()}

    def run(dist: dict) -> list[dict]:
        """الخطُّ كاملاً على توزيعٍ بعينه."""
        out = []
        for r in rows:
            sector, ps = r["sector"], r["ps"]
            model = model_of(sector)
            arch = spec_score.resolve_archetype_ex(sector, {})[0]
            fe = dict(r["fe"])
            med = medians.get(sector or "", {})
            vr = mv.valuation_report(model, fe, ps, med,
                                     r["inf"].get("current_price"))
            if vr.get("upside_pct") is not None:
                fe["fv_discount"] = vr["upside_pct"]
            res = inv.compute(fe, sector, dist, arch, medians=med,
                              rows=r["crows"])
            ln = red_lines.check(fe, ps, arch)
            gate = risk_gate.evaluate(fe, ps, ln)
            cf, _w = inv.confidence_of(res, inv._val(fe, "years_available"))
            ready = rdy.evaluate(res, gate["status"], cf,
                                 vr.get("valuation_method"))
            c = res["components"]
            out.append({
                "sym": r["sym"], "name": name_of(r["sym"]) or "",
                "sector": sector or "—", "model": model or "—", "arch": arch,
                "score": res["score"], "raw": res.get("raw_score"),
                "rel": res.get("relative_score"),
                "dc": res.get("data_completeness"), "conf": cf,
                "horizon": res.get("growth_horizon"),
                "q": (c["quality"] or {}).get("score"),
                "d": (c["dividend"] or {}).get("score"),
                "g": (c["growth"] or {}).get("score"),
                "v": (c["valuation"] or {}).get("score"),
                "g_reads": [x["key"] for x in (c["growth"] or {}).get("reads", [])],
                "vm": vr.get("valuation_method"),
                "vm_missing": vr.get("valuation_inputs_missing") or [],
                "readiness": ready["readiness"], "codes": ready.get("codes") or [],
                "gate": gate["status"], "abs": res.get("absolute") or {},
                "cap": res.get("ceiling_note"),
                "explain": inv.explain(res), "fe": r["fe"],
            })
        return out

    before = {x["sym"]: x for x in run(dist_old)}
    after = run(dist_new)
    print(f"\n  قُرئت {len(rows)} شركة · لم تُقرأ {sum(unread.values())} "
          f"({dict(unread)})")

    # ══ ٢ — النموّ ══
    print("\n" + "═" * 80)
    print("  ٢ — النموّ: أثرُ الإصلاح على الشركات لا على الكود")
    print("═" * 80)
    print(f"  {'المؤشّر':24}{'محسوب':>9}{'له مئين (قبل)':>16}{'له مئين (بعد)':>16}")
    print("─" * 80)
    for k in GROWTH_KEYS:
        calc = sum(1 for r in rows if inv._val(r["fe"], k) is not None)
        b = sum(1 for x in before.values() if k in x["g_reads"])
        a = sum(1 for x in after if k in x["g_reads"])
        print(f"  {k:24}{calc:>9}{b:>16}{a:>16}")
    for label, coll in (("قبل", list(before.values())), ("بعد", after)):
        hz = sum(1 for x in coll if x["horizon"] in ("5Y", "3Y", "LIMITED"))
        sc = sum(1 for x in coll if x["g"] is not None)
        print(f"\n  {label}: أفقُ نموّ {hz} · درجةُ نموّ {sc} "
              f"· الفجوة {hz - sc}")

    # ══ ٣ — الاكتمال ══
    print("\n" + "═" * 80)
    print("  ٣ — اكتمالُ البيانات")
    print("═" * 80)
    for label, coll in (("قبل", list(before.values())), ("بعد", after)):
        dcs = [x["dc"] for x in coll if isinstance(x["dc"], (int, float))]
        if not dcs:
            continue
        print(f"\n  {label}: وسيط {_med(dcs):.0%} · Q1 {_q(dcs,0.25):.0%} "
              f"· Q3 {_q(dcs,0.75):.0%}")
        for lo in (0, 20, 40, 60, 80):
            c = sum(1 for d in dcs if lo <= d * 100 < lo + 20
                    or (lo == 80 and d >= 1.0))
            print(f"      {lo:>3}–{lo+20:<3}٪ {c:>4}  {'█' * round(c/len(dcs)*40)}")

    # ══ ٤ — الجاهزية ══
    print("\n" + "═" * 80)
    print("  ٤ — الجاهزية وأسبابُها")
    print("═" * 80)
    for label, coll in (("قبل", list(before.values())), ("بعد", after)):
        R = Counter(x["readiness"] for x in coll)
        print(f"  {label}: READY {R.get('INVESTMENT_READY',0)} · "
              f"WATCH {R.get('WATCH',0)} · NOT_READY {R.get('NOT_READY',0)}")
    print("\n  أسبابُ المنع (بعد):")
    for k, v in Counter(c for x in after for c in x["codes"]).most_common():
        print(f"    {k:24} {v:>4}")

    # ══ ٥ — PB_ROE ══
    print("\n" + "═" * 80)
    print("  ٥ — PB_ROE: عتبةُ صلاحيةِ نموذجٍ لا حدٌّ ماليٌّ للقطاع")
    print("═" * 80)
    print(f"  model applicability threshold: median ROE ≥ "
          f"{mv.MIN_MEDIAN_ROE:.0f}٪")
    fin = [x for x in after if x["model"] == "FINANCIAL"]
    dropped = [x for x in fin
               if any("مقامٌ لا يصلح" in str(m) for m in x["vm_missing"])
               or (x["vm"] != "PB_ROE")]
    print(f"    شركاتُ النموذج المالي: {len(fin)}")
    print(f"    استعملت PB_ROE: {sum(1 for x in fin if x['vm']=='PB_ROE')}")
    print(f"    انتقلت إلى PE_MEDIAN: "
          f"{sum(1 for x in fin if x['vm']=='PE_MEDIAN')}")
    print(f"    بقيت بلا تقييم: {sum(1 for x in fin if not x['vm'])}")
    print("\n    وسيطُ العائد لكلّ قطاعٍ ماليّ:")
    for s in sorted({x["sector"] for x in fin}):
        m = (medians.get(s) or {}).get("roe")
        print(f"      {s:28} {('—' if m is None else f'{m:.2f}٪'):>10}"
              f"  {'✔ يصلح' if (m or 0) >= mv.MIN_MEDIAN_ROE else '✖ دون العتبة'}")

    # ══ ٦ — حساسيةُ العتبة (كشفٌ لا معايرة) ══
    print("\n" + "═" * 80)
    print("  ٦ — حساسيةُ PB_ROE — تجربةٌ للكشف، لا تُعتمد معايرةً")
    print("═" * 80)
    _orig = mv.MIN_MEDIAN_ROE
    try:
        for t in (3.0, 5.0, 7.0):
            mv.MIN_MEDIAN_ROE = t
            fvs, used = [], 0
            for r in rows:
                if model_of(r["sector"]) != "FINANCIAL":
                    continue
                vr = mv.valuation_report(
                    "FINANCIAL", r["fe"], r["ps"],
                    medians.get(r["sector"] or "", {}),
                    r["inf"].get("current_price"))
                if vr.get("valuation_method") == "PB_ROE":
                    used += 1
                    if vr.get("upside_pct") is not None:
                        fvs.append(vr["upside_pct"])
            ex = sum(1 for f in fvs if abs(f) > 200)
            print(f"    عتبة {t:>4.0f}٪ → PB_ROE صالحة لـ{used:>3} شركة · "
                  f"وسيطُ الفرق "
                  f"{('—' if not fvs else f'{_med(fvs):+.0f}٪'):>8} · "
                  f"متطرّفة (>±200٪) {ex}")
    finally:
        mv.MIN_MEDIAN_ROE = _orig
    print(f"    (أُعيدت العتبةُ إلى {mv.MIN_MEDIAN_ROE:.0f}٪)")

    # ══ ٧ — البوّابات المطلقة ══
    print("\n" + "═" * 80)
    print("  ٧ — البوّاباتُ المطلقة — POLICY / RISK GATES لا عتباتٍ مشتقّة")
    print("═" * 80)
    print("    هذه سقوفٌ سياسيّةٌ اختِيرت ترتيباً للجسامة، ولم تُشتقّ من")
    print("    توزيعٍ إحصائيّ. وشروطُ إشعالها تعريفيّةٌ لا اجتهادية.")
    fired = Counter()
    for x in after:
        for b in (x["abs"].get("breaches") or []):
            fired[b["key"]] += 1
    for k, (cap, why) in aq.CEILINGS.items():
        print(f"    {k:24} سقف {cap:>5.0f}  اشتعل على {fired.get(k,0):>4} شركة"
              f"   {why}")
    capped = [x for x in after if x["cap"]]
    print(f"\n    قُصَّت فعلاً: {len(capped)} شركة")
    print(f"  {'رمز':>6} {'الشركة':22}{'خام':>7}{'نسبيّ':>8}{'بعد القصّ':>10}")
    for x in sorted(capped, key=lambda z: (z["rel"] or 0) - (z["score"] or 0),
                    reverse=True)[:15]:
        print(f"  {x['sym']:>6} {x['name'][:22]:22}"
              f"{(x['raw'] or 0):>7.1f}{(x['rel'] or 0):>8.1f}"
              f"{(x['score'] or 0):>10.1f}")

    # ══ ٨ — الارتباط داخل البُعد ══
    print("\n" + "═" * 80)
    print("  ٨ — ارتباطُ المؤشّرات داخل البُعد الواحد")
    print("═" * 80)
    cols: dict = defaultdict(list)
    for r in rows:
        for k in ("roe", "roic", "operating_margin", "earnings_stability",
                  "cash_conversion_ratio", "p_e", "p_b", "fv_discount"):
            cols[k].append(inv._val(r["fe"], k))
    pairs = [("roe", "roic"), ("roe", "operating_margin"),
             ("roic", "operating_margin"),
             ("earnings_stability", "cash_conversion_ratio"),
             ("roe", "cash_conversion_ratio"),
             ("p_e", "p_b"), ("p_e", "fv_discount"), ("p_b", "fv_discount")]
    for a, b in pairs:
        r_, n = _pearson(cols[a], cols[b])
        flag = ("—" if r_ is None else
                "✖ تداخلٌ مرتفع" if abs(r_) >= 0.75 else
                "⚠ متوسّط" if abs(r_) >= 0.55 else "✔")
        print(f"    {a:22} × {b:22} r={('—' if r_ is None else f'{r_:+.2f}'):>6}"
              f"  n={n:>4}  {flag}")
    print("\n    (تشخيصٌ فقط — لم يُغيَّر وزنٌ بناءً على هذا)")

    # ══ ٩ — توزيعُ الدرجة ══
    print("\n" + "═" * 80)
    print("  ٩ — توزيعُ الدرجة")
    print("═" * 80)
    import statistics as st
    for label, coll in (("قبل", list(before.values())), ("بعد", after)):
        sc = sorted(x["score"] for x in coll if x["score"] is not None)
        if not sc:
            continue
        q1, q3 = _q(sc, 0.25), _q(sc, 0.75)
        print(f"\n  {label}: n={len(sc)} · المدى {sc[0]:.1f}–{sc[-1]:.1f} · "
              f"وسيط {_med(sc):.1f} · Q1 {q1:.1f} · Q3 {q3:.1f} · "
              f"IQR {q3-q1:.1f} · σ {st.pstdev(sc):.1f}")
        for lo in range(0, 100, 10):
            c = sum(1 for v in sc if lo <= v < lo + 10)
            print(f"      {lo:>3}–{lo+9:<3} {c:>4}  {'█' * round(c/len(sc)*40)}")

    # ══ ١٠ — تحيّزُ النموذج والقطاع ══
    print("\n" + "═" * 80)
    print("  ١٠ — وسيطُ الدرجة لكلّ نموذجٍ وقطاع")
    print("═" * 80)
    for key, title in (("model", "النموذج"), ("arch", "النمط"),
                       ("sector", "القطاع")):
        g: dict = defaultdict(list)
        for x in after:
            if x["score"] is not None:
                g[x[key]].append(x["score"])
        meds = {k: _med(v) for k, v in g.items() if len(v) >= 3}
        if not meds:
            continue
        print(f"\n  {title}:")
        for k in sorted(meds, key=lambda z: -meds[z]):
            print(f"    {str(k)[:34]:34} n={len(g[k]):>3}  وسيط {meds[k]:>5.1f}")
        print(f"    أعلى − أدنى = {max(meds.values()) - min(meds.values()):.1f}")

    # ══ ١١ — عيّنةٌ تفسيرية ══
    print("\n" + "═" * 80)
    print("  ١١ — عيّنةٌ تفسيرية")
    print("═" * 80)
    ok = sorted((x for x in after if x["score"] is not None),
                key=lambda z: -z["score"])
    mid = len(ok) // 2
    picks = ok[:5] + ok[mid - 2:mid + 3] + ok[-5:]
    seen_arch = set()
    for x in ok:
        if x["arch"] not in seen_arch:
            seen_arch.add(x["arch"])
            if x not in picks:
                picks.append(x)
    for x in picks:
        _f = lambda z: (f"{z:.1f}" if isinstance(z, (int, float)) else "—")
        print(f"\n  {x['sym']} {x['name'][:26]} · {x['sector'][:24]} · {x['model']}")
        print(f"      درجة {_f(x['score'])} (نسبيّ {_f(x['rel'])} · "
              f"خام {_f(x['raw'])}) · سقفٌ مطلق {x['abs'].get('ceiling')}")
        print(f"      جودة {_f(x['q'])} · توزيع {_f(x['d'])} · "
              f"نموّ {_f(x['g'])} · تقييم {_f(x['v'])}")
        print(f"      اكتمال {(x['dc'] or 0):.0%} · ثقة {x['conf']} · "
              f"بوّابة {x['gate']} · {x['readiness']} · طريقة {x['vm'] or '—'}")
        for c in x["explain"]["raised_by"][:2]:
            print(f"      ▲ {c['label']}: {c['value']} ({c['note']}) "
                  f"أثر {c['impact']:+.1f}")
        for c in x["explain"]["lowered_by"][:2]:
            print(f"      ▼ {c['label']}: {c['value']} ({c['note']}) "
                  f"أثر {c['impact']:+.1f}")

    # ══ ١٢ — أكبرُ التغيّرات ══
    print("\n" + "═" * 80)
    print("  ١٢ — أكبرُ عشرين تغيّراً بعد إصلاح المسطرة")
    print("═" * 80)
    deltas = []
    for x in after:
        b = before.get(x["sym"])
        if not b or b["score"] is None or x["score"] is None:
            continue
        deltas.append((x["score"] - b["score"], b, x))
    deltas.sort(key=lambda t: -abs(t[0]))
    print(f"  {'رمز':>6} {'الشركة':22}{'قبل':>7}{'بعد':>7}{'الفرق':>8}"
          f"{'اكتمال ق':>10}{'اكتمال ب':>10}")
    for dv, b, x in deltas[:20]:
        print(f"  {x['sym']:>6} {x['name'][:22]:22}{b['score']:>7.1f}"
              f"{x['score']:>7.1f}{dv:>+8.1f}"
              f"{(b['dc'] or 0)*100:>9.0f}٪{(x['dc'] or 0)*100:>9.0f}٪")
    big = sum(1 for d, _b, _x in deltas if abs(d) >= 10)
    print(f"\n  تغيّرَت بعشر نقاطٍ فأكثر: {big} من {len(deltas)}")

    print("\n" + "═" * 80)
    print("  انتهى — لم يُغيَّر وزنٌ ولا عتبةٌ ولا بوّابة في هذا التشغيل.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
