#!/usr/bin/env python3
"""حارسُ D637: لا غيابُ درجةِ جودةٍ بلا سببٍ مسمّى في المخزن، ولا عددُ خطوطٍ حمراء يشيخ."""
import datetime as dt, os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
from app.services import lastgood                                   # noqa: E402
from app.services.market_valuation_sweep import record_verdicts    # noqa: E402

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

an = (ROOT / "backend/app/services/analysis.py").read_text()
sw = (ROOT / "backend/app/services/market_valuation_sweep.py").read_text()
# الاستبعادُ بالخطّ الأحمر يمسّ عقدَ «المحرّك الواحد» (D149) — أمسكه حارسُه فأُرجئ إلى الإصدار الثاني (docs/BACKLOG_V2.md)
check("استُبعدت الشركة من التقييم: خطٌّ أحمر" not in an, "١ لا استبعادَ في شاشةٍ دون أخرى — الدرجةُ واحدةٌ في البطاقة والصفحة والجدول (D149)")
check('out["finance_score_unavailable"]' in sw and '"finance_score_unavailable": "تعذّر جلبُ' in sw,
      "٢ غيابُ الدرجة يُسمّى سببُه في المخزن (الاستبعاد · البيانات المحدودة · تعذّرُ المزوّد)")
today = dt.date.today()
lastgood.save("governance:deep", {"4250": {"decision": {"label": "انتظار"}, "at": today.isoformat(), "source": "page",
                                           "v": "E1", "red_lines": 2}})
done = {"4250": {"_verdict": {"decision": {"label": "انتظار"}, "evaluable": True, "red_lines": 0}}}
record_verdicts(done, today=today, engine_v="E1")
st = lastgood.load("governance:deep") or {}
check((st.get("4250") or {}).get("red_lines") == 0 and (st.get("4250") or {}).get("source") == "page",
      "٣ عددُ الخطوط يُحدَّث كلَّ مسحةٍ ولو حُمي حكمُ الصفحة الحديث (جبل عمر: خطٌّ زال وبقي مخزَّناً)", str(st.get("4250")))
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
