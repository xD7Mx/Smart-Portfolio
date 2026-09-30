#!/usr/bin/env python3
"""حارسُ D549: قوائمُ كلّ شركةٍ بمفتاحها — عمليتان تحفظان شركتين لا تمحو إحداهما الأخرى.

    python3 scripts/audit/xbrl_perkey_d549.py
"""
import os, sys, tempfile, json
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from datetime import date
from app.services import lastgood, tadawul_xbrl as X
today = date.today().isoformat()
# المفتاحُ الجامعُ القديم يحمل الراجحي بثلاث سنوات
lastgood.save(X.STORE_KEY, {"1120": {"as_of": today, "annual": [{"as_of": "2023-12-31"}], "quarterly": []}})
X.save_symbol("1120", {"as_of": today, "annual": [{"as_of": "2021-12-31"}], "quarterly": []})
X.save_symbol("2222", {"as_of": today, "annual": [{"as_of": "2021-12-31"}], "quarterly": []})
# عمليةٌ أخرى تكتب الجامعَ القديم بنسختها — لا تمسّ مفاتيحَ الشركات
lastgood.save(X.STORE_KEY, {"1120": {"as_of": today, "annual": [{"as_of": "2025-12-31"}], "quarterly": []}})
lastgood.flush()
ann = [p["as_of"] for p in X.for_symbol("1120", "annual")]
check(ann == ["2021-12-31", "2023-12-31"], "١ تاريخُ الشركة في مفتاحها لا يمحوه كاتبٌ للمفتاح الجامع", str(ann))
check([p["as_of"] for p in X.for_symbol("2222", "annual")] == ["2021-12-31"] and "2222" in X._store(),
      "٢ كلُّ شركةٍ بمفتاحها، والمخزنُ الكامل يجمعها")
raw = json.load(open(os.environ["LASTGOOD_PATH"]))
check(f"{X.STORE_KEY}:1120" in raw and "_stale_since" not in raw[f"{X.STORE_KEY}:1120"]["data"],
      "٣ يُحفظ السجلُّ بلا وسمِ «آخر بيانات» المحقون عند القراءة")
print(f"{'FAIL' if fail else 'PASS'} D549 — قوائمُ كلّ شركةٍ بمفتاحها")
sys.exit(fail)
