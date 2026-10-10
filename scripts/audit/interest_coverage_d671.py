#!/usr/bin/env python3
"""حارسُ D671 (المرشَّح 2.3): تغطيةُ الفوائد تُقرأ من بنديها، وما لا ينطبق لا يُعدّ ناقصاً في «ثقة X٪».

الحالُ قبل الإصلاح (gov_conf_door.py · run 38071763287): قارئُ المؤشّرات يقرأ الحقلَ المشتقّ `interest_coverage` وحده،
وطبقةُ «تداول» تحمل الربحَ التشغيليّ ومصروفَ التمويل لا المشتقّ — فغابت التغطيةُ في كلّ الأنماط تقريباً (71/72 · 46/46 ·
40/40) وكانت قواعدُ الدرجة ولجنةُ الخبراء تمرّ بلا تغطية، وثقةُ الخلاصة تُعاقَب على غيابها. والمصارفُ «ينقصها» السيولةُ
الجارية، ومن لا دَينَ عليه «تنقصه» التغطية — وليست بياناتٍ غائبة. ومؤشّراتُ الدرجة كانت خارج بصمة المحرّك.

    python3 scripts/audit/interest_coverage_d671.py
"""
import inspect, os, pathlib, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services.financial_features import compute_features   # noqa: E402
from app.services.confidence import compute_confidence, _CORE_FEATURES   # noqa: E402


def per(y, **kw):
    base = {"year": y, "revenue": 1000.0, "net_income": 100.0 + y % 3, "equity": 800.0, "eps": 1.0,
            "operating_cash_flow": 120.0, "free_cash_flow": 80.0, "total_assets": 2000.0, "gross_profit": 400.0,
            "operating_income": 150.0, "current_assets": 600.0, "current_liabilities": 300.0, "inventory": 100.0,
            "total_debt": 500.0, "interest_expense": 30.0, "debt_ratio": 40.0, "dividends_paid": -50.0,
            "shares_outstanding": 100.0, "capex": -40.0}
    base.update(kw)
    return base

# ١ · طبقةُ «تداول»: البندان حاضران والمشتقُّ غائب
f = compute_features([per(y) for y in range(2020, 2026)])
ic = (f.get("interest_coverage") or {}).get("value")
check(isinstance(ic, (int, float)) and abs(ic - 5.0) < 1e-6,
      "١ التغطيةُ تُحسب من الربح التشغيليّ ومصروف التمويل حين يغيب المشتقّ (150 ÷ 30 = 5×)", str(ic))
c = compute_confidence(f)
check(c.completeness_pct == 100.0, "٢ فلا تُعدّ ناقصةً في اكتمال «ثقة X٪»", str(c.completeness_pct))

# ٣ · لا دَينَ مقيساً ⇒ التغطيةُ لا تنطبق (لا ناقصة)
f2 = compute_features([per(y, total_debt=0.0, interest_expense=0.0) for y in range(2020, 2026)])
c2 = compute_confidence(f2)
check((f2.get("interest_coverage") or {}).get("value") is None and c2.completeness_pct == 100.0,
      "٣ ومن لا دَينَ عليه لا تُعدّ عليه التغطيةُ ناقصة", f"{(f2.get('interest_coverage') or {}).get('value')} · {c2.completeness_pct}")

# ٤ · ميزانيةُ مصرف: لا أصولَ ولا خصومَ جارية ⇒ السيولةُ الجارية لا تنطبق
f3 = compute_features([per(y, current_assets=None, current_liabilities=None, inventory=None) for y in range(2020, 2026)])
c3 = compute_confidence(f3)
check(c3.completeness_pct == 100.0, "٤ والمصرفُ لا تُعدّ عليه السيولةُ الجارية والسريعة ناقصتين", str(c3.completeness_pct))

# ٥ · والغيابُ الحقيقيُّ يبقى غياباً: دَينٌ قائمٌ بلا مصروفِ تمويلٍ منشور ⇒ ناقصة
f4 = compute_features([per(y, interest_expense=None) for y in range(2020, 2026)])
c4 = compute_confidence(f4)
check(c4.completeness_pct < 100.0, "٥ والغيابُ الحقيقيّ (دَينٌ بلا مصروفِ تمويلٍ منشور) يبقى ناقصاً — لا يُخفى",
      str(c4.completeness_pct))
check(len(_CORE_FEATURES) == 18, "٦ والمؤشّراتُ الأساسيةُ ثمانيةَ عشرَ كما هي — لم يُحذف منها شيءٌ ليرتفع الاكتمال")

from app.services.engine_identity import FILES   # noqa: E402
fz = (ROOT / "scripts/audit/engine_freeze_d635.py").read_text(encoding="utf-8")
check("backend/app/services/financial_features.py" in FILES and '"financial_features.py"' in fz,
      "٧ ومؤشّراتُ الدرجة داخل بصمة المحرّك وحارسِ التجميد — لا يُعدَّل مُدخَلُ الدرجة خارج الرقابة")
from app.services import governance_engine   # noqa: E402
check("_ENGINE_V" in inspect.getsource(governance_engine.evaluate_company),
      "٨ وكاشُ الخلاصة يتبع بصمةَ المحرّك — لا يبقى رقمٌ قديمٌ يوماً بعد النشر")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
