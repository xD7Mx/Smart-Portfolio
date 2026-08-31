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

MIN_PEERS = 3          # المادة ٣٩ — دونها لا وسيطَ يُعرض
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
        except Exception:                                         # noqa: BLE001
            continue
        for k in _MULTIPLES:
            if isinstance(px.get(k), (int, float)):
                by_sector[sector or ""][k].append(float(px[k]))
        for k in _FROM_FEATURES:
            v = inv._val(fe, k)
            if v is not None:
                by_sector[sector or ""][k].append(v)
        rows.append({"sym": sym, "sector": sector, "ps": ps,
                     "fe": fe, "inf": merged, "px": px})

    medians = {s: {k: _median(v) for k, v in ks.items()
                   if len(v) >= MIN_PEERS}
               for s, ks in by_sector.items()}
    told = sum(1 for s in medians for k in medians[s] if medians[s][k])
    print(f"  {len(rows)} شركةً قُرئت · {told} وسيطاً قطاعياً بُني "
          f"(بحدٍّ أدنى {MIN_PEERS} أقران)\n")

    # ══ المرّةُ الثانية: الدرجة ══
    grades: Counter = Counter()
    models: Counter = Counter()
    gates: Counter = Counter()
    conf: Counter = Counter()
    comp_live: Counter = Counter()
    comp_why: Counter = Counter()
    abstain: Counter = Counter()
    scores: list[float] = []
    hist: Counter = Counter()
    vmethods: Counter = Counter()
    miss_why: Counter = Counter()
    detail: list[dict] = []

    for r in rows:
        sector, fe, ps = r["sector"], r["fe"], r["ps"]
        model = model_of(sector)
        models[model or "بلا نموذج"] += 1
        arch = spec_score.resolve_archetype_ex(sector, {})[0]
        fe = dict(fe)
        fe.update(r["px"])
        med = medians.get(sector or "", {})
        # ══ القيمةُ العادلة من نموذج القطاع، ثم تدخل التقييم ══
        # التسلسلُ الذي أمرت به المواصفة: خامٌ → نموذجٌ → قيمةٌ عادلة →
        # سعرٌ مقابلها → درجة. فتُحسب أوّلاً ثم يُشتقّ منها الخصم.
        vr = mv.valuation_report(model, fe, ps, med,
                                 r["inf"].get("current_price"))
        if vr.get("upside_pct") is not None:
            fe["fv_discount"] = vr["upside_pct"]
        res = inv.compute(fe, sector, dist, arch, medians=med)
        ln = red_lines.check(fe, ps, arch)
        g = risk_gate.evaluate(fe, ps, ln)
        gates[g["status"]] += 1

        for name, c in res["components"].items():
            if c["score"] is not None:
                comp_live[name] += 1
            else:
                comp_why[f"{name}: {(c.get('reason') or '')[:26]}"] += 1

        if res["score"] is None:
            abstain[(res.get("abstain_reason") or "")[:44]] += 1
            continue
        scores.append(res["score"])
        hist[min(int(res["score"] // 10) * 10, 90)] += 1
        label = ("EXCLUDED" if g["status"] == risk_gate.EXCLUDED
                 else res["grade"])
        grades[label] += 1
        c, _why = inv.confidence_of(res, inv._val(fe, "years_available"))
        conf[c] += 1
        vmethods[vr.get("valuation_method") or "— لا طريقة"] += 1
        detail.append({
            "sym": r["sym"], "sector": sector, "score": res["score"],
            "grade": res["grade"], "conf": c, "gate": g["status"],
            "q": (res["components"]["quality"] or {}).get("score"),
            "d": (res["components"]["dividend"] or {}).get("score"),
            "g": (res["components"]["growth"] or {}).get("score"),
            "v": (res["components"]["valuation"] or {}).get("score"),
            "vm": vr.get("valuation_method_label") or "—",
            "fv": vr.get("fair_value"), "px": vr.get("current_price"),
            "up": vr.get("upside_pct"), "vconf": vr.get("valuation_confidence"),
        })
        for name, comp in res["components"].items():
            for m in (comp.get("missing") or []):
                if isinstance(m, dict):
                    miss_why[f"{m['key']} — {m['why']}"] += 1

    print("═" * 74)
    print("  النموذجُ الاقتصاديّ")
    print("═" * 74)
    for k, v in models.most_common():
        print(f"    {k:16} {v:>4}")

    print("\n" + "═" * 74)
    print("  التصنيفُ النهائيّ")
    print("═" * 74)
    tot = sum(grades.values()) or 1
    for k in ("A", "B", "C", "D", "E", "EXCLUDED"):
        v = grades.get(k, 0)
        print(f"    {k:10} {v:>4}   {v / tot:>5.0%}  {'█' * round(v / tot * 44)}")

    if scores:
        s = sorted(scores)
        print(f"\n  الدرجة — وسيط {s[len(s) // 2]:.1f} · "
              f"رُبيعٌ أدنى {s[len(s) // 4]:.1f} · "
              f"أعلى {s[len(s) * 3 // 4]:.1f} · "
              f"مدى {s[0]:.1f}–{s[-1]:.1f}")
        print("\n  توزيعُ الدرجة (كم شركةً في كل عَشْر):")
        for lo in range(0, 100, 10):
            v = hist.get(lo, 0)
            print(f"    {lo:>3}–{lo + 9:<3} {v:>4}  "
                  f"{'█' * round(v / max(len(s), 1) * 56)}")

    print("\n" + "═" * 74)
    print("  البوّابة · الثقة · المكوّنات")
    print("═" * 74)
    for k, v in gates.most_common():
        print(f"    بوّابة {k:12} {v:>4}")
    print()
    for k, v in conf.most_common():
        print(f"    ثقة {k:14} {v:>4}")
    print()
    for k in ("quality", "dividend", "growth", "valuation"):
        print(f"    قام {k:12} {comp_live.get(k, 0):>4} من {len(rows)}")
    if comp_why:
        print("\n  لماذا لم يقم مكوّن:")
        for k, v in comp_why.most_common(8):
            print(f"    {k:46} {v:>4}")
    if abstain:
        print("\n  امتناعٌ عن الدرجة:")
        for k, v in abstain.most_common(6):
            print(f"    {k:46} {v:>4}")

    print("\n" + "═" * 74)
    print("  طريقةُ التقييم المستعمَلة")
    print("═" * 74)
    for k, v in vmethods.most_common():
        print(f"    {k:34} {v:>4}")

    both = [d for d in detail
            if None not in (d["q"], d["d"], d["g"], d["v"])]
    print(f"\n  المكوّناتُ الأربعةُ معاً: {len(both)} شركة")

    print("\n" + "═" * 74)
    print("  أفضلُ عشرين بالدرجة")
    print("═" * 74)
    print(f"  {'رمز':>5} {'الشركة':22}{'درجة':>6}{'ص':>3}"
          f"{'جودة':>6}{'توزيع':>6}{'نموّ':>6}{'تقييم':>6}"
          f"{'قيمة':>8}{'سعر':>8}{'فرق':>7}  الثقة · الطريقة")
    print("─" * 74)
    for d in sorted(detail, key=lambda x: -(x["score"] or 0))[:20]:
        def _f(x, w=6):
            return f"{x:>{w}.1f}" if isinstance(x, (int, float)) else f"{'—':>{w}}"
        up = d["up"]
        up_s = f"{up:+.0f}%" if isinstance(up, (int, float)) else "—"
        nm = (name_of(d["sym"]) or "")[:22]
        print(f"  {d['sym']:>5} {nm:22}{_f(d['score'])}{d['grade']:>3}"
              f"{_f(d['q'])}{_f(d['d'])}{_f(d['g'])}{_f(d['v'])}"
              f"{_f(d['fv'], 8)}{_f(d['px'], 8)}{up_s:>7}"
              f"  {d['conf']} · {d['vm'][:26]}")
        print(f"        {d['sector']}")

    print("\n" + "═" * 74)
    print("  أكثرُ عشرِ سماتٍ إخفاقاً")
    print("═" * 74)
    for k, v in miss_why.most_common(10):
        print(f"    {v:>4}  {k}")

    print("\n" + "═" * 74)
    print("  اقرأ التوزيعَ قبل أن تُضبَط شريحة. ")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
