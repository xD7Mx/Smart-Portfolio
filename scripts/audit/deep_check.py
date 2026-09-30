"""كاشفٌ (قراءةٌ فقط): هل بقي الحصادُ العميق في المخزن؟ وإجراءاتُ الشركة (المنح) من «تداول».

    docker exec sp_backend python /app/scripts/audit/deep_check.py
"""
import asyncio
import json
import re
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_xbrl as X
    st = X._store()
    for s in ("1120", "2050", "4200", "2222"):
        rec = st.get(s) or {}
        print("@@STORE@@" + json.dumps({"s": s, "as_of": rec.get("as_of"),
                                         "annual": [str(p.get("as_of"))[:10] for p in rec.get("annual") or []],
                                         "quarterly": [str(p.get("as_of"))[:10] for p in rec.get("quarterly") or []],
                                         "files": len(rec.get("files") or []) if isinstance(rec.get("files"), list) else rec.get("files")},
                                        ensure_ascii=False))
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for
    url = (row_for("1120") or {}).get("company_url")
    full = X.ORIGIN + url if url and url.startswith("/") else url
    stc, page = await fetch(full)
    mb = X._BASE.search(page or "")
    ep = next((m.group(0) for m in X._NJ.finditer(page or "") if m.group(1) == "getCorporateAction"), None)
    print("@@CA_EP@@", stc, bool(mb), ep)
    if mb and ep:
        for params in ({}, {"requestLocale": "en"}):
            s2, body = await fetch(mb.group(1).rstrip("/") + "/" + ep, params=params, referer=full)
            txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body or ""))
            print("@@CA@@" + json.dumps({"status": s2, "len": len(body or ""), "head": (body or "")[:1500],
                                         "text": txt[:1500]}, ensure_ascii=False))


asyncio.run(main())
