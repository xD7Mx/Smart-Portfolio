#!/usr/bin/env python3
"""حارسُ D559: مؤتمراتُ المحلّلين من إعلانات «تداول» — الموعدُ الميلاديُّ لا الهجريّ، والحالةُ،
ورابطُ الحضور والعرض، وتصلُ المفكرةَ وعقلَ التطبيق والتقريرَ وصفحةَ الشركة.

    python3 scripts/audit/investor_calls_d559.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from datetime import date
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import investor_calls as C
T = date(2026, 9, 1)
# متونُ «تداول» الحقيقية (كاشف investor_calls_door)
azm = C.parse("""Announcement Detail | Saudi Azm for Communication and Information Technology Co. (the "Company") announces the organization of a conference call with investors and financial analysts, in cooperation with Al Rajhi Capital, to discuss the Company's financial results for the fiscal year ended 30 June 2026G, on Monday 25/03/1448H, corresponding to 07/09/2026G, at 11:00 AM (KSA time).
Those wishing to participate may register and join the call via the following link: https://alrajhibank.webex.com/weblink/register/r274683d43f5b5aae4ff019349bd05d83. For inquiries contact IR@azm.com
The Capital Market Authority and Saudi Exchange take no responsibility for the contents https://x.saudiexchange.sa/""", "2026-09-02", T)
check(azm["date"] == "2026-09-07" and azm["time"] == "11:00 AM" and azm["status"] == "upcoming"
      and azm["join"].startswith("https://alrajhibank.webex.com/") and not azm["join"].endswith(".") and azm["deck"] is None and azm["period"] == "السنة المالية 2026",
      "١ قبل المؤتمر: الميلاديُّ لا الهجريّ، والساعة، ورابطُ التسجيل", str(azm))
jo = C.parse("""Announcement Detail | Jabal Omar Development Company announces that it held an earnings conference call with investors and financial analysts to discuss the interim financial results for the period ended 30 June 2026 (six months), on 05/03/1448 AH, corresponding to 18/08/2026 AD.
The presentation shared during the phone call can be viewed through the following link:
https://jabalomar.com.sa/en/disclosure/""", "2026-08-19", T)
check(jo["date"] == "2026-08-18" and jo["status"] == "held" and jo["join"] is None and jo["deck"] == "https://jabalomar.com.sa/en/disclosure/"
      and jo["period"] == "الفترة المنتهية في 2026-06-30" and C._period_ar("its 2Q 2026 earnings call") == "الربع الثاني 2026"
      and C._period_ar("results for Q2 and the first half of 2026") == "النصف الأول 2026",
      "٢ بعده: عُقد، والعرضُ التقديميُّ من موقع الشركة", str(jo))
from app.services import lastgood
lastgood.save(C.STORE, {"calls": {"1": {"id": "1", "symbol": "7211", **azm}, "2": {"id": "2", "symbol": "4250", **jo}}})
check([c["id"] for c in C.for_symbol("4250")] == ["2"] and [c["id"] for c in C.upcoming(today=T)] == ["1"],
      "٣ لكلّ شركةٍ مؤتمراتُها، والقادمُ في السوق")
check(any("آخرُ مؤتمرٍ للمحلّلين عُقد 2026-08-18" in x for x in C.lines("4250")), "٤ سطرُ عقل التطبيق", str(C.lines("4250")))
R = lambda p: (ROOT / p).read_text(encoding="utf-8")
mk, am, qr, sch = R("backend/app/api/v1/endpoints/market.py"), R("backend/app/services/app_mind.py"), R("backend/app/services/quarter_report.py"), R("backend/app/scheduler/scheduler.py")
cp, doc = R("frontend/src/pages/CompanyPage.tsx"), R("frontend/src/components/reports/CompanyReportDocument.tsx")
check('@router.get("/investor-calls")' in mk and '"type": "مؤتمر المحللين"' in mk and "investor_calls import lines" in am
      and "from app.services.investor_calls import lines" in qr and "r.insights" in doc and "<InvestorCalls symbol=" in cp
      and 'id="investor_calls_evening"' in sch,
      "٥ يصل: صفحةَ الشركة، والمفكرة، وعقلَ التطبيق ورأيَ الذكاء، والتقرير — ويُحدَّث مساءً")
print(f"{'FAIL' if fail else 'PASS'} D559 — مؤتمرات المحلّلين")
sys.exit(fail)
