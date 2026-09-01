"""محرّكُ حوكمةٍ واحدٌ في التطبيق كلِّه — حارسُ D149.

## القاعدة المعتمدة

منطقُ **بطاقة سلامة الشركة** (‏`governance_engine.evaluate_company`) هو
منطقُ الحوكمة في كلّ قسم: صفحةُ الشركة · تحليلُ الذكاء · الفرز · تقييمُ
الأداء. فدرجةُ الشركة الواحدة لا تختلف باختلاف الشاشة.

## العطب الذي يمنعه

كان التحليلُ يستبدل ركنَ الجودة بدرجة «المواصفة» بعد حسابه، والبطاقةُ
لا تفعل — فخرجت الشركةُ الواحدة بقوائمها نفسِها بدرجتين: ‎67 في البطاقة
و‎74 في صفحة الشركة. وكان يستبدل الدرجةَ المتعذّرةَ بـ‎50، ورقمٌ لم يُقَس
يُعرض كأنه قياسٌ أسوأُ من فراغٍ معلَن.

والفحصُ **سلوكيّ**: يُشغَّل المحرّكان على الشركة نفسِها بمسبارٍ يقوم مقام
السوق، وتُقارَن الدرجتان — لا تُقرأ الشيفرة.

    python scripts/audit/gov_one_engine.py
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

SECTOR = "الاتصالات"


def _rows(n: int = 5, ni: float = 1e9) -> list[dict]:
    return [{"year": 2019 + k, "revenue": 9e9, "net_income": ni,
             "equity": 1e10, "eps": 3.0, "operating_cash_flow": 1.2e9,
             "capex": -2e8, "depreciation": 2e8, "total_debt": 1e9,
             "ending_cash": 5e8, "shares_outstanding": 3.3e8,
             "operating_income": 1.3e9, "total_assets": 1.4e10,
             "dividends_paid": -3e8, "total_liabilities": 4e9,
             "interest_expense": 5e7} for k in range(n)]


# حالاتٌ تغطّي المسارات: كاملةٌ · قصيرةُ التاريخ · خاسرةٌ · بلا قوائم
CASES = {"9001.SR": _rows(5), "9002.SR": _rows(2),
         "9003.SR": _rows(5, -4e8), "9004.SR": []}


def _stub() -> None:
    mod = types.ModuleType("app.services.market_data")

    class MS:
        async def get_financials(self, t, allow_supplement=False):
            return {"periods": CASES.get(t, [])}

        async def get_company_info(self, t):
            return {"name": "شركةُ فحص", "sector": SECTOR, "beta": 1.0,
                    "target_mean_price": 80.0, "current_price": 60.0,
                    "pe_ratio": 14, "price_to_book": 2}

        async def get_price(self, t):
            return {"price": 60.0, "change_pct": 0.0}

        async def get_history(self, *a, **k):
            return []

    mod.market_service = MS()
    sys.modules["app.services.market_data"] = mod


def main() -> int:
    _stub()
    from app.services.governance_engine import evaluate_company
    from app.services.analysis import analyze_company
    from app.services import cache

    rows, bad = [], []

    async def run():
        for sym in CASES:
            cache.clear()
            card = await evaluate_company(sym, sector=SECTOR)
            cache.clear()
            page = await analyze_company(sym, "شركةُ فحص")
            c = (card or {}).get("overall")
            a = ((page or {}).get("financial") or {}).get("score")
            rows.append((sym, c, a))
            if c != a:
                bad.append(sym)

    asyncio.run(run())

    print("═" * 60)
    print("  محرّكُ حوكمةٍ واحد — البطاقةُ وصفحةُ الشركة")
    print("═" * 60)
    print(f"  {'الرمز':12} {'البطاقة':>9} {'الصفحة':>9}")
    for sym, c, a in rows:
        print(f"  {sym:12} {str(c):>9} {str(a):>9}   "
              f"{'✔' if c == a else '✖ مختلفتان'}")

    # ولا خمسينَ مختلَقة: الشركةُ بلا قوائم تُعاد عدماً لا وسطاً
    empty = [a for s, _c, a in rows if s == "9004.SR"]
    no_fake = empty and empty[0] is None
    print(f"\n  بلا قوائم → {empty[0] if empty else '—'} "
          f"({'عدمٌ معلَن' if no_fake else 'رقمٌ مختلَق'})")

    ok = not bad and no_fake
    print("═" * 60)
    print("  ✔ درجةٌ واحدةٌ لا تختلف باختلاف الشاشة." if ok
          else f"  ✖ اختلفت في {len(bad)}: {bad}"
          if bad else "  ✖ رقمٌ مختلَقٌ عند غياب القوائم")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
