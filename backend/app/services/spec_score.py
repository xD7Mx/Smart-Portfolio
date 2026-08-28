"""درجةُ الجودة المالية — لكل نمطٍ بطاقتُه، والعتبةُ من السوق.

## المؤشّرُ معرفة، والعتبةُ ليست

**أيُّ** مؤشّرٍ يحكم في كلّ نوعٍ من الأعمال معرفةٌ راسخة: البنكُ بهامش
عمولاته وتكلفةِ مخاطره وكفاءتِه، والريتُ بأمواله من العمليات ورافعته،
والدوريُّ بعائده عبر الدورة وأسوأِ رافعةٍ بلغها. هذه البطاقاتُ مكتوبةٌ
في `archetype_spec.py` ويقرؤها المالك بلا برنامج.

أمّا **أين** يبدأ «الجيّد» فلا يُعرف بالرأي. وكان في المحرّك ستٌّ وستّون
عتبةً مزدوجة، ما يتتبّع منها إلى معيارٍ منشورٍ ثلاث. فصار المؤشّرُ يُقاس
**برتبته بين أقرانه في نمطه** على تداول نفسه (`peer_distribution`):

    الدرجة = Σ(رتبةُ المؤشّر في قطاعه × وزنه) ÷ Σ(الأوزان المقيسة)

فسبعون في البنوك وسبعون في التجزئة تعنيان الشيءَ نفسه — أفضلُ من سبعين
بالمئة من الأقران. وتبقى العتباتُ المعلَنة سنداً حين لا يكفي التوزيع،
ويُقال في المخرَج أيُّ أساسٍ حكم.

## الدرجةُ والتغطيةُ لا تُضربان

كانت الدرجةُ تنكمش نحو الخمسين بجذر التغطية، فيخرج رقمٌ واحد يخلط
«الشركةُ متوسّطة» بـ«لم نستطع قياسها» — وهما نقيضان في القرار. وقياسُه
على السوق: صفرُ شركةٍ فوق ‎75 من ‎386، ونصفُها تحت ‎42.

فصارا رقمين يُعرضان معاً ولا يُدمجان، وللتغطية **حدٌّ أدنى** دونه لا
درجةَ إطلاقاً بل امتناعٌ صريح — وذلك مخرَجٌ نافعٌ لا نقص.

## والترتيبُ وحده لا يكفي

هو نسبيّ: أسوأُ قطاعٍ يبقى فيه «الأفضل». فيلزمه خطوطٌ حمراء مطلقة في
`red_lines.py` تُبطِل الترتيبَ ولا تُخصم منه.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.data.archetype_spec import (SCORECARDS, FALLBACK_RULES,
                                     SECTOR_ARCHETYPE)

# أقلُّ ما تُبنى عليه درجة: ثلاثةُ أركانٍ مقيسة ونصفُ وزن البطاقة.
# دونها الرقمُ تخمينٌ يرتدي هيئةَ قياس.
MIN_PILLARS = 3
MIN_COVERAGE = 0.50


@dataclass
class MetricRead:
    key: str
    label: str
    value: float
    score: float          # 0–100 لهذا المؤشّر
    weight: float
    tone: str             # green | yellow | red
    # أساسُ الدرجة: رتبةٌ بين الأقران أم عتبةٌ معلَنة — يُقال ولا يُخمَّن.
    basis: str = "threshold"
    cohort: int = 0


@dataclass
class SpecScore:
    archetype: str
    score: Optional[float]
    coverage: float
    metrics: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    blocking: list = field(default_factory=list)   # عقوباتٌ مانعة اشتعلت
    abstain_reason: Optional[str] = None
    basis: Optional[str] = None

    @property
    def blocks_buy(self) -> bool:
        return any(b[1] == "منع شراء" for b in self.blocking)


def _val(features: dict, key: str):
    raw = (features or {}).get(key)
    v = raw.get("value") if isinstance(raw, dict) else raw
    return v if isinstance(v, (int, float)) else None


def _lerp(v: float, good: float, weak: float) -> float:
    """استيفاءٌ خطّيّ بين العتبتين — لا قفزةَ عند حدّ."""
    if good == weak:
        return 100.0 if v >= good else 0.0
    x = (v - weak) / (good - weak)
    return max(0.0, min(1.0, x)) * 100.0


# ══ اتّجاهاتٌ لا تُرتَّب ══ (قرارُ مجلس نِصاب)
# `band` نطاقٌ صحّيّ قيمتُه الصحيحة بنيويّة، و`*_abs` معيارٌ **منشور** له
# حدٌّ نظاميّ أو تعريفٌ عالميّ: كفايةُ رأس المال (بازل ‎10.5٪) · النسبةُ
# المجمّعة (دون المئة ربحُ اكتتاب). وترتيبُ هذه بين الأقران يقلب معناها:
# بنكٌ دون حدّ بازل لا يُنجّيه أن أقرانه أسوأ منه.
NO_RANK = ("band", "higher_abs", "lower_abs")


def _metric_score(v: float, good: float, weak: float, direction: str) -> float:
    if direction in ("higher", "higher_abs"):
        return _lerp(v, good, weak)
    if direction in ("lower", "lower_abs"):
        return _lerp(v, good, weak)      # good < weak فينعكس الميل تلقائياً
    # نطاقٌ صحّيّ [good, weak]: داخله مئة، وخارجه يتناقص بمقدار الخروج
    lo, hi = min(good, weak), max(good, weak)
    if lo <= v <= hi:
        return 100.0
    span = max(hi - lo, 1e-9)
    out = (lo - v) if v < lo else (v - hi)
    return max(0.0, 100.0 - (out / span) * 100.0)


def resolve_archetype(sector: str | None, features: dict) -> str:
    return resolve_archetype_ex(sector, features)[0]


def resolve_archetype_ex(sector: str | None, features: dict) -> tuple[str, bool]:
    """النمطُ من القطاع، وإلّا بقواعد حتميّة من البيانات — لا تخمين.

    ويُعاد معه ما إذا كان **محلولاً حقّاً**. فقد كان السقوطُ الأخير إلى
    `asset_light` صامتاً: ثلاثةُ رموز (‏2002 · 8270 · 4010) خرجت بقطاعٍ
    إنجليزيّ لم يُطابق الخريطة، ولم تُشعل قاعدةٌ حتميّة، فقيست بمسطرةٍ
    لا تخصّها وخرجت درجتُها كأنها معلومة. والصمتُ هنا أسوأ من الامتناع.
    """
    a = SECTOR_ARCHETYPE.get((sector or "").strip())
    if a:
        return a, True
    # مطابقةٌ متساهلة قبل الامتناع: المصدرُ يكتب القطاعَ بصيغٍ متقاربة
    # (‏«قطاع البنوك» · «البنوك » · حالةُ أحرفٍ مختلفة)، ولا يصحّ أن يمتنع
    # المحرّكُ عن شركةٍ نعرف نمطَها لفرقٍ في مسافةٍ أو بادئة.
    key = " ".join((sector or "").split()).strip().casefold()
    key = key[len("قطاع "):] if key.startswith("قطاع ") else key
    if key:
        for k, v in SECTOR_ARCHETYPE.items():
            if " ".join(k.split()).casefold() == key:
                return v, True
    lev = _val(features, "leverage_x")
    ie = _val(features, "interest_to_revenue")
    if lev is not None and lev >= 4 and ie is not None and ie >= 0.15:
        return "financial", True
    capex = _val(features, "capex_to_revenue")
    dep = _val(features, "depreciation_to_revenue")
    if capex is not None and capex >= 0.10 and dep is not None and dep >= 0.08:
        return "capital_infra", True
    inv = _val(features, "inventory_intensity")
    if inv is not None and inv >= 15:
        return "consumer_cyclical", True
    st = _val(features, "earnings_stability")
    if st is not None and st < 55:
        return "commodity", True
    # لا خريطةَ ولا قاعدةَ حتميّة: يُقاس بالنمط الخفيف ويُعلَن أنه غيرُ محلول.
    return "asset_light", False


def raw_composite(features: dict, archetype: str,
                  dist: dict | None = None) -> float | None:
    """الخلاصةُ الخام قبل ترتيبها بين شركات السوق.

    تُستعمل في موضعين: هنا لحساب الدرجة، وفي `peer_distribution` لبناء
    توزيع الخلاصة نفسها. ووحدةُ المصدر مقصودة — لو حُسبت مرّتين بشيفرتين
    لانحرف التوزيعُ عمّا يُقاس به.
    """
    card = SCORECARDS.get(archetype)
    if not card or card.get("abstain"):
        return None
    from app.services import peer_distribution as _pd
    d = dist if dist is not None else _pd.load()
    got_w = 0.0
    acc = 0.0
    n = 0
    for key, _label, weight, good, weak, direction in card["metrics"]:
        v = _val(features, key)
        if v is None:
            continue
        cuts = None if direction in NO_RANK else _pd.cuts_for(d, archetype, key)
        if cuts:
            sc = _pd.percentile_of(v, cuts,
                                   direction not in ("lower", "lower_abs"))
        else:
            sc = _metric_score(v, good, weak, direction)
        acc += sc * weight
        got_w += weight
        n += 1
    if n < MIN_PILLARS or not got_w:
        return None
    tot_w = sum(m[2] for m in card["metrics"])
    if tot_w and (got_w / tot_w) < MIN_COVERAGE:
        return None
    if any(k not in {m[0] for m in card["metrics"] if _val(features, m[0]) is not None}
           for k in (card.get("essential") or [])):
        return None
    return acc / got_w


def compute(features: dict, sector: str | None,
            archetype: str | None = None) -> SpecScore:
    resolved = True
    if archetype:
        arch = archetype
    else:
        arch, resolved = resolve_archetype_ex(sector, features)
    if not resolved:
        return SpecScore(
            archetype=arch, score=None, coverage=0.0,
            abstain_reason=(
                f"قطاعُ المصدر «{sector or 'غير معروف'}» لم يُطابق خريطةَ "
                "الأنماط ولم تنطبق قاعدةٌ حتميّة من القوائم — فلا مسطرةَ "
                "تخصّ هذه الورقة، ولا تُقاس بمسطرةِ غيرها."))
    card = SCORECARDS.get(arch) or SCORECARDS["asset_light"]

    if card.get("abstain"):
        return SpecScore(archetype=arch, score=None, coverage=0.0,
                         abstain_reason=card["abstain"])

    # ══ الرتبةُ في القطاع بدل العتبة المخترَعة ══ (بأمر المالك)
    # كانت كلُّ عتبةٍ رقمين اخترتُهما («ممتاز ‎2.9٪ · ضعيف ‎2.1٪»)، وما
    # يتتبّع منها إلى معيارٍ منشورٍ ثلاثٌ من ستٍّ وستّين. فصار المؤشّرُ
    # يُقاس برتبته بين أقرانه في نمطه على تداول نفسه — رقمٌ قابلٌ للتحقّق
    # من بياناتٍ عامّة، ويُعاير نفسه، ولا رأيَ لنا فيه.
    # وتبقى العتباتُ المعلَنة سنداً حين لا يكفي التوزيع (نمطٌ صغير أو
    # توزيعٌ لم يُبنَ بعد)، ويُقال في المخرَج أيُّ أساسٍ حكم.
    from app.services import peer_distribution as _pd
    dist = _pd.load()

    reads, missing = [], []
    got_w = tot_w = 0.0
    ranked = 0
    for key, label, weight, good, weak, direction in card["metrics"]:
        tot_w += weight
        v = _val(features, key)
        if v is None:
            missing.append(label)
            continue
        # ══ النطاقُ الصحّيّ لا يُرتَّب ══ (كشفه مجلسُ نِصاب)
        # كان `band` يُعامَل معاملةَ `higher` في الترتيب، فصندوقٌ يوزّع
        # ‎150٪ من أمواله من العمليات — أي يوزّع من دَينه، وهو أحدُ خطوطنا
        # الحمراء — يخرج **في قمّة قطاعه**. والترتيبُ يقلب المعنى هنا لأن
        # هذه المؤشّرات ليس «الأكثرُ» فيها خيراً ولا «الأقلّ»: للإنفاق
        # الرأسماليّ إلى الإهلاك قيمةٌ صحّيّة حول الواحد (دونها تآكلُ أصلٍ
        # وفوقها توسّعٌ بلا عائد)، وللتوزيع سقفٌ هو ما تولّده العمليات.
        # وهذه ليست عتباتٍ مخترَعة بل حقائقُ بنيويّة: أصلٌ يُستهلك ولا
        # يُجدَّد يتآكل، وتوزيعٌ يفوق الدخل يُموَّل من غيره. فتبقى بالعتبة.
        cuts = None if direction in NO_RANK else _pd.cuts_for(dist, arch, key)
        if cuts:
            higher = direction not in ("lower", "lower_abs")
            sc = _pd.percentile_of(v, cuts, higher)
            basis, cohort = "rank", _pd.cohort_size(dist, arch, key)
            ranked += 1
        else:
            sc = _metric_score(v, good, weak, direction)
            basis, cohort = "threshold", 0
        tone = "green" if sc >= 70 else "red" if sc <= 30 else "yellow"
        reads.append(MetricRead(key, label, v, sc, weight, tone,
                                basis=basis, cohort=cohort))
        got_w += weight

    coverage = (got_w / tot_w) if tot_w else 0.0

    # ══ ركنٌ لا تقوم الدرجةُ بدونه ══
    # بعضُ الأنماط لها مقياسٌ يُعرَّف به العملُ نفسه، وغيابُه ليس نقصَ
    # تغطيةٍ يُعوَّض ببقية الأركان: النسبةُ المجمّعة في التأمين تفصل ربحَ
    # الاكتتاب من ربح الاستثمار، وبدونها لا يُعرف أرابحةٌ هي في عملها أم
    # تخسر فيه وتغطّي العجزَ من محفظتها. فتُعلَن في البطاقة `essential`،
    # ويمتنع المحرّكُ عند غيابها امتناعاً صريحاً — كما يفعل محرّكُ القيمة
    # العادلة، فلا يتناقض شطرا الشاشة الواحدة.
    _got = {r.key for r in reads}
    _lost = [k for k in (card.get("essential") or []) if k not in _got]
    if _lost:
        _names = {k: lbl for k, lbl, *_ in card["metrics"]}
        return SpecScore(
            archetype=arch, score=None, coverage=round(coverage, 3),
            metrics=reads, missing=missing,
            abstain_reason=(
                "لم يصل ركنٌ لا تقوم درجةُ هذا النمط بدونه: "
                + " · ".join(_names.get(k, k) for k in _lost)
                + ". وبقيةُ الأركان لا تعوّضه."))

    # ══ الدرجةُ والتغطيةُ لا تُضربان ══
    # كانت الدرجةُ تنكمش نحو الخمسين بجذر التغطية، فيخرج رقمٌ واحد يخلط
    # «الشركةُ متوسّطة» بـ«لم نستطع قياسها» — وهما نقيضان في القرار.
    # فصارا رقمين يُعرضان معاً ولا يُدمجان، وللتغطية حدٌّ أدنى دونه لا
    # درجةَ إطلاقاً — وذلك مخرَجٌ نافعٌ لا نقص: يقول لا تشترِ على أساسنا.
    if len(reads) < MIN_PILLARS or coverage < MIN_COVERAGE:
        return SpecScore(
            archetype=arch, score=None, coverage=round(coverage, 3),
            metrics=reads, missing=missing,
            abstain_reason=(
                f"قِيس {len(reads)} من {len(card['metrics'])} أركانٍ فقط "
                f"({coverage:.0%} من الوزن) — دون الحدّ الذي تُبنى عليه "
                f"درجة. الغائب: {' · '.join(missing[:4])}."))

    adj = sum(r.score * r.weight for r in reads) / got_w

    # ══ الخلاصةُ تُرتَّب بين شركات السوق ══ (كشفه إحصاءُ الجاهزية)
    # متوسّطُ عدّة مئينات لا يبقى منتظماً بل يتكدّس حول الوسط، فتصير
    # عتباتُ القرار — المكتوبةُ لتُسمّي شرائح — بلا معنى: خرج «شراء قوي»
    # شركتين من ‎268 و«تجنّب» ‎43٪. فتُرتَّب الخلاصةُ مرّةً أخرى بين شركات
    # السوق كلِّها، فتعود إلى الانتظام وتصير كلُّ عتبةٍ شريحةً حقيقية.
    # والمعنى بعدها واحد: **رتبةُ الشركة في السوق، مقيسةً بأركان قطاعها**.
    _cc = (dist.get("composite") or {}).get("cuts")
    if isinstance(_cc, list) and len(_cc) >= 2:
        adj = _pd.percentile_of(adj, [float(c) for c in _cc], True)
        basis_note = "رتبةٌ في السوق بأركان القطاع"
    else:
        basis_note = None

    # العقوباتُ المانعة من البطاقة نفسها
    fired = []
    for key, op, limit, kind in card.get("blocking", []):
        v = _val(features, key)
        if v is None:
            continue
        hit = (v > limit) if op == "gt" else (v < limit)
        if hit:
            fired.append((key, kind))
            if kind == "سقف 35":
                adj = min(adj, 35.0)

    basis = (basis_note or "ترتيبٌ في القطاع" if ranked == len(reads) else
             "عتباتٌ معلَنة" if ranked == 0 else
             f"ترتيبٌ في {ranked} من {len(reads)} أركان")

    return SpecScore(archetype=arch, score=round(max(0.0, min(100.0, adj)), 1),
                     coverage=round(coverage, 3), metrics=reads,
                     missing=missing, blocking=fired, basis=basis)
