#!/usr/bin/env python3
"""تشخيص: نصُّ إعلانات العقود كما يصل — لبناء مستخرِجٍ صارم (طيبة 2.4 تريليون خطأ · الحفر 90 مليار · علم بلا قيمة). قارئٌ فقط."""
import asyncio, re, sys
sys.path.insert(0, "/app")
from app.services.tadawul_disclosure import list_for, detail
RX = re.compile(r"contract|award|purchase order|signing of an? (?:agreement|memorandum)", re.I)
FIN = re.compile(r"facilit|financing|loan|sukuk|murabaha", re.I)

async def main():
    for s in ("4090", "2381", "7203", "4322", "4325", "1303"):
        rows = [a for a in await list_for(s, 60) if RX.search(a.get("title") or "") and not FIN.search(a.get("title") or "")]
        print(f"\n══ {s} · {len(rows)} عقود")
        for a in rows[:3]:
            d = await detail(a["url"]) or {}
            print(f"  ── {a['date']} · {a['title'][:110]}")
            body = (d.get("text") or "").split("لا تتحمل أي من هيئة السوق المالية")[0]   # ما بعد إخلاء المسؤولية حشوُ الصفحة
            for ln in body.split("\n"):
                if "|" in ln:
                    print("     ", ln[:240])
asyncio.run(main())
