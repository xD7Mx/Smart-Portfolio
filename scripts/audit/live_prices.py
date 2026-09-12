#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D260 — اللحظيةُ زمنٌ لا لون: ميزانيةُ طزاجةٍ مقيسةٌ لا موعودة.
#
# قال المالك: «أريد الأسعارَ لحظيةً للتطبيق بالكامل، ولسانُ تاسي يومض
# عند التغيّر». والوميضُ **مبنيٌّ أصلاً** (حدثٌ لا حالة: يشتعل بلون
# الاتّجاه ثمّ يعود أبيض) — لكنه لا يشتعل إن لم يصل رقمٌ جديد. فالعطبُ
# في **زمن الوصول** لا في اللون، ولا يُصلَح بلونٍ أشدّ.
#
# وسلسلةُ التأخير حلقاتٌ متتابعة، وأبطؤها يحكم: جدولةُ اللقطة ← عمرُها
# المقبول ← مذكّرةُ إنعاش الفرز ← تخزينُ المؤشّر ← استعلامُ الواجهة.
# فتُقاس كلُّها بحدٍّ معلَن، وتُقاس **علاقتُها** ببعض: لقطةٌ تُجدَّد كلَّ
# دقيقةٍ وتُقبل حتى ربع ساعةٍ تعني أن الشاشةَ قد تعرض سعرَ ربعِ ساعةٍ
# مضت وتسمّيه لحظياً.
#
#   ٠· تخزينُ المؤشّر ≤ 20 ثانية
#   ١· وعمرُ لقطة السوق المقبول ≤ 5 دقائق
#   ٢· ومذكّرةُ إنعاش الفرز ≤ 60 ثانية
#   ٣· واستعلامُ اللسان ≤ 30 ثانية
#   ٤· واللقطةُ تُجدَّد كلَّ دقيقةٍ في الجلسة
#   ٥· والعمرُ المقبول لا يقلّ عن دورة التجديد (وإلا فراغٌ بين نبضتين)
#   ٦· والوميضُ حدثٌ: أوّلُ قراءةٍ لا تومض، والثباتُ لا يومض
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import pathlib  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.services import market_screener as ms  # noqa: E402
from app.services import tadawul_market as tm  # noqa: E402

check(tm.INDEX_TTL <= 20, "٠ تخزينُ رقم المؤشّر ≤ 20 ثانية", f"{tm.INDEX_TTL}s")
check(tm.MAX_AGE_SECONDS <= 300, "١ وعمرُ لقطة السوق المقبول ≤ 5 دقائق",
      f"{tm.MAX_AGE_SECONDS}s")
check(ms.REFRESHED_TTL <= 60, "٢ ومذكّرةُ إنعاش الفرز ≤ 60 ثانية",
      f"{ms.REFRESHED_TTL}s")

tick = (ROOT / "frontend" / "src" / "components" / "common"
        / "MarketTicker.tsx").read_text(encoding="utf-8")
# حاصلُ الضرب كما هو مكتوب (‏20 * 1000 · 5 * 60 * 1000) — لا تخمينَ
# لموضع الألف. (صُحّح: أوّلُ صياغةٍ قرأت «5 * 60» فحسبتها ‎0 ثانية.)
iv = []
for expr in re.findall(r"refetchInterval:\s*([0-9 */]+)", tick):
    ms_ = 1
    for n in re.findall(r"\d+", expr):
        ms_ *= int(n)
    iv.append(ms_)
check(bool(iv) and min(iv) <= 30_000, "٣ واستعلامُ اللسان ≤ 30 ثانية",
      f"{min(iv) // 1000}s" if iv else "لم يُقرأ")

# ── ٤ · ٥ · دورةُ التجديد مقابلَ العمر المقبول ──────────────────────────
jobs: list = []
from app.scheduler import scheduler as sch  # noqa: E402

_real = sch._scheduler.add_job
sch._scheduler.add_job = lambda f, t=None, **k: (jobs.append((k.get("id"), t)),
                                                 _real(f, t, **k))[1]
sch._scheduler.start = lambda *a, **k: None                      # type: ignore[assignment]
sch.settings.SCHEDULER_ENABLED = True                            # type: ignore[attr-defined]
sch.start_scheduler()
trig = next((t for i, t in jobs if i == "tadawul_snapshot"), None)
gap = None
if trig is not None:
    t0 = datetime(2026, 9, 13, 11, 0, tzinfo=timezone(timedelta(hours=3)))
    a = trig.get_next_fire_time(None, t0)
    b = trig.get_next_fire_time(a, a + timedelta(seconds=1)) if a else None
    gap = (b - a).total_seconds() if (a and b) else None
check(gap == 60, "٤ لقطةُ السوق تُجدَّد كلَّ دقيقةٍ في الجلسة",
      f"{gap}s" if gap else "لم يُقرأ المُطلِق")
check(gap is not None and tm.MAX_AGE_SECONDS >= gap,
      "٥ والعمرُ المقبول لا يقلّ عن دورة التجديد — وإلا فراغٌ بين نبضتين",
      f"عمر {tm.MAX_AGE_SECONDS}s · دورة {gap}s")

# ── ٦ · الوميضُ حدثٌ لا حالة ────────────────────────────────────────────
# يُقاس بالشرط المكتوب في المكوّن: أوّلُ قراءةٍ ليست تغيّراً، والثباتُ
# ليس تغيّراً — وإلا ومض الشريطُ كلَّ استعلامٍ فصار ضجيجاً.
check("was == null || was === p" in tick or "was === p" in tick,
      "٦ الوميضُ حدثٌ: أوّلُ قراءةٍ لا تومض، والثباتُ لا يومض")
css = (ROOT / "frontend" / "src" / "styles" / "globals.css").read_text(encoding="utf-8")
# الكتلةُ متداخلةُ الأقواس، فيُقرأ ما بين اسمها ونهايتها لا أوّلُ قوسٍ
# يُغلق. (صُحّح: الصياغةُ الأولى توقّفت عند أوّل `}` فلم تبلغ ‎100%.)
_blk = css.split("@keyframes mk-flash-up", 1)[-1].split("@keyframes", 1)[0]
m = re.search(r"100%\s*\{\s*color:\s*(#fff|white)", _blk)
check(bool(m), "٦ب ويعود الرقمُ أبيضَ بعد الوميض — اللونُ للتغيّر لا للمستوى")

print(("FAIL" if fail else "PASS") + " D260 — ميزانيةُ الطزاجة")
raise SystemExit(fail)
