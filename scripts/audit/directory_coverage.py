#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D241 — كلُّ ورقةٍ في السوق لها اسمٌ عربيٌّ وقطاعٌ مصنَّف.
#
# كشفه المالكُ بسؤاله عن ثمانيةِ رموزٍ بلا مضاعفات: ثلاثةٌ منها بلا صفٍّ
# في الدليل أصلاً — فتُعرض بأسمائها الإنجليزية (‏Petrochem · Buruj ·
# Dur Hospitality) في واجهةٍ عربية، ويمتنع عنها **السعرُ العادل** ولو
# جاءت مضاعفاتُها لأن قطاعَها «غير مصنّف». فالنقصُ في الدليل يُعطّل
# محرّكاً كاملاً بصمت.
#
# ويُقاس على الكون المعروض لا على الدليل: لكلّ رمزٍ في السوق الرئيسيّ
#   ١· اسمٌ عربيّ (لا رمزٌ ولا حروفٌ لاتينية)
#   ٢· قطاعٌ من لافتاتِ الدليل المعروفة — لا لافتةٌ مخترعةٌ لواحد
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import pathlib
import re
import sys
import tempfile as _tf

# مخزنُ حالةٍ معزول قبل أيّ استيراد — قاعدةُ اللجنة (‏D160): لا فحصٌ
# يلمس بيانات المالك المتتبَّعة، ولو كان قارئاً محضاً.
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.data.company_sectors import SYMBOL_TO_SECTOR_AR as SEC  # noqa: E402
from app.data.market_universe import MARKET_UNIVERSE as MU  # noqa: E402
from app.data.saudi_directory import SAUDI_DIRECTORY as DIR  # noqa: E402
from app.data.universe import main_market  # noqa: E402

MAIN = main_market(MU)
LATIN = re.compile(r"[A-Za-z]")

no_row = [s for s in MAIN if s not in DIR]
check(not no_row, "١ كلُّ رمزٍ في السوق الرئيسيّ له صفٌّ في الدليل",
      f"{len(no_row)} بلا صفّ: {' '.join(no_row[:8])}" if no_row else f"{len(MAIN)} رمزاً")

# الاسمُ المعروضُ عربيٌّ: يُقرأ كما تقرؤه الشاشة (‏name_ar من الكون).
latin = [s for s in MAIN if LATIN.search(str((MU.get(s) or {}).get("name_ar") or s))]
check(not latin, "٢ ولا اسمَ لاتينياً يُعرض في واجهةٍ عربية",
      " · ".join(f"{s}: {(MU.get(s) or {}).get('name_ar')}" for s in latin[:5]))

bare = [s for s in MAIN if str((MU.get(s) or {}).get("name_ar") or "") == s]
check(not bare, "٣ ولا اسمَ هو الرمزُ نفسُه", " ".join(bare[:8]))

nosec = [s for s in MAIN if not SEC.get(s)]
check(not nosec, "٤ ولا قطاعٍ غيرِ مصنَّف — وإلا امتنع السعرُ العادل صامتاً",
      " ".join(nosec[:8]))

# ══ قطاعاتٌ دون عتبة النظائر — تُقال ولا تُعَدّ عطباً ══
# ظننتُ لافتةً تخصّ رمزاً واحداً قرينةَ خطأٍ إملائيّ يفصل شركةً عن
# قطاعها. فقِيس، فكانت صحيحة: «المنتجات المنزلية والشخصية» فيها شركةٌ
# واحدةٌ مدرَجة (‏4165 الماجد للعود) — صفةٌ في السوق لا خطأٌ في دليلنا.
# لكنها **أثرٌ يجب أن يُعرف**: قطاعٌ دون خمسِ نظائرَ يمتنع فيه السعرُ
# العادل دائماً وبحقّ، فتُطبَع قائمتُه حتى لا يُفسَّر امتناعُه عطباً.
from collections import Counter  # noqa: E402
from app.services.relative_value import MIN_PEERS  # noqa: E402
counts = Counter(SEC[s] for s in MAIN if SEC.get(s))
thin = sorted((n, lbl) for lbl, n in counts.items() if n <= MIN_PEERS)
print(f"…  قطاعاتٌ يمتنع فيها السعرُ العادل لقلّة النظائر ({len(thin)}):")
for n, lbl in thin:
    print(f"     {lbl} — {n} شركة")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
