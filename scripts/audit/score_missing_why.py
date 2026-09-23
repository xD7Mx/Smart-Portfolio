#!/usr/bin/env python3
"""أيُّ الأوراق خرجت بلا درجةِ جودة — ولماذا (D430).

    docker exec sp_backend python /app/scripts/audit/score_missing_why.py

قِيس على خادم المالك: مسحةُ التقييم بعد إصلاحات D428 خرجت «لها درجةُ
جودة: 251» وكانت قبلها بساعة 270 — تسعَ عشرةَ ورقةً فقدت درجتَها في
مسحةٍ واحدة، والسعرُ العادلُ في الوقت نفسِه ارتفع (266 ← 268). فلا
يُستنتَج سببٌ قبل أن يُرى: يُحلَّل كلُّ رمزٍ في السوق الرئيسيّ كما تحلّله
المسحة، ويُطبع لكلّ ورقةٍ بلا درجة: صنفُها، وهل وصلت قوائمُها، وما قاله
المحرّكُ في موضع الدرجة. قارئٌ فقط — لا يكتب في مخزن.
"""
from __future__ import annotations

import asyncio
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")


async def main() -> int:
    try:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        from app.services.analysis import analyze_company
        from app.services.statement_merge import archetype_of
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0

    syms = sorted(main_market(MARKET_UNIVERSE).keys())
    sem = asyncio.Semaphore(6)
    missing: list[tuple[str, str, str]] = []
    kinds: collections.Counter = collections.Counter()

    async def _one(s: str):
        async with sem:
            try:
                a = await analyze_company(f"{s}.SR", allow_supplement=False)
            except Exception as e:                                # noqa: BLE001
                return s, None, f"استثناء: {type(e).__name__}: {e}"[:140]
            return s, a, None

    for s, a, err in await asyncio.gather(*(_one(s) for s in syms)):
        if err:
            missing.append((s, archetype_of(s) or "?", err))
            kinds["استثناء"] += 1
            continue
        if not a:
            continue
        fin = a.get("financial") if isinstance(a.get("financial"), dict) else {}
        sc = fin.get("score")
        if sc is None:
            gov = a.get("governance") if isinstance(a.get("governance"), dict) else {}
            sc = gov.get("score")
        if isinstance(sc, (int, float)):
            continue
        why = (fin.get("unavailable_reason") or fin.get("why")
               or fin.get("note") or fin.get("reason")
               or (a.get("governance") or {}).get("reason")
               if isinstance(a.get("governance"), dict) else None)
        keys = sorted(k for k in fin.keys())[:10] if fin else []
        n_per = len(((a.get("financials") or {}).get("periods") or [])) \
            if isinstance(a.get("financials"), dict) else "?"
        missing.append((s, archetype_of(s) or "?",
                        f"قوائم={n_per} · سبب={why!s:.90} · مفاتيح={keys}"))
        kinds[str(why)[:60]] += 1

    print(f"الكون: {len(syms)} · بلا درجةِ جودة: **{len(missing)}**\n")
    for s, arch, d in missing[:40]:
        print(f"  {s} [{arch}] — {d}")
    print("\nالأسبابُ مجموعةً:")
    for k, n in kinds.most_common():
        print(f"  {n}× {k}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
