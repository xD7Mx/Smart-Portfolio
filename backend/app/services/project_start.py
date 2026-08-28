"""تاريخ بداية المشروع — المرجع الزمني الوحيد لتحويل العائد إلى «سنوي».

لماذا يوجد: سجلّ النقد يبدأ يوم أدخل المالك بياناته في التطبيق، لا يوم بدأ
مشروعه فعلاً. فحساب المعدّل السنوي من هذا السجلّ يقسم على شهرٍ واحد ويضربه
في اثني عشر، فيقول «١٩٥٪ سنوياً» لعائدٍ حقيقيّه ١٠٪ منذ التأسيس.

والحلّ الذي اختاره المالك: **تاريخٌ واحد** يكتبه مرّة، فيصير مقام الزمن كلّه.
يعيش ملفّاً في مجلّد البيانات كبقية الإعدادات: يبقى بعد تحديث الحزمة وبعد
إعادة التشغيل، ولا يمسّ أي جدولٍ مالي ولا يغيّر رقماً واحداً من أرقامك — هو
مقامُ زمنٍ لا بيانات محفظة.
"""
import json
import os
from datetime import date

_PATH = ("/app/data/project.json" if os.path.isdir("/app/data")
         else os.path.join(os.getcwd(), "project.json"))


def get_project_start() -> date | None:
    """تاريخ البداية إن ضبطه المالك، وإلا None (فيعود الحساب إلى سجلّ النقد)."""
    try:
        with open(_PATH, encoding="utf-8") as f:
            raw = (json.load(f) or {}).get("start_date")
        return date.fromisoformat(raw) if raw else None
    except Exception:
        return None


def set_project_start(value: str | None) -> date | None:
    """يحفظ التاريخ (YYYY-MM-DD) أو يمسحه بقيمةٍ فارغة. يرفض تاريخاً مستقبلياً:
    مقامٌ سالب أو صفر يُنتج معدّلاً بلا معنى."""
    parsed = None
    if value:
        parsed = date.fromisoformat(str(value)[:10])
        if parsed > date.today():
            raise ValueError("تاريخ البداية في المستقبل")
    os.makedirs(os.path.dirname(_PATH), exist_ok=True)
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump({"start_date": parsed.isoformat() if parsed else None}, f, ensure_ascii=False)
    return parsed


def annualize(total_return_pct: float | None, days: int | None) -> float | None:
    """تحويل عائدٍ تراكمي إلى معدّلٍ مركّبٍ سنوي: (1+r)^(365/أيام) − 1.

    ولا يُحوَّل قبل ٩٠ يوماً: أسبوعٌ جيّد مضروبٌ في ٥٢ يَعِد بما لا يُعرف.
    وخسارةٌ تتجاوز رأس المال (r ≤ −100٪) لا جذر لها، فتُعاد None لا رقمٌ وهمي.
    """
    if total_return_pct is None or not days or days < 90:
        return None
    growth = 1 + total_return_pct / 100
    if growth <= 0:
        return None
    return round((growth ** (365 / days) - 1) * 100, 2)
