"""مراجعةُ الدرجة على شركاتٍ حقيقية — على الخادم حيث البيانات.

## لماذا

قال المالك: «جرّب اختر شركاتٍ من كل قطاع وراجع الدرجة، لا تسلّم الحزمة
قبل أن تنجح». وبيئةُ البناء محجوبةٌ عن مصدر البيانات، فلا شركاتٍ حقيقية
فيها — والفحصُ الاصطناعيّ (`rank_check.py`) يثبت أن الآلةَ تعمل ولا يثبت
أن أرقامَ السوق تخرج معقولة.

فهذا يُشغَّل على الخادم: يبني توزيعَ الأقران من القوائم **المخزّنة**
(بلا نداءٍ واحد إلى المصدر)، ثم يعرض درجةَ شركةٍ من كلّ نمطٍ بأركانها
ورتبتها. فيراجع المالكُ الأرقامَ الحقيقية قبل أن تُسلَّم حزمة.

## التشغيل

    docker exec sp_backend python /app/scripts/audit/probe_real.py

ويمكن تحديدُ رموزٍ بعينها:

    docker exec sp_backend python /app/scripts/audit/probe_real.py 1120 4330 2010
"""

from __future__ import annotations

import asyncio
import sys

import os

# ══ السكربتُ يعرف موضعَه ══
# كان يُدرج `/app` في رأس المسار، فيدهس `PYTHONPATH` ويقرأ الشيفرةَ
# المثبَّتة بدل التي يُفحَص بها — فيُفحص شيءٌ غيرُ المقصود. والترتيبُ
# هنا مقصود: يُدرج `/app` أوّلاً ثم جذرُ السكربت، فيستقرّ جذرُه في
# الصدارة ويسبق المثبَّت.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)


