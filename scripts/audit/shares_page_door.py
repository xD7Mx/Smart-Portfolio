"""كاشف (قراءةٌ فقط): هل في صفحة الشركة عددُ الأسهم المصدرة أو رأسُ المال؟ — لحَكَمِ عدد الأسهم (D600).

    docker exec sp_backend python /app/scripts/audit/shares_page_door.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for
    from app.services.tadawul_xbrl import ORIGIN
    for s in ("4083", "1835", "2222"):
        st, page = await fetch(ORIGIN + (row_for(s) or {}).get("company_url"))
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", page or ""))
        for kw in ("Issued Shares", "Paid Capital", "Paid Up Capital", "Shares Outstanding", "Number of Shares",
                   "Par Value", "Market Cap", "Authorized Capital", "Paid-up"):
            for m in list(re.finditer(re.escape(kw), txt, re.I))[:2]:
                print(f"@@{s}@@ [{kw}] …{txt[m.start():m.end() + 140]}", flush=True)

asyncio.run(main())
