"""مسبارُ الدرجة الاستثمارية على السوق الحقيقيّ — قبل ضبط أيّ عتبة.

## لماذا يُقاس قبل أن يُضبَط

العيّنةُ الاصطناعية أخرجت أقوى شركةٍ عند ‎73 لا ‎90، فبدت شرائحُ
التصنيف (‏A عند ‎90) خاويةً بالبناء. وهذا **قد** يكون انكماشاً حقيقياً
في المتوسّط المرجَّح، وقد يكون أثرَ سعرٍ ثابتٍ في العيّنة.

وقد ضُبطت عتبةٌ في هذا المشروع مرّةً على توزيعٍ مفترَض، فقيست النتيجةُ
بعدها ‎43٪ حيث تُوُقّع ‎22٪ (‏D124). فلا تُمَسّ شريحةٌ قبل أن يُقرأ
التوزيعُ الحقيقيّ.

## ما يقيسه

مرّتان على السوق: الأولى تجمع مضاعفاتِ كلّ شركة وتحسب **وسيطَ كلّ
قطاع** (بحدٍّ أدنى ثلاثةِ أقرانٍ — المادة ٣٩)، والثانية تُخرج الدرجةَ
بمكوّناتها. ثم يُعرض توزيعُ الدرجات والتصنيفات وحالاتُ البوّابة
والثقة، وأيُّ المكوّنات لا يقوم ولماذا.

    docker exec sp_backend python /app/scripts/audit/probe_investment.py
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

MIN_PEERS = 3          # دونها لا وسيطَ يُعرض ولا يُخترع
# ── شركاتٌ عيّنها المالك للتحقّق من تطبيق النموذج القطاعيّ (المادة ١٨) ──
WATCH = ("4165", "8012", "4002", "2381", "7202",
         "3003", "4340", "7203", "1182")
_MULTIPLES = ("p_e", "p_b", "ev_ebitda", "p_ffo", "p_e_normalized",
              "dividend_yield")
# والعائدُ على حقوق الملكية وسيطُه لازمٌ لطريقة «الدفتريّ مسنداً بالعائد»
_FROM_FEATURES = ("roe",)


def _median(vals: list[float]) -> float | None:
    v = sorted(vals)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


async def main(argv: list[str]) -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.economic_models import model_of
    from app.services import peer_distribution as pd
    from app.services import investment_score as inv
    from app.services import spec_score, red_lines, risk_gate
    from app.services import model_valuation as mv
    from app.services import investment_readiness as rdy
    from app.services import canonical as cn
    from app.data.saudi_directory import name_of
    from app.services.four_scores import build_company_features
    from app.services.market_data import market_service

    print("═" * 74)
    print("  بناءُ توزيع الأقران من القوائم المخزّنة…")
    print("═" * 74)
    dist = await pd.build()
    print(f"  {dist['companies']} شركةً · {len(dist['archetypes'])} نمطاً\n")

    # ══ المرّةُ الأولى: المضاعفاتُ ووسيطُ كلّ قطاع ══
    rows: list[dict] = []
    by_sector: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list))
    for sym, meta in MARKET_UNIVERSE.items():
        if sym.startswith("9"):
            continue
        try:
            data = await market_service.get_financials(f"{sym}.SR",
                                                       allow_supplement=False)
        except Exception:                                         # noqa: BLE001
            continue
        ps = (data or {}).get("periods") or []
        if len(ps) < 2:
            continue
        sector = meta.get("sector")
        # ══ السعرُ يُطلب صراحةً ══ (كشفه المسبار — التقييمُ 0 من 268)
        # السعرُ لا يمرّ في خطّ السمات: `build_company_features` يعيد
        # (‏eps · book_value · roe) فقط، و`price_features` يبحث عن
        # `current_price` فلا يجده فيعيد فراغاً. فكان مكوّنُ التقييم
        # صفراً **بالتركيب لا بشحّ البيانات**.
        info: dict = {}
        try:
            ci = await market_service.get_company_info(f"{sym}.SR")
            if isinstance(ci, dict):
                info = dict(ci)
        except Exception:                                         # noqa: BLE001
            pass
        try:
            fe, inf, _ = build_company_features(ps, info=info, sector=sector)
            merged = dict(inf or {})
            merged.update(info)
            px = inv.price_features(merged, fe, ps)
            # ══ الطبقةُ المعياريّة هي المرجع ══ (المادة ٨)
            # القوائمُ تُوحَّد أسماؤها وتُدقَّق إشاراتُها مرّةً، ثم يُبنى
            # التوزيعُ من طبقته: نصيبُ السهم المعلَن أوّلاً، ثم المدفوعُ
            # على عدد الأسهم. وما تعذّر يبقى غيرَ متاحٍ ولا يصير صفراً.
            crows, csrc = cn.normalize(ps)
            dv = cn.dividends(crows, merged, merged.get("current_price"))
            for k in ("dividend_yield", "dividend_years",
                      "dividend_growth", "payout_ratio"):
                if dv.get(k) is not None:
                    fe[k] = dv[k]
                else:
                    fe.pop(k, None)
        except Exception:                                         # noqa: BLE001
            continue
        for k in _MULTIPLES:
            if isinstance(px.get(k), (int, float)):
                by_sector[sector or ""][k].append(float(px[k]))
        for k in _FROM_FEATURES:
            v = inv._val(fe, k)
            if v is not None:
                by_sector[sector or ""][k].append(v)
        rows.append({"sym": sym, "sector": sector, "ps": ps, "crows": crows,
                     "fe": fe, "inf": merged, "px": px, "dv": dv,
                     "csrc": csrc})

    medians = {s: {k: _median(v) for k, v in ks.items()
                   if len(v) >= MIN_PEERS}
               for s, ks in by_sector.items()}
    told = sum(1 for s in medians for k in medians[s] if medians[s][k])
    print(f"  {len(rows)} شركةً قُرئت · {told} وسيطاً قطاعياً بُني "
          f"(بحدٍّ أدنى {MIN_PEERS} أقران)\n")

    # ══ المرّةُ الثانية: الدرجةُ والجاهزية ══
    rows_out: list[dict] = []
    for r in rows:
        sector, ps = r["sector"], r["ps"]
        model = model_of(sector)
        arch = spec_score.resolve_archetype_ex(sector, {})[0]
        fe = dict(r["fe"]); fe.update(r["px"])
        med = medians.get(sector or "", {})
        vr = mv.valuation_report(model, fe, ps, med,
                                 r["inf"].get("current_price"))
        if vr.get("upside_pct") is not None:
            fe["fv_discount"] = vr["upside_pct"]
        res = inv.compute(fe, sector, dist, arch, medians=med,
                          rows=r['crows'])
        ln = red_lines.check(fe, ps, arch)
        gate = risk_gate.evaluate(fe, ps, ln)
        cf, cwhy = inv.confidence_of(res, inv._val(fe, "years_available"))
        ready = rdy.evaluate(res, gate["status"], cf,
                             vr.get("valuation_method"))
        th, risk = rdy.thesis(res, ready, vr.get("upside_pct"))
        c = res["components"]
        rows_out.append({
            "sym": r["sym"], "name": name_of(r["sym"]) or "",
            "sector": sector or "—", "model": model or "—",
            "score": res["score"], "grade": res["grade"],
            "raw": res.get("raw_score"),
            "rel": res.get("relative_score"),
            "cap": res.get("ceiling_note"),
            "breaches": [b["why"] for b in
                         (res.get("absolute") or {}).get("breaches", [])],
            "explain": inv.explain(res),
            "q": (c["quality"] or {}).get("score"),
            "d": (c["dividend"] or {}).get("score"),
            "g": (c["growth"] or {}).get("score"),
            "v": (c["valuation"] or {}).get("score"),
            "dc": res.get("data_completeness"), "conf": cf,
            "horizon": res.get("growth_horizon"),
            "vm": vr.get("valuation_method"),
            "vm_label": vr.get("valuation_method_label") or "—",
            "fv": vr.get("fair_value"), "px": vr.get("current_price"),
            "up": vr.get("upside_pct"),
            "gate": gate["status"], "readiness": ready["readiness"],
            "decision": ready["decision"], "why": ready["why"],
            "codes": ready.get("codes") or [],
            "thesis": th, "risk": risk,
            "missing": [m for comp in c.values()
                        for m in (comp.get("missing") or [])],
            "comps_live": len(res.get("components_used") or []),
        })

    n = len(rows_out)
    R = Counter(x["readiness"] for x in rows_out)
    print("═" * 78)
    print("  ١ · ٢ · ٣ · ٤ · ٥ — تعدادُ السوق والجاهزية")
    print("═" * 78)
    print(f"    الشركاتُ المقروءة            {n}")
    for k in ("INVESTMENT_READY", "WATCH", "NOT_READY"):
        v = R.get(k, 0)
        print(f"    {k:22} {v:>4}  {v / max(n,1):>5.0%}  "
              f"{'█' * round(v / max(n,1) * 40)}")

    dcs = [x["dc"] for x in rows_out if isinstance(x["dc"], (int, float))]
    print("\n" + "═" * 78)
    print("  ٦ — اكتمالُ البيانات")
    print("═" * 78)
    if dcs:
        ds = sorted(dcs)
        print(f"    الوسيط {ds[len(ds)//2]:.0%} · "
              f"الرُّبيع الأدنى {ds[len(ds)//4]:.0%} · "
              f"الأعلى {ds[len(ds)*3//4]:.0%}")
        for lo in (0, 20, 40, 60, 80):
            hi = lo + 20
            cnt = sum(1 for d in ds if lo <= d * 100 < hi or (hi == 100 and d >= 1))
            print(f"    {lo:>3}–{hi:<3}٪ {cnt:>4}  {'█' * round(cnt/len(ds)*40)}")
    print("\n    المحاورُ القائمة لكلّ شركة:")
    for k, v in sorted(Counter(x["comps_live"] for x in rows_out).items()):
        print(f"      {k} من 4 → {v} شركة")

    print("\n" + "═" * 78)
    print("  ٧ — طريقةُ التقييم لكلّ شركة")
    print("═" * 78)
    for k, v in Counter(x["vm"] or "— لا طريقة" for x in rows_out).most_common():
        print(f"    {k:16} {v:>4}")
    print("\n    ولكلّ نموذجٍ طرقُه:")
    bym: dict = defaultdict(Counter)
    for x in rows_out:
        bym[x["model"]][x["vm"] or "—"] += 1
    for m in sorted(bym):
        print(f"      {m:14} {dict(bym[m])}")

    print("\n" + "═" * 78)
    print("  ٨ — أسبابُ عدم الجاهزية")
    print("═" * 78)
    cc = Counter(c for x in rows_out for c in x["codes"])
    for k, v in cc.most_common():
        print(f"    {k:24} {v:>4}")
    print("\n    وبالنصّ:")
    for k, v in Counter(w for x in rows_out for w in x["why"]).most_common(10):
        print(f"      {v:>4}  {k}")

    print("\n" + "═" * 78)
    print("  ٩ · ١٠ · ١١ — لا بدائلَ كاذبة ولا جاهزيةٌ ببيانٍ ناقص")
    print("═" * 78)
    bad_ready = [x for x in rows_out
                 if x["readiness"] == "INVESTMENT_READY" and
                 (x["comps_live"] < 4 or (x["dc"] or 0) < 0.80
                  or x["conf"] == "منخفضة" or not x["vm"])]
    print(f"    شركاتٌ READY بمحورٍ ناقصٍ أو ثقةٍ منخفضة: {len(bad_ready)}"
          f"  {'✔' if not bad_ready else '✖'}")
    for x in bad_ready[:10]:
        print(f"      ✖ {x['sym']} {x['name'][:20]} محاور {x['comps_live']}/4 "
              f"اكتمال {(x['dc'] or 0):.0%} ثقة {x['conf']} طريقة {x['vm']}")
    ghost = [x for x in rows_out if x["v"] is not None and not x["vm"]]
    print(f"    درجةُ تقييمٍ بلا طريقةٍ معلَنة: {len(ghost)}"
          f"  {'✔' if not ghost else '✖'}")
    hz = Counter(x["horizon"] for x in rows_out)
    print(f"    أفقُ النموّ: {dict(hz)}")

    print("\n" + "═" * 78)
    print("  ١٢ · ١٣ — كلُّ نموذجٍ وكلُّ قطاع")
    print("═" * 78)
    bys: dict = defaultdict(list)
    for x in rows_out:
        bys[x["sector"]].append(x)
    print(f"  {'القطاع':28}{'النموذج':12}{'عدد':>4}{'جاهز':>6}"
          f"{'مراقبة':>7}{'غير جاهز':>9}{'تغطية':>8}{'الثقة الغالبة':>14}")
    print("─" * 78)
    _CR = {"مرتفعة": 2, "متوسطة": 1, "منخفضة": 0}
    for sec in sorted(bys, key=lambda k: -len(bys[k])):
        g = bys[sec]
        dd = [x["dc"] for x in g if isinstance(x["dc"], (int, float))]
        cmode = Counter(x["conf"] for x in g).most_common(1)[0][0]
        print(f"  {sec[:28]:28}{g[0]['model']:12}{len(g):>4}"
              f"{sum(1 for x in g if x['readiness'] == 'INVESTMENT_READY'):>6}"
              f"{sum(1 for x in g if x['readiness'] == 'WATCH'):>7}"
              f"{sum(1 for x in g if x['readiness'] == 'NOT_READY'):>9}"
              f"{(f'{sum(dd)/len(dd):.0%}' if dd else '—'):>8}"
              f"{cmode:>14}")

    print("\n" + "═" * 78)
    print("  ١٤ — الشركاتُ التي كانت مُضلِّلة، بالاسم")
    print("═" * 78)
    seen = {x["sym"]: x for x in rows_out}
    for sym in WATCH:
        x = seen.get(sym)
        if x is None:
            print(f"  {sym}  {(name_of(sym) or '')[:26]:26} — لم تُقرأ")
            continue
        _f = lambda z, w=5: (f"{z:>{w}.1f}" if isinstance(z, (int, float))
                             else f"{'—':>{w}}")
        print(f"\n  {x['sym']} · {x['name'][:30]}")
        print(f"      القطاع {x['sector']}  ·  النموذج {x['model']}")
        print(f"      الدرجة {_f(x['score'])} · {x['grade']}   "
              f"جودة {_f(x['q'])} · توزيع {_f(x['d'])} · "
              f"نموّ {_f(x['g'])} · تقييم {_f(x['v'])}")
        print(f"      اكتمال {(x['dc'] or 0):.0%} · ثقة {x['conf']} · "
              f"أفق {x['horizon']} · طريقة {x['vm'] or '—'}")
        _up = (f"{x['up']:+.0f}%" if isinstance(x["up"], (int, float)) else "—")
        print(f"      قيمة {_f(x['fv'],7)} · سعر {_f(x['px'],7)} · "
              f"فرق {_up}")
        print(f"      الجاهزية {x['readiness']} — {x['decision']}")
        print(f"      الأطروحة: {x['thesis']}")
        print(f"      الخطر: {x['risk']}")
        if x["why"]:
            print(f"      النقص: {' · '.join(x['why'])}")

    print("\n" + "═" * 78)
    print("  المرشّحون — READY مرتّبين بالدرجة")
    print("═" * 78)
    cand = sorted((x for x in rows_out
                   if x["readiness"] == "INVESTMENT_READY"),
                  key=lambda z: -(z["score"] or 0))
    if not cand:
        print("    لا مرشّحَ اجتاز البوّابة.")
    print(f"  {'رمز':>5} {'الشركة':22}{'درجة':>6}{'خام':>6}{'جودة':>6}"
          f"{'توزيع':>6}{'نموّ':>6}{'تقييم':>6}{'تغطية':>7}"
          f"{'الثقة':>8}  الطريقة · الحالة")
    print("─" * 78)
    for x in cand[:20]:
        _f = lambda z, w=6: (f"{z:>{w}.1f}" if isinstance(z, (int, float))
                             else f"{'—':>{w}}")
        print(f"  {x['sym']:>5} {x['name'][:22]:22}{_f(x['score'])}"
              f"{_f(x['raw'])}{_f(x['q'])}{_f(x['d'])}{_f(x['g'])}"
              f"{_f(x['v'])}{(x['dc'] or 0)*100:>6.0f}٪{x['conf']:>8}"
              f"  {x['vm'] or '—'} · {x['readiness']}")
        print(f"        {x['sector']}")

    print("\n" + "═" * 78)
    print("  أكثرُ السماتِ إخفاقاً")
    print("═" * 78)
    mw = Counter(f"{m['key']} — {m['why']}" for x in rows_out
                 for m in x["missing"] if isinstance(m, dict))
    for k, v in mw.most_common(15):
        print(f"    {v:>4}  {k}")

    # ══ تقريرُ التحقّق الإحصائيّ ══ (المادتان ١١ و١٧)
    print("\n" + "═" * 78)
    print("  تقريرُ التحقّق — أصالحةٌ المعايرة إحصائياً؟")
    print("═" * 78)
    sc = sorted(x["score"] for x in rows_out if x["score"] is not None)
    if sc:
        import statistics as st
        q1, q2, q3 = (sc[len(sc)//4], sc[len(sc)//2], sc[len(sc)*3//4])
        print(f"    عدد الدرجات {len(sc)} · المدى {sc[0]:.1f}–{sc[-1]:.1f}")
        print(f"    الوسيط {q2:.1f} · الرُّبيعان {q1:.1f} و{q3:.1f} · "
              f"المدى الرُّبيعيّ {q3-q1:.1f}")
        print(f"    الانحراف {st.pstdev(sc):.1f}")
        print("\n    التوزيع في العشرات:")
        for lo in range(0, 100, 10):
            c = sum(1 for v in sc if lo <= v < lo + 10)
            print(f"      {lo:>3}–{lo+9:<3} {c:>4}  {'█' * round(c/len(sc)*46)}")
        # ── إنذاراتُ التحقّق ──
        warn = []
        if q3 - q1 < 15:
            warn.append(f"تركّزٌ شديد — المدى الرُّبيعيّ {q3-q1:.1f} دون ‎15")
        hi = sum(1 for v in sc if v >= 75) / len(sc)
        if hi > 0.35:
            warn.append(f"‏{hi:.0%} من السوق فوق ‎75 — تضخّمٌ عامّ")
        lo_share = sum(1 for v in sc if v < 40) / len(sc)
        if lo_share > 0.40:
            warn.append(f"‏{lo_share:.0%} دون ‎40 — قسوةٌ عامّة")
        print("\n    إنذاراتُ التوزيع: "
              + ("لا شيء ✔" if not warn else ""))
        for w in warn:
            print(f"      ✖ {w}")

        # ── أيُعاقَب قطاعٌ بخصائصه؟ ──
        print("\n    وسيطُ الدرجة لكلّ نموذج (تحيّزٌ منهجيّ إن تباعدت):")
        bymod: dict = defaultdict(list)
        for x in rows_out:
            if x["score"] is not None:
                bymod[x["model"]].append(x["score"])
        meds = {}
        for m in sorted(bymod):
            v = sorted(bymod[m])
            meds[m] = v[len(v)//2]
            print(f"      {m:14} n={len(v):>3}  وسيط {meds[m]:>5.1f}")
        if len(meds) > 1:
            spread = max(meds.values()) - min(meds.values())
            print(f"      الفارقُ بين أعلى نموذجٍ وأدناه {spread:.1f}"
                  f"  {'✔' if spread <= 15 else '✖ تحيّزٌ محتمل'}")

    capped = [x for x in rows_out if x["cap"]]
    print(f"\n    قُصَّت بالطبقة المطلقة: {len(capped)} شركة")
    for x in capped[:8]:
        print(f"      {x['sym']} {x['name'][:18]:18} {x['cap'][:60]}")

    print("\n" + "═" * 78)
    print("  لماذا هذه الدرجة — عيّنةُ تفسيرٍ من أعلى وأدنى")
    print("═" * 78)
    ranked = sorted((x for x in rows_out if x["score"] is not None),
                    key=lambda z: -z["score"])
    for x in (ranked[:3] + ranked[-3:]) if len(ranked) > 6 else ranked:
        e = x["explain"]
        print(f"\n  {x['sym']} {x['name'][:24]} — {x['score']}"
              f" (نسبيّ {x['rel']} · خام {x['raw']} · تغطية {(x['dc'] or 0):.0%})")
        for c in e["raised_by"]:
            print(f"      ▲ {c['label']}: {c['value']} — {c['note']}"
                  f"  (أثر {c['impact']:+.1f})")
        for c in e["lowered_by"]:
            print(f"      ▼ {c['label']}: {c['value']} — {c['note']}"
                  f"  (أثر {c['impact']:+.1f})")
        if x["breaches"]:
            print(f"      ⛔ {'، '.join(x['breaches'])}")

    print("\n" + "═" * 78)
    print("  انتهى التقرير — لم تُعدَّل قاعدةٌ لتحسين رقم.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
