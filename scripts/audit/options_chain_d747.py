#!/usr/bin/env python3
"""حارسُ D747 — البحثُ في السوق الأمريكي كلِّه وسلسلةُ عقود الخيارات (بأمر المالك 2026-11-15).

يُفحص على الدوالّ نفسِها: قراءةُ رمز العقد (‏OCC)، وتشكيلُ نتائج البحث (الأمريكيُّ أوّلاً ولا عقودَ فيها)، وتشكيلُ السلسلة (الآجالُ
بأيامها الباقية والعقودُ مرتّبةً بسعر التنفيذ)، ورفضُ الرمز السعوديّ، ومدى الشموع القصيرُ لعقد الخيار، والمساران.

    python3 scripts/audit/options_chain_d747.py
"""
import os, pathlib, sys, tempfile   # noqa: E401
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import options_chain as O   # noqa: E402
check(O.parse_option("SPY261116C00752000") == {"root": "SPY", "expiry": "2026-11-16", "type": "call", "strike": 752.0}
      and O.parse_option("aapl261218p00187500") == {"root": "AAPL", "expiry": "2026-12-18", "type": "put", "strike": 187.5}
      and O.parse_option("AAPL") is None and O.parse_option("SPY261332C00752000") is None,
      "١ رمزُ العقد: الأصلُ والأجلُ والنوعُ وسعرُ التنفيذ — والرمزُ غيرُ العقد أو بتاريخٍ مستحيل لا يُقرأ")
sr = O.shape_search([{"symbol": "NVD.DE", "shortname": "x", "exchange": "GER", "quoteType": "EQUITY"},
                     {"symbol": "NVDA", "longname": "NVIDIA Corporation", "exchange": "NMS", "quoteType": "EQUITY"},
                     {"symbol": "SNVDA=F", "shortname": "fut", "exchange": "CME", "quoteType": "FUTURE"},
                     {"symbol": "SPY261116C00752000", "quoteType": "OPTION"}, {"symbol": "QQQ", "shortname": "Invesco QQQ", "exchange": "NGM", "quoteType": "ETF"}])
check([r["symbol"] for r in sr] == ["NVDA", "QQQ", "NVD.DE", "SNVDA=F"] and sr[0]["type"] == "سهم" and sr[0]["exchange"] == "ناسداك"
      and sr[0]["options"] and sr[1]["type"] == "صندوق متداول" and not sr[2]["us"],
      "٢ البحث: الأمريكيُّ أوّلاً بنوعه وبورصته العربيين، ولا عقودَ خياراتٍ في النتائج", str([r["symbol"] for r in sr]))
res = {"underlyingSymbol": "SPY", "quote": {"regularMarketPrice": 754.37, "shortName": "SPDR"}, "expirationDates": [1794787200, 1795392000],
       "options": [{"expirationDate": 1794787200, "calls": [{"contractSymbol": "B", "strike": 760.0, "impliedVolatility": 0.2, "volume": 5},
                                                            {"contractSymbol": "A", "strike": 750.0, "openInterest": 9, "inTheMoney": True}], "puts": []}]}
ch = O.shape_chain(res, now=1794700000)
check([e["dte"] for e in ch["expirations"]] == [2, 9] and [r["strike"] for r in ch["calls"]] == [750.0, 760.0] and ch["calls"][1]["iv"] == 20.0
      and ch["calls"][0]["itm"] and ch["calls"][0]["oi"] == 9 and ch["expiry"] == 1794787200 and ch["delayed"] is True and ch["price"] == 754.37,
      "٣ السلسلة: الآجالُ بأيامها الباقية، والعقودُ بسعر التنفيذ تصاعدياً، والتذبذبُ نسبةً مئوية، والتأخّرُ معلن")
import asyncio   # noqa: E402
check(asyncio.run(O.chain("2222")) is None and asyncio.run(O.chain("2222.SR")) is None and asyncio.run(O.chain("bad sym")) is None,
      "٤ لا سلسلةَ لرمزٍ سعوديّ أو غيرِ صالح — ولا نداءَ للمزوّد")
md = (ROOT / "backend/app/services/market_data.py").read_text(encoding="utf-8")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
check('rng = ("5d" if base == 1 else "1mo") if opt else ("7d" if base == 1 else "60d")' in md and '"3mo" if opt else "2y"' in md,
      "٥ شموعُ العقد دون اليوم بمدًى قصيرٍ يقبله المزوّد (قِيس: المدى الطويل فارغٌ للعقود)")
check('@router.get("/symbol-search")' in mk and '@router.get("/options/{symbol}")' in mk,
      "٦ المساران: البحثُ في السوق كلِّه، وسلسلةُ العقود لأجلٍ واحد")
print(("FAIL" if fail else "PASS") + " D747 — البحثُ في السوق الأمريكي كلِّه وعقودُ الخيارات بآجالها")
sys.exit(fail)
