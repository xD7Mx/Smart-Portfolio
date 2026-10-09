#!/usr/bin/env python3
"""حارسُ D654: طريقُ النشر يشمل مزامنةَ القرار بعد كلّ نشرٍ يبدّل إصدارَ المحرّك، والمزامنةُ لا تكتب إلا للمخالِف."""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0
def check(ok, label):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}")
doc = (ROOT / "docs/ENGINES_V2.md").read_text(encoding="utf-8")
src = (ROOT / "scripts/audit/decision_page_sync_door.py").read_text(encoding="utf-8")
check("decision_page_sync_door.py" in doc and "parity_gate.py" in doc, "١ طريقُ النشر يسمّي مزامنةَ القرار ثمّ بوابةَ رقم اليوم")
i_off = src.find("cache.set, lastgood.save = (lambda *a, **k: None), (lambda *a, **k: None)")
i_diff = src.find("if pl and dl and pl != dl:")
i_on = src.find("cache.set, lastgood.save = _set, _save")
i_loop = src.find("for s, pl, dl in diff:")
check(0 < i_off < i_diff < i_on < i_loop, "٢ الصفحاتُ تُحسب أوّلاً بلا كتابة، ولا يُكتب إلا حكمُ المخالِفة بعد ذلك")
check("fair_value" not in src.split("cache.set, lastgood.save = _set, _save")[1], "٣ ولا تمسّ المزامنةُ رقماً — حكمُ الصفحة وحده")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
