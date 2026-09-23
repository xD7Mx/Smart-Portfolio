#!/usr/bin/env python3
"""مساراتُ عيّنةٍ من الأوراق التي سعرُها العادل دون 0.4× السعر. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fv_paths_low.py
"""
import asyncio, sys
sys.path.insert(0, "/app")


async def main():
    from app.services.analysis import analyze_company
    for s in ("2001", "4160", "2290", "7200", "2082", "2030", "8010", "4200", "2370", "1301"):
        an = await analyze_company(f"{s}.SR", allow_supplement=False) or {}
        fv = an.get("fair_value_detail") or {}
        ms = [(m.get("name"), m.get("value")) for m in fv.get("methods") or []]
        print(f"═ {s} · سعر {an.get('price')} · قيمة {fv.get('value')} · صنف {fv.get('archetype') or (an.get('governance_standard') or {}).get('archetype')}"
              f" · قطاع {an.get('sector')} · بيانات {fv.get('data_asof')}")
        for n, v in ms:
            print(f"     {n:<34} {v}")
        for m in fv.get("methods") or []:
            if m.get("inputs"):
                print(f"       ↳ {m.get('name')}: {str(m.get('inputs'))[:220]}")
        print(f"     ملاحظة: {str(fv.get('note') or fv.get('why') or '')[:200]}")
    return 0

sys.exit(asyncio.run(main()))
