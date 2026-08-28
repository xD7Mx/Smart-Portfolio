"""تدقيقُ الأساسيات مقابل القوائم — الأصلُ يُصحِّح الملخَّص.

## لماذا وُجد هذا الملفّ

قال المالك إنه يبني قراراً استثمارياً على هذه الأرقام، فيجب أن تكون بجودةٍ
استثمارية. وأضعفُ ما بقي بعد إصلاح المرجع القطاعيّ هو **انفراد المصدر**:
كلُّ الأساسيات (ربحية السهم · الدفترية · العائد على حقوق الملكية) تُقرأ من
لقطةٍ ملخَّصة واحدة، بلا ما يكشف خطأها أو قِدَمها.

ولقطة الملخَّص تُخطئ بطرقٍ معروفة ولا تشكو:
  • **تأخّرٌ عن القوائم**: تُحدَّث بوتيرةٍ مختلفة عن بنود القوائم نفسها،
    فتبقى ربحية السهم على الربع الماضي بعد صدور الجديد.
  • **أثرُ عمليات رأس المال**: منحةٌ أو تجزئةٌ تُغيّر عدد الأسهم، فتبقى
    الربحية والدفترية للسهم على العدد القديم مدّةً.
  • **اختلافُ التعريف**: «الربحية» قد تكون أساسية أو مخفَّضة، والفرق حقيقيّ
    في شركةٍ ذات أدواتٍ قابلة للتحويل.

والقوائم أصلٌ لأنها **بنودٌ مدقَّقة** لا مشتقّاتٍ محسوبة: صافي الربح وحقوق
الملكية وعدد الأسهم تُبلَّغ كما هي. فما اشتُقّ منها أوثقُ ممّا وصل مشتقّاً.

## القاعدة

١. تُشتقّ الأساسيات من القوائم متى أمكن، وتُقارن بالملخَّص.
٢. **الاختلاف الجوهريّ يُصحَّح لصالح القوائم** ويُسجَّل — لا يُبتلع صامتاً.
٣. ما لا تكفي القوائم لاشتقاقه يبقى من الملخَّص كما هو، بلا وسمِ تدقيق.
٤. لا يُختلق شيء: التدقيق يُصحّح أو يسكت، ولا يُنتج رقماً من عنده.
"""

from __future__ import annotations

# عتبةُ الاختلاف الجوهريّ: فرقٌ دون هذا الحدّ يقع من التقريب واختلاف لحظة
# القياس، وفوقه يعني رقمين مختلفين لا رقماً واحداً بدقّتين.
MATERIAL = 0.05          # ٥٪


def _num(v):
    return v if isinstance(v, (int, float)) else None


def _pct_diff(a: float, b: float) -> float:
    return abs(a - b) / abs(b) if b else 0.0


def audit(info: dict, periods: list[dict] | None) -> dict:
    """يُعيد {"values": {...}, "notes": [...], "corrected": [...]}.

    `values` هي الأساسيات بعد التدقيق — تُستعمل في التقييم بدل الخام.
    """
    info = dict(info or {})
    periods = periods or []
    out = {"values": info, "notes": [], "corrected": []}
    if not periods:
        out["notes"].append("لا قوائم للتدقيق — الأرقام من المصدر الملخَّص وحده.")
        return out

    last = periods[-1]
    net_income = _num(last.get("net_income"))
    equity = _num(last.get("equity"))
    shares = _num(last.get("shares_outstanding"))

    def _check(field: str, derived: float | None, label: str) -> None:
        """يقارن حقلاً بمشتقّه من القوائم، ويُصحّح عند الاختلاف الجوهريّ."""
        if derived is None or derived <= 0:
            return
        raw = _num(info.get(field))
        if raw is None or raw <= 0:
            # غيابُ الملخَّص لا يمنع الاشتقاق: القوائم تسدّ الفراغ.
            info[field] = round(derived, 4)
            out["corrected"].append(f"{label}: استُخرج من القوائم ({derived:,.2f})")
            return
        d = _pct_diff(raw, derived)
        if d >= MATERIAL:
            info[field] = round(derived, 4)
            out["corrected"].append(
                f"{label}: الملخَّص {raw:,.2f} والقوائم {derived:,.2f} "
                f"(فارق {d * 100:.0f}٪) — اعتُمدت القوائم")

    # ربحية السهم = صافي الربح ÷ عدد الأسهم
    if net_income is not None and shares:
        _check("eps", net_income / shares, "ربحية السهم")
    # القيمة الدفترية للسهم = حقوق الملكية ÷ عدد الأسهم
    if equity is not None and shares:
        _check("book_value", equity / shares, "القيمة الدفترية للسهم")
    # العائد على حقوق الملكية = صافي الربح ÷ حقوق الملكية (٪)
    if net_income is not None and equity:
        _check("roe", net_income / equity * 100, "العائد على حقوق الملكية")

    if not out["corrected"]:
        out["notes"].append(
            f"دُقّقت الأساسيات مقابل {len(periods)} فترة مالية — لا اختلاف جوهريّ.")
    out["values"] = info
    return out
