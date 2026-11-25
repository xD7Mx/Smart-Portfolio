#!/usr/bin/env python3
"""حارسُ D843 — «لاحظتُ بطئاً عند تحميل التطبيق للمحتوى والصفحات» (المالك 2026-11-25).

قيس على الخادم (‏perf_door_d843 · perf_door2_d843): طلباتُ الصفحة تنتهي معاً بعد ثوانٍ (المحفظةُ 7–13ث، والإشعاراتُ 17ث خلف طلبٍ واحد) وهي
وحدَها في عمليةٍ مستقلّة أقلُّ من نصف ثانية — شيءٌ متزامنٌ يحبس حلقةَ الخادم؛ ولسانُ الأخبار في رأس كلّ صفحةٍ يجلب الأرشيفَ كلَّه (‏638KB)
ليعرض اثني عشر عنواناً؛ وكلُّ طلبٍ من طلبات المحفظة الستّة يعيد حفظَ الحيازات ولو لم يتغيّر سعر.
  ١ رقيبُ الحلقة يسجّل كلَّ حبسٍ فوق 400ms بمدّته ومكانه — ويعمل مع إقلاع التطبيق.
  ٢ لسانُ الأخبار: أحدثُ ثمانين عنواناً بلا ملخّصاتها، وحين يعرض الأخبارَ وحده — وصفحةُ السوق بالأرشيف كاملاً كما كانت.
  ٣ تحديثُ أسعار الحيازات لا يكتب ما لم يتغيّر.

    python3 scripts/audit/perf_d843.py
"""
import asyncio
import json
import os
import pathlib
import sys
import tempfile
import time

os.environ["SP_STATE_DIR"] = tempfile.mkdtemp(prefix="sp_d843_")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import loop_watch as LW   # noqa: E402


def hog(sec):
    t = time.time()
    while time.time() - t < sec:
        pass


async def run():
    LW.start()
    await asyncio.sleep(0.3)
    hog(0.9)
    await asyncio.sleep(0.2)
    hog(0.1)                                       # دون العتبة — لا يُسجَّل
    await asyncio.sleep(0.4)
    LW.stop()
asyncio.run(run())
rows = json.load(open(LW.path(), encoding="utf-8"))
main = (ROOT / "backend/main.py").read_text(encoding="utf-8")
check(len(rows) == 1 and 800 <= rows[0]["ms"] <= 1300 and any("hog" in w for w in rows[0]["where"]) and "loop_watch.start()" in main,
      "١ رقيبُ الحلقة يسجّل الحبسَ فوق 400ms بمدّته ومكانه في الشيفرة (‏hog) ولا يسجّل ما دونه — ويعمل مع الإقلاع", json.dumps(rows, ensure_ascii=False)[:200])

mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
api = (ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")
tk = (ROOT / "frontend/src/components/common/MarketTicker.tsx").read_text(encoding="utf-8")
mp = (ROOT / "frontend/src/pages/MarketPage.tsx").read_text(encoding="utf-8")
check("limit: int | None = None, lite: bool = False" in mk and "query = query.limit(max(1, min(int(limit), 500)))" in mk and '"summary": None if lite else n.summary' in mk
      and 'params: { lang: "ar", limit: 80, lite: true }' in api and "marketApi.newsTicker()" in tk and "enabled: isOwner && wantNews" in tk
      and 'marketApi.news("ar")' not in tk and "marketApi.news(language)" in mp,
      "٢ لسانُ الأخبار: أحدثُ ثمانين عنواناً بلا ملخّصاتها، ويُجلب حين يعرض الأخبارَ وحده — وصفحةُ السوق بالأرشيف كاملاً")

ho = (ROOT / "backend/app/api/v1/endpoints/holdings.py").read_text(encoding="utf-8")
blk = ho[ho.index("async def refresh_holdings_prices"):ho.index("return fxs")]
check("abs(float(h.last_price) - float(p[\"price\"])) < 1e-9" in blk and "abs(float(h.unrealized_profit) - (mv - inv)) < 1e-6" in blk
      and blk.index("continue") < blk.index("changed = True") and "if changed:\n        await db.commit()" in blk,
      "٣ تحديثُ أسعار الحيازات لا يكتب حيازةً لم يتغيّر سعرُها ولا قيمتُها ولا ربحُها — ولا حفظَ إن لم يتغيّر شيء")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
