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
        js = squash(page[max(0, mm.start() - 2600):mm.start()])
        js = js[js.rfind("function"):] if "function" in js else js
        print("@@JS@@ …" + js[-1400:])
    for h in ("false", "true", "0", "1"):
        p = TO.call_params("major_holders", sym)
        p["history"] = h
        await asyncio.sleep(0.7)
        st, raw = await fetch(f"{base}/{eps['historyOfMajorShareHolder']}", params=p, referer=base)
        body = re.sub(r"<svg\b.*?</svg>|<script\b.*?</script>", " ", raw or "", flags=re.S | re.I)
        trs = re.findall(r"<tr\b.*?</tr>", body, re.S | re.I)
        got = TO.parse_response("major_holders", raw or "") if st == 200 else []
        print(f"\n@@MAJOR@@ history={h!r} · حالة {st} · {len(raw or '')} · صفوف {len(trs)} · مفهومٌ {len(got)} · {got[:2]}")
        for tr in trs[:6]:
            cells = [squash(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<t[hd]\b.*?</t[hd]>", tr, re.S | re.I)]
            print("   |", " | ".join(cells))
        print("   النصُّ بعد النموذج:", squash(re.sub(r"<[^>]+>", " ", body))[:900])
        if trs[1:2]:
            print("   خامُ صفّ:", squash(trs[1])[:700])
    for s in ("4013",):
        await asyncio.sleep(1.0)
        rec = await TO.read_symbol(s)
        secs = {k: len(rec[k]) for k in TO.KINDS if rec.get(k)}
        print(f"\n@@READ@@ {s} · البنود {secs} · تعذّر {rec.get('failed')} · {rec.get('error') or ''}")
        for k in TO.KINDS:
            for r in (rec.get(k) or [])[:3]:
                print(f"   [{k}] {r}")


asyncio.run(main())
