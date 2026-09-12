#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D283 — ساعةٌ ثانيةٌ لا تعرف اليوم: «قبل الافتتاح» يومَ السبت.
#
# رأى المالكُ في بطاقة نبض السوق «قبل الافتتاح» وهو يومُ عطلة، وسمّاه غيرَ
# منطقيّ — وهو كذلك. والجذرُ **منتِجان لمعنًى واحد**: `market_phase.py`
# حاكمٌ يعرف الأيّامَ ومزادَي الافتتاح والإغلاق ويقيسه الفحصُ دقيقةً
# دقيقة، و`ai_content._market_phase` نسخةٌ ثانيةٌ بثلاثة شروطٍ ساذجةٍ على
# الساعة وحدَها: أقلُّ من العاشرة ⇒ «قبل الافتتاح» — في السبت، وفي منتصف
# الليل، وفي كلّ يومٍ لا جلسةَ فيه.
#
#   ٠· طورُ النبض من الحاكم الواحد لا من ساعةٍ ثانية
#   ١· والجمعةُ والسبتُ عطلةٌ في كلّ ساعات اليوم
#   ٢· ولا يُقال «قبل الافتتاح» إلا في نافذته من يوم تداول
#   ٣· والعطلةُ تُميَّز عن «قبل جلسة اليوم» — حالتان لا واحدة
#   ٤· ولا يُوصَف افتتاحٌ لن يقع اليوم
#   ٥· وكلُّ حالٍ لها نصٌّ — لا حالَ بلا ترجمة
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import datetime as dt  # noqa: E402
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


from app.services import ai_content as ac  # noqa: E402
from app.services.market_phase import market_phase  # noqa: E402

# الأحدُ 2026-09-13 · الجمعةُ 2026-09-11 · السبتُ 2026-09-12
SUN, FRI, SAT = dt.date(2026, 9, 13), dt.date(2026, 9, 11), dt.date(2026, 9, 12)


def at(d: dt.date, h: int, m: int = 0) -> str:
    return ac._market_phase(dt.datetime(d.year, d.month, d.day, h, m))


# ── ١ · العطلةُ عطلةٌ في كلّ ساعة ───────────────────────────────────────
off = {at(d, h) for d in (FRI, SAT) for h in range(0, 24)}
check(off == {"weekend"},
      "١ الجمعةُ والسبتُ عطلةٌ في كلّ ساعات اليوم — لا «قبل افتتاح»", str(sorted(off)))

# ── ٢ · ٤ · نافذةُ ما قبل الافتتاح ──────────────────────────────────────
check(at(SUN, 9, 40) == "pre_open" and at(SUN, 9, 20) != "pre_open"
      and at(SUN, 10, 5) != "pre_open",
      "٢ و«قبل الافتتاح» في نافذته وحدَها من يوم تداول",
      f"09:20={at(SUN, 9, 20)} · 09:40={at(SUN, 9, 40)} · 10:05={at(SUN, 10, 5)}")
check(at(SUN, 11) == "intraday" and at(SUN, 15, 5) == "intraday",
      "٢ب والجلسةُ تشمل مزادَ الإغلاق", f"15:05={at(SUN, 15, 5)}")
check(at(SUN, 16) == "post_close",
      "٢ج وبعد الجرس حصيلةُ إغلاق", at(SUN, 16))

# ── ٣ · حالتان لا واحدة ─────────────────────────────────────────────────
check(at(SUN, 3) == "pre_session" and at(SAT, 3) == "weekend",
      "٣ والعطلةُ تُميَّز عن «قبل جلسة اليوم» — فرقٌ يقرؤه المالك",
      f"أحد 03:00={at(SUN, 3)} · سبت 03:00={at(SAT, 3)}")

# ── ٠ · الحاكمُ واحد ────────────────────────────────────────────────────
SRC = (ROOT / "backend" / "app" / "services"
       / "ai_content.py").read_text(encoding="utf-8")
check("from app.services.market_phase import market_phase" in SRC,
      "٠ الطورُ يُقرأ من الحاكم الواحد")
check("if hm < 10 * 60:" not in SRC,
      "٠ب ولا ساعةَ ثانيةً تحكم بشروطٍ من عندها")
# وتطابقُ السلوك: ما قاله الحاكمُ «مغلق» لا يقوله النبضُ «قبل الافتتاح».
bad = []
for d, dow in ((SUN, 0), (FRI, 5), (SAT, 6)):
    for h in range(0, 24):
        ruler = market_phase(dow, h * 60)
        got = at(d, h)
        if ruler == "closed" and got in ("pre_open", "intraday"):
            bad.append(f"{d}:{h}→{got}")
check(not bad, "٠ج ولا ساعةَ يقول فيها الحاكمُ «مغلق» والنبضُ «مفتوح»",
      "؛ ".join(bad[:4]))

# ── ٥ · كلُّ حالٍ لها نصّ ───────────────────────────────────────────────
states = {at(d, h) for d in (SUN, FRI, SAT) for h in range(24)}
missing = [s for s in states if s not in ac._PHASE_AR]
check(not missing, "٥ كلُّ حالٍ لها نصٌّ عربيّ — لا حالَ بلا ترجمة", str(missing))
check(all(ac._rule_brief(None, None, None, phase=s) for s in states),
      "٥ب وكلُّ حالٍ تُنتج قراءةً — لا فراغَ في البطاقة")
wk = ac._tasi_verb(0.8, "weekend")
check("افتتاح" not in wk and "أغلق" in wk,
      "٤ ولا يُوصَف افتتاحٌ لن يقع — تُقال حصيلةُ آخر إغلاقٍ بصيغة الماضي", wk)

print(("FAIL" if fail else "PASS") + " D283 — حاكمٌ واحدٌ لطور السوق")
raise SystemExit(fail)
