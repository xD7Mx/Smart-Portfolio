"""مدخلاتُ محرّك القيمة تصل فعلاً — حارسُ D148.

## العطب

`fair_value.py` كان يقرأ `total_equity` في موضعين، وهو اسمٌ **لا وجودَ
له** فيما يصلنا: المصدرُ يرسل `equity` و`stockholders_equity`. فلم
يُحسب `roic` قطُّ في التشغيل الحقيقيّ، وسقط قيدُ إعادة الاستثمار إلى
العائد على حقوق الملكية — وهو عينُ ما حذّر منه التعليقُ فوقه: يجعل
القيدَ سخيّاً للشركات المرفوعة، وهي أحوجُها إليه. وسلسلةُ العائد في
مسار الدخل المتبقّي كانت تنقطع من أوّل سنة.

وهو الثامنُ من صنفه في هذا المشروع: اسمُ حقلٍ لم يوجد في المصدر،
تستره عيّنةُ اختبارٍ تكتب الاسمَين معاً. فالفحصُ هنا **سلوكيّ**: لا
يقرأ الأسماء، بل يغيّر مدخلاً ويشترط أن تتغيّر النتيجة.

    python scripts/audit/fv_inputs.py
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _periods(equity_key: str, debt: float, ni: float = 2e9) -> list[dict]:
    sh = 1e9
    return [{"year": 2019 + k, "revenue": 3e10, "net_income": ni,
             equity_key: 1e10, "eps": ni / sh,
             "operating_cash_flow": ni * 1.2, "capex": -ni * 0.2,
             "depreciation": ni * 0.2, "total_debt": debt,
             "ending_cash": 0.0, "shares_outstanding": sh,
             "operating_income": ni * 1.4, "total_assets": 1e10 + debt,
             "dividends_paid": -ni * 0.3} for k in range(5)]


def _dcf(periods: list[dict]) -> float | None:
    from app.services import fair_value as fv
    o = fv.compute({"beta": 1.0}, 30.0, 16.0, 2.0, periods=periods,
                   archetype="asset_light", symbol="G")
    for m in o.get("methods", []):
        if "المخصوم" in m.get("name", ""):
            return m.get("value")
    return None


def main() -> int:
    T: list[tuple[str, bool, str]] = []

    def t(n, ok, d=""):
        T.append((n, bool(ok), d))

    # ١ — الأسماءُ الثلاثة تُقرأ سواءً
    vals = {k: _dcf(_periods(k, 1e10))
            for k in ("equity", "stockholders_equity", "total_equity")}
    uniq = {v for v in vals.values() if v is not None}
    t("١ أسماءُ حقوق الملكية الثلاثة سواء",
      len(uniq) == 1 and None not in vals.values(),
      " · ".join(f"{k}={v}" for k, v in vals.items()))

    # ٢ — الرافعةُ تُغيّر الخصم: دليلُ أنّ `roic` يُحسب فعلاً
    # عائدُ حقوقٍ ثابتٌ ‎20٪، وعائدُ رأس المال يهبط بزيادة الدَّين. فلو
    # لم يُحسب roic لتساوى الخصمُ في الحالتين.
    # رافعةٌ واقعية: دَينٌ نصفُ حقوق الملكية. وأضعافُها تمحو قيمةَ
    # الحقوق فيمتنع المحرّك — امتناعٌ صحيح، لكنّه لا يقيس ما نريد.
    no_debt = _dcf(_periods("equity", 0.0))
    lots = _dcf(_periods("equity", 5e9))
    t("٢ الرافعةُ تُغيّر الخصم (roic يُحسب)",
      no_debt is not None and lots is not None and lots < no_debt,
      f"بلا دَين {no_debt} · بدَينٍ نصفِ الحقوق {lots}")

    # ٣ — لا يُقرأ اسمٌ خامٌ لحقوق الملكية خارج خريطة الأسماء
    src = ""
    for base in (os.path.join(_ROOT, "backend", "app"), "/app/app"):
        p = os.path.join(base, "services", "fair_value.py")
        if os.path.exists(p):
            src = open(p, encoding="utf-8").read()
            break
    raw = [ln.strip() for ln in src.splitlines()
           if 'get("total_equity")' in ln and not ln.strip().startswith("#")]
    t("٣ لا اسمَ خامٌ خارج خريطة الأسماء", not raw,
      "يُقرأ عبر _eq_of" if not raw else " · ".join(raw)[:70])

    print("═" * 60)
    print("  مدخلاتُ محرّك القيمة تصل فعلاً")
    print("═" * 60)
    for n, ok, d in T:
        print(f"  {'PASS' if ok else 'FAIL'}  {n:34} {d}")
    bad = [n for n, ok, _ in T if not ok]
    print("═" * 60)
    print("  ✔ المدخلُ يصل، والرافعةُ تُقاس." if not bad
          else f"  ✖ أخفق {len(bad)}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
