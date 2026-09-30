"""كاشفٌ (قراءةٌ فقط): لماذا لم يعمق تاريخُ الراجحي؟ يقرأ ملفّاته كلّها بلا حفظ ويطبع
فتراتِ كلّ ملفّ، ومخزنَه الحاليّ، وحضورَه في لقطة «تداول».

    docker exec sp_backend python /app/scripts/audit/rajhi_deep.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_market import row_for
    from app.services.tadawul_http import fetch
    s = "1120"
    print("@@SNAP@@", bool((row_for(s) or {}).get("company_url")))
    rec = X._get(s) or {}
    print("@@STORE@@", json.dumps({"as_of": rec.get("as_of"), "annual": [str(p.get("as_of"))[:10] for p in rec.get("annual") or []],
                                   "quarterly": [str(p.get("as_of"))[:10] for p in rec.get("quarterly") or []]}))
    files, why = await X.filings_for_ex(s)
    print("@@FILES@@", len(files), why)
    for f in files:
        st, html = await fetch(X.ORIGIN + f["url"])
        g = X.parse(html or "") if st == 200 else {}
        print("@@F@@", json.dumps({"filed": f["filed"], "st": st, "kind": g.get("kind"),
                                    "periods": [(str(p.get("as_of"))[:10], p.get("col"), bool(p.get("bank_nfi") or p.get("net_income")))
                                                for p in g.get("periods") or []]}, ensure_ascii=False))
    r = await X.read_symbol(s, max_files=30)
    print("@@READ@@", json.dumps({"annual": [str(p.get("as_of"))[:10] for p in (r or {}).get("annual") or []],
                                  "quarterly": [str(p.get("as_of"))[:10] for p in (r or {}).get("quarterly") or []]}))


asyncio.run(main())
