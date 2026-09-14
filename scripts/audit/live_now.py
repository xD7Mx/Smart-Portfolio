#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D289 — «لا أقبل بتأخير 15 ثانية»: اللحظيةُ في المصدر لا في الشاشة.
#
# كان النبضُ في الواجهة ‎15 ثانية، و**اللقطةُ نفسُها مجدوَلةٌ كلَّ دقيقة**:
# فالتأخيرُ الحقيقيُّ دقيقةٌ في أسوأ الحال، والشاشةُ تسأل أربعَ مرّاتٍ عن
# الرقم نفسِه. وإسراعُ الشاشة وحدَه لا يُنتج لحظيةً — يُنتج ضجيجاً.
#
# فأُضيفت **طزاجةٌ عند الطلب**: النداءُ يوقظ تجديداً إن شاخت اللقطةُ، ثمّ
# يعود فوراً بما عنده. وخطرُها الوحيدُ إغراقُ المصدر، فثلاثةُ قيود:
#
#   ٠· مئةُ طلبٍ متوازٍ ⇒ نداءُ مصدرٍ **واحد**
#   ١· ولقطةٌ طازجةٌ لا تُوقظ شيئاً
#   ٢· وشائخةٌ تُوقظ تجديداً واحداً
#   ٣· والسوقُ مغلقٌ ⇒ لا إيقاظَ أصلاً
#   ٤· والشاشةُ لا تُحبَس في انتظار الشبكة
#   ٥· والنبضُ في الواجهة أسرعُ من سقف الشيخوخة
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import datetime as dt  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.api.v1.endpoints import market as EP  # noqa: E402
from app.services import cache, tadawul_market as M  # noqa: E402

_real = dt.datetime
calls = {"n": 0}


async def _slow():
    calls["n"] += 1
    await asyncio.sleep(0.6)                      # مصدرٌ بطيءٌ عمداً
    cache.set(M.STORE_KEY,
              {"at": _real.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "rows": {"2010": {"price": 70.5, "bid": 70.4, "bid_qty": 900,
                                 "ask": 70.6, "ask_qty": 700}}}, 600)
    return {"count": 1}


M.refresh = _slow                                                # type: ignore[assignment]


class _Sess(_real):
    @classmethod
    def now(cls, tz=None):
        return _real(2026, 9, 13, 11, 0) if tz is None else _real.now(tz)


class _Closed(_real):
    @classmethod
    def now(cls, tz=None):
        return _real(2026, 9, 12, 11, 0) if tz is None else _real.now(tz)


def _stale(sec: int = 40) -> None:
    cache.set(M.STORE_KEY,
              {"at": (_real.now(dt.timezone.utc)
                      - dt.timedelta(seconds=sec)).isoformat(),
               "rows": {"2010": {"price": 70.0, "bid": 69.9, "bid_qty": 800,
                                 "ask": 70.1, "ask_qty": 600}}}, 600)


def _reset() -> None:
    M._last_kick = 0.0
    M._inflight = None
    calls["n"] = 0


