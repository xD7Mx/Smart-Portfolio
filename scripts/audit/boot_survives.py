#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D271 — خطوةٌ واحدةٌ لا تُسقط كلَّ الشاشات، وحالٌ تُقاس لا تُكتَب.
#
# مرّتين رأى المالكُ التطبيقَ **فارغاً**: في D258 من خطأ تعبيرٍ في الجدولة،
# واليومَ من قاعدةٍ تأخّرت لحظةً عن قبول الاتّصالات — وهو المعتادُ حين
# تُبنى الحاويتان معاً. وفي المرّتين لم يكن العطبُ في الخطوة بل في أن
# **دورةَ الحياة تموت بها**: `init_db` و`start_scheduler` مكشوفتان، فيسقط
# معهما كلُّ ما لا يمسّهما — السوقُ والأسعارُ والقوائمُ والفرز.
#
# وأسوأُ من السقوط أن يقول الفحصُ «سليم» وهو ساقط: `"database": "ok"` كانت
# نصّاً ثابتاً، تُطمئن في اللحظة التي يُحتاج فيها التشخيص.
#
#   ٠· قاعدةٌ لا تستجيب: الخادمُ يقوم — ولا يموت
#   ١· وتُعاد المحاولةُ مرّاتٍ محدودةً قبل الاستسلام
#   ٢· وجدولةٌ ترمي استثناءً: الخادمُ يقوم — ويُعلَن توقّفُها
#   ٣· والحالُ تُقاس: قاعدةٌ ميّتةٌ لا تُقرأ «ok»
#   ٤· ولا يقول الفحصُ «سليم» وشيءٌ ساقط
#   ٥· وما نجح يُقال نجاحاً — لا يُعمَّم العطب
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
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


SRC = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")

# ── ٠ · ١ · قاعدةٌ لا تستجيب لا تقتل الخادم ─────────────────────────────
# يُقاس السلوكُ على دورة الحياة نفسِها: تُستبدَل `init_db` بواحدةٍ ترمي
# دائماً، ويُشغَّل الإقلاعُ كما يُشغّله uvicorn.
import main  # noqa: E402

tries = {"n": 0}


async def _dead_db():
    tries["n"] += 1
    raise OSError("Name or service not known")


main.init_db = _dead_db                                          # type: ignore[assignment]
main.DB_BOOT_TRIES = 3
_slept: list = []


async def _fast_sleep(s):
    _slept.append(s)


main._aio.sleep = _fast_sleep                                    # type: ignore[assignment]
main.start_scheduler = lambda: None                              # type: ignore[assignment]

booted = {"ok": False}


async def _boot():
    try:
        async with main.lifespan(main.app):
            booted["ok"] = True
    except BaseException as e:                                    # noqa: BLE001
        booted["err"] = f"{type(e).__name__}: {e}"


asyncio.run(_boot())
check(booted["ok"],
      "٠ قاعدةٌ لا تستجيب: الخادمُ يقوم — ولا تموت دورةُ الحياة",
      str(booted.get("err"))[:70])
# (والانتظاراتُ اللاحقةُ لمهامّ الخلفية — يُقاس تراجعُ القاعدة وحدَه.)
check(tries["n"] == 3 and _slept[:2] == [2, 4],
      "١ وتُعاد المحاولةُ بتراجعٍ محدودٍ قبل الاستسلام",
      f"{tries['n']} محاولات · تراجعٌ {_slept[:2]}")
check(main.DB_BOOT.get("ok") is False and main.DB_BOOT.get("error"),
      "١ب والعجزُ يُسجَّل بنصّه لا يُبتلع", str(main.DB_BOOT.get("error"))[:50])

# ── ٢ · جدولةٌ ترمي استثناءً ─────────────────────────────────────────────
async def _ok_db():
    return None


main.init_db = _ok_db                                            # type: ignore[assignment]


