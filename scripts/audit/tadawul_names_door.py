"""كاشفٌ للقراءة فقط: أسماءُ الشركات العربية كما تنشرها «تداول» (بأمر المالك: المصدرُ الرسميّ).

    docker exec sp_backend python /app/scripts/audit/tadawul_names_door.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")
from app.services import tadawul_market as TM            # noqa: E402

SEE = {"4083", "4080", "4130", "8040", "8280", "2287", "2240", "2340", "9532", "1050", "7010", "1211"}


async def main():
    for page in (TM.PAGE, TM.NOMU_PAGE):
        rows, why = await TM.fetch_rows(page, locale="ar")
        print(f"══ {page[-25:]}: صفوف {len(rows)} · {why}")
        if rows:
            print("   مفاتيحُ الصفّ:", sorted(rows[0].keys()))
        for r in rows:
            m = re.search(r"\b(\d{4})\b", str(r.get("companyRef") or r.get("symbol") or ""))
            if m and m.group(1) in SEE:
                print("  ", m.group(1), {k: v for k, v in r.items() if isinstance(v, str) and re.search(r"[؀-ۿ]", v)})


asyncio.run(main())
