#!/usr/bin/env python3
"""مسارُ الاستكمال لورقةٍ واحدة كما يجري في الحصاد (8210). قارئٌ فقط — لا يحفظ.

    docker exec sp_backend python /app/scripts/audit/pdf_trace_one.py
"""
import asyncio, sys
sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_pdf as P, tadawul_xbrl as X
    from app.services.tadawul_market import refresh, usable_rows
    if not (usable_rows()[0] or {}):
        await refresh()
    for s in ("8230", "2330", "1320"):
        rec = await X.read_symbol(s)
        an = (rec or {}).get("annual") or []
        qu = (rec or {}).get("quarterly") or []
        print(f"\n═ {s} · read_symbol → سنوات {[p.get('as_of') for p in an]} · مصادر {[p.get('source','XBRL') for p in an]}")
        last = max((p["year"] for p in an if p.get("source") != "تداول — PDF"), default=0)
        ref = next((p.get("shares_outstanding") for p in reversed([p for p in an if p.get("source") != "تداول — PDF"] + qu)
                    if isinstance(p.get("shares_outstanding"), (int, float)) and p["shares_outstanding"] > 0), None)
        rep = {}
        more = await P.read_annuals(s, after_year=last, ref_shares=ref, report=rep)
        print(f"   آخرُ XBRL {last} · مرجع {ref} · قرئ {[p['as_of'] for p in more]} · تقرير {rep}")
    return 0

sys.exit(asyncio.run(main()))
