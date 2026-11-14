#!/usr/bin/env python3
"""كاشفُ روابط تقارير الراجحي المالية (ملاحظةُ المالك 2026-11-14: «رابطُها ليس سليماً — يظهر رمزُ مشاركةٍ لا التقرير») — قارئٌ فقط.

لكلّ بندٍ من قائمة البحوث: كلُّ روابط ‎/-/media/‎ أو ‎.pdf‎ في شجرته بمساراتها، وما اختاره القارئُ الحاليّ."""
import asyncio, json, os, re, sys, time
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None


async def main():
    from app.services import research_reports as R
    from app.services.tadawul_http import smart_flow
    seen = {"n": 0}

    def plan():
        st, page = yield {"url": R.ARC_PAGE, "timeout": 40}
        ps = R.arc_params(page) if st == 200 else []
        print("الصفحة:", st, "· معاملات:", bool(ps))
        if not ps:
            return []
        p = {**ps[0], "category": "", "pageNo": 1}
        st2, raw = yield {"url": R.ARC_API, "params": p, "referer": R.ARC_PAGE,
                          "headers": {"X-Requested-With": "XMLHttpRequest", "Accept": "application/json, text/javascript, */*"}}
        print("القائمة:", st2, len(raw or ""))
        data = json.loads(raw or "null")
        items = data.get("Items") if isinstance(data, dict) else data
        for it in (items or [])[:4]:
            lv = list(R._leaves(it))
            title = next((v for pth, v in lv if pth and pth[-1] == "Title" and "Categories" not in pth and "Companies" not in pth), None)
            print("— البند:", (title or "")[:70])
            for pth, v in lv:
                if re.search(r"\.pdf($|\?)|/-/media/|https?://", v, re.I):
                    print("   ", "/".join(pth[-3:]), "→", v[:160])
        got = R.arc_items(raw)
        for g in got[:4]:
            print("اختيارُ القارئ:", g["url"][:160])
        return []
    await smart_flow(plan, warm=R.ARC + "/ar", timeout=40)
    # ما تعرضه «التوقعات» فعلاً لبنود الراجحي — من المخزَّن الذي تقرؤه الصفحة
    from app.services import forecasts as F
    items = await F.get()
    rj = [x for x in items or [] if "الراجحي" in str(x.get("source") or "") or "rajhi" in str(x.get("url") or "").lower()]
    print("بنودُ الراجحي في التوقعات:", len(rj), "من", len(items or []))
    from collections import Counter
    print("نطاقاتُ روابطها:", Counter(re.sub(r"^https?://([^/]+).*", r"\1", str(x.get("url") or "")) for x in rj).most_common(6))
    for x in rj[:8]:
        print("  ", x.get("date"), "|", x.get("kind"), "|", str(x.get("title"))[:50], "|", str(x.get("url"))[:150], "| via", x.get("via"))


asyncio.run(main())
