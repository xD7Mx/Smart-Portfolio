"""توزيعُ الأقران — العتبةُ تُشتقّ من السوق لا تُخترَع.

## لماذا

قال المالك: «لا تضع عتباتٍ من عندك، أريد ما هو معترفٌ به». وكان في
المحرّك ستٌّ وستّون عتبةً مزدوجة، ما يتتبّع منها إلى معيارٍ منشورٍ ثلاث.
والباقي اختياراتُ معايرةٍ كنتُ أشدّها وأُرخيها جولةً بعد جولة، فتتغيّر
الأرقامُ بلا أن يتغيّر معيار.

والخطأُ لم يكن في المؤشّرات — **أيُّ** مؤشّرٍ يحكم في كلّ نوعٍ من الأعمال
معرفةٌ راسخة: البنكُ بهامش عمولاته وتكلفة مخاطره، والريتُ بأمواله من
العمليات ورافعته، والدوريُّ بعائده عبر الدورة. الخطأُ كان في ادّعاء
معرفةِ **أين** يبدأ «الجيّد» — وهو ما لا يُعرف بالرأي.

فالحلُّ أن تُقاس الشركةُ بأقرانها في قطاعها على تداول نفسه: «هامشُ
العمولات ‎3.1٪ — أعلى من ‎78٪ من البنوك المدرجة». وهذا:

  · يُسقط كلَّ عتبةٍ لا مصدرَ لها — لا رأيَ لنا في شيء
  · يجعل كلَّ رقمٍ قابلاً للتحقّق من بياناتٍ عامّة
  · يجعل الدرجاتِ **قابلةً للمقارنة عبر القطاعات**: سبعون في البنوك
    وسبعون في التجزئة تعنيان الشيءَ نفسه — أفضلُ من سبعين بالمئة
  · يُعاير نفسه كلّما تغيّر السوق، بلا تدخّل

## حدُّ هذا المنهج — ويُعالَج خارجَه

الترتيبُ نسبيّ: أسوأُ قطاعٍ في السوق يبقى فيه «الأفضل». فلا يصلح وحده،
ويلزمه خطوطٌ حمراء **مطلقة** لا تحتاج معايرة (‏`red_lines.py`): من وقع
في واحدةٍ منها لا يُرتَّب أصلاً بل يُستبعد.

## كيف تُبنى

مرّةً في اليوم تُقرأ قوائمُ كلّ شركةٍ من مخزوننا (بلا نداءاتٍ جديدة إن
كانت محفوظة)، وتُحسب سماتُها، وتُجمع قيمُ كل مؤشّرٍ **داخل نمطه**، ثم
تُحفظ العشيراتُ (‏deciles) في المخزن الدائم. والتقييمُ بعدها بحثٌ في
جدولٍ لا حساب.

ولا يُبنى توزيعٌ من عيّنةٍ هزيلة: دون ثمانِ شركاتٍ في النمط لا رتبةَ
ذاتَ معنى، فيُعلَن ذلك ويعود التقييمُ إلى العتبات المعلَنة في المواصفة —
ويُقال في المخرَج أيُّ أساسٍ استُعمل.
"""

from __future__ import annotations

from loguru import logger

from app.services import lastgood

STORE_KEY = "quality:peer_distribution"

# أقلُّ عيّنةٍ تُعطي رتبةً ذاتَ معنى. دونها الرتبةُ ضجيجٌ: في نمطٍ من
# أربع شركاتٍ تنتقل الشركةُ من المئة إلى الخمسة والسبعين بفارقٍ لا يُذكر.
MIN_COHORT = 8

# عددُ نقاط القطع المحفوظة — عشيراتٌ تكفي لدقّةِ نقطةٍ مئوية عشرية.
_CUTS = 20


def _quantiles(values: list[float]) -> list[float]:
    """نقاطُ القطع بالاستيفاء الخطّيّ — لا تعتمد مكتبةً خارجية."""
    xs = sorted(values)
    n = len(xs)
    out = []
    for i in range(_CUTS + 1):
        pos = (n - 1) * (i / _CUTS)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        out.append(xs[lo] + (xs[hi] - xs[lo]) * frac)
    return out


