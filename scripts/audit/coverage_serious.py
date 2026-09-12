#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D280 — «أيُّ عجزٍ لإظهار نتيجة شركةٍ خذلان»، وامتناعٌ بسببٍ بطَل.
#
# قال المالك إنّ محرّكَي الدرجة والسعر العادل يجب أن يغطّيا **جميعَ**
# الشركات، فالمصدرُ رسميٌّ وفيه كلُّ ما ينقصنا. فقِيس العجزُ فوُجد بابان:
#
#   · ‎28 شركةً تمتنع **بالتصميم** في ملفّ النطاق: ‎25 تأميناً بسببٍ مكتوبٍ
#     نصُّه «غير متاحةٍ في ياهو» — وقد **بطَل السبب**: القوائمُ رسميةٌ من
#     تداول وفيها حقوقُ الملكية وصافي الربح، وهما مدخَلا نموذج العائد
#     الفائض المستعمَل للبنوك أصلاً. وثلاثٌ «غير مصنّفة» وقطاعاتُها
#     معروفةٌ في نطاق التطبيق نفسِه.
#   · ودفعةُ القوائم اثنتا عشرةَ شركةً في الليلة: ‎23 ليلةً لتغطية السوق،
#     والدرجةُ بلا قوائمَ رسميةٍ طوالها.
#
#   ٠· لا شركةَ بلا نموذجٍ في ملفّ النطاق
#   ١· والتأمينُ يُقيَّم بما تنشره القوائمُ الرسمية
#   ٢· وسقفُ ثقته «متوسط» لا «مرتفع» — النسبةُ المجمّعة غيرُ منشورة
#   ٣· ولا قطاعَ «غير مصنّف» يبقى بلا تصنيفٍ وهو معروفٌ عندنا
#   ٤· والدفعةُ تكفي لتغطيةٍ في أيّامٍ لا أسابيع
#   ٥· ولا تُرتهَن التغطيةُ بلقطةٍ قد تتأخّر
#   ٦· والعجزُ الباقي يُقاس ويُسمّى — لا يُصمَت عنه
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import json  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


UNI = json.loads((ROOT / "backend" / "app" / "data" / "fv_config"
                  / "market_universe.json").read_text(encoding="utf-8"))
COMPANIES = UNI["companies"]

# ── ٠ · لا شركةَ بلا نموذج ──────────────────────────────────────────────
no_model = [c["code"] for c in COMPANIES if c["model"] == "abstain"]
check(not no_model,
      "٠ لا شركةَ تمتنع بالتصميم — العجزُ يُقاس لا يُفترَض سلفاً",
      f"{len(no_model)} شركة" if no_model else f"{len(COMPANIES)} شركة")

# ── ١ · ٢ · التأمين ─────────────────────────────────────────────────────
ins = [c for c in COMPANIES if c["tadawul_sector"] == "التأمين"]
check(ins and all(c["model"] == "excess_return" for c in ins),
      "١ والتأمينُ يُقيَّم بالعائد الفائض — حقوقٌ وصافي ربحٍ من القوائم الرسمية",
      f"{len(ins)} شركةَ تأمين")
check(all(c["confidence_ceiling"] in ("medium", "low") for c in ins),
      "٢ وسقفُ ثقته دون «مرتفع» — النسبةُ المجمّعة والقيمةُ الكامنة غيرُ منشورتين",
      str(sorted({c["confidence_ceiling"] for c in ins})))

# ── ٣ · لا «غير مصنّف» وهو معروفٌ عندنا ─────────────────────────────────
from app.data.market_universe import MARKET_UNIVERSE  # noqa: E402

unknown = [c["code"] for c in COMPANIES
           if c["tadawul_sector"] == "غير مصنّف"
           and (MARKET_UNIVERSE.get(c["code"]) or {}).get("sector")]
check(not unknown,
      "٣ ولا شركةَ «غير مصنّفة» وقطاعُها معروفٌ في نطاق التطبيق", str(unknown))

# ── ٤ · ٥ · دفعةُ القوائم ───────────────────────────────────────────────
SCH = (ROOT / "backend" / "app" / "scheduler"
       / "scheduler.py").read_text(encoding="utf-8")
check("missing[:40]" in SCH,
      "٤ والدفعةُ أربعون لا اثنتا عشرة — تغطيةٌ في أيّامٍ لا أسابيع")
check('id="xbrl_statements_night"' in SCH,
      "٤ب ودفعةٌ ثانيةٌ ليليةٌ تختصر المدّةَ إلى النصف")
check("list(snapshot() or {}) or list(main_market(MARKET_UNIVERSE))" in SCH,
      "٥ ولا تُرتهَن التغطيةُ بلقطةٍ قد تتأخّر — النطاقُ من السوق الرئيسة")

# ── ٦ · العجزُ الباقي يُسمّى ────────────────────────────────────────────
check('logger.info("XBRL: {} مقروءةٌ من {} — الباقي {}"' in SCH,
      "٦ والباقي يُطبع في السجلّ كلَّ ليلة — لا يُعرَف بالمسبار")

# وسببُ الامتناع القديمُ لا يبقى مكتوباً بعد أن بطَل.
ENG = (ROOT / "backend" / "app" / "services" / "fair_value_engine"
       / "engine.py").read_text(encoding="utf-8")
check("غير متاحة في ياهو" not in ENG or 'route == "abstain"' in ENG,
      "٦ب وفرعُ الامتناع يبقى للحالة الحقيقية لا لقطاعٍ كاملٍ سلفاً")

print(("FAIL" if fail else "PASS") + " D280 — تغطيةٌ جادّةٌ لكلّ شركة")
raise SystemExit(fail)
