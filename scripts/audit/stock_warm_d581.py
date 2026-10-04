#!/usr/bin/env python3
"""حارسُ D581: صفحةُ السهم لا تنتظر أوّلَ فتح — صفحاتُ المحافظ والمراقبة تُجهَّز ثلاثَ مرّاتٍ يومياً، والسلامةُ
المالية تقرأ توزيعاتِ أقرانها متوازيةً وتعيش يوماً؛ ورسمُ برنت وتاسي يضع أرقامَ المحور في حارةٍ لا يعبرها الخطّ،
وشريحةُ «ثابتة» في عرض النطاق مرئيةٌ برقمها.

    python3 scripts/audit/stock_warm_d581.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0
def check(ok, label):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}")

sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text()
check(all(f'id="stock_warm_{k}"' in sch for k in ("morning", "close", "evening", "boot")),
      "١ تجهيزُ صفحات الأسهم ثلاثَ مرّاتٍ يومياً وبعد كلِّ إقلاع (الإعادةُ تمحو ذاكرةَ الخادم)")
w = (ROOT / "backend/app/services/stock_warm.py").read_text()
check(all(x in w for x in ("get_fair_value_models", "get_financial_health", "get_company_recommendations",
                           "get_company_events", "get_company_dividends", "analyze_company", "Watchlist", "Holding")),
      "٢ يُجهَّز كلُّ نداءٍ بطيءٍ قِيس، لشركات المحافظ والمراقبة")
h = (ROOT / "backend/app/services/financial_health.py").read_text()
check("asyncio.gather(*(_dps(s) for s in peers))" in h and "cache.set(tk, table, 24 * 60 * 60)" in h,
      "٣ السلامةُ المالية: توزيعاتُ الأقران متوازية، والجدولُ يعيش يوماً")
mw = (ROOT / "frontend/src/components/market/MarketWidgets.tsx").read_text()
check("mirror width={1}" not in mw and 'orientation="right" width={44}' in mw, "٤ محورُ برنت وتاسي في حارةٍ خارجَ الرسم")
check('background: "var(--hairline)"' in mw and "{unch}</div>" in mw and "unch > total * 0.05" not in mw,
      "٥ «ثابتة» حشوٌ محايدٌ مرئيٌّ ورقمُها دائماً")
cp = (ROOT / "frontend/src/pages/CompanyPage.tsx").read_text()
pre = cp.split("if (!company) return", 1)[0]
check(all(k in pre for k in ('["financials", s, "annual"]', '["fvm", s4]', '["health", s4]', '["quarter-reports", s]',
                            '["dividend-profile", s]', '["argaam-recs", s]')) and "prefetchQuery" in pre,
      "٦ صفحةُ السهم تجلب بياناتِ التبويبات في الخلفية بمفاتيحها نفسِها — قبل أيّ رجوعٍ مبكّر")
check('id="market_warm_dawn"' in sch and "async def warm_market" in w,
      "٧ D583: السوقُ كلُّه يُجهَّز قبل الفجر — لا يُحسب أوّلُ فتحٍ لشركةٍ من الفرز")
sys.exit(fail)
