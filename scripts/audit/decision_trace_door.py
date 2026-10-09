#!/usr/bin/env python3
"""كاشفُ مصدر القرار لشركةٍ يخالف فيها الفرزُ الصفحة — قارئٌ فقط (الكتابةُ معطَّلة). سلوشنز 7202 افتراضياً.

يحسب الحكمَ كما تحسبه الصفحة (بياناتٌ كاملة) وكما تحسبه المسحة (بلا مصدرٍ مكمِّل) بلا كاش، ويطبع لكلٍّ: القرار وقاعدتَه
وسببَه والسعرَ والسعرَ العادل والدرجة — ثمّ ما في المخزن العميق."""
import asyncio, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
_get = cache.get
cache.get = lambda k: None if str(k).startswith("analysis:") else _get(k)
from app.services.analysis import analyze_company

SYM = "7202"


def show(tag, a):
    d = a.get("decision") or {}
    fin = a.get("financial") or {}
    print(f"{tag}: القرار {d.get('raw')} · القاعدة {d.get('rule_id')} · قابلٌ للتقييم {a.get('evaluable')} · الدرجة {fin.get('score')}"
          f" · السعر {(a.get('price') or {}).get('price') if isinstance(a.get('price'), dict) else a.get('price')}"
          f" · السعرُ العادل {a.get('fair_value')} (حيّ {a.get('fair_value_live')} · مسحة {a.get('fair_value_official_asof')})")
    print(f"      السبب: {str(d.get('reason'))[:300]}")


async def main():
    page = await analyze_company(f"{SYM}.SR")
    show("الصفحة (كاملة)", page or {})
    sweep = await analyze_company(f"{SYM}.SR", allow_supplement=False, official=False)
    show("المسحة (بلا مكمِّل)", sweep or {})
    deep = (lastgood.load("governance:deep") or {}).get(SYM)
    print("المخزنُ العميق:", {k: deep.get(k) for k in ("decision", "source", "v", "at")} if isinstance(deep, dict) else deep)


asyncio.run(main())
