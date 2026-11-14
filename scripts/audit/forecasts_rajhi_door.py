#!/usr/bin/env python3
"""ما تعرضه «التوقعات» فعلاً لبنود الراجحي المالية بعد ‏D728 · D733 — قارئٌ فقط من المخزَّن الذي تقرؤه الصفحة."""
import asyncio, os, re, sys, time
from collections import Counter
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")


async def main():
    from app.services import forecasts as F
    items = await F.get()
    rj = [x for x in items or [] if "الراجحي" in str(x.get("source") or "")]
    print("بنودُ الراجحي في التوقعات:", len(rj), "من", len(items or []))
    print("بالصنف:", Counter(x.get("kind") for x in rj).most_common())
    urls = [str(x.get("url") or "") for x in rj]
    print("بلا رابط:", sum(1 for u in urls if not u), "· PDF:", sum(1 for u in urls if re.search(r"\.pdf($|\?)", u, re.I)),
          "· غيرُ ذلك:", [u[-80:] for u in urls if u and not re.search(r"\.pdf($|\?)", u, re.I)][:5])
    for x in rj[:8]:
        print("  ", x.get("date"), "|", x.get("kind"), "|", str(x.get("title"))[:46], "|", (str(x.get("url"))[-64:] if x.get("url") else "بلا رابط"))


asyncio.run(main())
