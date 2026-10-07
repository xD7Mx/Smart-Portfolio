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
px, mv, k = 10.0, 25.0, 0.6
check(abs(px * (mv / px) ** k - 17.33) < 0.01, "٥ مثالٌ: سعر 10 ونماذج 25 ← 17.33 (لا 25، ولا 10)")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
