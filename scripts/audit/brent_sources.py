#!/usr/bin/env python3
"""مصادرُ برنت وتاسي المباشرة — تُقاس قبل أن يُعتمَد أحدُها (D435).

    docker exec sp_backend python /app/scripts/audit/brent_sources.py

قال المالك: «حالةُ السوق لنفط برنت تعمل في حين أنّ الرقم لا يظهر… هل
يوجد رقمٌ مباشرٌ لترند من مصادرنا؟ أشعر أنّنا لم نذهب للمدى الذي نستطيع
الوصولَ إليه لإيجاد مصدرٍ مباشرٍ لسعر برنت».

وبرنت اليوم من ياهو وحدَه (‏`BZ=F`) — وياهو محكومٌ بحصّتنا الداخلية
(‏`can_call("yahoo")`) التي استنفدتها مسحاتُ التقييم، فخلت البطاقة. وقاعدةُ
`docs/FETCH_METHOD.md`: يُقاس المرشَّحُ قبل الاعتماد، بانتحال بصمة المتصفّح،
ويُطبع لكلّ مصدرٍ: الحالة · الرقم · زمنُ الردّ · طورُ التحديث (مباشر/مؤجَّل).
قارئٌ فقط — لا يكتب في مخزن.
"""
from __future__ import annotations

import json
import time

try:
    from curl_cffi import requests as cr
except Exception:                                                  # noqa: BLE001
    cr = None

TV_COLS = ["name", "description", "close", "change", "change_abs",
           "update_mode", "currency", "exchange"]
_BRENT = ["TVC:UKOIL", "ICEEUR:BRN1!", "NYMEX:BZ1!", "OANDA:BCOUSD",
          "CAPITALCOM:OILBRENT", "FX:UKOIL", "PEPPERSTONE:UKOIL"]
CANDIDATES = [
    *[(f"TradingView · برنت · {m}", "tv", m, _BRENT)
      for m in ("cfd", "futures", "global", "forex")],
    ("TradingView · تاسي", "tv", "ksa", ["TADAWUL:TASI"]),
    ("TradingView · تاسي (global)", "tv", "global", ["TADAWUL:TASI"]),
    ("Yahoo chart · برنت", "yahoo", "BZ=F", None),
]


def _tv(market: str, tickers: list[str]):
    url = f"https://scanner.tradingview.com/{market}/scan"
    body = {"symbols": {"tickers": tickers, "query": {"types": []}},
            "columns": TV_COLS}
    with cr.Session(impersonate="chrome") as s:
        r = s.post(url, data=json.dumps(body), timeout=20,
                   headers={"Content-Type": "application/json",
                            "Origin": "https://www.tradingview.com",
                            "Referer": "https://www.tradingview.com/"})
        return r.status_code, r.text or ""


def _yahoo(sym: str):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
    with cr.Session(impersonate="chrome") as s:
        r = s.get(url, params={"range": "5d", "interval": "1d"}, timeout=20)
        return r.status_code, r.text or ""


def main() -> int:
    if cr is None:
        print("⚠ curl_cffi غيرُ منصَّبة — لم يُقَس")
        return 0
    for title, kind, arg, tickers in CANDIDATES:
        t0 = time.perf_counter()
        try:
            st, txt = _tv(arg, tickers) if kind == "tv" else _yahoo(arg)
        except Exception as e:                                    # noqa: BLE001
            print(f"✘ {title} — {type(e).__name__}: {e}")
            continue
        dt = time.perf_counter() - t0
        print(f"═ {title} — HTTP {st} · {dt:.2f}s")
        try:
            d = json.loads(txt)
        except Exception:                                         # noqa: BLE001
            print(f"   ليس JSON: {txt[:160]!r}")
            continue
        if kind == "tv":
            for row in (d.get("data") or []):
                vals = dict(zip(TV_COLS, row.get("d") or []))
                print(f"   {row.get('s')}: {vals}")
            if not d.get("data"):
                print(f"   بلا صفوف: {str(d)[:200]}")
        else:
            m = (((d.get("chart") or {}).get("result") or [{}])[0] or {}).get("meta") or {}
            print(f"   سعر={m.get('regularMarketPrice')} · زمن={m.get('regularMarketTime')}"
                  f" · عملة={m.get('currency')} · خطأ={(d.get('chart') or {}).get('error')}")
    # ── والطريقُ المُقدَّمُ نفسُه على الخادم (‏D435) ─────────────────
    try:
        import asyncio
        import sys as _s
        _s.path.insert(0, "/app")
        from app.services.commodity_quote import brent_quote
        print(f"\n═ brent_quote() المُقدَّم: {asyncio.run(brent_quote())}")
    except Exception as e:                                        # noqa: BLE001
        print(f"\n⚠ brent_quote() لم يُقَس: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
