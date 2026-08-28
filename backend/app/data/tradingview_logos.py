"""
Symbol → {name_ar, logo_url} for Tadawul companies — collected LIVE from
tradingview.com's own Saudi market-movers screener data (captured 2026-07,
100 companies), the same "gather from a real source, commit as a static
file" pattern already used for شرعية compliance (maqasid_ratings.json).
Never a guessed or scraped-from-an-unverified-pattern URL: every entry here
traces back to a real (symbol, logoid) pair TradingView itself served.
"""

import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "tradingview_logos.json")
with open(_PATH, encoding="utf-8") as _f:
    TRADINGVIEW_LOGOS: dict[str, dict] = json.load(_f)
