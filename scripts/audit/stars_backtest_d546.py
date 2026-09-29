#!/usr/bin/env python3
"""حارسُ D546: نجومُ تاسي منذ 2015 — اختبارٌ شهريٌّ بما كان معلوماً في وقته، ومفاتيحُ المعايير.

    python3 scripts/audit/stars_backtest_d546.py
"""
import os, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from datetime import date
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import stars_backtest as B
from app.services import tasi_stars as S
from app.services import stars_factors as F

# ثلاثون سهماً بنموٍّ شهريٍّ ثابت (الأعلى رقماً الأسرع) وتاسي مستوٍ — الزخمُ مستمرّ
months, ym = [], "2013-01"
while ym <= date.today().isoformat()[:7]:
    months.append(ym); ym = B._ym_add(ym, 1)
px, uni = {}, {}
for i in range(30):
    s = f"S{i:02d}"
    g = (i - 15) / 1000
    px[s] = {"m": [[m, round(10 * (1 + g) ** k, 6)] for k, m in enumerate(months)], "div": []}
    uni[s] = {"sector": "A" if i % 2 else "B", "sharia": "NON_COMPLIANT" if i == 29 else "COMPLIANT", "shares": 1e6}
data = {"px": px, "tasi": {m: 1000.0 for m in months}}
fam_off = set(B.FAMILY_KEYS) - {"momentum"}
r = B.run(data, uni, {}, fam_off | {"large"})
tr = r.get("track") or []
check(tr[:1] == [{"d": "2014-12", "s": 100.0, "t": 100.0}] and len(tr) > 1 and tr[1]["d"] == "2015-01"
      and tr[-1]["d"] == months[-1],
      "١ السجلُّ يبدأ بناءً آخرَ ديسمبر 2014 وأوّلُ شهرٍ مقيسٍ يناير 2015 ويبلغ الشهرَ الجاري",
      f"{tr[:2]} … {tr[-1:]}")
check(r["total"] > 0 and r["tasi_total"] == 0 and r["beat_pct"] == 100 and r["months"] == len(tr) - 1,
      "٢ بالزخم وحده تُختار الأسرعُ نموّاً فتتفوّق كلَّ شهرٍ على تاسي المستوي", f"{r['total']} · {r['beat_pct']}%")
check("S29" not in r["last_pick"] and "S28" in r["last_pick"],
      "٣ مفتاحُ الشرعية مفعّلاً: غيرُ المتوافق لا يدخل السلّة", str(r["last_pick"][:5]))
r2 = B.run(data, uni, {}, fam_off | {"large", "sharia"})
check("S29" in r2["last_pick"], "٤ مفتاحُ الشرعية مطفأً: يدخل بترتيبه", str(r2["last_pick"][:3]))
rows = [("2024-03-30", {"net_income": 1.0})]
check(B._known(rows, "2024-02-29") is None and B._known(rows, "2024-03-31") == {"net_income": 1.0},
      "٥ القوائمُ لا تُرى قبل نشرها (السنويةُ بعد 90 يوماً من نهاية السنة)")
st = B._statements.__doc__ or ""
check(B.LAG_ANNUAL == 90 and "range=max&interval=1mo&events=div" in open(B.__file__, encoding="utf-8").read(),
      "٦ أسعارٌ شهريةٌ كاملةُ المدى بتوزيعاتها، ومهلةُ نشر السنويّ 90 يوماً")
# مفاتيحُ الترتيب الحيّ
row = {"symbol": "1120", "fair_value_upside_pct": 150.0, "fair_value_conf": "منخفضة", "finance_score": 80,
       "stmt_age_days": 400, "red_lines": 1, "sharia": "NON_COMPLIANT"}
check(not S.eligible(row) and S.eligible(row, frozenset({"outlier", "fresh", "redlines", "sharia"})),
      "٧ كلُّ شرطٍ مفتاح: الشاذُّ والقوائمُ والخطوطُ الحمراء والشرعيةُ تُطفأ فرادى")
check(S.parse_off("sharia,momentum,bogus") == frozenset({"sharia", "momentum"}),
      "٨ المفاتيحُ المجهولةُ تُهمَل ولا تُمرَّر")
cands = [{"symbol": str(k), "ret_12m": float(k), "finance_score": 50, "sector": "A"} for k in range(5)]
only_m = F.score_all(cands, set(), set(B.FAMILY_KEYS) - {"momentum"})
check(only_m["4"]["score"] == 100.0 and only_m["0"]["score"] == 0.0,
      "٩ العائلةُ المطفأةُ لا تدخل الدرجة — والمفعّلةُ بأوزانٍ متساوية", f"{only_m['4']['score']} · {only_m['0']['score']}")
print(f"{'FAIL' if fail else 'PASS'} D546 — نجومُ تاسي منذ 2015 ومفاتيحُ المعايير")
sys.exit(fail)
