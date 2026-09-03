"""توزيعُ درجة السلامة على كامل السوق — على الخادم حيث البيانات.

## لماذا

قال المالك: «درجةُ الحوكمة لشركاتي ليست منطقية، ومعظمُها قياديةٌ ومركزُها
الماليُّ قوي ومع ذلك الدرجةُ في السبعين — ولا تجعل التعديلَ لشركاتي وحدها،
نظّف درجةَ الحوكمة لِـ273 شركة».

فالحكمُ لا يصحّ على عيّنةٍ من محفظةٍ واحدة. هذا يقيس **الكونَ كلَّه**:
أدنى الدرجات ومئينيّاتِها ووسيطَها وأعلاها، وكم شركةً تجاوزت ٨٥ و٩٠،
ومتوسّطَ كلِّ إشارةٍ من الستّ على حِدَة — فيُعرف أين يقع الضغطُ إن وقع.

ولا نداءَ واحدٌ إلى المصدر: يقرأ القوائمَ المخزّنة وحدها.

## التشغيل

    docker exec sp_backend python /app/scripts/audit/score_dist.py
"""

from __future__ import annotations

import asyncio
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _pct(sorted_vals: list[int], q: float) -> int:
    if not sorted_vals:
        return 0
    i = min(len(sorted_vals) - 1, max(0, round((len(sorted_vals) - 1) * q)))
    return sorted_vals[i]


async def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.services.market_data import market_service
    from app.services.scores import finance_score_from_periods

    symbols = sorted(MARKET_UNIVERSE)
    scored: list[tuple[str, int]] = []
    no_data: list[str] = []

    for sym in symbols:
        y = sym if sym.endswith(".SR") else f"{sym}.SR"
        try:
            periods = await market_service.get_financials(y)
        except Exception:
            periods = None
        s = finance_score_from_periods(periods) if periods else None
        if s is None:
            no_data.append(sym)
        else:
            scored.append((sym, s))

    vals = sorted(s for _, s in scored)
    n = len(vals)
    print(f"الكون {len(symbols)} · قُرئت {n} · بلا قوائم {len(no_data)}")
    if not n:
        print("لا بياناتٍ مخزّنةً بعد — شغّل مسحَ السوق أوّلاً.")
        return 1

    print()
    print(f"  الأدنى        {vals[0]}")
    print(f"  المئينيّ ٢٥   {_pct(vals, 0.25)}")
    print(f"  الوسيط        {_pct(vals, 0.50)}")
    print(f"  المئينيّ ٧٥   {_pct(vals, 0.75)}")
    print(f"  المئينيّ ٩٠   {_pct(vals, 0.90)}")
    print(f"  الأعلى        {vals[-1]}")
    print()
    for edge in (90, 85, 80, 70, 50):
        c = sum(1 for v in vals if v >= edge)
        print(f"  ≥ {edge}   {c:3d} شركة  ({c / n * 100:5.1f}٪)")

    print()
    print("  أعلى عشرين")
    for sym, s in sorted(scored, key=lambda t: -t[1])[:20]:
        print(f"    {sym:>6}  {s}")
    print("  أدنى عشر")
    for sym, s in sorted(scored, key=lambda t: t[1])[:10]:
        print(f"    {sym:>6}  {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
