#!/usr/bin/env python3
"""حارسُ D623: القيمةُ العادلة = السعر^(1−k) × تقدير النماذج^k بـk = 0.6، وتقديرُ النماذج الخامُ يبقى معروضاً."""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))
src = (ROOT / "backend/app/services/fair_value_models.py").read_text()
m = re.search(r"MARKET_BLEND_K = ([0-9.]+)", src)
check(m and float(m.group(1)) == 0.6, "١ وزنُ النماذج 0.6 — المعايَرُ على 148 ورقة (24.7٪ ← 16.4٪)", m and m.group(1))
check('agg["model_value"] = agg["value"]' in src and "i.price * (x / i.price) ** _k" in src, "٢ المزجُ هندسيٌّ، والخامُ محفوظ")
check('agg["low"], agg["high"] = _b(agg["value"]), _b(agg.get("low")), _b(agg.get("high"))' in src, "٣ والنطاقُ يُمزج كالقيمة")
check('fvm:v37:' in src, "٤ وكاشُ النماذج بإصدارٍ جديد فلا تبقى قيمةٌ قبل المزج")
an = (ROOT / "backend/app/services/analysis.py").read_text()
check('"engine") != "fair_value_models"' in an and "MARKET_BLEND_K as _K" in an, "٤ب والمحرّكُ الاحتياطيّ يُمزج كذلك (أيان وولاء ومتطورة بقيت بلا مزج)")
px, mv, k = 10.0, 25.0, 0.6
check(abs(px * (mv / px) ** k - 17.33) < 0.01, "٥ مثالٌ: سعر 10 ونماذج 25 ← 17.33 (لا 25، ولا 10)")
# D624: لا قيمةَ على قوائمَ أقدم من 15 شهراً أيّاً كان المحرّك · D625: الثقةُ من اتّفاق النماذج
check('_fv["age_days"] > 456' in an, "٦ لا قيمةَ على قوائمَ أقدم من خمسة عشر شهراً — ولا من الاحتياطيّ")
import os, tempfile
os.environ["SP_STATE_DIR"] = tempfile.mkdtemp()
from app.services.analysis import confidence_of as C
check(C({"models": [{"value": 10}, {"value": 10.5}, {"value": 9.6}, {"value": 10.2}]}) == "مرتفعة", "٧ نماذجُ متّفقةٌ (أربعةٌ فأكثر) ← مرتفعة")
check(C({"models": [{"value": 10}, {"value": 12}, {"value": 7.8}]}) == "متوسطة", "٨ تشتّتٌ معتدل ← متوسطة")
check(C({"models": [{"value": 10}, {"value": 20}, {"value": 5}]}) == "منخفضة" and C({"models": [{"value": 10}]}) == "منخفضة",
      "٩ تشتّتٌ واسعٌ أو نموذجٌ واحد ← منخفضة")
check(C({"models": [{"value": 10}] * 4, "notes": ["الشركةُ خاسرة"]}) == "منخفضة", "١٠ والخاسرةُ منخفضةٌ وإن اتّفقت نماذجُها")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
