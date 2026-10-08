#!/usr/bin/env python3
"""حارسُ D638: سجلُّ التحقّق يُسجّل مرّةً في اليوم، ويقيس التقديرَ بما حدث بعد الأفق — بأجوبةٍ معروفةٍ سلفاً."""
import datetime as dt, os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
from app.services import engine_ledger as L   # noqa: E402

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

d = tempfile.mkdtemp()
t0 = dt.date(2026, 1, 1)
# خمسُ شركات: تقديرُها صعودٌ 20٪ فتحقّق +10٪ (أغلق نصفَ الفجوة)، وواحدةٌ قدّرنا هبوطَها فهبطت
rows0 = [{"s": f"10{i}0", "sec": "قطاع", "px": 10.0, "fv": 12.0, "conf": "مرتفعة", "cal": True} for i in range(5)]
rows0.append({"s": "2000", "sec": "قطاع", "px": 10.0, "fv": 8.0, "conf": "منخفضة", "cal": False})
check(L.snapshot(rows0, t0, d) == 6, "١ اليومُ يُسجَّل بصفوفه")
check(L.snapshot(rows0, t0, d) == 0, "٢ واليومُ المسجَّلُ لا يُكتب ثانيةً")
later = [dict(r, px=(11.0 if r["s"] != "2000" else 9.0)) for r in rows0]
L.snapshot(later, t0 + dt.timedelta(days=91), d)
rows = L.load(d)
check(len(rows) == 12, "٣ السجلُّ يُقرأ كاملاً", str(len(rows)))
res = L.outcomes(rows, today=t0 + dt.timedelta(days=95), factor=lambda s, a, b: 1.0)
a = (res.get(90) or {}).get("all") or {}
check(a.get("n") == 6 and a.get("hit") == 1.0, "٤ بعد 90 يوماً: ستّةُ تقديرات وكلُّها أصابت الاتجاه", str(a))
check(a.get("gap_closed") == 0.5, "٥ والفجوةُ المُغلَقة: نصفُها (قُدّر +20٪ فتحقّق +10٪)", str(a.get("gap_closed")))
check(180 not in res and 365 not in res, "٦ ولا يُقاس أفقٌ لم يحن — لا رقمَ قبل وقته")
check(set((res[90].get("by_conf") or {})) == {"مرتفعة", "منخفضة"} and res[90]["uncalibrated"]["n"] == 1,
      "٧ والقياسُ مقسومٌ بالثقة وبالمعايرة")
# تجزئةٌ 2:1 للشركة 1000 بين اليومين: سعرُها اللاحق 5.5 — بلا معاملٍ يبدو هبوطاً 45٪ (خطأ)، وبمعامله +10٪ (إصابة)
split_rows = [dict(r, px=5.5) if (r["s"] == "1000" and r["d"] != t0.isoformat()) else r for r in rows]
no_f = L.outcomes(split_rows, today=t0 + dt.timedelta(days=95), factor=lambda s, a, b: 1.0)[90]["all"]["hit"]
with_f = L.outcomes(split_rows, today=t0 + dt.timedelta(days=95), factor=lambda s, a, b: 2.0 if s == "1000" else 1.0)[90]["all"]["hit"]
check(no_f < 1.0 and with_f == 1.0, "٨ وأحداثُ رأس المال تُعدَّل بمعاملها: التجزئةُ لا تُحسب خسارة", f"بلا معامل {no_f} · بمعامله {with_f}")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text()
check('id="engine_ledger_daily"' in sch and 'id="engine_outcomes_monthly"' in sch, "٩ يُسجَّل كلَّ يوم تداولٍ ويُقاس أوّلَ كلّ شهر")
fz = (ROOT / "scripts/audit/engine_freeze_d635.py").read_text()
check("engine_ledger.py" not in fz, "١٠ السجلُّ خارجَ ملفّات المحرّك المجمَّدة — يقيس ولا يغيّر رقماً")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
