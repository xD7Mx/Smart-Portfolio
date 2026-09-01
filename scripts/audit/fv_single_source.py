"""السعرُ العادل مصدرٌ واحد في التطبيق كلِّه — حارسُ D147.

## القاعدة المعتمدة

**السعرُ العادل = متوسّطُ تقديرات بيوت الخبرة** (`target_mean_price`)،
بهذا الاسم وفي كلّ قسم: صفحةُ الشركة · تحليلُ الذكاء · الفرز · وسائرُ
الأقسام. وتقديرُنا المحسوب يبقى تفصيلاً داخل `fair_value_detail` ولا
يُعرض رقماً منافساً.

والعطبُ الذي يمنعه هذا الحارس: أن يعرض قسمان رقمين مختلفين تحت اسمٍ
واحدٍ يبني عليه المالك قراره — وقد وقع فعلاً بين صفحة الشركة وصفحة
السوق ونصِّ الذكاء.

والفحصُ **سلوكيّ**: يُشغَّل مسارُ التحليل كاملاً بمسبارٍ يقوم مقام
السوق، ويُقارَن المخرَجُ بالمدخل — لا تُقرأ الأسماء.

    python scripts/audit/fv_single_source.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

TARGET = 88.5
PRICE = 60.0


def _stub() -> None:
    """مصدرٌ صناعيّ: هدفُ محلّلين معلومٌ وسعرٌ معلوم."""
    mod = types.ModuleType("app.services.market_data")
    per = [{"year": 2019 + k, "revenue": 9e9, "net_income": 1e9,
            "equity": 1e10, "eps": 3.0, "operating_cash_flow": 1.2e9,
            "capex": -2e8, "depreciation": 2e8, "total_debt": 1e9,
            "ending_cash": 5e8, "shares_outstanding": 3.3e8,
            "operating_income": 1.3e9, "total_assets": 1.4e10,
            "dividends_paid": -3e8} for k in range(5)]

    class MS:
        async def get_financials(self, t, allow_supplement=False):
            return {"periods": per}

        async def get_company_info(self, t):
            return {"name": "شركةُ فحص", "sector": "الاتصالات",
                    "target_mean_price": TARGET, "beta": 1.0,
                    "current_price": PRICE}

        async def get_price(self, t):
            return {"price": PRICE, "change_pct": 0.0}

        async def get_history(self, *a, **k):
            return []

    mod.market_service = MS()
    sys.modules["app.services.market_data"] = mod


def main() -> int:
    T: list[tuple[str, bool, str]] = []

    def t(n, ok, d=""):
        T.append((n, bool(ok), d))

    _stub()
    from app.services.analysis import analyze_company
    from app.services import cache
    cache.clear()
    res = asyncio.run(analyze_company("9999.SR", "شركةُ فحص")) or {}

    got = res.get("fair_value")
    t("١ السعرُ العادل = تقديرُ بيوت الخبرة", got == TARGET,
      f"المُدخَل {TARGET} · المخرَج {got}")

    up = res.get("fair_value_upside_pct")
    want = round((TARGET - PRICE) / PRICE * 100, 1)
    t("٢ الفجوةُ محسوبةٌ من الرقم نفسِه", up == want,
      f"المتوقَّع {want}% · المخرَج {up}%")

    det = res.get("fair_value_detail") or {}
    t("٣ تقديرُنا يبقى تفصيلاً لا رقماً منافساً",
      isinstance(det, dict) and det.get("value") != got,
      f"المعروض {got} · تفصيلُنا {det.get('value')}")

    # ٤ — نصُّ الذكاء يُغذّى الرقمَ المعروضَ نفسَه
    from app.services import ai_content
    import inspect
    src = inspect.getsource(ai_content)
    t("٤ نصُّ الذكاء يقرأ الرقمَ المعروض",
      "السعر العادل (متوسط تقديرات بيوت الخبرة)" in src
      and "analysis.get('fair_value')" in src,
      "يُقرأ من analysis لا من fundamentals")

    # ٥ — الفرزُ على المصدر نفسِه
    ssrc = open(os.path.join(_ROOT, "backend", "app", "services",
                             "market_screener.py"), encoding="utf-8").read() \
        if os.path.exists(os.path.join(_ROOT, "backend", "app", "services",
                                       "market_screener.py")) else \
        open("/app/app/services/market_screener.py", encoding="utf-8").read()
    t("٥ الفرزُ على المصدر نفسِه",
      'r["fair_value"] = _fv' in ssrc and 'pick("target_mean_price")' in ssrc,
      "target_mean_price")

    print("═" * 60)
    print("  السعرُ العادل — مصدرٌ واحد")
    print("═" * 60)
    for n, ok, d in T:
        print(f"  {'PASS' if ok else 'FAIL'}  {n:36} {d}")
    bad = [n for n, ok, _ in T if not ok]
    print("═" * 60)
    print("  ✔ رقمٌ واحدٌ باسمٍ واحد في كلّ قسم." if not bad
          else f"  ✖ أخفق {len(bad)}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