def percentile_of(value: float, cuts: list[float], higher_is_better: bool) -> float:
    """رتبةُ قيمةٍ بين صفرٍ ومئة داخل توزيعٍ محفوظ.

    والاتّجاهُ يُطبَّق هنا لا في الجدول: تكلفةُ المخاطر كلّما قلّت كان
    خيراً، فرتبتُها مقلوبة.

    ══ التعادلُ يُعطى وسطَ مداه لا طرفَه ══ (كشفه اختبارٌ بعشرين شركة)
    كانت القيمةُ المساوية لأدنى نقطةِ قطعٍ تُعطى صفراً، فإذا تساوى
    القطاعُ كلُّه في مؤشّرٍ — وهو شائعٌ في المؤشّرات المشتقّة — خرج
    **الجميع** بصفر، أي عوقب القطاعُ كلُّه على تشابهه. والصوابُ أن
    التعادلَ لا يحمل معلومةً: من ساوى كلَّ أقرانه فهو وسطُهم، ومن ساوى
    طائفةً منهم فرتبتُه وسطُ مدى تلك الطائفة.
    """
    if not cuts or len(cuts) < 2:
        return 50.0
    if cuts[0] == cuts[-1]:
        return 50.0                      # توزيعٌ متعادلٌ كلُّه — لا معلومة
    if value < cuts[0]:
        p = 0.0
    elif value > cuts[-1]:
        p = 100.0
    else:
        # مدى نقاط القطع التي تساوي القيمة — الرتبةُ وسطُه.
        lo_i = hi_i = None
        for i, c in enumerate(cuts):
            if c == value:
                lo_i = i if lo_i is None else lo_i
                hi_i = i
        if lo_i is not None:
            p = ((lo_i + hi_i) / 2) / _CUTS * 100.0
        else:
            p = 100.0
            for i in range(len(cuts) - 1):
                lo, hi = cuts[i], cuts[i + 1]
                if lo <= value <= hi:
                    span = hi - lo
                    frac = 0.5 if span <= 0 else (value - lo) / span
                    p = (i + frac) / _CUTS * 100.0
                    break
    return p if higher_is_better else 100.0 - p


def load() -> dict:
    """التوزيعُ المحفوظ — أو قاموسٌ فارغ إن لم يُبنَ بعد."""
    d = lastgood.load(STORE_KEY)
    return d if isinstance(d, dict) else {}


def cuts_for(dist: dict, archetype: str, key: str) -> list[float] | None:
    row = ((dist.get("archetypes") or {}).get(archetype) or {}).get(key)
    if not isinstance(row, dict):
        return None
    cuts = row.get("cuts")
    if isinstance(cuts, list) and len(cuts) >= 2 and row.get("n", 0) >= MIN_COHORT:
        return [float(c) for c in cuts]
    return None


def cohort_size(dist: dict, archetype: str, key: str) -> int:
    row = ((dist.get("archetypes") or {}).get(archetype) or {}).get(key)
    return int(row.get("n", 0)) if isinstance(row, dict) else 0


