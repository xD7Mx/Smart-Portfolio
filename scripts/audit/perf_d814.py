#!/usr/bin/env python3
"""حارسُ D814 (الخادم) — «التطبيقُ يأخذ وقتاً: عند التحميل أو البحث أو المسح أو تشغيل الإطارات أو الرسم — خلِّه سريعاً» (المالك 2026-11-24).

قِيس على الخادم (‏perf_door_d814.py): قائمةُ المراقبة الباردة 13–14 ثانية لأنّ كلَّ رمزٍ خارجَ «تداول» يُسأل عنه ياهو وحده (5–9 ثوانٍ لكلٍّ)
والقائمةُ تنتظر أبطأها؛ ومسحُ السوق 163ث (السعوديّ) و377ث (الأمريكيّ) وقراءاتُ الذكاء لأفضل ستّ فرصٍ فيه تتتابع واحدةً بعد واحدة.

  ١ أسعارُ مجموعةٍ: نداءٌ واحدٌ للرموز كلِّها خارجَ «تداول» (لا نداءٌ لكلّ رمز)، ويُخبّأ كلُّ سعرٍ لرمزه — والنداءُ التالي من المخبّأ بلا شبكة.
  ٢ وما لم يُجب عنه النداءُ الواحد: بمهلةٍ كلّية — الرمزُ البطيءُ لا يحبس القائمة، ويكمل في الخلفية فيُخبّأ للنداء التالي.
  ٣ المسح: قراءاتُ الذكاء معاً (ثلاثٌ في آن) لا متتابعة، والرسومُ عشرةً معاً، وزمنُ كلّ مرحلةٍ مسجَّلٌ مع المسح.

    python3 scripts/audit/perf_d814.py
"""
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp_d814_")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import cache  # noqa: E402
from app.services import live_quote as LQ  # noqa: E402
from app.services.market_data import market_service as M, PriceData  # noqa: E402

M._tadawul_price = staticmethod(lambda base: {"symbol": f"{base}.SR", "price": 10.0, "change": 0.1, "change_pct": 1.0} if base.isdigit() else None)
batch_calls: list = []
one_calls: list = []


async def fake_quotes(symbols):
    batch_calls.append(list(symbols))
    return {s.upper(): {"regularMarketPrice": 100.0 + i, "regularMarketPreviousClose": 99.0 + i, "regularMarketChange": 1.0, "regularMarketChangePercent": 1.01}
            for i, s in enumerate(symbols) if s != "SLOW1"}

LQ.yahoo_quotes = fake_quotes


async def fake_one(sym):
    one_calls.append(sym)
    await asyncio.sleep(30 if sym == "SLOW1" else 0.05)
    return PriceData(sym, 5.0, 0.0, 0.0)

M.primary.get_price = fake_one
cache.clear()
SYMS = ["2222", "1120", "BTC-USD", "BZ=F", "GC=F", "NIO", "NVDA", "NIO270319P00004000", "SLOW1"]


async def run1():
    t0 = time.monotonic()
    a = await M.get_prices(SYMS, budget=1.5)
    t1 = time.monotonic() - t0
    b0 = len(batch_calls)
    t2 = time.monotonic()
    b = await M.get_prices([s for s in SYMS if s != "SLOW1"], budget=1.5)
    return a, t1, b, time.monotonic() - t2, b0

a, t1, b, t2, b0 = asyncio.run(run1())
check(len(batch_calls) == 1 and sorted(batch_calls[0]) == sorted([s for s in SYMS if not s.isdigit()]) and all(a.get(s, {}).get("price") for s in SYMS if s != "SLOW1")
      and a["BTC-USD"]["change_pct"] == 1.01 and one_calls == ["SLOW1"] and len(b) == 8 and b0 == 1 and t2 < 0.2,
      "١ أسعارُ مجموعةٍ: نداءٌ واحدٌ للرموز كلِّها خارجَ «تداول» (سلعٌ وعملاتٌ مشفّرةٌ وأسهمٌ وعقد)، والتالي من المخبّأ بلا شبكة",
      f"دفعات {len(batch_calls)} · فرادى {one_calls} · التالي {t2 * 1000:.0f}ms")
check(t1 < 2.5 and "SLOW1" not in a,
      "٢ والرمزُ البطيءُ لا يحبس القائمة: تُعاد بعد المهلة الكلّية بما وصل (والبطيءُ يكمل في الخلفية)", f"{t1:.2f}ث")

# ── ٣ المسح ──
from app.services import chart_scan as CS  # noqa: E402
from app.services import saqr_council as CN  # noqa: E402
src = (ROOT / "backend/app/services/chart_scan.py").read_text(encoding="utf-8")
live = {"n": 0, "max": 0}


async def fake_link(*a, **k):
    live["n"] += 1
    live["max"] = max(live["max"], live["n"])
    await asyncio.sleep(0.5)
    live["n"] -= 1
    return "قراءة"


async def fake_ctx(market):
    return {"reg": {}}


async def fake_collect(market, cands, ctx, conc=4, flow_max=20):
    return {c["symbol"]: {"heads": []} for c in cands}

CN.link, CN.context, CN.collect = fake_link, fake_ctx, fake_collect
CN.judge = lambda ev: {"veto": False, "veto_why": ""}
CN.compact = lambda bd: {"verdict": "يوافق", "score": 50}
CN.earn_days = lambda s: None
items = [{"symbol": f"S{i}", "name": f"س{i}", "side": "long", "close": 10.0, "tr": None, "setup": "x", "quality": 70, "horizon_n": 1} for i in range(6)]


async def run3():
    t0 = time.monotonic()
    ap, rej = await CS.review("us", items, {}, True)
    return ap, time.monotonic() - t0

ap, tr = asyncio.run(run3())
check(all(x.get("link") == "قراءة" for x in ap) and tr < 1.4 and live["max"] == 3 and CS.CONC >= 10 and '"phases": {"read":' in src and "conc=8" in src,
      "٣ المسح: قراءاتُ الذكاء لأفضل ستّ فرصٍ ثلاثٌ في آن (لا متتابعة)، والرسومُ عشرةً معاً، وزمنُ كلّ مرحلةٍ يُسجَّل مع المسح",
      f"{tr:.2f}ث · معاً {live['max']} · CONC {CS.CONC}")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
