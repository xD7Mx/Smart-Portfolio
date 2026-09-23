#!/usr/bin/env python3
"""أسماءُ صفوفِ الدَّينِ وتكلفةِ التمويل التي لا نطابقها (D425).

    docker exec sp_backend python /app/scripts/audit/debt_label_gap.py

قِيس على خادم المالك بإحصاء الباب الواحد: أكبرُ ما بقي من النقص ثلاثةُ
بنودٍ بعينها — `total_debt` في ‎40 ورقة، و`ebit` في ‎33، و`interest_expense`
في ‎32 — ومجموعُها ‎105 من ‎126. وهي متلازمةٌ: `ebit` يُشتقّ من تكلفة
التمويل، وتغطيةُ الفوائد تقوم على الاثنين، فسقوطُ اسمٍ واحدٍ يُسقط
مساراً كاملاً من مسارات السعر العادل.

وظننتُ أوّلاً أنّ السببَ صياغاتٌ عربيةٌ غيرُ مخرَّطة («تكاليف تمويل» ·
«أعباء تمويلية»)، فقِيست الخريطةُ فظهر أنّ أسماءَ الملفّ **إنجليزيةٌ**
كلُّها. فالظنُّ سقط، ولا يُبنى على ظنٍّ ثانٍ: تُقرأ أسماءُ الصفوف
**كما وردت** في ملفّات الأوراق الناقصة بعينها، وتُرتَّب بتكرارها،
فتُضاف إلى الخريطة بالحرف.

قارئٌ فقط — لا يكتب في خريطةٍ ولا في مخزَن.
"""
from __future__ import annotations

import asyncio
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

GAP_FIELDS = ("total_debt", "ebit", "interest_expense")
MAX_SYMS = 40           # يكفي لترتيب الأسماء بتكرارها، ويحدُّ الشبكة

# معنيانِ فقط — لا نبحث عن كلّ شيءٍ بل عن هذين البندَين بعينهما
LOOK = {
    "دَينٌ/قروض": r"borrow|loan|sukuk|debt securit|financ(?:e|ing) lease|"
                  r"murabaha|tawarruq|term facilit|credit facilit",
    "تكلفةُ تمويل": r"financ(?:e|ial) (?:cost|charge|expense)|interest expense|"
                    r"interest on|cost of funds|special commission expense",
}


async def main() -> int:
    try:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        from app.services import tadawul_xbrl as X
        from app.services.market_data import market_service
        from xbrl_labels import _unmatched
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0

    syms = sorted(main_market(MARKET_UNIVERSE).keys())

    async def _needs(s: str) -> str | None:
        try:
            d = await market_service.get_financials(s, allow_supplement=False)
        except Exception:                                         # noqa: BLE001
            return None
        rows = [r for r in ((d or {}).get("periods") or []) if r.get("as_of")]
        if not rows:
            return None
        last = max(rows, key=lambda r: str(r.get("as_of")))
        miss = [k for k in GAP_FIELDS
                if not isinstance(last.get(k), (int, float))]
        return s if miss else None

    sem = asyncio.Semaphore(8)

    async def _g(s):
        async with sem:
            return await _needs(s)

    need = [s for s in await asyncio.gather(*(_g(s) for s in syms)) if s]
    print(f"أوراقٌ ينقصها أحدُ البنود الثلاثة: **{len(need)}** من {len(syms)}")
    picks = need[:MAX_SYMS]
    print(f"تُقرأ ملفّاتُ {len(picks)} منها\n")

    found: dict[str, collections.Counter] = {k: collections.Counter()
                                             for k in LOOK}
    example: dict[str, str] = {}
    read_ok = 0
    why: collections.Counter = collections.Counter()

    async def _one(s: str):
        async with sem:
            try:
                rows, err = await _unmatched(X, s)
            except Exception as e:                                # noqa: BLE001
                return s, None, type(e).__name__
            return s, rows, err

    for s, rows, err in await asyncio.gather(*(_one(s) for s in picks)):
        if not rows:
            why[str(err or "لا صفوف")] += 1
            continue
        read_ok += 1
        for name, val in rows:
            for meaning, pat in LOOK.items():
                if re.search(pat, name, re.I):
                    found[meaning][name] += 1
                    example.setdefault(name, f"{s} = {val}")

    print(f"قُرئت ملفّاتُ {read_ok} ورقة"
          + (f" · تعذّرَ: {dict(why)}" if why else ""))
    total = 0
    for meaning, cnt in found.items():
        print(f"\n═ {meaning} — أسماءٌ غيرُ مطابَقة: {len(cnt)} ═")
        for name, n in cnt.most_common(18):
            total += 1
            print(f"  {n:>3}× {name}")
            print(f"       مثالٌ: {example.get(name, '')}")
    if not total:
        print("\nلا اسمَ غيرَ مطابَقٍ بهذين المعنيَين — فالنقصُ غيابُ بندٍ"
              " لا عجزُ خريطة، ولا يُعالَج بإضافةِ اسم.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
