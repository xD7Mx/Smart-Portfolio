#!/usr/bin/env python3
"""كم رمزاً نالت فعلاً أرباحَ اثني عشرَ شهراً؟ — لا يُدَّعى ما لا يُقاس.

    python3 scripts/audit/ttm_coverage.py

بُني مسارُ «أرباحِ اثني عشرَ شهراً» بتحقّقٍ لكلّ رمز (‏D414): تُجمع
أرباعُ سنةٍ كاملةٍ وتُقارَن بسنويّها المنشور، فإن تطابقا قُبل الجمع.
وهو الصوابُ — لكنّه **شرطٌ صارم**، وقد لا يتحقّق إلا لقلّة. وكاشفٌ
سابقٌ (`period_used_vs_available`) وجد أنّ ‎270 من ‎273 لا سنةَ أساسٍ
مشتركةً لها بين المخزنَين.

فميزةٌ تُبنى ولا تعمل ادّعاءٌ بشكلِ شفرة. وهذا الكاشفُ يُخرج الرقمَ
الصادق: كم رمزاً نال مجموعاً مُتحقَّقاً، وكم رُفض، ولماذا — فيُعرَف
هل يبقى العملُ أم يحتاج مصدرَ أرباعٍ أعمق.
"""
from __future__ import annotations

import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")


def main() -> int:
    try:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        from app.services import tadawul_xbrl as X
        from app.services.market_data import _ttm_from
    except (ModuleNotFoundError, ImportError) as e:
        print(f"⚠ بيئةٌ ناقصة ({e}) — لم يُقَس")
        return 0

    syms = sorted(main_market(MARKET_UNIVERSE).keys())
    tally = collections.Counter()
    ok_rows = []
    for s in syms:
        try:
            ann = X.for_symbol(s, "annual") or []
            qtr = X.for_symbol(s, "quarterly") or []
        except Exception:                                         # noqa: BLE001
            tally["تعذّرت القراءة"] += 1
            continue
        if not qtr:
            tally["بلا أرباعٍ محفوظة"] += 1
            continue
        if len(qtr) < 4:
            tally["أرباعٌ دون أربعة"] += 1
            continue
        t = _ttm_from(qtr, ann)
        if t is None:
            tally["أرباعٌ مكرّرةُ التواريخ"] += 1
        elif t.get("unverified"):
            tally["لم يُتحقَّق — لا سنةَ أساس"] += 1
        else:
            tally["مجموعٌ مُتحقَّق"] += 1
            # وغربالٌ خشنٌ على المقام: سهمٌ سعوديٌّ ربحيتُه بالريالات
            # لا بالمئات. فما تجاوز المئةَ مقامُه معطوبٌ على الأرجح —
            # وهو غربالٌ **تقريبيّ** لا حكم، والبوّابةُ الحقيقيةُ في
            # المحرّك تقيس بالسعر لا بعتبةٍ عامّة.
            # والربحيةُ لا تُحسب هنا (‏D418-ب): تُحسب في المحرّك بمقامٍ
            # واحدٍ مُتحقَّقٍ منه. فيُقاس هنا **صافي الربح** وحدَه.
            if not isinstance(t.get("net_income"), (int, float)):
                tally["منها: بلا صافي ربحٍ مجموع"] += 1
            ok_rows.append((s, t.get("as_of"), t.get("verified_on"),
                            t.get("net_income")))

    print(f"الكون: {len(syms)} رمزاً في السوق الرئيسيّ\n")
    for k, v in tally.most_common():
        print(f"  {v:>4}  {k}")
    got = tally["مجموعٌ مُتحقَّق"]
    print(f"\nنالت أرباحَ اثني عشرَ شهراً: **{got} من {len(syms)}**"
          f" ({got * 100 // max(1, len(syms))}٪)")
    for s, a, y, e in ok_rows[:15]:
        print(f"    {s}  حتى {a}  · مُتحقَّقٌ بسنة {y}"
              + (f" · صافي ربحٍ {e:,.0f}" if isinstance(e, (int, float)) else ""))
    if got == 0:
        print("\nالحكم: المسارُ **لا يعمل على أحد** — شرطُ التحقّق صارمٌ"
              " والمخزَنُ لا يحمل ما يُتحقَّق به. فلا يُدَّعى عاملاً،"
              " ويُفتح عطبٌ باسمه لتعميق مخزن الأرباع.")
    elif got < len(syms) // 4:
        print("\nالحكم: يعمل على **أقلّيّة** — الشرطُ صوابٌ ولا يُخفَّف،"
              " والعلاجُ تعميقُ مخزن الأرباع لا تليينُ التحقّق.")
    else:
        print("\nالحكم: يعمل على أكثر السوق.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
