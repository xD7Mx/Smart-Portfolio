#!/usr/bin/env python3
"""‏D806 — إعادةُ كتابة تقرير جلسةٍ بتاريخها (مهمّةُ ‏research_rewrite في ‏ops.yml).

قال المالك (2026-11-24): «التقريرُ اليوميّ كاتبٌ: لا توجد أخبار — عيبٌ لا أقبله»، ثمّ: «نعم، أرسله اليوم».
فالمهمّة: تُقرأ أوّلاً تقاريرُ الجهات التي فشلت قراءتُها، ثمّ يُكتب تقريرُ الجلسة لكلّ محفظة (بلا إرسال)؛ ثمّ — بإذن المالك وحده
(‏SP_SEND=1 · «YYYY-MM-DD+send») — يُرسَل تقريرُ المحفظة الافتراضية إلى تلغرام، **ولا يُرسَل تقريرٌ بلا أخبار** مهما كان.

    docker exec -e SP_DAY=2026-11-24 -e SP_SEND=1 sp_backend python /tmp/research_rewrite.py
"""
import os
import time

os.environ.setdefault("TZ", "Asia/Riyadh")
time.tzset()

import asyncio  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, "/app")


async def main() -> int:
    from datetime import date
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Portfolio
    from app.services import research_desk as RD
    day = date.fromisoformat(os.environ["SP_DAY"])
    send = os.environ.get("SP_SEND") == "1"
    print("القراءة:", await RD.ingest(budget=6, days=5))
    print("الكتابة:", await RD.compose_all(send=False, day=day))
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Portfolio.id, Portfolio.is_default)
                                 .where(Portfolio.is_archived.is_(False)).order_by(Portfolio.id))).all()
    main_pid = next((pid for pid, d in rows if d), rows[0][0] if rows else None)
    r = RD.load_report(main_pid, day.isoformat()) if main_pid is not None else None
    if not r or r.get("date") != day.isoformat():
        print("لا تقريرَ لهذه الجلسة — لا يُرسَل شيء")
        return 1
    print(f"التقرير: مصدرُ النصّ {r.get('text_source')} · محليّ {len(r.get('local') or [])} · عالميّ {len(r.get('global') or [])}"
          f" · عنوان {'نعم' if r.get('headline') else 'لا'} · مصادر {r.get('n_sources')}")
    if not send:
        return 0
    if not (r.get("local") or r.get("global")):
        print("لا يُرسَل: التقريرُ بلا أخبار")
        return 1
    ok = await RD.deliver(r)
    print("الإرسالُ إلى تلغرام:", "تمّ" if ok else "تعذّر")
    if ok:
        sent = RD._load("sent.json", {})
        sent[day.isoformat()] = main_pid
        RD._save("sent.json", dict(sorted(sent.items())[-60:]))
    return 0 if ok else 1


sys.exit(asyncio.run(main()))
