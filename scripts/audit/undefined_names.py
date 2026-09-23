#!/usr/bin/env python3
"""لا اسمَ يُقرأ بعد حذفه — في الخادم كلِّه (D428).

    python3 scripts/audit/undefined_names.py

قِيس بتشغيل اللجنة كاملةً لا حرّاسِها متفرّقين: `market_screener.py` يقرأ
`_fv` وقد حُذف في D386 حين صار حقلاً باسمه. فرفع `NameError` في **كلّ صفّ**،
و`_enrich_fundamentals` تُنادى بلا مِمْسَك — فسقط بناءُ جدول السوق كلُّه
**ستّةَ أيام** (من 17 سبتمبر) وخُدم آخرُ نسخةٍ سليمةٍ قبلها. وكانت اللجنةُ
حمراءَ عليه طوالَها (‏`score_source.py` يسقط)، وكنتُ أقرأ حرّاساً منفردةً
خضراءَ ولا أقرأ اللجنة.

ومسحُ الصنف كلِّه وجد ثلاثةً أخرى من العائلة نفسِها:

  · `analysis.py` — `logger` اسمٌ محلّيٌّ يُستورَد لاحقاً في الدالّة، فالإشارةُ
    إليه **داخل مِمْسَك الخطأ** ترفع: يفشل «أرقام» فيسقط تحليلُ السهم كلُّه.
  · `market_data.py` — `_raw` دالّةٌ محلّيةٌ في مسارٍ ويُناديها مسارٌ آخر.
  · `valuation.py` — كتلةٌ ميّتةٌ بعد `return` تقرأ أسماءً غيرَ معرّفة.

وهذا صنفٌ لا تكشفه الفحوصُ السلوكيةُ إلا إن مرّت بالسطر عينِه، والمسارُ
الذي يمرّ به قد يكون مسارَ خطأٍ نادراً. فيُمسَح الخادمُ كلُّه ساكناً.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
_APP = None
for c in (ROOT / "backend" / "app", pathlib.Path("/app/app")):
    if c.is_dir():
        _APP = c
        break
if _APP is None:
    print("⚠ لا شفرةَ خادمٍ في مسارٍ معروف — لم يُقَس")
    sys.exit(0)

try:
    import pyflakes  # noqa: F401
except ModuleNotFoundError:
    # ولا يُحسَب غيابُ الأداة نجاحاً — يُعلَن أنّ الصنفَ لم يُمسَح
    print("⚠ pyflakes غيرُ منصَّبٍ في هذه البيئة — لم يُقَس"
          " (‏python3 -m pip install pyflakes)")
    sys.exit(0)

r = subprocess.run([sys.executable, "-m", "pyflakes", str(_APP)],
                   capture_output=True, text=True)
lines = (r.stdout or "").splitlines()
bad = [ln for ln in lines
       if "undefined name" in ln or "referenced before assignment" in ln]
files = len(list(_APP.rglob("*.py")))
ok = not bad
print(f"{'PASS' if ok else 'FAIL'} ١ لا اسمَ غيرَ معرّفٍ في {files} ملفّاً"
      + ("" if ok else f" — {len(bad)} موضعاً"))
for ln in bad[:25]:
    try:
        ln = str(pathlib.Path(ln.split(":", 1)[0]).relative_to(ROOT)) + ":" \
            + ln.split(":", 1)[1]
    except ValueError:
        pass
    print(f"     {ln}")
print(("FAIL" if bad else "PASS")
      + " D428 — لا اسمَ يُقرأ بعد حذفه في الخادم كلِّه")
sys.exit(1 if bad else 0)
