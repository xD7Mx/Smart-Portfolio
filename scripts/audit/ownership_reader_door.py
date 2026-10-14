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
    for sym in ("2222", "4013"):
        page = await TO.company_page(sym)
        print(f"\n@@PAGE@@ {sym} · {len(page or '')} حرفاً")
        if not page:
            continue
        base = TO._BASE_RE.search(page).group(1).rstrip("/")
        eps = {m.group(1): m.group(0) for m in TO._EP_RE.finditer(page)}
        from datetime import date, timedelta
        t = date.today()
        for label, p in (("history=0 بلا تاريخ", {"symbol": sym, "history": "0"}),
                         ("history=0 بلغة", {"requestLocale": "en", "symbol": sym, "history": "0"}),
                         ("history=1 بسنة", {"symbol": sym, "history": "1", "fromDate": (t - timedelta(days=365)).strftime("%Y/%m/%d"),
                                             "toDate": t.strftime("%Y/%m/%d")}),
                         ("بلا history", {"symbol": sym})):
            await asyncio.sleep(0.7)
            st, raw = await fetch(f"{base}/{eps['historyOfMajorShareHolder']}", params=p, referer=base)
            body = re.sub(r"<svg\b.*?</svg>|<script\b.*?</script>", " ", raw or "", flags=re.S | re.I)
            trs = re.findall(r"<tr\b.*?</tr>", body, re.S | re.I)
            got = TO.parse_response("major_holders", raw or "") if st == 200 else []
            print(f"@@MAJOR@@ {sym} · {label} · حالة {st} · {len(raw or '')} · صفوف {len(trs)} · مفهومٌ {len(got)} · {got[:3]}")
            for tr in trs[:4]:
                cells = [squash(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<t[hd]\b.*?</t[hd]>", tr, re.S | re.I)]
                print("   |", " | ".join(cells)[:300])
    for s in ():
        rec = await TO.read_symbol(s)
        secs = {k: len(rec[k]) for k in TO.KINDS if rec.get(k)}
        print(f"\n@@READ@@ {s} · البنود {secs} · تعذّر {rec.get('failed')} · {rec.get('error') or ''}")
        for k in TO.KINDS:
            for r in (rec.get(k) or [])[:3]:
                print(f"   [{k}] {r}")


asyncio.run(main())
