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
    try:
        from app.data.universe import is_main
    except Exception:                                              # noqa: BLE001
        is_main = lambda x: not x.startswith("9")                  # noqa: E731
    for s in sorted(str(k).replace(".SR", "") for k in rows if is_main(str(k).replace(".SR", ""))):
        rec = st.get(s) or {}
        last = max((p.get("year") or 0 for p in rec.get("annual") or []), default=0)
        if last < cut:
            stale.append((s, last))
    # التأمينُ والصناديقُ العقاريةُ أوّلاً، ودفعاتٌ بميزانيةِ وقتٍ دون حدّ المهمّة (ساعة)
    stale.sort(key=lambda x: (0 if x[0].startswith(("80", "81", "82", "83")) else 1 if x[0].startswith(("433", "434", "435")) else 2, x[0]))
    print(f"أوراقٌ تقف قوائمُها قبل {cut}: {len(stale)}")
    import time
    t0, done = time.monotonic(), []
    for i in range(0, len(stale), 4):
        if time.monotonic() - t0 > 45 * 60:
            print(f"ميزانيةُ الوقت نفدت — بقي {len(stale) - i} للدفعة التالية")
            break
        chunk = [s for s, _ in stale[i:i + 4]]
        print("الحصاد:", chunk, await X.refresh(chunk, conc=2))
        done += stale[i:i + 4]
    stale = done
    st = X._store()
    moved = collections.Counter()
    for s, before in stale:
        if False:
            pass
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
