#!/usr/bin/env python3
"""حارسُ D647: سجلُّ التحقّق يختم كلَّ صفٍّ ببصمة الشيفرة العاملة لا بصمةِ الأساس المجمَّد، ويحكم على كلّ إصدارٍ بأيّامه.

العطب: `_fingerprint()` قرأ `engine_baseline.json` — فلمّا نُشر الإصدارُ الثاني (8b766b22b3e7) صارت أيّامُه تُنسب إلى
1.0 (47f14f50eddf)، ويختلط الحكمان في أوّل تقريرٍ بعد 90 يوماً."""
import datetime as dt, os, pathlib, shutil, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts/audit"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
from app.services import engine_identity as I, engine_ledger as L   # noqa: E402
import engine_freeze_d635 as F                                        # noqa: E402

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

frz = tuple(f.relative_to(F.ROOT).as_posix() for f in F.FILES)
check(I.FILES == frz, "١ قائمةُ ملفّات المحرّك هي قائمةُ حارس التجميد حرفاً بحرف",
      f"زائد {set(I.FILES) - set(frz) or '—'} · ناقص {set(frz) - set(I.FILES) or '—'}")
check(I.fingerprint() == F.fingerprint(), "٢ والبصمةُ هي بصمةُ الحارس", f"{I.fingerprint()} · {F.fingerprint()}")

# الحاوية: ‎./backend مربوطٌ على ‎/app — فالملفّاتُ في ‎<مجلد>/app/services بلا «backend/»
box = pathlib.Path(tempfile.mkdtemp())
for rel in I.FILES:
    dst = box / rel.removeprefix("backend/")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / rel, dst)
check(I.fingerprint(box) == F.fingerprint(), "٣ وفي تخطيط الحاوية (‎/app) البصمةُ نفسُها")
(box / "app/services/analysis.py").write_text("# تغيير\n", encoding="utf-8")
check(I.fingerprint(box) != F.fingerprint(), "٤ وتغيّرُ ملفٍّ واحدٍ من المحرّك يغيّرها")

base = ROOT / "scripts/audit/engine_baseline.json"
src = (ROOT / "backend/app/services/engine_ledger.py").read_text(encoding="utf-8")
fn = src[src.index("def _fingerprint"):src.index("def current_rows")]
check("engine_baseline" not in fn and "engine_identity" in fn, "٥ السجلُّ لا يقرأ بصمةَ الأساس المجمَّد")

d = tempfile.mkdtemp()
t0 = dt.date(2026, 1, 1)
L.snapshot([{"s": "1010", "sec": "قطاع", "px": 10.0, "fv": 12.0, "conf": "مرتفعة", "cal": True}], t0, d)
fp = (L.load(d) or [{}])[0].get("fp")
check(fp == F.fingerprint(), "٦ الصفُّ المكتوبُ يحمل بصمةَ الشيفرة العاملة", f"{fp}")

# يومان بإصدارين: الأوّل أصاب والثاني أخطأ — فلا يُخفي أحدُهما الآخر
rows = [{"d": t0.isoformat(), "fp": "v1", "s": "1010", "px": 10.0, "fv": 12.0, "conf": "مرتفعة", "cal": True},
        {"d": (t0 + dt.timedelta(days=1)).isoformat(), "fp": "v2", "s": "2020", "px": 10.0, "fv": 12.0, "conf": "مرتفعة", "cal": True},
        {"d": (t0 + dt.timedelta(days=91)).isoformat(), "fp": "v2", "s": "1010", "px": 11.0},
        {"d": (t0 + dt.timedelta(days=92)).isoformat(), "fp": "v2", "s": "2020", "px": 9.0}]
res = L.outcomes(rows, today=t0 + dt.timedelta(days=100), factor=lambda s, a, b: 1.0)
by = (res.get(90) or {}).get("by_fp") or {}
check(by.get("v1", {}).get("hit") == 1.0 and by.get("v2", {}).get("hit") == 0.0,
      "٧ والحكمُ مقسومٌ بالإصدار: لكلٍّ أيّامُه", str(by))
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
check('v.get("by_fp")' in sch, "٨ والتقريرُ الشهريُّ للمالك يعرض كلَّ إصدارٍ بسطره")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
