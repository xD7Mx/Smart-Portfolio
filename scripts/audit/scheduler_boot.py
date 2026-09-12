#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D258 — جدولةٌ لا تُقلع تُسقط التطبيقَ كلَّه، لا نفسَها.
#
# ## ما وقع
# أضفتُ مهمّةً بـ`day_of_week="sun-thu"`. وترتيبُ الأيام في APScheduler
# ‏mon=0…sun=6، فالمدى ‎6 ← 3 **مقلوب** فيرفع ValueError. وموضعُ النداء
# في `lifespan` — فسقط الإقلاعُ كلُّه: «Application startup failed».
# ورأى المالكُ **تطبيقاً فارغاً**: الواجهةُ تُخدَم والخلفيةُ لا تُقلع.
#
# ## لماذا لم تكشفه اللجنة
# لأن كلّ فحوصنا تستورد **خدماتٍ**، ولا واحدَ منها يُقلع **التطبيق**.
# والوحدةُ التي تعمل وحدَها قد تُسقط المجموعَ عند التركيب — وهذا صنفُ
# عطبٍ لا يُكشف إلا بتشغيل نقطة الدخول نفسِها.
#
#   ٠· الجدولةُ تُقلع بلا استثناء — كلُّ مُطلِقٍ يُبنى فعلاً
#   ١· وكلُّ مهمّةٍ لها زمنُ تشغيلٍ قادمٌ محسوب (لا مُطلِقٌ ميت)
#   ٢· ولا مدًى مقلوبٌ في أيّام الأسبوع (القاعدةُ التي انكسرت)
#   ٣· والمهامُّ المسجَّلةُ تُغطّي ما أضفناه هذا اليوم
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ.setdefault("SCHEDULER_ENABLED", "true")

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


from app.scheduler import scheduler as sch  # noqa: E402

# لا تُشغَّل حلقةٌ ولا يُفتح اتّصال: يُعطَّل `start` وحدَه، ويبقى تسجيلُ
# المهامّ وبناءُ مُطلِقاتها كما هو في الإقلاع الحقيقيّ.
jobs: list = []
_real_add = sch._scheduler.add_job


def _add(func, trigger=None, **kw):
    jobs.append((kw.get("id"), trigger))
    return _real_add(func, trigger, **kw)


sch._scheduler.add_job = _add                                    # type: ignore[assignment]
sch._scheduler.start = lambda *a, **k: None                      # type: ignore[assignment]
sch.settings.SCHEDULER_ENABLED = True                            # type: ignore[attr-defined]

err = None
try:
    sch.start_scheduler()
except Exception as e:                                            # noqa: BLE001
    err = f"{type(e).__name__}: {e}"
check(err is None, "٠ الجدولةُ تُقلع بلا استثناء — وإلا سقط التطبيقُ كلُّه",
      err or f"{len(jobs)} مهمّة")

now = datetime.now(timezone(timedelta(hours=3)))
dead = []
for jid, trig in jobs:
    try:
        nxt = trig.get_next_fire_time(None, now) if trig is not None else None
    except Exception as e:                                        # noqa: BLE001
        dead.append(f"{jid}: {type(e).__name__}")
        continue
    if trig is not None and nxt is None:
        dead.append(f"{jid}: بلا زمنٍ قادم")
check(not dead, "١ ولكلّ مهمّةٍ زمنُ تشغيلٍ قادمٌ محسوب", "؛ ".join(dead[:3]))

src = (ROOT / "backend" / "app" / "scheduler" / "scheduler.py").read_text(encoding="utf-8")
ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
bad = []
for m in re.finditer(r'day_of_week=[\x22\x27]([a-z]{3})-([a-z]{3})[\x22\x27]', src):
    a, b = m.group(1), m.group(2)
    if a in ORDER and b in ORDER and ORDER.index(a) > ORDER.index(b):
        bad.append(m.group(0))
check(not bad, "٢ ولا مدًى مقلوبٌ في أيّام الأسبوع (‏mon=0…sun=6)",
      "؛ ".join(bad[:3]))

ids = {jid for jid, _ in jobs}
want = {"tadawul_snapshot", "risk_free_weekly", "sector_betas_monthly",
        "argaam_results_daily", "directory_sync_weekly"}
missing = want - ids
check(not missing, "٣ والمهامُّ الجديدةُ مسجَّلةٌ فعلاً",
      "غاب: " + "، ".join(sorted(missing)) if missing else f"{len(ids)} مهمّة")

print(("FAIL" if fail else "PASS") + " D258 — الجدولةُ تُقلع")
raise SystemExit(fail)
