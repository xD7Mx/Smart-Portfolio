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


def main() -> int:
    try:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        from app.services import tadawul_xbrl as X
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0

    syms = sorted(main_market(MARKET_UNIVERSE).keys())
    # ما ينقص **أحدثَ فترةٍ مستعمَلة**، وهل يوجد في أيّ فترةٍ محفوظة
    missing_latest = collections.Counter()
    held_elsewhere = collections.Counter()
    no_row_at_all = collections.Counter()
    per_symbol_gap = collections.Counter()
    no_statements = 0

    for s in syms:
        try:
            ann = X.for_symbol(s, "annual") or []
            qtr = X.for_symbol(s, "quarterly") or []
        except Exception:                                         # noqa: BLE001
            continue
        rows = [r for r in (ann + qtr) if r.get("as_of")]
        if not rows:
            no_statements += 1
            continue
        latest = max(rows, key=lambda r: str(r.get("as_of")))
        gaps = 0
        for k in NEEDED:
            v = latest.get(k)
            if isinstance(v, (int, float)):
                continue
            missing_latest[k] += 1
            gaps += 1
            # هل يحمله صفٌّ آخرُ محفوظٌ لهذه الورقة؟
            if any(isinstance(r.get(k), (int, float)) for r in rows):
                held_elsewhere[k] += 1
            else:
                no_row_at_all[k] += 1
        if gaps:
            per_symbol_gap[gaps] += 1

    print(f"الكون: {len(syms)} رمزاً · بلا قوائمَ محفوظةٍ: {no_statements}\n")
    print(f"  {'البند':22s} {'ناقصٌ في الأحدث':>16s} "
          f"{'نملكه في فترةٍ أخرى':>20s} {'لا نملكه أبداً':>16s}")
    for k in NEEDED:
        m = missing_latest[k]
        if not m:
            continue
        print(f"  {k:22s} {m:>16d} {held_elsewhere[k]:>20d} "
              f"{no_row_at_all[k]:>16d}")

    _read_gap = sum(held_elsewhere.values())
    _src_gap = sum(no_row_at_all.values())
    print(f"\nفجوةُ قراءةٍ (نملكه ولا نقرؤه): **{_read_gap}** بندٍ")
    print(f"فجوةُ مصدرٍ (لا نملكه): **{_src_gap}** بندٍ")
    print(f"\nتوزيعُ الأوراق بعدد بنودها الناقصة: "
          + "، ".join(f"{n} بندٍ:{c}" for n, c in sorted(per_symbol_gap.items())))

    if _read_gap > _src_gap:
        print("\nالحكم: الأكثرُ **فجوةُ قراءة** — وعلاجُها شفرةٌ لا ذكاء:"
              " يُكمَل البندُ من فترةٍ محفوظةٍ بمصدرها المعلَن. فتُبدأ بها"
              " قبل أيّ مستخرِجٍ لغويّ، فهي أرخصُ وأوثق.")
    else:
        print("\nالحكم: الأكثرُ **فجوةُ مصدر** — فلا تُسدّ بشفرةٍ عندنا،"
              " وهنا يصحّ المستخرِجُ من إفصاحٍ منشورٍ بتحقّقٍ قاعديّ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
