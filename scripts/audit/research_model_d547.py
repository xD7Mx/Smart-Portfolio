#!/usr/bin/env python3
"""حارسُ D547: نموذجُ الأبحاث — توقّعٌ مدرَّبٌ على تاريخ الشركة بسيرٍ إلى الأمام، وربعٌ رابعٌ
مشتقّ، وقراءةٌ تاريخية، ولا نظرَ للأمام.

    python3 scripts/audit/research_model_d547.py
"""
import os, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import research_model as R
from app.services import quarter_report as Q

V = {3: 100, 6: 120, 9: 90, 12: 140}
q, a = [], []
for y in range(2021, 2027):
    g = 1.1 ** (y - 2021)
    for m, d in ((3, "03-31"), (6, "06-30"), (9, "09-30")):
        if y == 2026 and m > 6:
            continue
        q.append({"as_of": f"{y}-{d}", "col": 0, "revenue": V[m] * g})
    if y < 2026:
        a.append({"as_of": f"{y}-12-31", "revenue": sum(V.values()) * g, "eps": 2 * g})
s = R.quarter_series(q, a, "revenue")
check(dict(s).get("2021-12-31") == 140.0, "١ الربعُ الرابعُ مشتقٌّ = السنويُّ − الأرباعِ الثلاثة")
f = R.forecast(q, a, "revenue")
check(f and f["as_of"] == "2026-09-30" and abs(f["value"] - 90 * 1.1 ** 5) < 0.01 and f["mape"] == 0.0,
      "٢ التوقّعُ بالطريقة الأدقّ على تاريخ الشركة يصيب سلسلةً موسميةً نامية", str(f and f["value"]))
check(f and f["tested"] >= 4 and f["hit"] == 100, "٣ ويُعلَن خطؤها التاريخيّ وصدقُ اتّجاهها وعددُ الأرباع المختبرة")
leak = [dict(p) for p in q]
leak[-1]["revenue"] = 10 ** 9                    # الربعُ المتوقَّع نفسُه لا يدخل في توقّعه
check(R.expected_at(leak, a, "revenue", "2026-06-30") == R.expected_at(q, a, "revenue", "2026-06-30"),
      "٤ لا نظرَ للأمام: توقّعُ ربعٍ لا يتأثّر بقيمته")
se = R.seasonality(s)
check(se and se["strongest"] == "الرابع", "٥ الموسمية: أقوى الأرباعِ الرابع", str(se))
gr = R.growth(a)
check(gr.get("rev_cagr") == 10.0, "٦ النموُّ المركّبُ للإيراد عبر السنوات المنشورة", str(gr.get("rev_cagr")))
months = [(f"{2010 + k // 12}-{k % 12 + 1:02d}", 10 * 1.01 ** k) for k in range(24)]
ph = R.price_history(months, {m: 100.0 for m, _ in months}, [["2010-05-01", 1.0], ["2011-05-01", 1.1]])
check(ph.get("max_dd") == 0.0 and ph.get("tasi_cagr") == 0.0 and ph["div"]["years_paid"] == 2,
      "٧ السهمُ منذ أوّل شهر: المركّبُ مقابلَ تاسي وأقصى تراجعٍ وسنواتُ التوزيع")
t = Q.table(q, bank=False, annual=a)
row = next(r for r in t["rows"] if r["key"] == "revenue")
check(abs(row["expected"] - 120 * 1.1 ** 5) < 0.01, "٨ عمودُ «توقّعاتنا» في التقرير من النموذج المدرَّب", str(row["expected"]))
print(f"{'FAIL' if fail else 'PASS'} D547 — نموذجُ الأبحاث بعمق تاريخ الشركة")
sys.exit(fail)
