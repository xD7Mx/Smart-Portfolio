"""معايرةُ المحرّكين — إحصاءٌ مقطعيّ على السوق كلِّه، لا حكايةُ شركة.

## لماذا وُجد هذا الملفّ

مسحُ السوق (`market_sweep.py`) يسأل: **أيناقض المحرّكُ نفسه؟** وقد صار
جوابُه صفراً. وهذا سؤالٌ عن الاتّساق لا عن الصحّة: محرّكٌ متّسقٌ تماماً قد
يكون منحرفاً تماماً — يقول عن كل شركةٍ إنها رخيصة، بلا تناقضٍ واحد.

وهذا الملفّ يسأل السؤال الآخر: **أمعايَرٌ هو؟** ويجيب بإحصاءاتٍ مقطعية
على ٣٩٧ شركة في تشغيلةٍ واحدة — لا تنتظر نتائجَ سنة. ولكلّ إحصاءٍ نطاقٌ
مُعلَنٌ سلفاً: ما يقع خارجه انحرافٌ يُسمّى ويُقاس، لا انطباعٌ يُتناقش.

وأصلُ هذه الإحصاءات مراجعةٌ خارجية للمنهجية طلبها المالك. وأشدُّها
دلالةً **ميلُ انحدار مضاعف الدفترية على العائد**: النظرية تقول إن الميل
يقارب ‎1÷(r−g)، فمقارنةُ ميلنا بميل السوق على العيّنة نفسها تختصر انحيازَنا
كلَّه في رقمٍ واحد — أعلى يعني أننا نشتري العائد بأغلى ممّا يدفعه السوق،
وأدنى يعني أننا نرفض كلَّ شركةٍ ممتازة.

## التشغيل

    docker exec sp_backend python /app/scripts/audit/calibration.py
    docker exec sp_backend python /app/scripts/audit/calibration.py --limit 120

وينبّه حين تكون الحصّةُ المتبقّية دون الاحتياطيّ — فلا يُعمي التطبيق.
"""

from __future__ import annotations

import asyncio
import statistics as st
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, ".")

RESERVE = 120
_FLOOR_PCT = 9.0

# ── النطاقاتُ المعلَنة سلفاً ─────────────────────────────────────────────
BANDS = {
    "وسيط القيمة ÷ السعر": (0.95, 1.10),
    "المرجَّح بالقيمة السوقية": (0.90, 1.10),
    "نسبة المسارات المُسقَطة بحدّ العقل": (0.0, 0.10),
    "نسبة الامتناع للتشتّت": (0.05, 0.12),
    "نسبة الشركات عند أرضية معدّل الخصم": (0.0, 0.25),
    "نسبة القيمة فوق أعلى سعر ٥٢ أسبوعاً": (0.0, 0.20),
    "عدد «شراء قوي»": (8, 16),
    "ارتباط الدرجة بالتغطية": (-0.20, 0.20),
    "انحراف الدرجة المعياريّ": (12, 16),
    "نسبة الدرجات فوق ٧٥": (0.08, 0.12),
    "نسبة الدرجات تحت ٤٥": (0.18, 0.25),
}


def _corr(xs, ys):
    if len(xs) < 3:
        return None
    try:
        return round(st.correlation(xs, ys), 3)
    except Exception:                                             # noqa: BLE001
        return None


def _slope(xs, ys):
    """ميلُ انحدارٍ بسيط — به يُقارن تسعيرُنا للعائد بتسعير السوق."""
    if len(xs) < 5:
        return None
    mx, my = st.fmean(xs), st.fmean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den, 2)


def _verdict(name, value):
    lo, hi = BANDS.get(name, (None, None))
    if value is None or lo is None:
        return "—"
    return "معاير" if lo <= value <= hi else ("مرتفع" if value > hi else "منخفض")


