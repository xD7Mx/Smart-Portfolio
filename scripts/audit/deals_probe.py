#!/usr/bin/env python3
"""مسبارُ الصفقات الخاصة — يقيس على الخادم ما حُجب عن حاويتي (D273).

    docker exec sp_backend python /app/scripts/audit/deals_probe.py
    docker exec sp_backend python /app/scripts/audit/deals_probe.py --apply

يطبع: أوصلت الصفحةُ؟ · اكتُشف النداء؟ · كم صفّاً؟ · **أسماءُ الحقول كما
وردت** · كم صفقةً فُهمت. فإن لم تُطابَق الأسماءُ عُرفت الحقيقيةُ من الطبع
بدل تخمينها. ولا يكتب شيئاً إلا بـ`--apply`.
"""
from __future__ import annotations

import asyncio
import json
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")


async def main() -> int:
    apply = "--apply" in sys.argv[1:]
    from app.services import special_deals as sd
    from app.services.tadawul_http import fetch

    status, body = await fetch(sd.PAGE)
    print(f"صفحةُ الصفقات الخاصة: HTTP {status} · {len(body or '')} حرفاً")
    if status != 200 or not body:
        return 1
    mb, me = sd._BASE_RE.search(body), sd._EP_RE.search(body)
    print(f"أساسُ الصفحة: {'وُجد' if mb else 'لم يوجد'}")
    print(f"نداءُ الجدول: {me.group(1) if me else 'لم يوجد — اطبع أسماءَ النداءات أدناه'}")
    if not me:
        import re
        names = sorted(set(re.findall(r"=NJ([A-Za-z]{4,40})=/", body)))
        print("النداءاتُ الموجودةُ في الصفحة: " + (", ".join(names) or "لا شيء"))
        return 1

    rows, why = await sd.fetch_rows()
    if why:
        print(f"تعذّر: {why}")
        return 1
    print(f"صفوفٌ خام: {len(rows)}")
    if rows:
        print("أسماءُ الحقول كما وردت:")
        print("  " + ", ".join(sorted(rows[0].keys())))
        print("أوّلُ صفٍّ كما ورد:")
        print("  " + json.dumps(rows[0], ensure_ascii=False)[:400])
    deals = sd.normalize(rows)
    print(f"صفقاتٌ فُهمت: {len(deals)} من {len(rows)}")
    for d in deals[:5]:
        print("  " + json.dumps(d, ensure_ascii=False))
    if len(deals) < len(rows):
        print("\nما لم يُفهَم يُترك عمداً. وإن كان الفارقُ كبيراً فالأسماءُ "
              "أعلاه هي الحقيقة — تُضاف إلى FIELDS في special_deals.py.")
    if apply:
        print("\n" + json.dumps(await sd.refresh(), ensure_ascii=False))
    return 0


raise SystemExit(asyncio.run(main()))
