#!/usr/bin/env python3
"""كاتبٌ لا يمحو ما كتبه غيرُه في المخزَن المشترك (D423).

    python3 scripts/audit/lastgood_no_clobber.py

قِيس على خادم المالك في دورةٍ كاملة: الحصادُ أعلن **«قُرئت 176»**، ثمّ
قرأ كاشفُ `xbrl_store_census.py` القرصَ بعدها بدقائق فوجد **صفرَ رمزٍ**
تحت `market:xbrl` — والملفُّ قابلٌ للكتابة، وفيه ‎273 مفتاحاً أخرى،
وكُتب قبل ‎155 ثانية. فالحصادُ كُتب ثمّ **مُحي**.

وسببُه في بنية المخزَن نفسِها: كلُّ عملية تحمل نسخةً كاملةً في الذاكرة
تُقرأ **مرّةً واحدةً** عند أوّل استعمال، و`flush` تكتب تلك النسخةَ
كاملةً فوق الملفّ. فخادمُ التطبيق الطويلُ العمر يقرأ المخزَنَ عند
إقلاعه — قبل الحصاد — ثمّ يكتب لقطةَ أسعارٍ كلَّ خمسِ ثوانٍ، فتنزل
نسختُه القديمةُ فوق الملفّ وتمحو كلَّ مفتاحٍ كتبته عمليةٌ أخرى بعده.

وأثرُه ليس مفتاحاً ضائعاً: **مسحةُ التقييم تعذّرت في ‎269 ورقةً من
‎273**، وخرجت السلسلةُ «لها قوائمُ = 0/60»، وصفرُ سعرٍ عادلٍ للسوق
كلِّه. أي أنّ المحرّكَين كانا يعملان على قوائمَ مُحيت من تحتهما، ولا
ينبّه إلى ذلك شيء.

فالشرطُ المقيسُ هنا: **الكتابةُ تدمج ولا تحلّ محلّ**. عمليةٌ تكتب
مفتاحَها فلا تمسّ مفاتيحَ غيرِها، ولو كانت نسختُها في الذاكرة أقدمَ
من الملفّ.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


if not (BACKEND / "app" / "services" / "lastgood.py").is_file():
    print("⚠ لا مصدرَ للمخزَن في هذه البيئة — لم يُقَس")
    sys.exit(0)

# ── العمليةُ المحكيّة: تقرأ أوّلاً، ثمّ يكتب غيرُها، ثمّ تكتب هي ──────
# وهذا بالحرف ترتيبُ الخادمِ الطويلِ العمر مع حاصدِ القوائم.
_SCRIPT = r"""
import json, os, sys, time
sys.path.insert(0, %(backend)r)
from app.services import lastgood

which = sys.argv[1]
if which == "old":
    lastgood.load("anything")          # يقرأ المخزَنَ إلى ذاكرته أوّلاً
    print("READY", flush=True)
    sys.stdin.readline()               # ينتظر حتى يكتب غيرُه
    lastgood.save("market:quote", {"p": 1})
    lastgood.flush()
else:
    lastgood.save("market:xbrl", {"1010": {"annual": [1, 2, 3]}})
    lastgood.flush()
"""


def _run(path: str, which: str, **kw):
    env = {**os.environ, "LASTGOOD_PATH": path}
    return subprocess.Popen(
        [sys.executable, "-c", _SCRIPT % {"backend": str(BACKEND)}, which],
        env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, **kw)


with tempfile.TemporaryDirectory() as d:
    store = os.path.join(d, "lastgood.json")
    with open(store, "w", encoding="utf-8") as f:
        json.dump({"market:seed": {"data": {"x": 1}, "saved_at": 0}}, f)

    old = _run(store, "old")
    assert old.stdout is not None and old.stdin is not None
    old.stdout.readline()                       # قرأ نسختَه القديمة
    _run(store, "new").wait(60)                 # وكتب غيرُه مفتاحاً جديداً
    old.stdin.write("go\n")
    old.stdin.flush()
    old.wait(60)

    with open(store, encoding="utf-8") as f:
        final = json.load(f)

    check("market:xbrl" in final,
          "١ مفتاحُ عمليةٍ أخرى يبقى بعد كتابةِ عمليةٍ نسختُها أقدم",
          f"المفاتيحُ: {sorted(final)}")
    check("market:quote" in final,
          "١ب ومفتاحُ الكاتبِ الأخيرِ يُكتب — الدمجُ لا يُلغي كتابته")
    check("market:seed" in final,
          "١ج وما كان في الملفّ قبلهما باقٍ")
    _x = (final.get("market:xbrl") or {}).get("data") or {}
    check(bool(_x.get("1010")),
          "١د والمحتوى نفسُه لا الهيكلُ فقط", str(_x)[:80])

print(("FAIL" if fail else "PASS")
      + " D423 — الكتابةُ في المخزَن تدمج ولا تمحو ما كتبه غيرُها")
sys.exit(fail)
