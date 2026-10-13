#!/usr/bin/env python3
"""حارسُ D634: قاعدةُ الإصدار الأوّل للقطاعات التي لم تجتز المعايرة مطبَّقةٌ كما سُجّلت قبل القياس (`docs/ENGINES_V1.md`)."""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

doc = (ROOT / "docs/ENGINES_V1.md").read_text()
an = (ROOT / "backend/app/services/analysis.py").read_text()
sw = (ROOT / "backend/app/services/market_valuation_sweep.py").read_text()
sc = (ROOT / "backend/app/services/market_screener.py").read_text()
sf = (ROOT / "backend/app/services/stars_factors.py").read_text()
ap = (ROOT / "frontend/src/components/analysis/AnalysisPanel.tsx").read_text()

check("القائمةُ المغلقة" in doc or "قائمةٌ مغلقة" in doc and "يُستبعد من ترتيب المختبر بالقيمة" in doc,
      "١ القاعدةُ مسجَّلةٌ في الميثاق التنفيذيّ قبل القياس")
# ‏D702: الوسمُ بالنتيجة لا بالمحلّلين — القطاعاتُ التي ترتيبُ المحرّك المركّب فيها ضعيفٌ بالنتيجة (دون 0.10 أو سالبٌ في نصف)
import sys as _sys
_sys.path.insert(0, str(ROOT / "backend"))
import os as _os, tempfile as _tf
_d = _tf.mkdtemp(); _os.environ.setdefault("LASTGOOD_PATH", _os.path.join(_d, "l.json")); _os.environ.setdefault("SP_STATE_DIR", _d)
from app.services.analysis import V1_UNCALIBRATED as _V, OUTCOME_SECTOR_IC as _IC
secs = set(_V)
want = {k for k, (a, h1, h2) in _IC.items() if a < 0.10 or h1 < 0 or h2 < 0}
check(secs == want and len(secs) == 8 and "السلع الرأسمالية" not in secs and "التطبيقات وخدمات التقنية" not in secs,
      "٢ (D702) القطاعاتُ الموسومة هي ما ضعف فيه المحرّكُ بالنتيجة — لا ما ابتعد عن المحلّلين", str(sorted(secs)))
i628, i634 = an.find("‏D628: رقمٌ نماذجُه"), an.find("‏D634 · الإصدارُ الأوّل")
check(0 < i628 < i634, "٣ الوسمُ بعد D628 — فلا يُحجب رقمٌ لأجل الوسم وحده")
check('"confidence": "منخفضة", "calibrated": False' in an and '"fair_value_calibration_note"' in an,
      "٤ الرقمُ يُنشر بثقةٍ منخفضةٍ وسببٍ مسمّى")
check('"fair_value_calibrated": a.get("fair_value_calibrated")' in sw, "٥ المسحةُ تحفظ الحالة في المخزن")
check('"fair_value_calibrated", "fair_value_calibration_note"' in sc, "٦ والفرزُ يقرؤها من المخزن")
check('r.get("fair_value_calibrated") is not False else None' in sf, "٧ والمختبرُ لا يرتّب بالقيمة ما لم يُعايَر")
check("data.fair_value_calibration_note" in ap, "٨ والسببُ ظاهرٌ مع الرقم")
gt = (ROOT / "scripts/audit/engine_gate.py").read_text()
check("bad_open = {k: v for k, v in bad_sec.items() if k not in V1_UNCALIBRATED}" in gt and '"@@METRICS@@"' in gt,
      "٩ البوابةُ تحكم بالبند ٤ على غير الموسوم وحده، وتُخرج مقاييسَها لحارس التجميد")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
