"""D526 — الدرجةُ والسعرُ العادلُ أرقامٌ وعناوين: لا تعريفاتٍ ولا تبريرات (بأمر المالك).

    python3 scripts/audit/no_notes_d526.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src" / "components" / "analysis"
BANNED = {
    "FairValuePanel.tsx": ("r.notes", "r.model_set", "r.excluded", "r?.reason"),
    "HealthPanel.tsx": ("p.why",),
    "StockOpinion.tsx": ("tension.note",),
}
fail = 0
for name, keys in BANNED.items():
    src = (ROOT / name).read_text(encoding="utf-8")
    hit = [k for k in keys if k in src]
    print(("FAIL" if hit else "PASS"), name, "— حواشٍ تُرسَم:" if hit else "— أرقامٌ وعناوين فقط", *hit)
    fail |= bool(hit)
ap = (ROOT / "AnalysisPanel.tsx").read_text(encoding="utf-8")
fv = (ROOT / "FairValuePanel.tsx").read_text(encoding="utf-8")
ok = ("ميزان خبراء الحوكمة</p>" not in ap and 'title="هدف المحللين"' not in fv
      and '["تقدير المحللين", (data.analyst_target ?? f.target_mean_price) != null' in ap)
print(("PASS" if ok else "FAIL"), "D537 لا «ميزان خبراء» في صفحة السهم، وتقديرُ المحللين في «البيانات المالية» وحدها")
fail |= not ok
print(("FAIL" if fail else "PASS") + " D526 · D537 — صفحةُ السهم أرقامٌ في أماكنها")
sys.exit(fail)
