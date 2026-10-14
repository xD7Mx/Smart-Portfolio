"""كاشفُ D708 (قراءةٌ فقط — لا يحفظ): قارئُ الملكية الجديد على صفحات «تداول» الحيّة. قِيس أنّ النداءات تعيد HTML (‏run 38583682788)،
وأنّ ‏historyOfMajorShareHolder يطلب ‎symbol · fromDate · toDate · history. فيطبع: كيف تضبط شيفرةُ الصفحة ‎history وصيغةَ التاريخ، وما يعيده
النداءُ الثالث بكلّ قيمةٍ مرئيّة، ثمّ ‎read_symbol الجديدةَ على أربع شركات — البنودُ وعددُ الصفوف وأوّلُها — بلا كتابة.

    docker exec sp_backend python /app/scripts/audit/ownership_reader_door.py
"""
import asyncio
import os
import re
import sys
import time

os.environ["TZ"] = "Asia/Riyadh"                 # كخادم التطبيق (main.py) — فتعمل اللقطةُ في عمليةٍ مستقلّة
if hasattr(time, "tzset"):
    time.tzset()
sys.path.insert(0, "/app")


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


async def main():
    from app.services import tadawul_ownership as TO
    from app.services.tadawul_http import fetch
    sym = "1120"
    page = await TO.company_page(sym)
    print(f"@@PAGE@@ {sym} · {len(page or '')} حرفاً")
    if not page:
        return
    base = TO._BASE_RE.search(page).group(1).rstrip("/")
    eps = {m.group(1): m.group(0) for m in TO._EP_RE.finditer(page)}
    m = list(re.finditer(r"NJhistoryOfMajorShareHolder", page))
    for mm in m[:2]:
        print("@@JS@@ …" + squash(page[max(0, mm.start() - 1700):mm.start() + 80])[-1500:])
    for h in ("history", "false", "true", "1", "0", "Y", "N", ""):
        for span in (365, 30):
            p = TO.call_params("major_holders", sym)
            p["history"] = h
            if span != 365:
                from datetime import date, timedelta
                t = date.today()
                p["fromDate"] = (t - timedelta(days=span)).strftime("%Y/%m/%d")
            await asyncio.sleep(0.7)
            st, raw = await fetch(f"{base}/{eps['historyOfMajorShareHolder']}", params=p, referer=base)
            got = TO.parse_response("major_holders", raw or "") if st == 200 else []
            print(f"@@MAJOR@@ history={h!r} · {span} يوماً · حالة {st} · {len(raw or '')} · مفهومٌ {len(got)} · "
                  + (str(got[:3]) if got else repr(squash(raw)[:300])))
            if st == 200 and len(raw or "") > 200 and not got:
                print("   مطلعٌ أطول:", squash(raw)[:1500])
    for s in ("2222", "1120", "2010", "7010"):
        await asyncio.sleep(1.0)
        rec = await TO.read_symbol(s)
        secs = {k: len(rec[k]) for k in TO.KINDS if rec.get(k)}
        print(f"\n@@READ@@ {s} · البنود {secs} · تعذّر {rec.get('failed')} · {rec.get('error') or ''}")
        for k in TO.KINDS:
            for r in (rec.get(k) or [])[:3]:
                print(f"   [{k}] {r}")


asyncio.run(main())
