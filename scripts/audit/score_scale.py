#!/usr/bin/env python3

# ══ فحصٌ لا يكتب في بيانات المالك ══ (D160)
# الوحداتُ تقرأ مسارَ المخزن عند **تحميلها**، فيُحوَّل في رأس الوحدة قبل
# أيّ استيرادٍ من `app` — بما فيها الاستيراداتُ المؤجَّلة داخل الدوالّ.
# وسكربتُ فحصٍ يغيّر حالةً ليس فحصاً.
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

# ─────────────────────────────────────────────────────────────────────────
# D162 — مقياسُ درجة السلامة يبلغ سقفَه بشركةٍ ممكنةِ الوجود.
#
# كانت الإشاراتُ الستُّ خطوطاً مستقيمة من صيغة `50 + قيمة × معامل`،
# فاستلزم بلوغُ التسعين — في الشركة الواحدة معاً — نموّاً ‎٢٠٪ سنوياً،
# وتدفّقاً تشغيليّاً ضِعفَ الربح، ومديونيةً ‎١٠٪، وتغطيةَ فوائدَ ‎١٢٫٥ ضعفاً.
# فتكدّست الشركاتُ القياديةُ عند السبعين وصار «الممتاز» يُقرأ «متوسّطاً».
#
# فحصٌ سلوكيّ لا قراءةَ نصّ: يبني شركاتٍ بأرقامٍ في متناول سوقٍ حقيقية
# ويطالب الدرجةَ بأن توافق وصفَها — لا يقرأ ثوابتَ المنحنيات.
# ─────────────────────────────────────────────────────────────────────────
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backend"))
from app.services.scores import _finance_score_from_periods  # noqa: E402

fail = 0


def say(ok, label, detail=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")


def periods(rev, ni, ocf, fcf, eq, debt, cov, capex=None):
    """سلسلةُ ثلاثِ سنواتٍ متّسقةٍ ينمو إيرادُها بالمعدّل المطلوب."""
    out = []
    for i in range(3):
        f = (1 + rev["g"] / 100) ** i
        out.append({
            "revenue": rev["base"] * f,
            "net_income": ni * f,
            "operating_cash_flow": ocf * f,
            "free_cash_flow": fcf * f,
            "equity": eq,
            "debt_ratio": debt,
            "interest_coverage": cov,
            "capex": capex,
        })
    return out


# شركةٌ قياديةٌ واقعية: نموٌّ ‎١٠٪، تدفّقٌ تشغيليٌّ ‎١٫٣ ضِعفَ الربح،
# هامشُ تدفّقٍ حرٍّ ‎١٥٪، عائدٌ على حقوق الملكية ‎٢٢٪، مديونيةٌ ‎٣٠٪،
# وتغطيةُ فوائدَ ‎١٠ أضعاف. كلُّ رقمٍ منها موجودٌ في السوق السعودية.
leader = periods({"base": 1000.0, "g": 10}, ni=150, ocf=195, fcf=150, eq=682, debt=0.30, cov=10)
s_leader = _finance_score_from_periods(leader)
say(s_leader is not None and s_leader >= 88,
    "١ الشركةُ القياديةُ الواقعية تتجاوز ٨٨", f"الدرجة {s_leader}")

# شركةٌ سليمةٌ بلا تميّز: نموٌّ ‎٦٪، تغطيةُ ربحٍ بالنقد ‎١٫٠،
# هامشٌ حرٌّ ‎٧٪، عائدٌ ‎١٥٪، مديونيةٌ ‎٤٥٪، تغطيةُ فوائدَ ‎٥.
sound = periods({"base": 1000.0, "g": 6}, ni=100, ocf=100, fcf=70, eq=667, debt=0.45, cov=5)
s_sound = _finance_score_from_periods(sound)
say(s_sound is not None and 68 <= s_sound <= 82,
    "٢ الشركةُ السليمةُ بلا تميّزٍ في السبعينات", f"الدرجة {s_sound}")

# شركةٌ متعثّرة: انكماشٌ ‎١٥٪، ربحٌ محاسبيٌّ بلا نقد، تدفّقٌ حرٌّ سالب،
# عائدٌ ‎٢٪، مديونيةٌ ‎٨٥٪، تغطيةُ فوائدَ ‎١.
weak = periods({"base": 1000.0, "g": -15}, ni=20, ocf=6, fcf=-80, eq=1000, debt=0.85, cov=1)
s_weak = _finance_score_from_periods(weak)
say(s_weak is not None and s_weak <= 35,
    "٣ الشركةُ المتعثّرةُ دون ٣٥", f"الدرجة {s_weak}")

say(s_weak < s_sound < s_leader,
    "٤ الترتيبُ يتصاعد مع الجودة", f"{s_weak} < {s_sound} < {s_leader}")

# السقفُ مبلوغٌ فعلاً: شركةٌ ممتازةٌ في كلّ إشارةٍ تتجاوز ٩٥ —
# فالمدى الأعلى ليس حبراً على ورق.
best = periods({"base": 1000.0, "g": 25}, ni=300, ocf=450, fcf=300, eq=857, debt=0.10, cov=20)
s_best = _finance_score_from_periods(best)
say(s_best is not None and s_best >= 95, "٥ المدى الأعلى مبلوغ", f"الدرجة {s_best}")

# والقاعُ كذلك: لا أرضيةَ خفيّةٌ عند الخمسين.
worst = periods({"base": 1000.0, "g": -30}, ni=-200, ocf=-250, fcf=-300, eq=1000, debt=0.98, cov=0)
s_worst = _finance_score_from_periods(worst)
say(s_worst is not None and s_worst <= 12, "٦ المدى الأدنى مبلوغ", f"الدرجة {s_worst}")

# بنكٌ: يُعفى من ثلاثِ إشاراتٍ باستدلالِ البيانات، ومع ذلك ينال درجةً
# تليق بعائدِه ونموِّه — لا سبعين لأنّ المسطرةَ لا تعرف كيف تقيسه.
bank = [
    {"revenue": 1000.0 * (1.12 ** i), "net_income": 400 * (1.12 ** i),
     "operating_cash_flow": None, "free_cash_flow": None, "equity": 2000,
     "debt_ratio": 0.86, "interest_coverage": None, "capex": None}
    for i in range(3)
]
s_bank = _finance_score_from_periods(bank)
say(s_bank is not None and s_bank >= 82, "٧ البنكُ القويُّ يتجاوز ٨٢", f"الدرجة {s_bank}")

# ولا يعتمد شيءٌ من ذلك على رمزٍ أو قطاع — الدالّةُ لا تأخذ قطاعاً أصلاً،
# والفحصُ يثبت أنّ الدرجةَ دالّةُ الأرقامِ وحدَها.
say(_finance_score_from_periods(leader) == s_leader,
    "٨ الدرجةُ ثابتةٌ لنفس الأرقام")

print()
print("النتيجة:", "نظيف ✔" if not fail else "فيه ملاحظات ✘")
sys.exit(fail)
