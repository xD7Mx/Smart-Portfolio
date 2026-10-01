"""كاشف D574: يعيد بناءَ مستشار الريت من إعلاناته (التوزيعات والتقييم والقوائم الأولية)، ثم يقيس
عودةَ قرار «الراجحي ريت» بعد أن كان «بيانات غير كافية».

    docker exec sp_backend python /app/scripts/audit/reit_interim_rebuild.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


def out(tag, obj):
    print(f"@@{tag}@@ " + json.dumps(obj, ensure_ascii=False, default=str)[:3000])


async def main():
    from app.services import lastgood
    from app.services import reit_advisor as R
    reits = sorted({k.split(":", 1)[1] for k in lastgood.keys_with_prefix("reit:")} | {"4340"})
    out("REITS", reits)
    for s in reits:
        try:
            await R.build(s, force=True)
            ls = R.latest_statement(s)
            out("STMT", {"sym": s, "as_of": (ls or {}).get("as_of"), "nav": (ls or {}).get("nav"),
                         "n": len((R.cached(s) or {}).get("stmts") or [])})
        except Exception as e:                                    # noqa: BLE001
            out("ERR", {"sym": s, "e": repr(e)[:200]})
    from app.services import cache
    for k in [k for k in list(cache._store) if str(k).startswith("analysis:4340")]:
        cache._store.pop(k, None)                                 # في ذاكرة الكاشف وحده
    from app.services.analysis import analyze_company
    a = await analyze_company("4340.SR") or {}
    d = a.get("decision") or {}
    out("DECISION_4340", {"decision": d.get("label") or d.get("decision") or d if not isinstance(d, dict) else
                          {k: d.get(k) for k in ("label", "decision", "action", "reason", "confidence")}})

asyncio.run(main())
