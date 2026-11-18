#!/usr/bin/env python3
"""كاشفُ مجال صقر الأمريكيّ الكامل (‏D766): أيُّ مصدرٍ يعطي **كلَّ** الشركات الأمريكية التي لها عقودُ خيارات، وأيُّ حقولٍ أساسيةٍ يُحكم
بها على متانتها قبل التحليل الفنيّ. يُجرّب على الخادم: قائمةَ الرموز ذات الخيارات من «سيبوي» (‏Cboe)، وحقولَ مُصفّي TradingView
حقلاً حقلاً (الأساسيةَ والفنية)، ثمّ مُصفّياً واحداً على السوق كلّه بما صلح. قراءةٌ فقط — لا يكتب شيئاً.

    docker exec sp_backend python /app/scripts/audit/us_universe_door.py
"""
import csv, io, json, sys, time   # noqa: E401
sys.path.insert(0, "/app")
sys.stdout.reconfigure(line_buffering=True)
from curl_cffi import requests as cr   # noqa: E402

H = {"Content-Type": "application/json", "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"}


def tv(body: dict):
    with cr.Session(impersonate="chrome") as s:
        r = s.post("https://scanner.tradingview.com/america/scan", data=json.dumps(body), timeout=20, headers=H)
    return r.status_code, r.text


# ١ قائمةُ الرموز ذات الخيارات من سيبوي
for url in ("https://www.cboe.com/us/options/symboldir/equity_index_options/?download=csv",
            "https://www.cboe.com/available_weeklys/get_csv_download/"):
    try:
        t0 = time.time()
        with cr.Session(impersonate="chrome") as s:
            r = s.get(url, timeout=25)
        body = r.text or ""
        rows = list(csv.reader(io.StringIO(body)))
        print(f"Cboe {url[:70]} · {r.status_code} · {len(body)} بايت · {len(rows)} صفّ · {time.time() - t0:.1f}ث")
        for row in rows[:4]:
            print("   ", row[:6])
    except Exception as e:                                        # noqa: BLE001
        print("Cboe تعذّر:", url[:60], type(e).__name__, str(e)[:120])

# ٢ حقولُ TradingView حقلاً حقلاً
FIELDS = ["name", "description", "type", "subtype", "typespecs", "exchange", "is_primary", "sector", "industry", "close", "change", "volume",
          "average_volume_10d_calc", "average_volume_30d_calc", "relative_volume_10d_calc", "Value.Traded", "market_cap_basic",
          "SMA20", "SMA50", "SMA200", "EMA20", "EMA50", "Perf.W", "Perf.1M", "Perf.3M", "Perf.6M", "Perf.Y", "RSI", "ATR",
          "price_52_week_high", "price_52_week_low", "High.3M", "Low.3M", "High.6M", "Low.6M",
          "price_earnings_ttm", "earnings_per_share_diluted_ttm", "earnings_per_share_basic_ttm", "net_income", "net_income_ttm",
          "total_revenue", "total_revenue_ttm", "revenue_per_employee", "gross_margin", "operating_margin", "net_margin", "after_tax_margin",
          "return_on_equity", "return_on_assets", "return_on_invested_capital", "debt_to_equity", "current_ratio", "quick_ratio",
          "free_cash_flow", "free_cash_flow_ttm", "total_debt", "total_assets", "total_equity", "cash_n_short_term_invest",
          "piotroski_f_score_ttm", "piotroski_f_score_fy", "altman_z_score_ttm", "altman_z_score_fy", "beta_1_year",
          "earnings_release_next_date", "earnings_release_date", "dividend_yield_recent", "number_of_employees",
          "revenue_growth_ttm_yoy", "total_revenue_yoy_growth_ttm", "net_income_yoy_growth_ttm", "earnings_per_share_diluted_yoy_growth_ttm"]
ok = []
for f in FIELDS:
    code, txt = tv({"symbols": {"tickers": ["NASDAQ:AAPL", "NYSE:F", "NASDAQ:NIO"]}, "columns": [f]})
    try:
        vals = [row["d"][0] for row in json.loads(txt).get("data") or []]
    except Exception:                                             # noqa: BLE001
        vals = None
    good = code == 200 and vals is not None
    if good:
        ok.append(f)
    print(f"  {'✓' if good else '✗'} {f:42s} {code} {str(vals)[:90] if good else txt[:90]}")
print("\nالحقولُ الصالحة:", len(ok), "من", len(FIELDS))

# ٣ مُصفٍّ واحدٌ على السوق كلّه: أسهمٌ عاديةٌ وصناديقُ في البورصات الثلاث، بسعرٍ وحجمٍ يكفيان لسوق خيارات
base = [{"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]},
        {"left": "close", "operation": "greater", "right": 3},
        {"left": "average_volume_10d_calc", "operation": "greater", "right": 300000}]
for flt, tag in ((base + [{"left": "type", "operation": "in_range", "right": ["stock", "fund"]}], "أسهم وصناديق"),
                 (base + [{"left": "type", "operation": "equal", "right": "stock"}], "أسهم وحدها")):
    t0 = time.time()
    code, txt = tv({"filter": flt, "columns": [c for c in ok if c not in ("typespecs",)][:60], "sort": {"sortBy": "Value.Traded", "sortOrder": "desc"},
                    "range": [0, 6000]})
    try:
        d = json.loads(txt)
        rows = d.get("data") or []
        print(f"\nمُصفٍّ ({tag}): {code} · {len(rows)} رمزاً من {d.get('totalCount')} · {time.time() - t0:.1f}ث · {len(txt) // 1024}KB")
        if rows:
            cols = [c for c in ok if c not in ("typespecs",)][:60]
            r0 = dict(zip(cols, rows[0]["d"]))
            print("   أوّلُها:", rows[0]["s"], {k: r0[k] for k in list(r0)[:30]})
            last = dict(zip(cols, rows[-1]["d"]))
            print("   آخرُها:", rows[-1]["s"], {k: last.get(k) for k in ("close", "market_cap_basic", "average_volume_10d_calc", "type", "subtype")})
            from collections import Counter
            print("   الأنواع:", Counter((dict(zip(cols, r["d"])).get("type"), dict(zip(cols, r["d"])).get("subtype")) for r in rows).most_common(12))
    except Exception as e:                                        # noqa: BLE001
        print("مُصفٍّ تعذّر:", code, type(e).__name__, txt[:200])