def _boom():
    raise ValueError("day_of_week='sun-thu' مقلوب")               # عطبُ D258 نفسُه


main.start_scheduler = _boom                                     # type: ignore[assignment]
booted2 = {"ok": False}


async def _boot2():
    try:
        async with main.lifespan(main.app):
            booted2["ok"] = True
    except BaseException as e:                                    # noqa: BLE001
        booted2["err"] = f"{type(e).__name__}: {e}"


asyncio.run(_boot2())
check(booted2["ok"],
      "٢ جدولةٌ ترمي استثناءً: الخادمُ يقوم — وهو عطبُ D258 بعينه",
      str(booted2.get("err"))[:70])
check(main.SCHED_BOOT.get("ok") is False,
      "٢ب ويُعلَن توقّفُها لا يُصمَت عنه", str(main.SCHED_BOOT)[:60])

# ── ٣ · ٤ · الحالُ تُقاس لا تُكتَب ───────────────────────────────────────
from app.api.v1.endpoints import health as H  # noqa: E402

HSRC = (ROOT / "backend" / "app" / "api" / "v1" / "endpoints"
        / "health.py").read_text(encoding="utf-8")
check(not re.search(r'"database"\s*:\s*"ok"', HSRC),
      "٣ لا حالَ مكتوبةً في الشيفرة — تُسأل القاعدةُ ويُقال ما رُدّ")

out = asyncio.run(H.health_check())
d = (out.get("data") if isinstance(out, dict) else {}) or {}
svc = d.get("services") or {}
check(svc.get("database") != "ok",
      "٣ب وقاعدةٌ ميّتةٌ في هذا الصندوق لا تُقرأ «ok»", str(svc.get("database"))[:50])
check(d.get("status") != "healthy",
      "٤ ولا يقول الفحصُ «سليم» وشيءٌ ساقط", str(d.get("status")))
check("خلل" in str(out.get("message") or ""),
      "٤ب والرسالةُ تسمّي الساقطَ باسمه", str(out.get("message"))[:60])

# ── ٥ · وما نجح يُقال نجاحاً ─────────────────────────────────────────────
async def _alive():
    return "ok"


H._db_state = _alive                                             # type: ignore[assignment]
main.SCHED_BOOT["ok"] = True
out2 = asyncio.run(H.health_check())
d2 = (out2.get("data") if isinstance(out2, dict) else {}) or {}
check(d2.get("status") == "healthy"
      and (d2.get("services") or {}).get("scheduler") == "ok",
      "٥ وحين يستجيب الجميعُ يُقال سليماً — لا يُعمَّم العطب", str(d2.get("status")))

# ── ٦ · عقدةٌ واحدةٌ أطفأت الفروعَ كلَّها ────────────────────────────────
# قِيس على الخادم: «لقطةُ السوق 0 رمزاً» — ومنها انهار ما بعدها: رابطُ
# صفحة الشركة يُقرأ من اللقطة، وقارئُ XBRL يبني عليه فردَّ «بلا ملفّات»،
# فبقيت القوائمُ صفراً فامتنع السعرُ العادل. والسببُ أن اللقطةَ مجدوَلةٌ
# في ساعات التداول وحدَها، فحاويةٌ تُعاد مساءَ الخميس تبقى فارغةً للأحد.
MAIN = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
check("_warm_tadawul" in MAIN and "_aio.create_task(_warm_tadawul())" in MAIN,
      "٦ اللقطةُ تُملأ عند الإقلاع إن كانت فارغة — لا تنتظر ساعةَ تداول")
check("if rows:\n                return" in MAIN,
      "٦ب ولا تُعاد إن كانت عامرة — لا نداءَ بلا حاجة")
check("_warm_betas" in MAIN and "_aio.create_task(_warm_betas())" in MAIN,
      "٦ج والبيتا تُبنى عند الإقلاع إن غابت — لا تُنتظَر دورةٌ شهرية")
