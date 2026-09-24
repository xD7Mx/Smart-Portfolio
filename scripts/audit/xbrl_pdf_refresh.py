#!/usr/bin/env python3
"""يستكمل من قوائم «تداول» PDF كلَّ ورقةٍ تقف قوائمُها المحفوظة قبل السنة الماضية (D476).

    docker exec sp_backend python /app/scripts/audit/xbrl_pdf_refresh.py

يكتب في مخزن القوائم ما يكتبه الحصادُ الليليُّ نفسُه (مصدرٌ رسميٌّ لا أرقامُ المالك)،
ويطبع لكلّ ورقة: آخرَ سنةٍ قبلُ وبعدُ، وعيّنةً من الأرقام، وأسبابَ الرفض.
"""
import asyncio, collections, sys
from datetime import date
sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_market import refresh as mkt, usable_rows
    if not (usable_rows()[0] or {}):
        await mkt()
    rows = usable_rows()[0] or {}
    st = X._store()
    cut = date.today().year - 1
    stale = []
    for s in sorted(str(k).replace(".SR", "") for k in rows):
        rec = st.get(s) or {}
        last = max((p.get("year") or 0 for p in rec.get("annual") or []), default=0)
        if last < cut:
            stale.append((s, last))
    print(f"أوراقٌ تقف قوائمُها قبل {cut}: {len(stale)}")
    rep = await X.refresh([s for s, _ in stale], conc=4)
    print("الحصاد:", rep)
    st = X._store()
    moved = collections.Counter()
    for s, before in stale:
        rec = st.get(s) or {}
        an = rec.get("annual") or []
        after = max((p.get("year") or 0 for p in an), default=0)
        moved["تقدّمت" if after > before else "بقيت"] += 1
        tail = an[-1] if an else {}
        print(f"  {s}: {before} → {after} · {tail.get('source', 'XBRL')} · إيراد {tail.get('revenue')} · ربح {tail.get('net_income')}"
              f" · حقوق {tail.get('equity')} · ربحيةُ سهم {tail.get('eps')} · أسهم {tail.get('shares_outstanding')}")
    print("الخلاصة:", dict(moved))
    return 0

sys.exit(asyncio.run(main()))
