#!/usr/bin/env python3
"""الفترةُ التي يُقيَّم بها ≠ أحدثُ فترةٍ متاحة؟ (‏D412؟)

    python3 scripts/audit/period_used_vs_available.py

قياسان متناقضان على الخادم نفسِه بعد تصحيح حدّ الشيخوخة إلى ‎137 يوماً:

  · سلسلةُ المعلومة: «القوائمُ المحفوظة — وسيطُ العمر **84 يوماً**».
  · مسحةُ التقييم: «شائخةُ الأرقام **266 من 270**» — أي فوق ‎137.

ولا يكذب أحدُهما بالضرورة: الأوّلُ يقيس **أحدثَ ما هو محفوظ**، والثاني
يقيس **أحدثَ فترةٍ استعملها المحرّكُ فعلاً**. فإن كان المحرّكُ يقيّم
بالسنويّ (‏ينتهي ‎2025-12-31 = نحوُ ‎266 يوماً) والربعيُّ الأحدثُ محفوظٌ
ولا يُستعمَل — فذاك عجزُ بناءٍ لا نقصُ إفصاح، وهو أثقلُ ممّا عالجناه:
**نقيّم بأرقامٍ عمرُها ثلاثةُ أضعافِ ما نملك**.

فيُقارَن لكلّ رمزٍ في عيّنةٍ ممتدّة: أحدثُ فترةٍ في المخزَن (سنويٌّ
وربعيّ) مقابل أحدثِ فترةٍ وصلت المحرّكَ. ولا يُصلَح شيءٌ قبل أن يظهر
الفارقُ بعينه.
"""
from __future__ import annotations

import pathlib
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")


def _age(d: str | None) -> int | None:
    if not d:
        return None
    try:
        return (date.today() - date.fromisoformat(str(d)[:10])).days
    except Exception:                                             # noqa: BLE001
        return None


def main() -> int:
    try:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        from app.services import tadawul_xbrl as X
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0

    syms = sorted(main_market(MARKET_UNIVERSE).keys())
    step = max(1, len(syms) // 30)
    probe = syms[::step][:30]

    def _newest(sym: str, kind: str) -> str | None:
        try:
            rows = X.for_symbol(sym, kind) or []
        except Exception:                                         # noqa: BLE001
            return None
        ds = [str(r.get("as_of") or "")[:10] for r in rows if r.get("as_of")]
        return max(ds) if ds else None

    rows, gaps = [], 0
    for s in probe:
        a, q = _newest(s, "annual"), _newest(s, "quarterly")
        rows.append((s, a, q))
        if a and q and q > a:
            gaps += 1

    print(f"عيّنةٌ ممتدّةٌ: {len(probe)} رمزاً")
    print("والمحرّكُ يقرأ **السنويَّ وحدَه** (`get_financials` ← "
          "`for_symbol(sym, 'annual')`)\n")
    print(f"  {'رمز':6s} {'سنويٌّ (المستعمَل)':20s} {'عمر':6s} "
          f"{'ربعيٌّ (المتاح)':20s} {'عمر':6s}")
    for s, a, q in rows:
        _m = "   ← أحدثُ متاحٌ لا يُستعمَل" if (a and q and q > a) else ""
        print(f"  {s:6s} {str(a or '—'):20s} {str(_age(a) or '—'):6s} "
              f"{str(q or '—'):20s} {str(_age(q) or '—'):6s}{_m}")

    _aa = [x for x in (_age(a) for _, a, _ in rows) if x is not None]
    _qq = [x for x in (_age(q) for _, _, q in rows) if x is not None]
    med = lambda v: sorted(v)[len(v) // 2] if v else "—"          # noqa: E731
    print(f"\nوسيطُ عمرِ السنويّ المستعمَل: {med(_aa)} يوماً")
    print(f"وسيطُ عمرِ الربعيّ المتاح:    {med(_qq)} يوماً")
    print(f"أوراقٌ تملك أحدثَ مما تُقيَّم به: {gaps} من {len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
