"""كاشف (قراءةٌ فقط): أيُّ المصدرين أحدث لكلّ شركة — جدولُ «المعلومات المالية» في صفحة الشركة أم ملفّاتُ XBRL؟
أحدثُ تاريخٍ في جداول الصفحة (ميزانيةٌ ربعية) مقابلَ أحدثِ فترةٍ مخزّنةٍ من XBRL ومقابلَ آخرِ إعلان نتائج.
عيّنةٌ: التأمينُ كلُّه وعشرون من بقية السوق.

    docker exec sp_backend python /app/scripts/audit/profile_vs_xbrl_door.py
"""
import asyncio
import re
import sys
import time

sys.path.insert(0, "/app")


async def main():
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for, usable_rows
    from app.services.tadawul_xbrl import ORIGIN, for_symbol
    from app.services.results_announcements import latest
    from app.services.statement_merge import archetype_of
    rows = usable_rows()[0] or {}
    syms = sorted(rows)
    ins = [s for s in syms if archetype_of(s) == "insurance"]
    rest = [s for s in syms if s not in ins and s[:1] in "1234"][::9][:20]
    tally = {"page_newer": 0, "xbrl_newer": 0, "same": 0, "page_none": 0}
    t0 = time.time()
    for s in ins + rest:
        url = (row_for(s) or {}).get("company_url")
        if not url:
            continue
        st, page = await fetch(ORIGIN + url)
        dates = re.findall(r"<th[^>]*>\s*(20\d\d-\d\d-\d\d)\s*</th>", page or "")
        pmax = max(dates) if dates else None
        xq = [p.get("as_of") for p in (for_symbol(s, "quarterly") or []) + (for_symbol(s, "annual") or []) if p.get("as_of")]
        xmax = max(xq) if xq else None
        ra = (latest(s) or {}).get("as_of")
        k = "page_none" if not pmax else "same" if pmax == xmax else "page_newer" if (not xmax or pmax > xmax) else "xbrl_newer"
        tally[k] += 1
        print(f"@@{s}@@ {archetype_of(s)} page={pmax} xbrl={xmax} announce={ra} kb={len(page or '') // 1024} {k}", flush=True)
    print(f"@@TALLY@@ {tally} secs={round(time.time() - t0)}", flush=True)

asyncio.run(main())
