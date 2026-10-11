"""كاشفُ تشخيص: لماذا اختلف قرارُ الصفحة عن الفرز في ثمانٍ (‏parity_gate · run 38130632842، صباحَ الأحد والسوقُ مفتوح)
وكان صفراً في بوابة المرشَّح؟ قارئٌ فقط — الكاشُ والمخازنُ معطَّلةُ الكتابة والقراءة لتحليلٍ طازج.

لكلّ رمز: ما في المخزن العميق الذي يقرؤه الفرز (القرارُ وقاعدتُه ومصدرُه وتاريخُه وإصدارُ محرّكه ونسبةُ العادل إلى السعر)،
وقرارُ الصفحة طازجاً (بياناتٌ مكمِّلة) بقاعدته وسعره، وقرارُ المسحة طازجاً (بلا مكمِّل) — فيُعرف أيّ الثلاثة اختلف ولماذا.
"""
import asyncio
import sys

sys.path.insert(0, "/app")
from app.services import cache, lastgood   # noqa: E402
_load0 = lastgood.load
cache.set = lambda *a, **k: None
cache.get = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
lastgood.load = lambda key, *a, **k: None if str(key).startswith("analysis:") else _load0(key, *a, **k)

SYMS = ("2370", "4013", "4165", "4335", "4337", "4344", "4345", "4350")


def _d(dec):
    if not isinstance(dec, dict):
        return str(dec)
    return f"{dec.get('label') or dec.get('raw')} [{dec.get('rule_id')}]"


async def main():
    from app.services.analysis import analyze_company, _ENGINE_V
    deep = _load0("governance:deep") or {}
    print(f"═ المحرّك الحاليّ {_ENGINE_V}")
    for s in SYMS:
        d = deep.get(s) if isinstance(deep.get(s), dict) else {}
        print(f"═ {s}\n   الفرز: {_d(d.get('decision'))} · مصدر {d.get('source', 'صفحة')} · {d.get('at')} · v {d.get('v')}"
              f" · عادل/سعر {d.get('value_to_price')} · عادل {d.get('fair_value')}")
        for lab, sup, off in (("الصفحة", True, True), ("المسحة", False, False)):
            try:
                a = await asyncio.wait_for(analyze_company(f"{s}.SR", None, db=None, allow_supplement=sup, official=off), timeout=60) or {}
                px, fv = a.get("price"), a.get("fair_value")
                print(f"   {lab}: {_d(a.get('decision'))} · قابلٌ للحكم {a.get('evaluable')} · سعر {px} · عادل {fv}"
                      + (f" · عادل/سعر {round(fv / px, 3)}" if fv and px else ""))
            except Exception as e:                                # noqa: BLE001
                print(f"   {lab}: تعذّر {type(e).__name__}")


asyncio.run(main())
