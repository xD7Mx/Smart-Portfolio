#!/usr/bin/env python3
"""حارسُ D603–D604: رسائلُ تلغرام بلا سطرٍ تبريريّ؛ ولا يُحكَم بتوقّعٍ غيرِ مقارَن؛ وملخّصُ الإغلاق قليلٌ مفيد.

    python3 scripts/audit/digest_d604.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

am = (ROOT / "backend/app/services/advisor_memory.py").read_text()
check("صقر — متابعةُ نصائحك" not in am, "١ لا سطرَ «صقر — متابعةُ نصائحك» — الحدثُ نفسُه أوّلاً")
from app.services.advisor_memory import forecast_comparable, evaluate
# المغذيات كما وصلت: توقّعٌ 2,330.7 مليوناً والأرباعُ الفعلية حول 380–900
check(not forecast_comparable(2330.7e6, [850e6, 700e6, 420e6, 390e6]), "٢ توقّعٌ بستّة أضعاف الأرباع الفعلية لا يُحكَم به")
check(forecast_comparable(800e6, [850e6, 700e6, 760e6]), "٣ والتوقّعُ بحجم الأرباع يُحكَم به كما كان")
check(not forecast_comparable(800e6, [850e6]), "٤ وبلا سجلٍّ كافٍ (ربعان) لا حكم")
a = {"symbol": "2020", "name": "المغذيات", "at": "2099-01-01", "status": "active", "qty": 0, "_res_bad": True,
     "forecast": {"as_of": "2026-06-30", "net_income": 2330.7e6, "mape": 20},
     "tranches": [{"n": 1, "shares": 10, "amount": 1180, "status": "paused", "cond": [{"k": "results", "nth": 1}]}]}
a2, ev = evaluate(a, {"price": 118, "qty": 0, "results": ["2026-06-30"], "ni_latest": 378.7e6,
                      "ni_hist": [850e6, 700e6, 420e6, 390e6]})
check(a2["tranches"][0]["status"] != "paused" and any("تصحيح" in e for e in ev),
      "٥ والإيقافُ السابقُ على توقّعٍ غيرِ مقارَن يُرفع ويُبلَّغ تصحيحُه مرّة", str(ev))
from app.services.market_close_digest import compose
lines = compose({"price": 11234.5, "change_pct": 0.62},
                {"advancers": 160, "decliners": 85, "sectors": [{"sector": "البنوك", "avg_change_pct": 1.2},
                                                                  {"sector": "التأمين", "avg_change_pct": -0.8}]},
                [("الراجحي", 2.1), ("سدافكو", -1.4), ("أرامكو", 0.3)], {"price": 78.4, "change_pct": -1.1},
                [{"headline": "ساما تثبّت الفائدة", "impact": "دعمٌ للبنوك"}, {"headline": "x", "impact": ""}])
check(lines[0].startswith("تاسي أغلق 11,234.50 (+0.62٪) · صاعدة 160 / هابطة 85"), "٦ أوّلُ سطرٍ هو السوقُ نفسُه", lines[0])
check(any(l.startswith("الأقوى: البنوك") and "الأضعف: التأمين" in l for l in lines), "٧ والأقوى والأضعفُ من القطاعات")
check(any(l == "محفظتك: الراجحي +2.10٪" for l in lines), "٨ ومحفظتُك: ما تحرّك 2٪ فأكثر وحده", str(lines))
check(sum(l.startswith("• ") for l in lines) == 1, "٩ والخبرُ بلا أثرٍ لا يُكتب — القليلُ المفيد")
check(compose(None, None, [], None, []) == [], "١٠ وبلا بياناتٍ لا رسالة")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text()
check('job_close_digest, CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=15, minute=35)' in sch, "١١ بعد الإغلاق، أيامَ التداول وحدها")
dg = (ROOT / "backend/app/services/market_close_digest.py").read_text()
check("لم يتداول السوقُ اليوم" in dg and 'last.get("day") == today' in dg, "١٢ مرّةً في اليوم، ولا رسالةَ في عطلةٍ (الإغلاقُ كالأمس)")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
