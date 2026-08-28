"""
Governance Rule Engine — Phase 2 of the governance-engine redesign.

Loads every rule from app/data/governance_rules.yaml (never hard-coded in
Python) and evaluates a merged features dict against them. No AI, no
"eval()" of arbitrary code — each rule is a declarative {feature, op,
value} triple resolved by a small, closed set of comparison operators.

Callers merge whatever feature sources apply before calling evaluate():
  - financial_features.compute_features() output for quality/safety rules
  - a market/valuation snapshot (pe_ratio, peg_ratio, ev_ebitda, pb_ratio,
    pe_vs_sector_pct, ...) for valuation rules
  - a technical snapshot (trend, rsi, macd_signal, price_vs_ma50_pct, ...)
    for timing rules
  - hard-filter-only flags (audit_qualified, trading_suspended,
    bankruptcy_risk, consecutive_loss_years) when available

A rule whose referenced feature is missing (None / absent) is silently
skipped for that company — it never fabricates a penalty from missing
data. That gap is instead surfaced later via the Confidence Score.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml

_RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "governance_rules.yaml")

_OPS = {
    "gte": lambda v, x: v >= x,
    "lte": lambda v, x: v <= x,
    "gt": lambda v, x: v > x,
    "lt": lambda v, x: v < x,
    "eq": lambda v, x: v == x,
    "neq": lambda v, x: v != x,
    "between": lambda v, x: x[0] <= v <= x[1],
}
OPS = _OPS  # public alias — other engines (decision_engine) reuse the same closed operator set


@dataclass
class RuleHit:
    id: str
    category: str
    kind: str  # "penalty" | "bonus"
    severity: Optional[str]
    points: float  # signed: negative for penalties, positive for bonuses
    message: str
    feature: str
    value: Any


@dataclass
class HardFilterHit:
    id: str
    message: str
    feature: str
    value: Any


@dataclass
class RuleEvalResult:
    hard_filter: Optional[HardFilterHit] = None
    hits_by_category: dict[str, list[RuleHit]] = field(default_factory=dict)
    # Per category: the maximum bonus points this company COULD have earned
    # given only the features that actually had data — the denominator for
    # normalized scoring, so a company is measured on the signals we can
    # see, never dragged toward the base by data the provider never returned.
    achievable_bonus_by_category: dict[str, float] = field(default_factory=dict)
    # إجماليُّ ما كان يمكن كسبُه لو توفّرت كلُّ البيانات — به تُقاس التغطية،
    # وبها تنكمش الدرجةُ نحو أساسها. وبلا هذا المقام تصير الدرجةُ الكاملة
    # على شاهدٍ واحد مساويةً للدرجة الكاملة على عشرة.
    total_bonus_by_category: dict[str, float] = field(default_factory=dict)

    def rejected(self) -> bool:
        return self.hard_filter is not None

    def category_delta(self, category: str) -> float:
        return sum(h.points for h in self.hits_by_category.get(category, []))


_cache: dict | None = None
_cache_mtime: float | None = None


def rules_version() -> int:
    """A short token that changes whenever governance_rules.yaml is edited —
    embedded in per-company cache keys so a rules change auto-invalidates
    every cached evaluation (no restart, no 24h wait for scores to update)."""
    try:
        return int(os.path.getmtime(_RULES_PATH))
    except OSError:
        return 0


def load_rules(force: bool = False) -> dict:
    """Cached load, invalidated automatically if the YAML file's mtime
    changes — editing the file takes effect without a code deploy/restart
    beyond the next request (or immediately if force=True)."""
    global _cache, _cache_mtime
    mtime = os.path.getmtime(_RULES_PATH)
    if force or _cache is None or mtime != _cache_mtime:
        with open(_RULES_PATH, "r", encoding="utf-8") as fh:
            _cache = yaml.safe_load(fh) or {}
        _cache_mtime = mtime
    return _cache


def _feature_value(features: dict, name: str) -> Any:
    """features values may be either a raw scalar or a Feature-Engine-style
    {"value": ..., "note": ...} dict — accept both transparently."""
    raw = features.get(name)
    if isinstance(raw, dict) and "value" in raw:
        return raw["value"]
    return raw


def _check(rule: dict, value: Any) -> bool:
    op = rule.get("op")
    fn = _OPS.get(op)
    if fn is None:
        return False
    try:
        return bool(fn(value, rule.get("value")))
    except TypeError:
        return False


def _apply_overrides(base: dict, override_list: list) -> None:
    """Patch `base` (id -> rule) in place. `disabled: true` removes a rule
    ENTIRELY (so a metric structurally meaningless for the sector — e.g.
    operating cash flow for a bank, whose loan-book growth shows up as a
    NEGATIVE outflow — neither penalizes it nor pollutes its bonus
    denominator); otherwise the override merges its fields over the base
    rule (threshold tweak) or adds a brand-new sector rule."""
    for r in override_list:
        if r.get("disabled"):
            base.pop(r["id"], None)
        else:
            base[r["id"]] = {**base.get(r["id"], {}), **r}


def _merged_rules(cfg: dict, category: str, sector: str | None) -> list[dict]:
    """Resolve the effective rule set for a sector, in three layers:

      1. the general base rules (apply to every company),
      2. the sector's ARCHETYPE overrides — a reusable structural profile
         (financial / reit / cyclical / inventory_retail /
         capital_infra / general) that every market sector maps to via
         `sector_archetype`, so the engine is principled market-wide, not
         hand-tuned per holding,
      3. any per-sector fine-tuning in `sector_overrides` (wins over the
         archetype) for a specific threshold a whole archetype shouldn't own.

    A sector with no archetype mapping and no override falls back to the
    general base rules unchanged."""
    base = {r["id"]: dict(r) for r in cfg.get(category, [])}
    if sector:
        archetype = cfg.get("sector_archetype", {}).get(sector)
        if archetype:
            _apply_overrides(base, cfg.get("archetypes", {}).get(archetype, {}).get(category, []))
        _apply_overrides(base, cfg.get("sector_overrides", {}).get(sector, {}).get(category, []))
    return list(base.values())


def evaluate(features: dict, config: dict | None = None, sector: str | None = None) -> RuleEvalResult:
    """features: merged dict of feature_name -> value (or Feature dict).
    config: pass a pre-loaded rules dict to skip the cached load (useful
    for tests); normally omitted.
    sector: real Arabic sector name (Company.sector) — when it has an
    entry under sector_overrides in governance_rules.yaml, those override
    the general thresholds for this evaluation only."""
    cfg = config or load_rules()
    result = RuleEvalResult()

    for hf in cfg.get("hard_filters", []):
        value = _feature_value(features, hf["feature"])
        if value is None:
            continue
        if _check(hf, value):
            result.hard_filter = HardFilterHit(
                id=hf["id"], message=hf["message"], feature=hf["feature"], value=value,
            )
            return result  # a hard filter hit stops evaluation immediately

    for category in ("quality", "valuation", "safety", "timing"):
        hits: list[RuleHit] = []
        # feature -> best bonus points earnable on it (data present), so two
        # threshold tiers on the same feature (good vs. excellent) count once
        # at the higher tier instead of double-inflating the denominator.
        bonus_potential: dict[str, float] = {}
        total_potential: dict[str, float] = {}
        for rule in _merged_rules(cfg, category, sector):
            value = _feature_value(features, rule["feature"])
            kind = rule.get("kind", "penalty")
            if kind == "bonus":
                f0 = rule["feature"]
                total_potential[f0] = max(total_potential.get(f0, 0),
                                          abs(rule.get("points", 5)))
            if value is not None and kind == "bonus":
                pts = abs(rule.get("points", 5))
                f = rule["feature"]
                bonus_potential[f] = max(bonus_potential.get(f, 0), pts)
            if value is None:
                continue
            if not _check(rule, value):
                continue
            if kind == "penalty":
                severity = rule.get("severity", "medium")
                weight = cfg.get("severity_weight", {}).get(severity, 8)
                points = -abs(rule.get("points", weight))
            else:
                severity = None
                points = abs(rule.get("points", 5))
            message = rule["message"].format(value=_fmt(value))
            hits.append(RuleHit(
                id=rule["id"], category=category, kind=kind, severity=severity,
                points=points, message=message, feature=rule["feature"], value=value,
            ))
        # ══ درجاتُ المؤشّر الواحد لا تُجمع ══ (بأمر المالك: جودةٌ استثمارية)
        # المقام يعدّ المؤشّر مرّةً عند أعلى درجاته (سطر `bonus_potential`
        # أعلاه)، وكان البسط يجمع كلَّ درجةٍ تحقّقت. والدرجاتُ متدرّجة
        # يُقصد بها التمييز لا التراكم: «ممتاز ‏≥١٥٪» و«جيّد ‏[١٠،١٥]»
        # تلتقيان عند ١٥ بالضبط، فتُدفع مكافأتان لرقمٍ واحد.
        # وأثرُه لم يكن تجميلياً: شركةُ تأمينٍ عائدُها ١٥٪ بالضبط كسبت
        # ١٢ من مقامٍ قدره ٨، فبلغت مئةً من مئة على **مؤشّرٍ واحد** —
        # ودرجةٌ كاملة على مؤشّرٍ واحد أسوأ من درجةٍ منخفضة، لأنها تُقرأ
        # يقيناً وهي أضيقُ ما يكون.
        # فيُبقى من مكافآت المؤشّر الواحد أعلاها، ويُطابق البسطُ المقام.
        best: dict[str, RuleHit] = {}
        kept: list[RuleHit] = []
        for h in hits:
            if h.kind != "bonus":
                kept.append(h)
                continue
            prev = best.get(h.feature)
            if prev is None or h.points > prev.points:
                best[h.feature] = h
        hits = kept + list(best.values())
        result.hits_by_category[category] = hits
        result.achievable_bonus_by_category[category] = sum(bonus_potential.values())
        result.total_bonus_by_category[category] = sum(total_potential.values())

    return result


def _fmt(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 2)
    return value


def archetype_for(sector: str | None) -> str:
    """النمط القطاعيّ المطبَّق — أو «general» إن لم يكن له نمط خاصّ."""
    cfg = load_rules()
    return (cfg.get("sector_archetype", {}) or {}).get(sector or "", "general")


def standard_for(sector: str | None) -> dict:
    """المعيار المعترف به المطبَّق على هذا القطاع، بما يُقاس منه وما يتعذّر.

    سأل المالك عن معيار درجة الحوكمة كما سأل عن معيار القيمة العادلة.
    والفرق أن التقييم له معيارٌ عالميٌّ واحد (‏DCF)، أمّا التحليل المالي
    فله **إطارٌ لكل نوع نشاط** — البنك لا يُقاس بما يُقاس به مصنع.
    فيُعاد هنا اسمُ الإطار وما طُبِّق منه وما تعذّر، ويُعرض للمالك: حكمٌ
    يُعرَف إطارُه ونطاقُه يُبنى عليه، وحكمٌ مجهولُ الإطار لا يُبنى عليه.
    """
    cfg = load_rules()
    arch = archetype_for(sector)
    std = (cfg.get("archetype_standards", {}) or {})
    return {"archetype": arch,
            **(std.get(arch) or std.get("default") or {})}


def scope_for(sector: str | None, periods: list[dict] | None,
              info: dict | None = None) -> dict:
    """نطاقُ المعيار **لهذه الشركة بعينها** لا لنمطها فقط.

    القائمة الساكنة في `archetype_standards` تصف ما يتعذّر **عادةً**. لكنّ
    بعض البنود يصير مشتقّاً متى وصلت بنودُه: نسبة التكلفة إلى الدخل (‏CIR)
    — أحد أركان CAMELS — تُشتقّ من قائمة الدخل نفسها متى وصل الإيراد
    والدخل التشغيليّ. فيُنقل عندئذٍ من «يتعذّر» إلى «مُطبَّق».

    ولماذا يُحسب لكل شركة لا لكل نمط: التغطية تختلف من رمزٍ لآخر عند
    المصدر نفسه. ونطاقٌ يُعلَن ساكناً بينما الواقع أوسع أو أضيق هو ادّعاء
    في الاتجاهين — والمالك يزن الحكم بنطاقه.
    """
    std = dict(standard_for(sector))
    applied = list(std.get("applied") or [])
    unavailable = list(std.get("unavailable") or [])

    from app.services import sector_metrics

    sm = sector_metrics.compute(std.get("archetype") or "general",
                                periods, info, (info or {}).get("current_price"))
    derived = list(sm.get("derived") or [])

    # ما اشتُقّ يخرج من قائمة «يتعذّر»: المطابقة بجذر الاسم لأن القائمة
    # الساكنة تكتبه بصيغته الكاملة («هامش صافي الفائدة (‏NIM)») والمشتقّ
    # يكتبه بقيمته.
    for root in ("التكلفة إلى الدخل", "NIM", "FFO", "المتعثّرة"):
        if any(root in d for d in derived):
            unavailable = [u for u in unavailable if root not in u]
    # تكلفةُ المخاطر لا تُغني عن نسبة التعثّر ولا تُخرجها من «يتعذّر» —
    # تدفّقُ السنة ليس رصيدَ المحفظة، وخلطُهما ادّعاءٌ لا اختصار.
    if any("تكلفة المخاطر" in d for d in derived):
        unavailable = [u for u in unavailable if "NPL" not in u]
        unavailable.append("رصيدُ القروض المتعثّرة (‏NPL) — تُقاس تكلفةُ المخاطر بدلاً منه")

    # وما وُعد باشتقاقه ولم تصل بنوده يُعلَن خارج النطاق **لهذه الشركة**.
    # القائمة الساكنة لم تعد تذكره لأنه يُقاس عادةً، فلو سكتنا عنه هنا
    # لاختفى الغياب بدل أن يُعلَن — وهو أسوأ من إعلانه.
    for miss in (sm.get("missing") or []):
        if miss not in unavailable:
            unavailable.append(miss)

    std["applied"] = applied + derived
    std["unavailable"] = unavailable
    std["derived_now"] = derived
    std["metrics"] = sm.get("metrics") or []
    std["features"] = sm.get("features") or {}
    return std
