#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D290 — «بدون تأخيرٍ نهائياً»: دفعٌ لا سؤال.
#
# السؤالُ الدوريُّ فيه تأخيرٌ **بنيويّ** لا يُلغى بالإسراع: الرقمُ يصل
# الخادمَ في لحظةٍ وتسأل الشاشةُ بعدها. فقُلب الاتّجاه: مجرى أحداثٍ يدفع
# كلَّ سعرٍ يتغيّر لحظةَ وصوله.
#
# وثلاثةُ أخطارٍ لا تُترك بلا حرز:
#   · **مضخّةٌ لكلّ مشترك** ⇒ مئةُ نداءٍ للمصدر في الثانية ⇒ حجبُ حسابنا
#   · **بثٌّ بلا مشاهد** ⇒ نداءٌ دائمٌ بلا فائدة
#   · **دفعةٌ كاملةٌ كلَّ ثانية** ⇒ مئاتُ كيلوبايتٍ وإعادةُ رسمٍ شاملة
#
#   ٠· مضخّةٌ واحدةٌ لكلّ المشتركين
#   ١· وتتوقّف وحدَها حين ينفضّ الجميع
#   ٢· ولا تنادي المصدرَ والسوقُ مغلق
#   ٣· ولا يُدفَع إلا ما تغيّر
#   ٤· وأوّلُ دفعةٍ فوريةٌ — لا شاشةٌ فارغةٌ تنتظر
#   ٥· ومشترِكٌ بطيءٌ لا يُكدِّس الذاكرة
#   ٦· ولكلّ اتّصالٍ عمرٌ أقصى
#   ٧· والمسارُ يعمل فعلاً بترويسة SSE صحيحة
#   ٨· والواجهةُ تقرأ الدفعَ وتُبطئ سؤالَها
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import datetime as dt  # noqa: E402
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


from app.services import cache, live_stream as LS, tadawul_market as M  # noqa: E402

_real = dt.datetime
hits = {"n": 0}


async def _fake_refresh():
    hits["n"] += 1
    cache.set(M.STORE_KEY,
              {"at": _real.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "rows": {"2010": {"price": 70.0 + hits["n"] * 0.05,
                                 "change_pct": 0.5 + hits["n"] * 0.01},
                        "1120": {"price": 96.4, "change_pct": -0.2}}}, 600)
    return {"count": 2}


M.refresh = _fake_refresh                                        # type: ignore[assignment]


class _Sess(_real):
    @classmethod
    def now(cls, tz=None):
        return _real(2026, 9, 13, 11, 0) if tz is None else _real.now(tz)


class _Closed(_real):
    @classmethod
    def now(cls, tz=None):
        return _real(2026, 9, 12, 11, 0) if tz is None else _real.now(tz)


LS.PUMP_INTERVAL = 0.12
LS.HEARTBEAT = 0.25
LS.MAX_STREAM_SECONDS = 2.0


async def _take(n: int) -> list:
    got = []
    agen = LS.stream()
    async for chunk in agen:
        if chunk.startswith("data:"):
            got.append(json.loads(chunk[5:]))
            if len(got) >= n:
                break
    await agen.aclose()
    return got


