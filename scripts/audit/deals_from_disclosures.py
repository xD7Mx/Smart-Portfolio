#!/usr/bin/env python3
"""هل تُفصَح الصفقاتُ الخاصة في إفصاحات «تداول»؟ — قياسٌ واحد.

    docker exec sp_backend python /app/scripts/audit/deals_from_disclosures.py

قِيس أن صفحةَ الصفقات الخاصة لم تبقَ عامّةً في «تداول» (مسارُها يُصرَف،
وصفرُ روابطَ في قائمتها)، وأن «أرقام» تبيعها. وبقي بابٌ رسميٌّ مبنيٌّ
عندنا: **الإفصاحات**. فيُسأل: كم إفصاحاً يذكر «صفقة خاصة»، وما نصُّها؟
ولا يُبنى شيءٌ قبل الجواب.
"""
from __future__ import annotations

import asyncio
import re
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

WORDS = re.compile(r"صفقة\s*خاصة|صفقات\s*خاصة|صفقة\s*متفاوض|كمية\s*كبيرة"
                   r"|Special\s*Deal", re.I)


async def main() -> int:
    from app.services.tadawul_announcements import fetch_tadawul_announcements

    try:
        items = await fetch_tadawul_announcements(force=True)
    except Exception as e:                                        # noqa: BLE001
        print(f"تعذّر جلبُ الإفصاحات: {type(e).__name__}: {e}")
        return 1
    print(f"إفصاحاتٌ وصلت: {len(items)}")
    if items:
        d = [str(i.get("date") or "") for i in items if i.get("date")]
        if d:
            print(f"مداها: {min(d)} … {max(d)}")
        print("عيّنةٌ من العناوين:")
        for i in items[:5]:
            print(f"   {i.get('date','')} · {i.get('symbol','')} · "
                  f"{str(i.get('title',''))[:90]}")

    hits = [i for i in items
            if WORDS.search(f"{i.get('title','')} {i.get('type','')}")]
    print(f"\nإفصاحاتٌ تذكر صفقةً خاصة: {len(hits)}")
    for i in hits[:15]:
        print(f"   {i.get('date','')} · {i.get('symbol','')} · "
              f"{str(i.get('title',''))[:110]}")
    if not hits:
        print("   (لا شيء — فالصفقاتُ الخاصة لا تُفصَح بهذا اللفظ في ما وصل)")
    return 0


raise SystemExit(asyncio.run(main()))
