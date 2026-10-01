#!/usr/bin/env python3
"""حارسُ D571: المراجعةُ الأسبوعية — صفٌّ لكلّ شركةٍ من موقفها، وتجميعٌ بالإجراء، وجاهزُ التنفيذ،
ومواعيدُ أسبوعين، وتنبيهُ التشتّت، والربطُ بصقر والجدول الأسبوعي وتقسيمُ رسالة تلغرام.

    python3 scripts/audit/advisor_weekly_d571.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from datetime import date
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import advisor as A
from app.services import advisor_weekly as W
T = date(2026, 10, 1)
SAD = {"symbol": "2270", "name": "سدافكو", "held": True, "qty": 22, "value": 4045.8, "price": 183.9, "decision": "شراء",
       "rsi": 19.9, "trend": "هابط", "sma200": 216.05, "w52_low": 183.9, "eps_g": -24.9, "target": 3.5, "weight": 1.22,
       "remaining": 7548.92, "capital": 331277.74, "results_due": "2026-10-30",
       "advice": {"الدفعات": [{"n": 1, "الحالة": "تحقّق شرطُها — جاهزة"}, {"n": 2, "الحالة": "تنتظر شرطها"}]}}
REIT = {"symbol": "4340", "name": "الراجحي ريت", "held": True, "qty": 1007, "value": 7784, "price": 7.73, "decision": "شراء",
        "trend": "هابط", "target": 2.8, "weight": 2.35, "remaining": 1491.67, "capital": 331277.74, "is_reit": True, "sma200": 8.08,
        "reit": {"nav": 8.385, "premium": -7.8, "trend": "صاعد", "nav_change": 2.6, "next_expected": "2026-12-01"}}
FULL = {"symbol": "1120", "name": "الراجحي", "held": True, "value": 27000, "price": 63, "decision": "شراء", "target": 8.4,
        "weight": 8.4, "remaining": 0, "capital": 331277.74}
fs = [SAD, REIT, FULL]
rows = [W.row(f, A.stance(f), T) for f in fs]
by = {r["symbol"]: r for r in rows}
check(by["2270"]["action"].startswith("انتظر") and by["2270"]["next"]["shares"] == 13 and "2026-10-30" in by["2270"]["event"]
      and by["2270"]["ready"] == [1], "١ سدافكو: انتظر الشرط، والدفعةُ التالية 13 سهماً، وموعدُ النتائج، والأولى جاهزة", str(by["2270"]))
check(by["4340"]["action"] == "أضف على دفعتين" and by["4340"]["next"]["when"] == "الآن" and "2026-12-01" in by["4340"]["event"],
      "٢ الراجحي ريت: أضف — الأولى الآن، وموعدُ التوزيع القادم", str(by["4340"]["event"]))
check(by["1120"]["action"] == "احتفظ" and by["1120"]["next"] is None, "٣ بلغ هدفَه ⇒ احتفظ بلا دفعة")
up = W.upcoming(fs, T)
check(not any("2026-12-01" in u for u in up) and W.upcoming(fs, date(2026, 10, 20)) and any("2026-10-30" in u for u in W.upcoming(fs, date(2026, 10, 20))),
      "٤ مواعيدُ الأسبوعين وحدها: نتائجُ 30 أكتوبر تظهر من 20 أكتوبر، وتوزيعُ ديسمبر لا يظهر الآن", str(up))
r = {"date": T.isoformat(), "rows": rows, "upcoming": ["سدافكو: موعدُ النتائج حتى 2026-10-30"], "summary": None,
     "portfolio": {"capital": 331277.74, "cash": 249147.84, "to_targets": 9040.6, "count": 14, "spread": True}}
txt = W.render(r)
order = [txt.index(h) for h in ("أضف على دفعتين:", "انتظر الشرط ثمّ أضف على دفعات:", "احتفظ:")]
check(order == sorted(order) and "جاهزٌ للتنفيذ" in txt and "سدافكو: الدفعة 1" in txt and "فوق 12" in txt
      and "مواعيدُ الأسبوعين القادمين" in txt and "القرارُ لك" in txt,
      "٥ الورقة: مجمّعةٌ بالإجراء بترتيب الأولوية، وجاهزُ التنفيذ أوّلاً، وتنبيهُ التشتّت، والمواعيد")
check(W.asks_weekly("أعطني مراجعة الأسبوع") and W.asks_weekly("المراجعة الاسبوعية للمحفظة") and not W.asks_weekly("راجع سدافكو"),
      "٦ «مراجعة الأسبوع» تصل الورقة")
R = lambda p: (ROOT / p).read_text(encoding="utf-8")
sch, chat, mem, wk = R("backend/app/scheduler/scheduler.py"), R("backend/app/services/ai_chat.py"), R("backend/app/services/advisor_memory.py"), R("backend/app/services/advisor_weekly.py")
check('day_of_week="thu"' in sch and 'id="advisor_weekly_thu"' in sch and "advisor_weekly.asks_weekly(question)" in chat
      and "> 3800" in mem and "set_scope(pid, False)" in wk and "remember(f, st, active_pid())" in wk,
      "٧ الخميسَ مساءً لكلّ محفظةٍ بعزلها، والنصائحُ تُحفظ للمتابعة، ورسالةُ تلغرام تُقسَّم دون 4096 حرفاً")
print(f"{'FAIL' if fail else 'PASS'} D571 — المراجعة الأسبوعية")
sys.exit(fail)
