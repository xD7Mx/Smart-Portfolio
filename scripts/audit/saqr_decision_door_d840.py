#!/usr/bin/env python3
"""كاشفُ D840 على الخادم — القرارُ الواحد: كم فرصةً وافق عليها صقرٌ اليوم، وحكمُه على كلّ توصيةٍ قائمةٍ في «عقود الخيارات»،
وحكمُ التحليل الذكيّ على أوّل فرصةٍ موافَقٍ عليها. قراءةٌ فقط — لا يكتب شيئاً.

    docker exec sp_backend python /app/scripts/audit/saqr_decision_door_d840.py
"""
import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in (ROOT / "backend", pathlib.Path("/app")):
    if p.exists():
        sys.path.insert(0, str(p))

from app.services import chart_scan as CS        # noqa: E402
from app.services import saqr_council as CN      # noqa: E402
from app.services import option_picks as OP      # noqa: E402
from app.services import saqr_trader as TR       # noqa: E402

d = CS.fresh("us")
print("المسح:", (d or {}).get("at"), "· فرص:", len((d or {}).get("items") or []), "· مرفوضة:", len((d or {}).get("rejected") or []))
ap = CN.opportunities("us")
print("بموافقةٍ كاملة:", len(ap), sorted(ap)[:20])
print("حدُّ النجاح:", TR.win_floor())
for b in OP.book_budgets():
    bk = OP.book_load(b)
    print(f"\nدفترُ {b}$ — قائمة {len(bk['open'])}:")
    for e in bk["open"]:
        st = CN.stance(e["symbol"])
        print(f"  {e['contract']}: {CN.rule(st, e['type'] == 'call')[0]} — {st['text'][:110]}")


async def adv():
    from app.services import option_advisor as OA
    for s in sorted(ap)[:2]:
        r = await OA.analyze(s, budget=300, with_summary=False)
        print(f"\nالتحليلُ الذكيّ {s}: {r.get('saqr', {}).get('state')} · best:",
              [(c["contract"], c["verdict"], (c.get("saqr") or {}).get("p30")) for c in r.get("best") or []], "·", ((r.get("fit") or {}).get("text") or "")[:120])
asyncio.run(adv())
