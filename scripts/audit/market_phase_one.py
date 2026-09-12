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

# ── ٦ · اللقطةُ لا ترفض نفسَها في العطلة ────────────────────────────────
# قِيس على الخادم: «بلا سعرٍ في اللقطة: 40 من 40» والسوقُ مغلقٌ منذ الخميس.
# قاعدةُ الطزاجة صوابٌ داخل الجلسة، وخارجَها تمحو آخرَ إغلاقٍ مسجَّل —
# وهو الرقمُ الصحيحُ الوحيدُ حينها. والجهلُ ليس حكماً (D285).
from app.services import cache, lastgood  # noqa: E402
from app.services import tadawul_market as tmk  # noqa: E402

ROWS = {"2010": {"price": 70.0, "bid": 69.8, "bid_qty": 100}}
cache.set(tmk.STORE_KEY, None, 0)
lastgood.save(tmk.STORE_KEY, {"at": "2026-09-10T15:20:00+00:00", "rows": ROWS})
# «لا لقطةَ حيّة» تُحاكى بالدالّة نفسِها: مخزنُ الحالة يختم زمنَ حفظه هو،
# فلا يشيخ سجلٌّ كُتب قبل لحظة — والمقصودُ قياسُ فرعِ البديل لا المخزن.
tmk.snapshot = lambda: {}                                        # type: ignore[assignment]

import datetime as _d2  # noqa: E402
_real_dt = _d2.datetime


class _SatNow(_real_dt):
    @classmethod
    def now(cls, tz=None):
        return _real_dt(2026, 9, 12, 23, 0)      # سبتٌ — السوق مغلق


class _SunNow(_real_dt):
    @classmethod
    def now(cls, tz=None):
        return _real_dt(2026, 9, 13, 11, 0)      # أحدٌ 11:00 — الجلسة قائمة


_d2.datetime = _SatNow                                           # type: ignore[misc]
rows, live, at = tmk.usable_rows()
check(rows and not live and at,
      "٦ في العطلة يُقرأ آخرُ إغلاقٍ مسجَّل — ويُعلَن أنه ليس حيّاً",
      f"{len(rows)} رمزاً · حيّة={live}")
check(tmk.row_for("2010.SR").get("price") == 70.0,
      "٦ب فيعود السعرُ والعمقُ والسعرُ العادل للعمل يومَي العطلة")

_d2.datetime = _SunNow                                           # type: ignore[misc]
rows2, live2, _ = tmk.usable_rows()
check(not rows2,
      "٦ج وداخلَ الجلسة لا بديلَ عن الحيّ — سعرٌ شائخٌ يُعرض لحظياً كذب",
      f"{len(rows2)} رمزاً")
_d2.datetime = _real_dt                                          # type: ignore[misc]

check(tmk.CLOSE_MAX_DAYS <= 7,
      "٦د وللإغلاق عمرٌ أقصى — لا يُقرأ إغلاقُ شهرٍ مضى", str(tmk.CLOSE_MAX_DAYS))

print(("FAIL" if fail else "PASS") + " D283 — حاكمٌ واحدٌ لطور السوق")
raise SystemExit(fail)
