#!/usr/bin/env python3
"""حارسُ D656: تعذّرُ جلبٍ لحظيٌّ من «تداول» لا يُخفي بطاقةَ الأحداث يوماً — قِيس: «الغاز» صفرٌ في 16:59 وثلاثةٌ في 17:01."""
import asyncio, datetime as dt, os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

import app.services.material_events as ME, app.services.tadawul_disclosure as TD   # noqa: E402
from app.services import events_view as EV, cache, lastgood                        # noqa: E402
state = {"n": 1}
async def _ev(sym):
    return {"events": [{"kind": "acquisition", "date": dt.date.today().isoformat(), "title": "Gas acquires Jaco", "url": "u1",
                        "value": 1e8}] * state["n"], "asof": dt.date.today().isoformat()}
async def _det(u):
    return {"title": "الغاز تستحوذ على جاكو"}
ME.events_for, TD.detail = _ev, _det
r1 = asyncio.run(EV.for_display("2080"))
check(len(r1["events"]) == 1 and lastgood.load("events:view:2080"), "١ ما وصل يُعرض ويُحفظ لقطةً")
state["n"] = 0
cache.set("events:view:v2:2080", None, 1)                              # كأنّ كاشَ العرض انقضى
cache._store.pop("events:view:v2:2080", None)
cache.set("events:v1:2080", {"events": []}, 24 * 3600)
r2 = asyncio.run(EV.for_display("2080"))
check(len(r2["events"]) == 1, "٢ وصفرٌ لحظيٌّ بعده يعرض آخرَ ما عُرف — لا تختفي البطاقة", str(len(r2["events"])))
check(cache.get("events:v1:2080") is None, "٣ وصفرُ المستخرِج يُبطَل فيُعاد جلبُه قريباً لا بعد يوم")
_tomb = cache._store.get("events:v1:2080", (0, 1))
check(_tomb[1] is None and _tomb[0] - __import__("time").time() > 24 * 3600,
      "٣ب والإبطالُ شاهدُ قبرٍ أطولُ عمراً من الصفر المحفوظ — فلا يعود من القرص في الدمج (D619)")
exp = cache._store.get("events:view:v2:2080", (0, None))[0] - __import__("time").time()
check(0 < exp <= 10 * 60 + 5, "٤ والعرضُ في هذه الحال لا يُحفظ إلا دقائق", f"{exp:.0f} ثانية")
me = (ROOT / "frontend/src/components/analysis/MaterialEvents.tsx").read_text(encoding="utf-8")
check("{filings(e.filings)}" in me and "جُمعت" not in me, "٥ والبندُ المجموع يقول كم إفصاحاً جمع — رقماً لا تبريراً (D660)")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