async def build(symbols: list[str] | None = None, allow_fetch: bool = False) -> dict:
    """يبني التوزيعَ من قوائم السوق المخزّنة ويحفظه.

    `allow_fetch=False` هو الوضع الطبيعيّ: يقرأ ما هو محفوظٌ عندنا فقط
    فلا يُنفق حصّةَ المصدر. والمهمّةُ المجدوَلة تسبقه فتملأ المخزن.
    """
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.archetype_spec import SCORECARDS
    from app.services.market_data import market_service
    from app.services.four_scores import build_company_features
    from app.services.spec_score import resolve_archetype_ex
    from datetime import date

    # ══ السوقُ الرئيسة وحدها — قبل أيّ حساب ══ (D136)
    # كان الكونُ يمرّ كاملاً (‏409 شركة) فتدخل شركاتُ «نمو» كلَّ عشيرةٍ
    # وكلَّ وسيطٍ وكلَّ مئين، ثم تُستبعد في حلقة التسجيل وحدها — فيظهر
    # الاستبعادُ في العدّ ولا يقع في الحساب. وسوقُ «نمو» رقيقةُ التداول
    # محدودةُ الإفصاح، فمن قِيس عليها قِيس بمسطرةٍ ليست مسطرتَه.
    from app.data.universe import is_main
    syms = [s for s in (symbols or list(MARKET_UNIVERSE.keys()))
            if is_main(s)]
    # كلُّ مفتاحٍ تطلبه أيُّ بطاقة — لا نجمع ما لا يُستعمل.
    wanted: set[str] = set()
    for card in SCORECARDS.values():
        if card.get("abstain"):
            continue
        for k, *_rest in card["metrics"]:
            wanted.add(k)
    from app.services import governance_pillar
    wanted |= set(governance_pillar.METRIC_KEYS)

    # ══ المفاتيحُ من المواصفة القطاعية وحدها ══
    # كانت هنا كتلةٌ تجمع مفاتيحَ «النماذج الاقتصادية الخمسة» أيضاً
    # (‏D134). وقد رجعت الحوكمةُ إلى محرّكها الأصليّ فلم يبقَ من يقرأ تلك
    # النماذج — فصار جمعُ مفاتيحها بناءَ توزيعاتٍ لا يرتّب بها أحد.
    # وحسابٌ لا يقرؤه أحدٌ ضوضاءُ تُبطئ وتوهم أنها تعمل.

    pools: dict[str, dict[str, list[float]]] = {}
    raws: dict[str, list[dict]] = {}      # السماتُ محفوظةٌ لحساب الخلاصة
    seen = 0
    for raw in syms:
        sym = raw if str(raw).endswith(".SR") else f"{raw}.SR"
        try:
            data = await market_service.get_financials(
                sym, allow_supplement=allow_fetch)
        except Exception:                                         # noqa: BLE001
            continue
        periods = (data or {}).get("periods") or []
        if len(periods) < 2:
            continue
        meta = MARKET_UNIVERSE.get(str(raw).replace(".SR", "")) or {}
        try:
            feats, _info, _q = build_company_features(
                periods, info=None, sector=meta.get("sector"))
            arch, _ok = resolve_archetype_ex(meta.get("sector"), feats)
        except Exception:                                         # noqa: BLE001
            continue
        seen += 1
        raws.setdefault(arch, []).append(feats)
        bucket = pools.setdefault(arch, {})
        for k in wanted:
            v = feats.get(k)
            v = v.get("value") if isinstance(v, dict) else v
            if isinstance(v, (int, float)) and v == v and abs(v) != float("inf"):
                bucket.setdefault(k, []).append(float(v))

    out = {"as_of": date.today().isoformat(), "companies": seen, "archetypes": {}}
    for arch, keys in pools.items():
        row = {}
        for k, vals in keys.items():
            if len(vals) >= MIN_COHORT:
                row[k] = {"n": len(vals), "cuts": [round(c, 6) for c in _quantiles(vals)]}
        if row:
            out["archetypes"][arch] = row

    # ══ توزيعُ الخلاصة نفسها ══ (كشفه إحصاءُ الجاهزية)
    # كلُّ مؤشّرٍ يُرتَّب في قطاعه فيصير مئيناً منتظماً، لكنّ **متوسّطها
    # المرجَّح** لا يبقى منتظماً: متوسّطُ عدّة متغيّراتٍ يتكدّس حول الوسط.
    # فبلوغُ ‎85 يقتضي العُشرَ الأعلى في كلّ ركنٍ تقريباً — وقِيس على السوق
    # فخرج «شراء قوي» شركتين من ‎268، و«تجنّب» ‎43٪.
    #
    # وعتباتُ القرار مكتوبةٌ لتُسمّي شرائح («العُشر الأعلى» · «الثلث
    # الأعلى»)، فلا تصحّ إلا على مقياسٍ منتظم. فتُرتَّب الخلاصةُ مرّةً
    # أخرى **بين شركات السوق كلِّها**، فتعود إلى الانتظام وتصير كلُّ عتبةٍ
    # شريحةً حقيقيةً قابلةً للتحقّق.
    #
    # والمعنى بعدها واضحٌ وواحد: **درجةُ الشركة رتبتُها بين شركات السوق،
    # مقيسةً بأركان قطاعها هي.** فالمسطرةُ قطاعية والمقارنةُ سوقية — وهو
    # ما يحتاجه من يوازن بين فرصٍ من قطاعاتٍ مختلفة.
    try:
        from app.services import spec_score as _sp
        comps = []
        for arch, feats_list in raws.items():
            for fe in feats_list:
                r = _sp.raw_composite(fe, arch, out)
                if r is not None:
                    comps.append(r)
        if len(comps) >= MIN_COHORT * 4:
            out["composite"] = {"n": len(comps),
                                "cuts": [round(c, 6) for c in _quantiles(comps)]}
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"composite distribution failed: {e}")
    lastgood.save(STORE_KEY, out)
    logger.info(f"peer distribution built: {seen} companies · "
                f"{len(out['archetypes'])} archetypes")
    return out