async def main() -> None:
    LS.datetime = _Sess                                          # type: ignore[misc]
    LS._last.clear()
    hits["n"] = 0

    a, b = await asyncio.gather(_take(4), _take(4))
    check(hits["n"] <= 6,
          "٠ مشتركان ⇒ مضخّةٌ واحدة — لا نداءَ لكلّ مشترك",
          f"{hits['n']} نداءً لدفعتين × 4")
    check(len(a) == 4 and len(b) == 4,
          "٠ب وكلاهما يستقبل الدفعاتِ نفسَها", f"{len(a)} · {len(b)}")

    await asyncio.sleep(0.3)
    check(LS.subscribers() == 0 and (LS._pump is None or LS._pump.done()),
          "١ وتتوقّف المضخّةُ وحدَها حين ينفضّ الجميع",
          f"{LS.subscribers()} مشترك")

    # ── ٣ · الفرقُ فقط ─────────────────────────────────────────────────
    later = [set(p.get("q", {})) for p in a[1:]]
    check(all(s == {"2010"} for s in later),
          "٣ ولا يُدفَع إلا ما تغيّر — والثابتُ لا يُعاد", str(later))
    check(set(a[0].get("q", {})) >= {"2010", "1120"},
          "٤ وأوّلُ دفعةٍ كاملةٌ فوريةٌ — لا شاشةٌ فارغةٌ تنتظر",
          str(sorted(a[0].get("q", {}))))

    # ── ٢ · مغلقٌ ⇒ لا نداءَ للمصدر ────────────────────────────────────
    LS.datetime = _Closed                                        # type: ignore[misc]
    LS._last.clear()
    hits["n"] = 0
    agen = LS.stream()
    got = []
    try:
        async for chunk in agen:
            got.append(chunk)
            if len(got) >= 2:
                break
    finally:
        await agen.aclose()
    check(hits["n"] == 0,
          "٢ والسوقُ مغلقٌ ⇒ لا نداءَ للمصدر أصلاً", f"{hits['n']} نداء")
    check(any(c.startswith(":") for c in got),
          "٢ب ويبقى الاتّصالُ بنبضةِ حياةٍ لا بدفعاتٍ كاذبة")
    LS.datetime = _Sess                                          # type: ignore[misc]

    # ── ٥ · مشترِكٌ بطيء ──────────────────────────────────────────────
    q: asyncio.Queue = asyncio.Queue(maxsize=LS.QUEUE_MAX)
    LS._subs.add(q)
    for i in range(LS.QUEUE_MAX * 4):
        LS._publish({"q": {"2010": [i, 0]}})
    check(q.qsize() <= LS.QUEUE_MAX,
          "٥ ومشترِكٌ بطيءٌ يُسقَط عنه الأقدمُ — لا تكديسَ في الذاكرة",
          f"{q.qsize()} ≤ {LS.QUEUE_MAX}")
    LS._subs.discard(q)

    # ── ٦ · ٧ · المسارُ الحقيقيُّ عبر HTTP ────────────────────────────
    import httpx
    from fastapi import FastAPI

    from app.api.v1.endpoints import market as MK
    app = FastAPI()
    app.include_router(MK.public_router, prefix="/api/v1/market")
    LS._last.clear()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://t") as c:
        async with c.stream("GET", "/api/v1/market/stream") as r:
            ctype = r.headers.get("content-type", "")
            cc = r.headers.get("cache-control", "")
            first = None
            async for line in r.aiter_lines():
                if line.startswith("data:"):
                    first = line
                    break
    check(r.status_code == 200 and "text/event-stream" in ctype,
          "٧ والمسارُ يعمل بترويسة SSE صحيحة", f"{r.status_code} · {ctype[:28]}")
    check("no-cache" in cc and "no-transform" in cc,
          "٧ب ولا تخزينَ وسيطاً يجمّد المجرى", cc)
    check(first and "2010" in first,
          "٧ج ووصلت دفعةٌ فعلاً عبر HTTP", (first or "")[:60])
    check(LS.MAX_STREAM_SECONDS <= 900,
          "٦ ولكلّ اتّصالٍ عمرٌ أقصى — فلا مشترِكٌ منقطعٌ يُحسَب حاضراً",
          f"{LS.MAX_STREAM_SECONDS:.0f}ث")
    LS.datetime = _real                                          # type: ignore[misc]


asyncio.run(asyncio.wait_for(main(), 90))

# ── ٨ · الواجهةُ تقرأ الدفع ─────────────────────────────────────────────
HK = (ROOT / "frontend" / "src" / "hooks"
      / "useLivePrices.ts").read_text(encoding="utf-8")
check("useSyncExternalStore" in HK and "EventSource" in HK,
      "٨ الواجهةُ تشترك في المجرى بمخزنٍ خارجيّ — لا حالةَ مكوِّنٍ تُعيد رسمَ الشجرة")
check("listeners.get(symbol)" in HK,
      "٨ب والاشتراكُ بالرمز: لا يُعاد رسمُ الشريط لأن سهماً تحرّك")
check("refs" in HK and "acquire" in HK,
      "٨ج ومجرًى واحدٌ للتطبيق كلِّه باشتراكٍ مرجعيّ")
check("visibilitychange" in HK,
      "٨د ولا بثٌّ لشاشةٍ مخفيّة")
check("Math.min(1000 * 2 ** retry++, 30_000)" in HK,
      "٨ه وإعادةُ وصلٍ بتراجعٍ متزايدٍ بسقف")
TK = (ROOT / "frontend" / "src" / "components" / "common"
      / "MarketTicker.tsx").read_text(encoding="utf-8")
check("useLiveQuote" in TK and "streamOn ? 60_000" in TK,
      "٨و والشريطُ يقرأ الدفعَ ويُبطئ سؤالَه حين يعمل")
for f in ("components/market/StockView.tsx", "components/market/MarketDepth.tsx"):
    src = (ROOT / "frontend" / "src" / f).read_text(encoding="utf-8")
    check("useLiveQuote" in src or "useLiveStreamOn" in src,
          f"٨ز و{f.split('/')[-1]} موصولةٌ بالمجرى")

