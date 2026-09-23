#!/usr/bin/env python3
"""ما الذي ينقص كلَّ ورقة — وهل نملكه ولا نقرؤه؟

    python3 scripts/audit/missing_inputs_census.py

أمر المالك أن نبلغ **أقصى مدًى متاح**: «تداولُ وأرقامُ بأيدينا، ولدينا
الذكاءُ القاعديُّ وجيمناي». وقبل أن يُبنى مستخرِجٌ ذكيّ يجب أن يُعرَف
**أين الفجوةُ بالضبط**، وأيُّ صنفٍ هي:

  · **فجوةُ قراءة**: الرقمُ موجودٌ في صفٍّ محفوظٍ عندنا ولا يصل المحرّك.
    وعلاجُها شفرةٌ لا ذكاء — وهي أرخصُ وأوثقُ ما يُعالَج.
  · **فجوةُ مصدر**: لا صفَّ يحمله أصلاً. وهنا يصحّ أن يُستخرَج من
    إفصاحٍ منشورٍ (‏أرقام · تداول) بمساعدةِ نموذجٍ لغويّ — **مستخرِجاً
    لا مقدِّراً**: يقرأ رقماً مكتوباً ويُسمّي موضعَه، ويتحقّق القاعديُّ
    منه بهويّةٍ محاسبيةٍ قبل القبول.
  · **فجوةُ وجود**: الشركةُ لا تملك البندَ أصلاً (لا دَينَ · لا توزيع).
    وهذه ليست نقصاً ولا تُعالَج.

فلا يُبنى شيءٌ قبل أن يُقال أيُّها الأكثر. والامتناعُ عن القياس هنا
يعني بناءَ مستخرِجٍ ربّما لا يُحتاج إليه — وهو عينُ ما وقعتُ فيه في
D415 حين بنيتُ مساراً يعمل على ‎1٪.
"""
from __future__ import annotations

import asyncio
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

# البنودُ التي يقوم عليها المحرّكان — بأسمائها في القوائم
NEEDED = ("revenue", "net_income", "equity", "total_assets",
          "total_liabilities", "shares_outstanding", "operating_cash_flow",
          "capex", "total_debt", "ebit", "interest_expense")


# ══ ويُقاس ما يصل المحرّكَ لا المخزَنُ الخام ══ (D421)
# أوّلُ صياغةٍ قرأت `tadawul_xbrl.for_symbol` — وهو المخزَنُ **قبل**
# طبقة الإكمال. والهويّاتُ المحاسبية تُشتقّ عند القراءة في
# `statement_merge` ولا تُكتب في المخزَن. فبعد إضافة ثلاثِ هويّاتٍ
# (‏D420) خرج الإحصاءُ **متطابقاً حرفياً** — لأنّه يقيس طبقةً لم تُمسّ
# ويحكم بها على أخرى. وهو عينُ عطب D410: قياسُ الشجرةِ بدل ما يُنفَّذ.
# فالقراءةُ الآن من **البابِ الواحد** الذي يقرأ منه المحرّك.


async def main() -> int:
    try:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        from app.services.market_data import market_service
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0

    syms = sorted(main_market(MARKET_UNIVERSE).keys())
    missing_latest = collections.Counter()
    derived_now = collections.Counter()
    per_symbol_gap = collections.Counter()
    no_statements = 0

    async def _one(s: str):
        try:
            d = await market_service.get_financials(s, allow_supplement=False)
        except Exception:                                         # noqa: BLE001
            return None
        return (d or {}).get("periods") or []

    sem = asyncio.Semaphore(8)

    async def _guarded(s: str):
        async with sem:
            return s, await _one(s)

    res = await asyncio.gather(*(_guarded(s) for s in syms))
    for s, rows in res:
        rows = [r for r in (rows or []) if r.get("as_of")]
        if not rows:
            no_statements += 1
            continue
        latest = max(rows, key=lambda r: str(r.get("as_of")))
        _src = latest.get("field_sources") or {}
        gaps = 0
        for k in NEEDED:
            if isinstance(latest.get(k), (int, float)):
                # وما جاء بهويّةٍ يُعَدّ مكسباً مُعلَناً لا صمتاً
                if "مشتقّ" in str(_src.get(k) or ""):
                    derived_now[k] += 1
                continue
            missing_latest[k] += 1
            gaps += 1
        if gaps:
            per_symbol_gap[gaps] += 1

    print(f"الكون: {len(syms)} رمزاً · بلا قوائمَ تصل المحرّك: {no_statements}\n")
    print(f"  {'البند':22s} {'ناقصٌ في الأحدث':>16s} {'سُدّ باشتقاقٍ مُعلَن':>20s}")
    for k in NEEDED:
        if not (missing_latest[k] or derived_now[k]):
            continue
        print(f"  {k:22s} {missing_latest[k]:>16d} {derived_now[k]:>20d}")

    print(f"\nمجموعُ النقص: **{sum(missing_latest.values())}** بندٍ")
    print(f"وما سُدّ باشتقاقٍ مُعلَن: **{sum(derived_now.values())}** بندٍ")
    print(f"\nتوزيعُ الأوراق بعدد بنودها الناقصة: "
          + "، ".join(f"{n} بندٍ:{c}" for n, c in sorted(per_symbol_gap.items())))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
