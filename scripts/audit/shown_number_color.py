#!/usr/bin/env python3
"""اللونُ يتبع الرقمَ المعروضَ لا حقلاً آخر (‏D404).

    python3 scripts/audit/shown_number_color.py

كان صفُّ التقييم في صفحة السهم يُبدّل **الرقمَ** والوسمَ بين حقلَين —
سعرِنا العادل وهدفِ المحللين — ولا يُبدّل **نسبةَ الفرق** التي يُشتقّ
منها اللون. فحين يُعرض هدفُ المحللين يُقرأ `fair_value_upside_pct` وهو
غائب، فيخرج الرقمُ رمادياً محايداً ولو كان الهدفُ أعلى السعرَ بعشرين
في المئة. لونٌ يكذب على قارئه، وهو أخطرُ من رقمٍ ناقص: الرقمُ الناقصُ
يُرى، واللونُ الكاذبُ يُصدَّق بلا قراءة.

ومعه بندٌ من الميثاق: حين يغيب الرقمان لا يُحذف الصفُّ صامتاً — يُقال
«غير متوفّر». فالفراغُ الصامتُ يُقرأ «لا فرق»، والمالكُ يحارب الفراغ.

## ما يُقاس

  ١ · لا سطرَ يعرض رقمَ المحللين احتياطاً ويقرأ نسبةَ حقلنا وحدَها.
  ٢ · وصفُّ التقييم يُعلن «غير متوفّر» حين يغيب الرقمان.
  ٣ · والمعروضُ ونسبتُه يُحسبان مرّةً واحدةً — لا تعبيرٌ شرطيٌّ مكرّرٌ
      ثلاثَ مرّاتٍ في سطر، فذاك ما سهّل نسيانَ أحدِها.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


def _front() -> pathlib.Path | None:
    for base in (ROOT, pathlib.Path("/app"), pathlib.Path.cwd()):
        c = base / "frontend" / "src"
        if c.is_dir():
            return c
    return None


FRONT = _front()
if FRONT is None:
    print("⚠ لا شجرةَ واجهةٍ في هذه البيئة — لم يُقَس")
    sys.exit(0)


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


# ── ١ · لا لونَ من حقلٍ غيرِ الحقلِ المعروض ────────────────────────────
# واستثناءٌ **مُعلَنٌ في الشفرة** لا مسكوتٌ عنه: خانةُ «الفرصة» في صفحة
# الذكاء تُخفّف لونَها بقصدٍ حين تعرض النسبةَ النسبيةَ بعلامة «≈» (‏D230
# بأمر المالك: لا خانةً فارغة). فمن أراد استثناءً كتب `D404-مُعلَن` فوق
# السطر، فيُرى الاستثناءُ في مراجعةِ الفرق ولا يمرّ صامتاً.
MARK = "D404-مُعلَن"

_mismatch = []
for _f in sorted(FRONT.rglob("*.tsx")):
    _raw = _f.read_text("utf-8").splitlines()
    for _i, _ln in enumerate(_strip_comments(_f.read_text("utf-8")).splitlines(), 1):
        if any(MARK in _raw[_j] for _j in range(max(0, _i - 4), min(len(_raw), _i))):
            continue
        # سطرٌ يعرض هدفَ المحللين (احتياطاً أو أصلاً) ويقرأ نسبةَ حقلنا
        # وحدَها: لونٌ من حقلٍ لا يُعرض رقمُه.
        # ══ القاعدةُ بعد أمر المالك: «أرقامٌ فقط» ══ (D404-ب)
        # كان الفحصُ يمنع أيَّ `*_upside_pct` داخل تعبير اللون، وكان
        # وكيلاً صحيحاً حين كان الصفُّ الواحد يعرض حقلَين متبادلَين.
        # ثمّ أمر المالك أن تكون صفحةُ السهم **أرقاماً بأسمائها الثابتة**
        # بلا تبديلِ اسمٍ ولا عبارةِ اعتذار، فصار لكلّ رقمٍ صفُّه.
        # فالمنعُ المطلقُ لم يعد يحرس معنًى — والمعنى الباقي: **لا يلوّن
        # صفٌّ من حقلٍ لا يَعرض رقمَه**. فيُقاس التقابلُ لا الوجود.
        if "className" not in _ln:
            continue
        if ("pos-ink" not in _ln) and ("neg-ink" not in _ln):
            continue
        for _fld, _val in (("fair_value_upside_pct", "fair_value"),
                           ("analyst_target_upside_pct", "analyst_target"),
                           ("rel_upside_pct", "rel_value")):
            if _fld in _ln and _val not in _ln:
                _mismatch.append((_f.name, _i,
                                  f"لونٌ من `{_fld}` بلا `{_val}` في صفّه: "
                                  + _ln.strip()[:55]))
                break
for _n, _i, _t in _mismatch[:8]:
    print(f"     {_n}:{_i}  {_t}")
check(not _mismatch, "١ لا لونَ يتبع حقلاً غيرَ الرقمِ المعروض",
      f"{len(_mismatch)} موضعاً")

# ── ٢ · وغيابُ الرقمَين يُعلَن لا يُحذف ────────────────────────────────
_sv = FRONT / "components" / "market" / "StockView.tsx"
if not _sv.exists():
    print("⚠ لا صفحةَ سهمٍ في هذه البيئة — لم يُقَس")
else:
    T = _sv.read_text("utf-8")
    # ══ والغيابُ شَرطةٌ لا جملة ══ (بأمر المالك)
    # «واجهةٌ رسميةٌ بلا فلسفة… فقط أرقامٌ تظهر». فكانت الشاشةُ تكتب
    # «غير متوفّر» وتُبدّل اسمَ الصفّ إلى «هدف المحللين» حين يغيب رقمُنا
    # — وكلاهما مواربة. فالأسماءُ ثابتةٌ وما غاب يُكتب شَرطة، والاجتهادُ
    # خلف الشاشة لا عليها.
    # والتعليقُ الذي يشرح الإزالةَ يحمل العبارةَ نفسَها، فيُقرأ مخالفةً.
    # فتُزال التعليقاتُ قبل القياس — يُقاس **ما يُعرَض** لا ما يُشرَح.
    _vis = _strip_comments(T)
    _at = _vis.find("السعر العادل")
    _blk = _vis[max(0, _at - 600): _at + 1800] if _at >= 0 else ""
    check("غير متوفّر" not in _blk,
          "٢ صفحةُ السهم: لا عبارةَ اعتذارٍ في موضع رقم")
    check('data.fair_value != null ? `${fmt(data.fair_value)} ﷼` : "—"' in _vis,
          "٢ب والغيابُ شَرطةٌ في مكان الرقم")
    check('? "السعر العادل" : "هدف المحللين' not in _vis,
          "٢ج ولا يُبدَّل اسمُ الصفّ فيَظنّ القارئُ رقماً مكانَ آخر")

    # ── ٣ · والمعروضُ ونسبتُه يُحسبان مرّةً واحدة ──────────────────────
    _reps = sum(1 for _ln in _strip_comments(T).splitlines()
                if _ln.count("data.fair_value != null ?") >= 2)
    check(_reps == 0,
          "٣ ولا تعبيرَ شرطياً مكرّراً في سطرٍ واحدٍ يفرّق الرقمَ عن لونه",
          f"{_reps} سطراً" if _reps else "")

print(("FAIL" if fail else "PASS")
      + " D404 — اللونُ يتبع الرقمَ المعروض، والغيابُ يُعلَن")
sys.exit(fail)
