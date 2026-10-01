#!/usr/bin/env python3
"""حارسُ D574: قوائمُ الريت الأولية تصل إعلاناً لا تبويبَ قوائم — فتُقرأ منه وتُقدِّم تاريخَ آخر قائمة،
فلا يمتنع القرارُ بقاعدة القِدَم (قِيس: الراجحي ريت «بيانات غير كافية» وقد أعلن قوائمَ يونيو).

    python3 scripts/audit/reit_interim_d574.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import reit_advisor as R
# متنُ إعلان «الخبير ريت» الحقيقيّ (كاشف reit_interim_door)
txt = ("يعلن مدير الصندوق عن إتاحة القوائم المالية الأولية للفترة المنتهية في 30 يونيو 2026م "
       "| البند | الفترة الحالية |\n| صافي الأصول (الموجودات) | 1,267,043,423 |\n"
       "| صافي الربح / ( الخسارة ) | 18,171,636 |\n| عدد الوحدات القائمة في نهاية الفترة | 141,008,848 |\n"
       "| صافي قيمة الوحدة | 8.985 |\n| العائد للفترة % | % 3.59 |")
p = R.parse_statement(txt)
check(bool(p) and p.get("as_of") == "2026-06-30" and abs((p.get("nav") or 0) - 8.985) < 1e-9,
      "١ نهايةُ الفترة وصافي قيمة الوحدة من نصّ الإعلان", str(p))
check(bool(p) and p.get("net_profit") == 18171636 and p.get("units") == 141008848 and p.get("net_assets") == 1267043423,
      "٢ صافي الربح وعددُ الوحدات وصافي الأصول", str(p))
check(R.parse_statement("يعلن مدير الصندوق عن توزيع أرباح نقدية") is None, "٣ إعلانٌ بلا قوائم لا يُختلق منه شيء")

from app.services import lastgood
lastgood.save(R.STORE.format("4340"), {"dists": [{"date": "2026-01-01"}],
              "stmts": [{"as_of": "2025-12-31", "nav": 7.0}, {"as_of": "2026-06-30", "nav": 6.9}]})
ls = R.latest_statement("4340.SR")
check(bool(ls) and ls["as_of"] == "2026-06-30", "٤ أحدثُ قائمةٍ معلنة", str(ls))

src = (ROOT / "backend/app/services/four_scores.py").read_text()
check("latest_statement(" in src and 'feats["_asof"] = _ls["as_of"]' in src,
      "٥ تاريخُ آخر قائمةٍ معلنة يُقدِّم _asof للريت")
for f in ("analysis.py", "governance_engine.py", "peer_distribution.py"):
    s = (ROOT / "backend/app/services" / f).read_text()
    check("symbol=" in s.split("build_company_features(", 2)[-1][:400], f"٦ {f} يمرّر الرمزَ صراحةً")
sys.exit(fail)
