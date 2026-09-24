#!/usr/bin/env python3
"""لماذا بقيت ورقةٌ متأخّرة؟ — كلُّ ملفٍّ سنويّ: فتراتُه وحكمُ الصمّام عليها. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/pdf_reject_diag.py
"""
import asyncio, sys
sys.path.insert(0, "/app")
SYMS = ["8210", "2010", "8030", "4330", "8200", "2330", "8230", "4340"]


async def main():
    from app.services import tadawul_pdf as P, tadawul_xbrl as X
    from app.services.tadawul_http import fetch_bytes
    from app.services.tadawul_market import refresh, usable_rows
    if not (usable_rows()[0] or {}):
        await refresh()
    st = X._store()
    for s in SYMS:
        rec = st.get(s) or {}
        an = rec.get("annual") or []
        ref = next((p.get("shares_outstanding") for p in reversed(an + (rec.get("quarterly") or []))
                    if isinstance(p.get("shares_outstanding"), (int, float)) and p["shares_outstanding"] > 0), None)
        links, why = await P.pdf_links(s)
        print(f"\n═ {s} · آخرُ سنة {max((p.get('year') or 0 for p in an), default=0)} · أسهمٌ مرجعية {ref} · روابط {len(links)} {why or ''}")
        for f in links[:10]:
            code, data = await fetch_bytes(f["url"], referer=f["referer"])
            if code != 200 or not data.startswith(b"%PDF"):
                print(f"   {f['filed']} · تحميل {code}"); continue
            r = P.parse_pdf(data)
            tag = "سنويّ" if r.get("annual") else "ليس سنوياً"
            print(f"   {f['filed']} · {tag} · فترات {len(r['periods'])} · {r.get('reason') or ''}")
            if r.get("annual"):
                for p in r["periods"]:
                    print(f"      {p['as_of']} · ربح {p.get('net_income')} · ربحيةُ سهم {p.get('eps')} · أصول {p.get('total_assets')}"
                          f" · حقوق {p.get('equity')} · أسهم {p.get('shares_outstanding')} → {P.valid(p, ref) or 'مقبول'}")
    return 0

sys.exit(asyncio.run(main()))
