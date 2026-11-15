#!/usr/bin/env python3
"""مُرسِلُ التقرير اليوميّ (‏D746): يكتب تقريرَ جلسة اليوم لكلّ محفظةٍ ويرسله ملفَّ PDF مؤرَّخاً إلى تلغرام كما يفعل المجدولُ بعد الإغلاق.
لا يمسّ المحفظةَ ولا أرقامَها — يكتب في ذاكرة قسم الأبحاث وحدها، ويطبع ما أُرسل."""
import asyncio, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")


async def main():
    from app.services import research_desk as RD
    rep = await RD.compose_all(send=True)
    print("أُرسل:", rep)
    for pid in rep:
        r = RD.load_report(pid)
        fin, heavy = (r["market"].get("fin") or {}), [h["name"] for h in r["market"].get("heavy") or []]
        print(f"  محفظة {pid}: مكرّر {fin.get('pe') and round(fin['pe'], 2)} · دفترية {fin.get('pb') and round(fin['pb'], 2)} · "
              f"تغطية {fin.get('cover')} · الأكبرُ وزناً {heavy} · إقليمي {len((r.get('regional') or {}).get('rows') or [])}")


asyncio.run(main())
