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

_SB = tempfile.mkdtemp(prefix="sp_d843_")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
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

# ٤ مخزنُ «آخر قيمةٍ صالحة»: داخل الحلقة لا يُقرأ الملفُّ كلُّه حين كتبه غيرُها — يُنعَش في خيطٍ جانبيّ وتخدم النسخةُ الحاليةُ حتى يتمّ
from app.services import lastgood as LG   # noqa: E402
LG.save("a", {"v": 1})
LG.flush()
other = json.load(open(LG._PATH, encoding="utf-8"))
other["b"] = {"data": {"v": 2}, "saved_at": time.time()}
time.sleep(0.02)
json.dump(other, open(LG._PATH, "w", encoding="utf-8"))        # عمليةٌ أخرى تكتب
calls = {"n": 0}
_orig = LG._read_disk


def slow_read():
    calls["n"] += 1
    time.sleep(0.6)
    return _orig()
LG._read_disk = slow_read


async def in_loop():
    t0 = time.monotonic()
    a = LG.load("a")
    b0 = LG.load("b")
    dt = time.monotonic() - t0
    await asyncio.sleep(1.0)
    return dt, a, b0, LG.load("b")
dt, a, b0, b1 = asyncio.run(in_loop())
LG._read_disk = _orig
check(dt < 0.1 and (a or {}).get("v") == 1 and b0 is None and (b1 or {}).get("v") == 2 and calls["n"] == 1,
      "٤ مخزنُ «آخر قيمةٍ صالحة»: داخل حلقة الخادم لا يُقرأ الملفُّ كلُّه حين كتبه غيرُها (كان يحبسها حتى 35ث) — يُنعَش في خيطٍ جانبيٍّ مرّةً "
      "وتخدم النسخةُ الحاليةُ حتى يتمّ، ثمّ يُرى ما كتبه غيرُها", f"{dt * 1000:.0f}ms · قراءات {calls['n']} · {b0} ⇐ {b1}")

# ٥ سجلُّ حالة السوق: سؤالُ الساعة يقرأ ذيلَه لا السجلَّ كلَّه
import datetime as _dt   # noqa: E402
from app.services import market_state as MS   # noqa: E402
MS._OBS = os.path.join(_SB, "obs.jsonl")
with open(MS._OBS, "w", encoding="utf-8") as fh:
    for i in range(60000):
        fh.write(json.dumps({"at": "2026-11-24T10:00", "code": 1}) + "\n")
    for i in range(30):
        fh.write(json.dumps({"at": "2026-11-25T10:%02d" % i, "code": 2}) + "\n")
t0 = time.monotonic()
obs = MS._today_obs(_dt.datetime(2026, 11, 25, 12, 0))
ms = (time.monotonic() - t0) * 1000
src = (ROOT / "backend/app/services/market_state.py").read_text(encoding="utf-8")
check(len(obs) == 30 and obs[0]["at"].endswith("10:00") and ms < 60 and "f.readlines()" not in src,
      "٥ سؤالُ الساعة (كلَّ عشرين ثانيةً من كلّ صفحة) يقرأ ذيلَ سجلّ حالة السوق لا السجلَّ كلَّه (كان يحبس الخادمَ حتى 6.3ث)", f"{len(obs)} · {ms:.0f}ms")

# ٦ الكتابةُ إلى القرص لا تجوّع الخادم: دقيقةٌ بين كتابات الملفّين، وتسلسلٌ واحدٌ لا اثنان، واليتيمُ يُكنس عند الإقلاع
from app.services import cache as C   # noqa: E402
cs = (ROOT / "backend/app/services/cache.py").read_text(encoding="utf-8")
lg = (ROOT / "backend/app/services/lastgood.py").read_text(encoding="utf-8")
sd = os.path.dirname(C._path())
os.makedirs(sd, exist_ok=True)
old_t, new_t = os.path.join(sd, "tmpold.tmp"), os.path.join(sd, "tmpnew.tmp")
for f in (old_t, new_t, LG._PATH + ".tmp.999"):
    open(f, "w").write("x")
os.utime(old_t, (time.time() - 7200, time.time() - 7200))
os.utime(LG._PATH + ".tmp.999", (time.time() - 7200, time.time() - 7200))
swept = C.sweep_orphans()
check(C._WRITE_EVERY >= 60 and LG._FLUSH_INTERVAL >= 60 and "json.dumps(v, ensure_ascii=False)\n        except" not in cs
      and swept == 2 and os.path.exists(new_t) and not os.path.exists(old_t) and "_c.sweep_orphans()" in main,
      "٦ ملفّا الذاكرة (86MB و29MB) يُكتبان كلَّ دقيقةٍ لا كلَّ خمس ثوانٍ وبتسلسلٍ واحد — كانت كتابتُهما تجوّع حلقةَ الخادم — "
      "والنسخُ المؤقّتةُ اليتيمةُ تُكنس عند الإقلاع (ولا تُمسّ الحديثة)", f"{C._WRITE_EVERY} · {LG._FLUSH_INTERVAL} · كُنس {swept}")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