async def main() -> None:
    M.datetime = _Sess                                           # type: ignore[misc]

    # ── ٠ · مئةُ طلبٍ ⇒ نداءٌ واحد ──────────────────────────────────────
    _reset(); _stale()
    woke = [M.ensure_fresh() for _ in range(100)]
    await asyncio.sleep(0.9)
    check(calls["n"] == 1 and sum(woke) == 1,
          "٠ مئةُ طلبٍ متوازٍ ⇒ نداءُ مصدرٍ واحد — لا إغراق",
          f"{calls['n']} نداء · أوقظ {sum(woke)}")

    # ── ١ · طازجةٌ لا تُوقظ ─────────────────────────────────────────────
    before = calls["n"]
    M.ensure_fresh()
    await asyncio.sleep(0.2)
    check(calls["n"] == before, "١ ولقطةٌ عمرُها لحظةٌ لا تُوقظ شيئاً",
          f"+{calls['n'] - before}")
    age = M.age_seconds()
    check(age is not None and age < M.LIVE_TTL,
          "١ب والعمرُ يُقاس بالثواني لا يُخمَّن", f"{age:.1f}ث" if age else "—")

    # ── ٢ · شائخةٌ تُوقظ واحداً ─────────────────────────────────────────
    _reset(); _stale(30)
    M.ensure_fresh()
    await asyncio.sleep(0.9)
    check(calls["n"] == 1 and (M.age_seconds() or 99) < 2,
          "٢ ولقطةٌ شائخةٌ تُوقظ تجديداً فيصل الرقمُ الجديد", f"{calls['n']} نداء")

    # ── ٣ · مغلقٌ ⇒ لا إيقاظ ───────────────────────────────────────────
    M.datetime = _Closed                                         # type: ignore[misc]
    _reset(); _stale(300)
    woke2 = M.ensure_fresh()
    await asyncio.sleep(0.2)
    check(woke2 is False and calls["n"] == 0,
          "٣ والسوقُ مغلقٌ ⇒ لا إيقاظَ أصلاً — لا نداءَ بلا معنى")
    M.datetime = _Sess                                           # type: ignore[misc]

    # ── ٤ · الشاشةُ لا تُحبَس ───────────────────────────────────────────
    _reset(); _stale()
    t0 = time.perf_counter()
    res = await EP.get_market_depth("2010")
    ms = (time.perf_counter() - t0) * 1000
    d = (res.get("data") or {})
    check(ms < 150 and d.get("bids"),
          "٤ والشاشةُ تعود فوراً بما عندها — لا تنتظر الشبكة",
          f"{ms:.0f}ms · طلبُ {d['bids'][0]['price'] if d.get('bids') else '—'}")
    await asyncio.sleep(0.9)
    res2 = (await EP.get_market_depth("2010")).get("data") or {}
    check(res2["bids"][0]["price"] == 70.4,
          "٤ب ثمّ يصل الأحدثُ في النداء التالي",
          str(res2["bids"][0]["price"]))

    _reset(); _stale()
    t0 = time.perf_counter()
    await asyncio.gather(*(EP.get_market_depth("2010") for _ in range(100)))
    ms = (time.perf_counter() - t0) * 1000
    check(ms < 500 and calls["n"] == 1,
          "٤ج ومئةُ نداءٍ على المسار: نداءُ مصدرٍ واحدٌ وزمنٌ لا يُحسّ",
          f"{ms:.0f}ms · {calls['n']} نداء")
    M.datetime = _real                                           # type: ignore[misc]


asyncio.run(main())

# ── ٥ · النبضُ أسرعُ من سقف الشيخوخة ───────────────────────────────────
HK = (ROOT / "frontend" / "src" / "hooks"
      / "useMarketLive.ts").read_text(encoding="utf-8")
import re  # noqa: E402
open_ms = int(re.search(r"open:\s*([\d_]+)", HK).group(1).replace("_", ""))
check(open_ms <= M.LIVE_TTL * 1000,
      "٥ ونبضُ الشاشة أسرعُ من سقف شيخوخة المصدر — وإلا ضاع تغيّر",
      f"{open_ms}ms مقابل سقفٍ {M.LIVE_TTL * 1000}ms")
check(M.INDEX_TTL <= open_ms / 1000,
      "٥ب وتخزينُ المؤشّر لا يتجاوز نبضَ الشاشة", f"{M.INDEX_TTL}ث")
MK = (ROOT / "backend" / "app" / "api" / "v1" / "endpoints"
      / "market.py").read_text(encoding="utf-8")
check(MK.count("ensure_fresh") >= 2,
      "٥ج والإيقاظُ في مسارات السعر لا في مسارٍ واحد")

print(("FAIL" if fail else "PASS") + " D289 — لحظيةٌ في المصدر، بلا إغراق")
raise SystemExit(fail)
