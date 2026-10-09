#!/usr/bin/env python3
"""مزامنةُ القرار بعد النشر — ما تفعله صفحةُ الشركة حين تُفتح، للشركات التي يخالف فيها قرارُ الفرز قرارَ صفحتها وحدها.

بعد نشرٍ يتبدّل فيه إصدارُ المحرّك تفقد أحكامُ الصفحات (ببياناتٍ أوفى) حمايتَها (D578) فتكتب المسحةُ أحكامَها (ببياناتٍ أقلّ)،
فيقول الفرزُ «انتظار» والصفحةُ «شراء» حتى تُفتح الصفحة (قِيس بعد المرشَّح ٤: سلوشنز 7202). فهذا يحسب كلَّ صفحةٍ بلا كتابة،
ثمّ يحسب المخالِفةَ وحدها كما تُحسب عند فتحها فتكتب حكمَها في المخزن العميق — لا رقمَ يُختلق ولا رقمَ يُغيَّر."""
import asyncio, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
_set, _save = cache.set, lastgood.save
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market, is_nomu
from app.services.analysis import analyze_company

uni = {s: m for s, m in main_market(MARKET_UNIVERSE).items() if not is_nomu(s)}
_label = lambda d: (d.get("label") or d.get("raw")) if isinstance(d, dict) else d   # noqa: E731


async def main():
    deep = lastgood.load("governance:deep") or {}
    cache.set, lastgood.save = (lambda *a, **k: None), (lambda *a, **k: None)
    sem = asyncio.Semaphore(4)

    async def one(s):
        async with sem:
            try:
                return s, await asyncio.wait_for(analyze_company(f"{s}.SR", uni[s].get("name_ar")), timeout=45)
            except Exception:                                      # noqa: BLE001
                return s, None
    res = dict(await asyncio.gather(*(one(s) for s in sorted(uni))))
    diff = []
    for s, a in res.items():
        d = deep.get(s) if isinstance(deep.get(s), dict) else {}
        pl, dl = _label((a or {}).get("decision")), _label(d.get("decision"))
        if pl and dl and pl != dl:
            diff.append((s, pl, dl))
    print(f"قراراتٌ تخالف فيها الصفحةُ الفرز: {len(diff)}")
    cache.set, lastgood.save = _set, _save                          # فتحُ الصفحة: يكتب حكمَها كما يفعل التطبيق
    for s, pl, dl in diff:
        a = await analyze_company(f"{s}.SR", uni[s].get("name_ar"))
        now = _label(((lastgood.load("governance:deep") or {}).get(s) or {}).get("decision"))
        print(f"  {s} {uni[s].get('name_ar')} · الصفحة {pl} · الفرز كان {dl} ← صار {now}")


asyncio.run(main())