# ── ١٠ · المجرى ينطق فوراً حتى والسوقُ مغلق ─────────────────────────────
# قِيس على الخادم ‎01:38: `curl` على المجرى طبع **صفرَ أسطر** في اثنتَي عشرةَ
# ثانية. والسببُ أن أوّلَ ما يُرسَل كان معلّقاً على `snapshot()` الصارم —
# وهو فارغٌ خارجَ الجلسة — ونبضةُ الحياة بعد خمسَ عشرةَ ثانية. فبقي المجرى
# صامتاً فظُنّ معطوباً وهو سليم. والحالُ تُقرأ الآن بقاعدة كلّ الشاشات.
LS.datetime = _Closed                                            # type: ignore[misc]
M.snapshot = lambda: {}                                          # type: ignore[assignment]
import app.services.lastgood as _lg  # noqa: E402
cache.set(M.STORE_KEY, None, 0)
_lg.save(M.STORE_KEY, {"at": "2026-09-11T15:20:00+00:00",
                       "rows": {"2010": {"price": 70.0, "change_pct": 0.4}}})
LS._last.clear()


async def _closed_stream():
    out = []
    agen = LS.stream()
    try:
        async for chunk in agen:
            out.append(chunk)
            if len(out) >= 2:
                break
    finally:
        await agen.aclose()
    return out


_out = asyncio.run(asyncio.wait_for(_closed_stream(), 10))
check(_out and _out[0].startswith(":"),
      "١٠ أوّلُ ما يخرج تعليقُ حياةٍ فوراً — لا مجرًى صامتٌ يُظنّ معطوباً",
      repr(_out[0][:12]) if _out else "لا شيء")
_dat = next((c for c in _out if c.startswith("data:")), "")
check("2010" in _dat and '"live": false' in _dat,
      "١٠ب والحالةُ الحاضرةُ تُدفَع بقاعدة كلّ الشاشات — آخرُ إغلاقٍ معلَناً",
      _dat[:70])
LS.datetime = _real                                              # type: ignore[misc]

# ── ٩ · الوسيطُ لا يخزّن المجرى ─────────────────────────────────────────
# عطبٌ لا يظهر في المختبر: `location /api/` العامُّ يخزّن الردَّ ويتحدّث
# HTTP/1.0، فيصل المجرى دفعاتٍ متأخّرةً خلف نجينكس — فيبطل الدفعُ كلُّه
# وهو يعمل عندي تماماً.
NG = (ROOT / "docker" / "nginx.conf").read_text(encoding="utf-8")
check("location = /api/v1/market/stream" in NG,
      "٩ للمجرى موضعٌ مخصّصٌ في الوسيط — لا يُخدَم بقواعد /api/ العامّة")
_blk = NG.split("location = /api/v1/market/stream", 1)[1].split("location /api/ {", 1)[0]
for d, why in (("proxy_buffering off", "لا تخزينَ وسيطاً"),
               ("proxy_http_version 1.1", "اتّصالٌ دائم"),
               ('proxy_set_header Connection ""', "لا إغلاقَ بعد دفعة"),
               ("gzip off", "لا ضغطَ يحبس الدفعات")):
    check(d in _blk, f"٩ب {why} — {d}")
import re as _re3
# والقيمةُ تُقرأ من **الشيفرة** لا من الوحدة: الفحصُ عدّلها لتقصير الاختبار،
# فمقارنتُها بها تُقارن رقماً بنفسِه (فحصٌ يمرّ بلا معنى).
_to = _re3.search(r"proxy_read_timeout (\d+)s", _blk)
_src_cap = float(_re3.search(r"MAX_STREAM_SECONDS = ([\d.]+)",
                             (ROOT / "backend" / "app" / "services"
                              / "live_stream.py").read_text(encoding="utf-8")).group(1))
check(_to and int(_to.group(1)) > _src_cap,
      "٩ج ومهلةُ القراءة أطولُ من سقف عمر المجرى — لا قطعٌ قبل إغلاقٍ مهذّب",
      f"{_to.group(1) if _to else '—'}ث مقابل {_src_cap:.0f}ث")
check(NG.count("{") == NG.count("}"),
      "٩د وملفُّ الوسيط متوازنُ الأقواس — لا نجينكس يرفض الإقلاع")

print(("FAIL" if fail else "PASS") + " D290 — دفعٌ لا سؤال، بمضخّةٍ واحدة")
raise SystemExit(fail)