async def run(limit: int) -> int:
    from app.services.analysis import analyze_company
    from app.data.market_universe import MARKET_UNIVERSE
    from app.api.v1.endpoints.holdings import yahoo_symbol
    from app.core.database import AsyncSessionLocal
    from app.services.usage_tracker import usage as _usage

    pairs = [(yahoo_symbol(s), m.get("name_ar") or s)
             for s, m in list(MARKET_UNIVERSE.items())[:limit]]

    from app.services.fair_value import RISK_FREE, MIN_EQUITY_PREMIUM
    global _FLOOR_PCT
    _FLOOR_PCT = (RISK_FREE + MIN_EQUITY_PREMIUM) * 100

    # ── تفكيكُ الفجوة: أيُّ مسارٍ يسحب الوسيط ──
    # الوسيطُ رقمٌ واحد لا يقول أين الخلل. ووسيطُ كل مسارٍ منسوباً إلى
    # السعر يقوله مباشرةً: من كان ‎0.55 هو من يسحب، ومن كان ‎1.00 معاير.
    per_path: dict[str, list] = {}
    vp, mcap_v, mcap_p = [], 0.0, 0.0
    dropped_paths = total_paths = 0
    abstained = at_floor = above_52w = 0
    strong_buys = 0
    scores, coverages = [], []
    spec_scores, spec_cov = [], []
    pb_val, pb_mkt, roes = [], [], []
    by_sector: dict[str, list] = {}
    checked = 0

    async with AsyncSessionLocal() as db:
        for sym, name in pairs:
            u = _usage("yahoo")
            lim = u.get("daily_limit") or 0
            if lim and lim - u.get("daily_used", 0) <= RESERVE:
                print(f"⏸ وقف عند {checked}: الحصّةُ بلغت الاحتياطيّ.")
                break
            try:
                a = await analyze_company(sym, name, db=db, allow_supplement=False)
            except Exception:                                     # noqa: BLE001
                continue
            if not a:
                continue
            checked += 1
            fv = a.get("fair_value_detail") or {}
            price, value = a.get("price"), a.get("fair_value")
            f = a.get("fundamentals") or {}
            sec = a.get("sector") or "غير مصنّف"

            if fv.get("unavailable_reason") and "متضاربة" in fv["unavailable_reason"]:
                abstained += 1
            total_paths += len(fv.get("methods") or []) + (fv.get("dropped_paths") or 0)
            dropped_paths += fv.get("dropped_paths") or 0
            # الأرضيةُ تُقرأ من المحرّك نفسه: كان الفحصُ يقارن بنصّ «10.0%»
            # فيعدّ **من لا بيتا لهم** (‏β=1 ⇒ r=10.0٪) أرضيةً — وهو قياسٌ
            # لشيءٍ آخر. والفرقُ ليس تفصيلاً: ‎39٪ ظهرت «مرتفعة» وهي ليست
            # عند الأرضية أصلاً.
            _rt = (fv.get("assumptions") or {}).get("معدّل الخصم")
            try:
                if _rt and float(str(_rt).rstrip("%")) <= _FLOOR_PCT + 0.01:
                    at_floor += 1
            except ValueError:
                pass

            if price:
                for m in (fv.get("methods") or []):
                    if isinstance(m.get("value"), (int, float)):
                        per_path.setdefault(m["name"], []).append(m["value"] / price)
            if price and value:
                ratio = value / price
                vp.append(ratio)
                by_sector.setdefault(sec, []).append(ratio)
                w = f.get("market_cap") or 0
                if w:
                    mcap_v += value / price * w
                    mcap_p += w
                hi52 = f.get("week52_high")
                if hi52 and value > hi52:
                    above_52w += 1
                bv, roe = f.get("book_value"), f.get("roe")
                if bv and bv > 0 and roe is not None:
                    pb_val.append(value / bv)
                    pb_mkt.append(price / bv)
                    roes.append(roe)

            sc = (a.get("financial") or {}).get("score")
            if sc is not None:
                scores.append(sc)
                cv = (a.get("scores") or {}).get("quality", {})
                if isinstance(cv, dict) and cv.get("coverage") is not None:
                    coverages.append((sc, cv["coverage"]))
            if ((a.get("decision") or {}).get("label")) == "شراء قوي":
                strong_buys += 1
            # ── درجةُ المواصفة تُقاس بجانب القديمة ──
            sp = (a.get("financial") or {}).get("spec") or a.get("spec")
            if isinstance(sp, dict) and sp.get("score") is not None:
                spec_scores.append(sp["score"])
                spec_cov.append(sp.get("coverage") or 0)

    print("═" * 62)
    print(f"معايرةُ المحرّكين — {checked} شركةً")
    print("═" * 62)

    rows = []
    if vp:
        rows.append(("وسيط القيمة ÷ السعر", round(st.median(vp), 3)))
        if len(vp) >= 4:
            q = st.quantiles(vp, n=4)
            print(f"  المدى الربيعيّ: {q[0]:.2f} – {q[2]:.2f}")
    if mcap_p:
        rows.append(("المرجَّح بالقيمة السوقية", round(mcap_v / mcap_p, 3)))
    if total_paths:
        rows.append(("نسبة المسارات المُسقَطة بحدّ العقل",
                     round(dropped_paths / total_paths, 3)))
    if checked:
        rows.append(("نسبة الامتناع للتشتّت", round(abstained / checked, 3)))
        rows.append(("نسبة الشركات عند أرضية معدّل الخصم", round(at_floor / checked, 3)))
    if vp:
        rows.append(("نسبة القيمة فوق أعلى سعر ٥٢ أسبوعاً", round(above_52w / len(vp), 3)))
    rows.append(("عدد «شراء قوي»", strong_buys))
    if scores:
        rows.append(("انحراف الدرجة المعياريّ",
                     round(st.pstdev(scores), 1) if len(scores) > 1 else 0))
        rows.append(("نسبة الدرجات فوق ٧٥",
                     round(sum(1 for x in scores if x > 75) / len(scores), 3)))
        rows.append(("نسبة الدرجات تحت ٤٥",
                     round(sum(1 for x in scores if x < 45) / len(scores), 3)))
    if len(coverages) >= 3:
        rows.append(("ارتباط الدرجة بالتغطية",
                     _corr([c for _, c in coverages], [s for s, _ in coverages])))

    for name, val in rows:
        print(f"  {name:38} {str(val):>8}   {_verdict(name, val)}")

    if spec_scores:
        import statistics as _st
        print(f"\n  محرّكُ المواصفة — {len(spec_scores)} شركة:")
        print(f"      المتوسّط {_st.fmean(spec_scores):.1f} (الهدف 52–58) · "
              f"الانحراف {_st.pstdev(spec_scores):.1f} (12–16)")
        print(f"      فوق 75: {sum(1 for x in spec_scores if x > 75)/len(spec_scores):.1%} "
              f"(8–12٪) · تحت 42: {sum(1 for x in spec_scores if x < 42)/len(spec_scores):.1%} "
              f"(22–28٪)")
        if spec_cov:
            print(f"      وسيطُ التغطية {_st.median(spec_cov):.2f}")

    if per_path:
        print("\n  تفكيكُ الفجوة — وسيطُ كل مسارٍ ÷ السعر:")
        for nm, xs in sorted(per_path.items(), key=lambda kv: -len(kv[1])):
            if len(xs) >= 5:
                print(f"      {nm:32} {st.median(xs):.3f}   ({len(xs)} شركة)")

    # ── الاختبار الأمضى: ميلُ مضاعف الدفترية على العائد ──
    if len(roes) >= 8:
        s_ours, s_mkt = _slope(roes, pb_val), _slope(roes, pb_mkt)
        print()
        print(f"  ميلُ (قيمتنا÷الدفترية) على العائد   {s_ours}")
        print(f"  ميلُ (السعر÷الدفترية) على العائد    {s_mkt}")
        if s_ours and s_mkt:
            gap = (s_ours / s_mkt - 1) * 100 if s_mkt else None
            state = ("معاير" if gap is not None and abs(gap) <= 25
                     else "نشتري العائد أغلى من السوق" if gap and gap > 0
                     else "نرفض الشركات الممتازة")
            print(f"  الفارق {gap:+.0f}٪ → {state}")

    # ── القطاعات: انحيازٌ بنيويّ أم فرصة ──
    if by_sector:
        print("\n  القطاعاتُ الخارجة عن ±25٪:")
        out = [(s, st.median(v)) for s, v in by_sector.items() if len(v) >= 3]
        for sec, med in sorted(out, key=lambda x: -x[1]):
            if med > 1.25 or med < 0.75:
                print(f"      {sec:28} {med:.2f}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    lim = 400
    if "--limit" in args:
        lim = int(args[args.index("--limit") + 1])
    sys.exit(asyncio.run(run(lim)))