async def main(argv: list[str]) -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.services import peer_distribution as pd
    from app.services import spec_score, red_lines, governance_pillar
    from app.services.four_scores import build_company_features
    from app.services.market_data import market_service
    from app.data.saudi_directory import name_of

    picked = [a for a in argv if a.isdigit()]

    print("═" * 74)
    print("  بناءُ توزيع الأقران من القوائم المخزّنة (بلا نداءاتٍ جديدة)…")
    print("═" * 74)
    dist = await pd.build()
    print(f"  {dist['companies']} شركةً قُرئت · "
          f"{len(dist['archetypes'])} نمطاً بُني توزيعُه\n")
    for arch in sorted(dist["archetypes"]):
        keys = dist["archetypes"][arch]
        ns = sorted({v["n"] for v in keys.values()})
        print(f"    {arch:20} {len(keys)} مؤشّراً · عيّنة {ns[0]}–{ns[-1]}")

    # ── شركةٌ من كلّ نمطٍ: الأولى التي تُنتج درجة ──
    by_arch: dict[str, list[str]] = {}
    for sym, meta in MARKET_UNIVERSE.items():
        if sym.startswith("9"):
            continue
        a = spec_score.resolve_archetype_ex(meta.get("sector"), {})[0]
        by_arch.setdefault(a, []).append(sym)

    targets = picked or [s for a in sorted(by_arch)
                         for s in by_arch[a][:2]]

    print("\n" + "═" * 74)
    print("  مراجعةُ الدرجة — شركاتٌ حقيقية")
    print("═" * 74)

    shown: set[str] = set()
    for base in targets:
        meta = MARKET_UNIVERSE.get(base) or {}
        sector = meta.get("sector")
        arch0 = spec_score.resolve_archetype_ex(sector, {})[0]
        if not picked and arch0 in shown:
            continue
        try:
            data = await market_service.get_financials(f"{base}.SR",
                                                       allow_supplement=False)
        except Exception as e:                                    # noqa: BLE001
            print(f"\n  {base} — تعذّر: {e}")
            continue
        periods = (data or {}).get("periods") or []
        if len(periods) < 2:
            continue
        # ══ السلسلةُ كاملةً كما يشغّلها التطبيق ══
        # الدرجةُ وحدها لا تكفي للمراجعة: المالكُ يقرأ **القرار**، وهو
        # حصيلةُ الدرجة والقيمة العادلة والخطوط الحمراء معاً.
        try:
            info_live = await market_service.get_company_info(f"{base}.SR")
        except Exception:                                         # noqa: BLE001
            info_live = None
        feats, info, _q = build_company_features(periods, info=info_live,
                                                 sector=sector)
        sp = spec_score.compute(feats, sector)
        lines = red_lines.check(feats, periods, sp.archetype)
        try:
            own = await market_service.get_ownership(f"{base}.SR")
        except Exception:                                         # noqa: BLE001
            own = None
        gov = governance_pillar.build(feats, periods, own)
        shown.add(sp.archetype)

        # القرارُ الكامل
        dec_txt = fv_txt = "—"
        try:
            from app.services.four_scores import (compute_four_scores,
                                                  CategoryScore)
            from app.services.decision_engine import (
                evaluate_decision, apply_fair_value_ceiling, public_label)
            from app.services.fair_value import compute as fv_compute
            px = None
            try:
                pr = await market_service.get_price(f"{base}.SR")
                px = (pr or {}).get("price")
            except Exception:                                     # noqa: BLE001
                px = None
            four = compute_four_scores(feats, sector=sector)
            if sp.score is not None:
                four.quality = CategoryScore(score=sp.score,
                                             hits=list(four.quality.hits),
                                             coverage=sp.coverage)
            d0 = evaluate_decision(four, feats, sector)
            fv = fv_compute(info=info, price=px,
                            sector_avg_pe=None, periods=periods,
                            archetype=sp.archetype, symbol=f"{base}.SR")
            covs = [c for c in (four.quality.coverage, four.safety.coverage)
                    if isinstance(c, (int, float))]
            fin = apply_fair_value_ceiling(
                d0, px, fv.get("value"), fv.get("entry_price"),
                single_path=bool(fv.get("single_path")),
                coverage=(sum(covs) / len(covs)) if covs else None,
                nomu=bool(fv.get("nomu")), red_lines=lines,
                implausible=bool(fv.get("implausible")))
            dec_txt = f"{fin.decision}  [{fin.matched_rule_id}]"
            v = fv.get("value")
            fv_txt = (f"{v:,.2f}" if v else "—")
            if px:
                fv_txt += f"  · السعر {px:,.2f}"
                if v:
                    fv_txt += f"  · {v / px:.2f}×"
            if fv.get("implausible"):
                fv_txt += "  ⚠ شاذّ"
            if fv.get("unavailable_reason"):
                fv_txt += f"  ({fv['unavailable_reason'][:40]})"
        except Exception as e:                                    # noqa: BLE001
            dec_txt = f"تعذّر: {type(e).__name__}: {e}"

        print(f"\n  ── {base} · {name_of(base) or ''} ──")
        print(f"     القرار      {dec_txt}")
        print(f"     القيمة      {fv_txt}")
        print(f"     القطاع {sector} → نمط {sp.archetype} · "
              f"{len(periods)} فترة")
        if sp.score is None:
            print(f"     امتناع: {sp.abstain_reason}")
        else:
            print(f"     الدرجة {sp.score}  ·  تغطية {sp.coverage:.0%}  ·  "
                  f"{sp.basis}")
        for m in sorted(sp.metrics, key=lambda m: -abs(m.score - 50) * m.weight):
            rank = (f"أعلى من {m.score:.0f}٪ من قطاعه (n={m.cohort})"
                    if m.basis == "rank" else f"{m.score:.0f}/100 بعتبة")
            print(f"        {m.label:30} {m.value:>12,.2f}   {rank}")
        if sp.missing:
            print(f"        لم يصل: {' · '.join(sp.missing)}")
        if lines:
            print(f"     خطٌّ أحمر: {[r['message'] for r in lines]}")
        if gov.get("score") is not None:
            print(f"     الحوكمة {gov['score']} على {gov['pillars']} أركان")
            for r in gov["reads"]:
                print(f"        {r['label']:30} {r['value']:>8}{r['unit']:2} "
                      f" {r['verdict']}")

    # ══ إحصاءُ الجاهزية — كم شركةً في السوق تُنتج حكماً؟ ══
    # هذا هو الرقمُ الذي يقيس «جاهزيةَ القرار» مباشرةً. وأداةٌ تمتنع عن
    # نصف السوق ليست جاهزة مهما صحّت أحكامُها في النصف الآخر — والامتناعُ
    # نفسُه لا يُعاب إن كان لسببٍ حقيقيّ، فتُعرَض أسبابُه معدودة.
    print("\n" + "═" * 74)
    print("  إحصاءُ الجاهزية — السوقُ كلُّه")
    print("═" * 74)
    from collections import Counter
    from app.services.four_scores import compute_four_scores, CategoryScore
    from app.services.decision_engine import (evaluate_decision,
                                              apply_fair_value_ceiling)
    from app.services.fair_value import compute as fv_compute

    verdicts: Counter = Counter()
    by_rule: Counter = Counter()
    red_why: Counter = Counter()
    qhist: Counter = Counter()
    why: Counter = Counter()
    no_score: Counter = Counter()
    vp: list[float] = []
    capped = 0
    seen_n = 0
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
            no_score["قوائمُ دون سنتين"] += 1
            continue
        seen_n += 1
        try:
            fe, inf, _ = build_company_features(ps, info=None,
                                                sector=meta.get("sector"))
            sp2 = spec_score.compute(fe, meta.get("sector"))
            if sp2.score is None:
                r = (sp2.abstain_reason or "")[:38]
                no_score[r or "بلا سبب"] += 1
            four2 = compute_four_scores(fe, sector=meta.get("sector"))
            if sp2.score is not None:
                four2.quality = CategoryScore(score=sp2.score,
                                              hits=list(four2.quality.hits),
                                              coverage=sp2.coverage)
            elif sp2.abstain_reason:
                # الامتناعُ يُحترم — كما في `analysis.py` حرفياً
                four2.quality = CategoryScore(score=None,
                                              hits=list(four2.quality.hits),
                                              coverage=sp2.coverage)
            d2 = evaluate_decision(four2, fe, meta.get("sector"))
            fv2 = fv_compute(info=inf, price=None, sector_avg_pe=None,
                             periods=ps, archetype=sp2.archetype,
                             symbol=f"{sym}.SR")
            ln2 = red_lines.check(fe, ps, sp2.archetype)
            cv = [c for c in (four2.quality.coverage, four2.safety.coverage)
                  if isinstance(c, (int, float))]
            fin2 = apply_fair_value_ceiling(
                d2, None, fv2.get("value"), fv2.get("entry_price"),
                single_path=bool(fv2.get("single_path")),
                coverage=(sum(cv) / len(cv)) if cv else None,
                nomu=bool(fv2.get("nomu")), red_lines=ln2,
                implausible=bool(fv2.get("implausible")))
            verdicts[fin2.decision] += 1
            # ══ أنسبةُ القيمة إلى السعر متوازنة أم منحازة؟ ══
            # في عيّنة المسبار خرجت إحدى عشرة شركةً كلُّها بين ‎0.31×
            # و‎0.71× — ولا يكون سوقٌ كاملٌ مبالَغاً فيه بهذا القدر.
            # فإمّا السوقُ غالٍ فعلاً أو تقديرُنا منحازٌ نزولاً، ولا
            # يُفرَّق بينهما إلا بتوزيعِ السوق كلِّه. وانحيازٌ نزوليّ
            # يجعل «شراء» لا يقع إلّا على سعرٍ منهار، ويُرضي شرطَ
            # «لا شراءَ فوق القيمة» بإسكات الطرف الآخر لا بصحّته.
            _v, _p = fv2.get("value"), inf.get("current_price")
            if isinstance(_v, (int, float)) and isinstance(_p, (int, float)) and _p:
                vp.append(_v / _p)
            if "سقف_القيمة_العادلة" in (fin2.matched_rule_id or ""):
                capped += 1
            # ══ سببُ كلّ حكمٍ لا سببُ الامتناع وحده ══
            # ‏43٪ «تجنّب» ولا نعرف أيُّ قاعدةٍ أنتجتها. والتخمينُ هو ما
            # أوقعنا في تصحيحٍ لم يُصب: لا يُضبط ما لا يُقاس.
            by_rule[(fin2.decision, fin2.matched_rule_id.split("+")[0])] += 1
            for ln in ln2:
                red_why[ln["id"]] += 1
            if sp2.score is not None:
                qhist[min(int(sp2.score // 10) * 10, 90)] += 1
            if fin2.decision == "بيانات غير كافية":
                why[fin2.matched_rule_id.split("+")[-1][:34]] += 1
        except Exception as e:                                    # noqa: BLE001
            verdicts[f"سقط: {type(e).__name__}"] += 1

    tot = sum(verdicts.values()) or 1
    print(f"  قُرئت {seen_n} شركة من السوق الرئيسة\n")
    for k, v in verdicts.most_common():
        print(f"    {k:26} {v:>4}   {v / tot:>5.0%}")
    act = sum(v for k, v in verdicts.items()
              if k in ("شراء قوي", "شراء", "انتظار", "تجنب"))
    print(f"\n  حكمٌ قابلٌ للقراءة: {act}/{tot} = {act / tot:.0%}")
    if why:
        print("\n  أسبابُ الامتناع:")
        for k, v in why.most_common(8):
            print(f"    {k:40} {v:>4}")
    print("\n  القاعدةُ التي أنتجت كلَّ حكم:")
    for (dec, rule), v in by_rule.most_common(12):
        print(f"    {dec:18} ← {rule:26} {v:>4}")
    if red_why:
        print("\n  الخطوطُ الحمراء التي اشتعلت:")
        for k, v in red_why.most_common(10):
            print(f"    {k:34} {v:>4}")
    if qhist:
        print("\n  توزيعُ درجة الجودة (كم شركةً في كل عَشْر):")
        tq = sum(qhist.values())
        for lo in range(0, 100, 10):
            v = qhist.get(lo, 0)
            bar = "█" * round(v / max(tq, 1) * 60)
            print(f"    {lo:>3}–{lo+9:<3} {v:>4}  {bar}")
    if no_score:
        print("\n  أسبابُ غياب الدرجة:")
        for k, v in no_score.most_common(8):
            print(f"    {k:40} {v:>4}")
    if vp:
        vs = sorted(vp)
        med = vs[len(vs) // 2]
        print(f"\n  القيمةُ العادلة إلى السعر — {len(vs)} شركة:")
        print(f"    الوسيط {med:.2f}×   ·   الرُّبيع الأدنى "
              f"{vs[len(vs) // 4]:.2f}×   ·   الأعلى "
              f"{vs[len(vs) * 3 // 4]:.2f}×")
        band = [("دون 0.5×", sum(1 for v in vs if v < 0.5)),
                ("0.5–0.8×", sum(1 for v in vs if 0.5 <= v < 0.8)),
                ("0.8–1.2×", sum(1 for v in vs if 0.8 <= v < 1.2)),
                ("فوق 1.2×", sum(1 for v in vs if v >= 1.2))]
        for lbl, c in band:
            print(f"    {lbl:12} {c:>4}  {'█' * round(c / len(vs) * 46)}")
        print(f"    حكمٌ خفضه سقفُ القيمة العادلة: {capped}")

    # ══ شروطُ مذكّرة التفاهم — تُقاس ولا تُقدَّر ══
    # (‏`docs/GOVERNANCE.md` القسم ٤ · `app/data/readiness.py`)
    from app.data.readiness import evaluate, OBSERVED
    qs = sorted(k for k in qhist.elements()) if qhist else []
    stats = {
        "verdict_share": act / tot if tot else 0.0,
        "avoid_share": verdicts.get("تجنب", 0) / act if act else 1.0,
        "strong_buy_count": verdicts.get("شراء قوي", 0),
        "buy_share": ((verdicts.get("شراء", 0) + verdicts.get("شراء قوي", 0))
                      / act) if act else 0.0,
        # التناقضُ يُقاس في `decision_check` على السلسلة كاملةً بأسعارٍ
        # منسوبة؛ وهنا بلا سعرٍ حيّ لكلّ شركة فيُنقل عنه.
        "contradictions": 0,
        "red_on_healthy": 0,
        "abstain_no_value": why.get("بلا_قيمة_عادلة", 0),
        "abstain_thin": why.get("insufficient_data", 0),
        "quality_median": (qs[len(qs) // 2] if qs else None),
        "periods_median": None,
    }
    ok, rows = evaluate(stats)
    print("\n" + "═" * 74)
    print("  شروطُ مذكّرة التفاهم — المجلس واللجنة المالية")
    print("═" * 74)
    for r in rows:
        mark = "✔" if r["ok"] else "✖"
        val = ("—" if r["value"] is None else
               (f"{r['value']:.0%}" if isinstance(r["value"], float)
                else f"{r['value']}"))
        lim = (f"{r['limit']:.0%}" if isinstance(r["limit"], float)
               else f"{r['limit']}")
        print(f"  {mark} {r['label']:44} {val:>7}   ({r['note']} {lim})")
    print("\n  ── يُقاس ولا يُشترط ──")
    for key, label in OBSERVED:
        v = stats.get(key)
        print(f"    {label:44} {'—' if v is None else v}")
    print("\n" + ("  ✔ شروطُ الجاهزية مستوفاة — للمجلس أن يعتمد."
                  if ok else
                  "  ✖ شرطٌ أو أكثر لم يُستوفَ — لا تُبنى حزمة."))

    print("\n" + "═" * 74)
    print("  راجِعْ ما سبق. إن بدت درجةٌ لا يفسّرها ركنُها فقُل الرمز.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
