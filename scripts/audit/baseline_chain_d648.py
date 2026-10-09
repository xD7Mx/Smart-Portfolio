#!/usr/bin/env python3
"""حارسُ D648: سلسلةُ الإصدارات المجمَّدة لا تنكسر — كلُّ أساسٍ جديدٍ يتفوّق على سابقه ولا يتراجع.

حارسُ التجميد (D635) يقارن المرشَّحَ بالأساس، لكنّ الأساسَ نفسَه يُكتب بأمرٍ واحد (`engine_report_save --baseline`):
فلو جُمّد إصدارٌ أضعفُ لصار هو المسطرة وانخفض السقفُ بصمت. فالأساسُ يسمّي سابقَه (`sources.previous`)، وتقريرُ
السابق محفوظٌ ببصمته، ويُقارنان بمقارنة الحارس نفسِها."""
import json, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/audit"))
import engine_freeze_d635 as F   # noqa: E402

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

base = json.loads(F.BASE.read_text(encoding="utf-8"))
ver = base.get("version")
prev = str((base.get("sources") or {}).get("previous") or "")
m = re.search(r"\b([0-9a-f]{12})\b", prev)
if ver == "1.0":
    check(True, "١ الإصدارُ الأوّل لا سابقَ له")
else:
    check(bool(m), f"١ الأساسُ {ver} يسمّي سابقَه ببصمته", prev or "لا sources.previous")
    rep = F.REPORTS / f"{m.group(1)}.json" if m else None
    check(bool(rep and rep.exists()), "٢ وتقريرُ السابق محفوظٌ ببصمته", str(rep) if rep else "")
    if rep and rep.exists():
        old = json.loads(rep.read_text(encoding="utf-8")).get("metrics") or {}
        worse, better = F.compare(old, base.get("metrics") or {})
        check(not worse, f"٣ الأساسُ {ver} لا يتراجع عن سابقه في شيء", "؛ ".join(worse))
        check(bool(better), f"٤ ويتفوّق عليه في مقياسٍ واحدٍ على الأقلّ", f"{len(better)} مقاييس")
own = F.REPORTS / f"{base.get('fingerprint')}.json"
if ver != "1.0":
    same = own.exists() and json.loads(own.read_text(encoding="utf-8")).get("metrics") == base.get("metrics")
    check(same, "٥ ومقاييسُ الأساس هي تقريرُ بصمته نفسُه — قِيس قبل النشر وطابقه الإنتاج")

# المقارنةُ نفسُها تُسقط أساساً أضعف — بحالةٍ معروفةٍ سلفاً
weak = dict(base.get("metrics") or {}, coverage=(base["metrics"]["coverage"] - 0.05))
w, _ = F.compare(base.get("metrics") or {}, weak)
check(any(x.startswith("coverage") for x in w), "٦ وأساسٌ أضعفُ تغطيةً يُكشف تراجعُه")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
