#!/usr/bin/env python3
"""قوائمُ المؤمِّنين في «تداول»: ما الملفّاتُ المودَعة، وما يفهمه قارئُنا منها؟ قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/insurer_xbrl_door.py

لكلّ مؤمِّنٍ: أحدثُ الملفّات بتاريخ إيداعها، ولكلّ ملفٍّ: نوعُه وفتراتُه وبنودُه
المطابَقة — أو أوّلُ أسماء البنود فيه إن لم يُفهم، ليُعرف الاسمُ الذي فاتنا.
ثمّ ما هو محفوظٌ لدينا اليوم.
"""
import asyncio, re, sys
sys.path.insert(0, "/app")

SYMS = ["8010", "8210", "8230"]


async def main():
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import refresh, usable_rows
    if not (usable_rows()[0] or {}):
        await refresh()
    for s in SYMS:
        files, why = await X.filings_for_ex(s)
        print(f"\n═ {s} · ملفّات {len(files)} · {why or ''}")
        for f in files[:8]:
            st, html = await fetch(X.ORIGIN + f["url"])
            if st != 200 or not html:
                print(f"   {f['filed']} · HTTP {st}"); continue
            got = X.parse(html)
            ps = got.get("periods") or []
            print(f"   {f['filed']} · {got.get('kind')} · فترات {len(ps)} · {[p.get('as_of') for p in ps]}")
            if ps:
                p = ps[0]
                print("      ", {k: p.get(k) for k in ("revenue", "net_income", "equity", "total_assets", "eps", "insurer_layout", "revenue_source")})
            else:
                names = re.findall(r"<td[^>]*>\s*([A-Za-z][^<]{3,90}?)\s*</td>", html)[:40]
                print("       لم يُفهم — أوّلُ البنود:", names)
        rec = X._store().get(s) or {}
        print(f"   المحفوظ: as_of={rec.get('as_of')} · سنوي {[p.get('as_of') for p in rec.get('annual') or []]} · ربعي {[p.get('as_of') for p in (rec.get('quarterly') or [])][-4:]}")
    return 0

sys.exit(asyncio.run(main()))
