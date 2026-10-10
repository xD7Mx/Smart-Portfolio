#!/usr/bin/env python3
"""حارسُ D594: (١) لا سعرَ عادلاً من قوائمَ أقدمَ من خمسة عشر شهراً — ولا من المحرّك الاحتياطيّ؛
(٢) عددُ الأسهم من القوائم يُحاكَم إلى القيمة السوقية ÷ السعر (منحةٌ أو تجزئةٌ بعد آخر قوائم).

    python3 scripts/audit/fv_stale_shares_d594.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services.fair_value_models import market_shares_check, blend
notes = []
# المتحدة الدولية كما قِيس: القوائم 25 مليوناً، والسوقُ 6.8 مليار على 27.22
s = market_shares_check(25e6, 6.805e9, 27.22, notes)
check(abs(s - 250e6) < 1e6 and notes, "١ عددُ القوائم المخالفُ للسوق عشراً يُستبدل بعدد السوق ويُعلَن", f"{s/1e6:.0f}M")
notes = []
s = market_shares_check(100e6, 1.0e9 * 1.1, 10.0, notes)
check(s == 100e6 and not notes, "٢ وفرقٌ دون 15٪ (أسهمُ خزينةٍ أو تقريب) لا يُمَسّ — لا تسويةَ على غير عطب")
# ‏D674: منحةُ سهمٍ لكلّ خمسة (1.2×) عطبٌ يُسوّى — كانت تمرّ تحت حدّ المرّة والنصف (قِيس «الرمز» 0.70)
notes = []
s = market_shares_check(100e6, 1.0e9 * 1.2, 10.0, notes)
check(abs(s - 120e6) < 1 and notes, "٢ب ومنحةُ سهمٍ لكلّ خمسة (1.2×) تُسوّى بعدد السوق ويُعلَن (D674)", f"{s/1e6:.0f}M")
notes = []
s = market_shares_check(30e6, 42.9e6 * 52.65, 52.65, notes)
check(abs(s - 42.9e6) < 1e3 and notes, "٢ج و«الرمز» (30 مليوناً في القوائم و42.9 في السوق) يُقيَّم بعدد السوق", f"{s/1e6:.1f}M")
check(market_shares_check(100e6, None, 10.0, []) == 100e6, "٣ وبلا قيمةٍ سوقيةٍ يبقى عددُ القوائم")
stale = {"value": None, "reason": "أحدثُ قوائم منشورة لدينا (سنةُ 2022) أقدمُ من خمسة عشر شهراً — لا تُقيَّم", "price": 7.44}
r = blend(dict(stale), {"value": 3.27, "low": 3.0, "high": 3.5}, "insurance", None)
check(r.get("value") is None, "٤ وامتناعُ القِدَم لا يعوّضه المحرّكُ المُعايَر (سلامة 3.27 بقوائم 2022)", str(r.get("value")))
r2 = blend({"value": None, "reason": "لا إيراد", "price": 7.0}, {"value": 5.0}, "insurance", None)
check(r2.get("value") == 5.0, "٥ أمّا غيابُ النماذج لسببٍ آخر فالمُعايَرُ احتياطُه كما كان")
src = (ROOT / "backend/app/services/fair_value_models.py").read_text()
check("results_announcements import latest" in src and "market_shares_check(shares, _mc" in src,
      "٧ وحين تغيب القيمةُ السوقية فالحَكَمُ آخرُ إعلان نتائج (الربحُ ÷ ربحيةِ السهم بعد المنحة)")
ana = (ROOT / "backend/app/services/analysis.py").read_text()
check('"خمسة عشر شهراً" in str(_new.get("reason")' in ana, "٦ والصفحةُ لا تعرض رقمَ المحرّك القديم حين يمتنع الجديدُ للقِدَم")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
