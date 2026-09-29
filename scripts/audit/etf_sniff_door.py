"""كاشفٌ للقراءة فقط (D518): ما الذي تطلبه صفحةُ الصناديق فعلاً لتعيد صناديقها؟

بلا معامِلها أعادت الخدمةُ أسهمَ الرئيسيّ. فيُفتح المتصفّحُ على الصفحة وتُسجَّل
نداءاتُها إلى الخدمة بمساراتها ومعاملاتها وجسمِ ما عاد (FETCH_METHOD §٤ج).

    docker exec sp_backend python /app/scripts/audit/etf_sniff_door.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")
from app.services.browser_fetch import sniff               # noqa: E402
from app.services.tadawul_market import ETF_PAGE            # noqa: E402


async def main():
    res = await sniff(ETF_PAGE, settle_ms=12000, want=r"(?i)NJ|Market|json|fund|etf", max_bodies=4)
    calls = [c for c in (res.get("calls") or []) if c.get("type") in ("xhr", "fetch")]
    print(f"نداءات {len(calls)}")
    for c in calls[:20]:
        print(f"   {c.get('status')} {c.get('method', '')} {str(c.get('url'))[:220]} · {c.get('size')}")
        if c.get("post"):
            print(f"      post: {str(c.get('post'))[:300]}")
    for k, v in list((res.get("bodies") or {}).items())[:3]:
        syms = sorted(set(re.findall(r"\b(94\d\d)\b", str(v))))
        print(f"   ⟵ {str(k)[:160]} · رموز94 {syms[:10]}\n      {str(v)[:400]}")


asyncio.run(main())
