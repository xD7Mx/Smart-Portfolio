#!/usr/bin/env python3
"""ما الذي يرفعه التحليلُ حين «تتعذّر» الورقة (D424).

    docker exec sp_backend python /app/scripts/audit/analyze_raises.py

قِيس على خادم المالك: مسحةُ التقييم «تعذّرت 268 من 273 · لها سعرٌ عادل:
صفر»، والسلسلةُ «محرّكُ السعر العادل — صامتٌ=6». و`_one` في المسحة تمسك
كلَّ استثناءٍ وتُسجّله في مستوى **debug** ثمّ تُعيد `None`، فتُعَدّ الورقةُ
«متعذّرةً» بلا اسمِ خطأٍ ولا موضع. فسقوطُ سوقٍ كاملٍ يظهر رقماً في
تقريرٍ ولا يظهر سببُه في سجلٍّ — وذاك أخطرُ من السقوط.

فيُنادى التحليلُ هنا **بلا مِمْسَك**: يُطبَع صنفُ الخطأ ونصُّه وآخرُ
إطارٍ في شفرتنا، لعيّنةٍ من الرموز. قارئٌ فقط.
"""
from __future__ import annotations

import asyncio
import pathlib
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

SAMPLE = ("1010", "2222", "2010", "1120", "4001", "2280", "1211", "4300")


async def main() -> int:
    try:
        from app.services.analysis import analyze_company
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0

    kinds: dict[str, int] = {}
    for s in SAMPLE:
        try:
            a = await analyze_company(f"{s}.SR", allow_supplement=False)
        except Exception as e:                                    # noqa: BLE001
            tb = traceback.extract_tb(e.__traceback__)
            ours = [f for f in tb if "/app/app/" in f.filename
                    or "/backend/app/" in f.filename]
            last = ours[-1] if ours else (tb[-1] if tb else None)
            where = (f"{pathlib.Path(last.filename).name}:{last.lineno} "
                     f"في {last.name} — {last.line}") if last else "?"
            key = f"{type(e).__name__}: {e}"
            kinds[key] = kinds.get(key, 0) + 1
            print(f"✘ {s} — {key}\n    {where}")
            continue
        if not a:
            print(f"✘ {s} — التحليلُ ردّ فارغاً بلا استثناء")
            continue
        fv = a.get("fair_value")
        why = (a.get("fair_value_detail") or {}).get("unavailable_reason")
        print(f"✔ {s} — سعرٌ عادل={fv} · درجة="
              f"{(a.get('financial') or {}).get('score')}"
              + (f" · امتناعٌ: {why}" if fv is None else ""))

    if kinds:
        print("\nأصنافُ الخطأ مجموعةً:")
        for k, n in sorted(kinds.items(), key=lambda x: -x[1]):
            print(f"  {n}× {k}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
