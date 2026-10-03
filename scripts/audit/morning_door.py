"""كاشف (قراءةٌ فقط): تقريرُ ليلة القارئ البصري، وإعلاناتُ صندوق 4346، وسعرُ صافولا حول توزيع حصّة المراعي.

    docker exec sp_backend python /app/scripts/audit/morning_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


def out(tag, obj):
    print(f"@@{tag}@@ " + json.dumps(obj, ensure_ascii=False, default=str)[:3500])


async def main():
    from app.services import lastgood
    out("LAST_RUN", lastgood.load("know:_last_run"))
    keys = [k for k in lastgood.keys_with_prefix("know:") if not k.startswith("know:_")]
    out("KNOW", {"companies": len(keys), "with_files": sum(1 for k in keys if (lastgood.load(k) or {}).get("files"))})
    from app.services import tadawul_disclosure as D
    from app.services.reit_advisor import parse_statement, _STMT_TITLE
    items = await D.list_for("4346", size=80)
    out("T4346", [(i.get("date"), (i.get("title") or "")[:110]) for i in items[:30]])
    for it in items:
        t = it.get("title") or ""
        if _STMT_TITLE.search(t) or "financial" in t.lower():
            det = await D.detail(it["url"])
            txt = (det or {}).get("text") or ""
            out("S4346", {"title": t[:140], "date": it.get("date"), "parsed": parse_statement(txt), "text": txt[:1200]})
            break
    from app.services.market_data import market_service
    pts = await market_service._yahoo()._fetch_chart_points("2050.SR", "10y", "1d")
    cl = [(str(p.get("date"))[:10], p.get("close")) for p in pts or [] if p.get("close")]
    jumps = [(cl[i - 1], cl[i], round(cl[i][1] / cl[i - 1][1] - 1, 3)) for i in range(1, len(cl)) if abs(cl[i][1] / cl[i - 1][1] - 1) > 0.15]
    out("SAVOLA_JUMPS", jumps)
    out("SAVOLA_SAMPLE", [c for c in cl if c[0][:7] in ("2023-12", "2024-06", "2024-12", "2025-06", "2025-12")][::5] + cl[-3:])
    from app.services import fair_value_models as FV
    i = await FV.gather("2050")
    if i:
        out("SAVOLA_IN", {"price": i.price, "shares": i.shares, "hist": i.hist,
                          "annual": [(p.get("as_of"), p.get("shares_outstanding"), p.get("net_income"), p.get("equity")) for p in i.annual[-6:]]})

asyncio.run(main())