SCH3 = (ROOT / "backend" / "app" / "scheduler"
        / "scheduler.py").read_text(encoding="utf-8")
check('id="sector_betas_weekly"' in SCH3,
      "٦د ودورتُها أسبوعيةٌ لا شهرية — شهرٌ بلا بيتا شهرٌ بثقةٍ مخصومة")
check("create_task(_warm_tadawul())" in MAIN
      and MAIN.index("create_task(_warm_tadawul())")
      < MAIN.index("create_task(_warm_betas())"),
      "٦ه واللقطةُ قبل البيتا — الترتيبُ يتبع التبعية")

# ── ٧ · نوعٌ خاطئٌ من منتِجٍ واحدٍ يردّ المعاملةَ كلَّها (D320) ───────────
# قِيس على خادم المالك: `invalid input for query argument $8: '2026-09-14'
# (expected a datetime.date …)` — ثمّ سطرٌ بعده: `Startup snapshot
# skipped: This Session's transaction has been rolled back`. فقناةُ
# أخبارٍ أطفأت لقطةَ الإقلاع. والعلاجُ حاجزُ نوعٍ عند **الكتابة**، لا
# ثقةٌ بكلّ منتِج. ويُقاس بالسلوك على الدالّة نفسِها.
import datetime as _dt
import importlib as _il

_ce = _il.import_module("app.services.content_engine")
_ac = _il.import_module("app.services.argaam_calendar")

_s = _ce._as_dt("2026-09-14")
check(isinstance(_s, _dt.datetime) and _s.tzinfo is not None
      and (_s.year, _s.month, _s.day) == (2026, 9, 14),
      "٧ تاريخٌ نصٌّ يُحوَّل لحظةً واعيةً بمنطقتها — لا يُسلَّم للقاعدة نصّاً",
      repr(_s))
_n = _ce._as_dt("ليس تاريخاً")
check(_n is None, "٧ب ومجهولُ التاريخ يُكتب بلا تاريخ — لا لحظةَ اليومِ كذباً",
      repr(_n))
_naive = _ce._as_dt(_dt.datetime(2026, 9, 14, 10, 0))
check(_naive is not None and _naive.tzinfo is not None,
      "٧ج ولحظةٌ بلا منطقةٍ تُوسَم بمنطقتها — لا مقارنةَ واعٍ بغافل")
check(_ce._as_dt(_dt.date(2026, 9, 14)) is not None
      and _ce._as_dt(None) is None,
      "٧د ويومٌ مجرّدٌ يُقبل، والفراغُ يبقى فراغاً")

# ── ٧ه · والمنتِجُ يتكلّم لغةَ العقد: لحظةٌ ومفتاحُ `company` ─────────────
# قِيس: `_match_company` كان يُكتب في `symbol` والمستهلِكُ يقرأ `company`
# — فيسقط الرمزُ المطابَقُ صامتاً ويُخزَّن الخبرُ بلا شركة.
class _M:
    def group(self, i):                                           # noqa: D102
        return {1: "2026", 2: "09", 3: "14"}[i]


_d = _ac._news_dt(_M())
check(isinstance(_d, _dt.datetime) and _d.tzinfo is not None,
      "٧ه وتاريخُ خبر «أرقام» لحظةٌ من عنده — لا نصٌّ يُرفَض عند الكتابة",
      repr(_d))
check(_ac._news_dt(None) is None, "٧و وغيابُه يبقى غياباً")
_NEWS_SRC = (ROOT / "backend" / "app" / "services"
             / "argaam_calendar.py").read_text(encoding="utf-8")
check('"company": hit[0] if hit else None' in _NEWS_SRC,
      "٧ز والرمزُ المطابَقُ يُكتب بالمفتاح الذي يقرؤه المستهلِك")

print(("FAIL" if fail else "PASS") + " D271 — الإقلاعُ لا يموت، والحالُ تُقاس")
raise SystemExit(fail)
