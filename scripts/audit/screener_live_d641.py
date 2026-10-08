#!/usr/bin/env python3
"""حارسُ D641: صفُّ الفرز (ومنه يقرأ المختبر) يحمل آخرَ ما كتبته المسحة عند كلّ قراءة — لا لقطةَ البناء؛
ولا احتياطَ بركن الحوكمة درجةً للجودة."""
import os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
from app.services import lastgood                                  # noqa: E402
from app.services.content_engine import _FUND_STORE_KEY            # noqa: E402
from app.services.market_screener import with_live_decisions       # noqa: E402

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

lastgood.save(_FUND_STORE_KEY, {
    "1324": {"finance_score": 77.0},                                         # صالح الراشد: درجةٌ وصلت بعد البناء
    "7205": {"finance_score": None, "finance_score_unavailable": "بيانات مالية محدودة"},
    "4250": {"fair_value": 20.0, "fair_value_conf": "متوسطة", "fair_value_calibrated": False,
             "fair_value_calibration_note": "قطاعٌ لم يجتز"},
})
lastgood.save("governance:deep", {"4250": {"decision": {"label": "انتظار"}, "red_lines": 0}})
rows = [{"symbol": "1324", "price": 50.0, "finance_score": None},
        {"symbol": "7205", "price": 10.0, "finance_score": 72.5},
        {"symbol": "4250", "price": 16.0, "red_lines": 2, "fair_value": 30.0, "fair_value_upside_pct": 87.5, "decision": "انتظار"}]
out = {r["symbol"]: r for r in with_live_decisions(rows)}
check(out["1324"]["finance_score"] == 77.0, "١ درجةٌ في المخزن بعد بناء الفرز تظهر في الصفّ (صالح الراشد 77 لا «—»)")
check(out["7205"]["finance_score"] is None, "٢ وما لا درجةَ له في المخزن لا تبقى له درجةُ لقطةٍ قديمة (دي بي اس)")
check(out["4250"]["red_lines"] == 0, "٣ وعددُ الخطوط الحمراء من المخزن العميق المحدَّث (جبل عمر)")
check(out["4250"]["fair_value"] == 20.0 and out["4250"]["fair_value_upside_pct"] == 25.0
      and out["4250"]["fair_value_calibrated"] is False and out["4250"]["fair_value_conf"] == "متوسطة",
      "٤ والسعرُ العادلُ بحقوله من المخزن، والصعودُ يُعاد حسابُه بالسعر الحيّ", str({k: out["4250"].get(k) for k in ("fair_value", "fair_value_upside_pct")}))
sw = (ROOT / "backend/app/services/market_valuation_sweep.py").read_text()
check('(a.get("governance") or {}).get("score")' not in sw
      and 'out["finance_score"] = round(float(_sc), 1) if isinstance(_sc, (int, float)) else None' in sw,
      "٥ المسحةُ لا تحتاط بركن الحوكمة درجةً للجودة، وتكتب «لا شيء» صراحةً")
cg = (ROOT / "scripts/audit/candidate_gate.py").read_text()
check("from app.services.market_valuation_sweep import _one" in cg and "_fund_store_put_many" not in cg
      and "record_verdicts" not in cg and "lastgood.save" not in cg,
      "٦ قياسُ المرشَّح يحسب بشيفرته ولا يكتب في أيّ مخزن (D642)")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
