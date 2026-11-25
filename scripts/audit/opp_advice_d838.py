#!/usr/bin/env python3
"""حارسُ D838 (الخادم) — التحليلُ الذكيّ من فرصة صقر: آجالُ مدّتها، وسببُ «لا عقد» بالأعداد (المالك 2026-11-25).

قيس على الخادم (‏opp_vs_advice_door_d838): ATR — ستّةَ عشرَ عقداً في أربعة آجال كلُّها بلا عرضٍ وطلب، والجوابُ «لا عقدَ مقبولاً ضمن هذه الشروط».
  ١ أقصرُ أجلٍ من الفرصة (‏min_dte): تُفحص أقربُ ثلاثة آجالٍ تتّسع لمدّتها وحدها — لا الأسبوعُ ولا الشهر.
  ٢ لا عقدَ مقبول: السببُ بالأعداد (بلا عرضٍ وطلب · بلا سيولة · فارقٌ واسع)، وإن كانت كلُّها ميّتةً قيل إنّ الفرصةَ على السهم نفسِه — بميزانيةٍ وبدونها.
  ٣ الطريقُ يقبل ‏min_dte في حدوده ويرفض ما خرج عنها.

    python3 scripts/audit/opp_advice_d838.py
"""
import asyncio
import os
import pathlib
import sys
import tempfile

_SB = tempfile.mkdtemp(prefix="sp_d838_")
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


from app.services import option_advisor as OA   # noqa: E402
from app.services import options_chain as OC   # noqa: E402

EXPS = [{"t": i + 1, "date": d, "dte": n} for i, (d, n) in enumerate((("2026-11-28", 3), ("2026-12-18", 23), ("2027-01-15", 51),
                                                                       ("2027-02-19", 86), ("2027-05-21", 177), ("2027-11-19", 359)))]
asked: list[int] = []
MODE = {"dead": True}


async def fake_chain(sym, t=None):
    if t is None:
        return {"symbol": sym, "price": 100.0, "expirations": EXPS}
    asked.append(t)
    dead = MODE["dead"]
    rows = [{"contract": f"ATR{t}C{k}", "strike": float(k), "last": 3.0, "bid": 0 if dead else 2.9, "ask": 0 if dead else 3.0, "volume": 5 if dead else 400,
             "oi": 0 if dead else 3000, "iv": 40} for k in (90, 95, 100, 105, 110)]
    return {"symbol": sym, "price": 100.0, "calls": rows, "puts": [dict(r, contract=r["contract"].replace("C", "P")) for r in rows]}


async def fake_ctx(sym):
    return {"trend": {"state": "صاعد", "close": 100, "sma50": 95, "sma200": 90, "ret3m": 8.0, "strength": 4}, "hv": 0.3, "news": None, "earnings": None, "events": []}
OC.chain = fake_chain
OA._context = fake_ctx

# ── ١ ──
asked.clear()
r1 = asyncio.run(OA.analyze("ATR", budget=200, side="call", min_dte=75, with_summary=False))
got1 = sorted(set(asked))
asked.clear()
r0 = asyncio.run(OA.analyze("ATR", budget=200, with_summary=False))
got0 = sorted(set(asked))
check(got1 == [4, 5, 6] and r1["expiries"] == ["2027-02-19", "2027-05-21", "2027-11-19"] and any(t in got0 for t in (2, 3)),
      "١ من الفرصة تُفحص أقربُ ثلاثة آجالٍ تتّسع لمدّتها (≥ 75 يوماً) وحدها — وبلا فرصةٍ آجالُ المدى كلُّها كما كانت", f"{r1['expiries']} · {got0}")

# ── ٢ ──
t1 = (r1.get("fit") or {}).get("text") or ""
r_nob = asyncio.run(OA.analyze("ATR", side="call", min_dte=75, with_summary=False))
t2 = (r_nob.get("fit") or {}).get("text") or ""
MODE["dead"] = False
r_ok = asyncio.run(OA.analyze("ATR", budget=2000, side="call", min_dte=75, with_summary=False))
check(("بلا عرضٍ وطلبٍ حيّين" in t1 or "لا عرضَ ولا طلبَ" in t1) and "على السهم نفسِه" in t1 and "ضمن هذه الشروط" not in t1 and t2 == t1 and not r1["best"]
      and r_ok["best"] and (r_ok.get("fit") or {}).get("ok"),
      "٢ لا عقدَ مقبول: السببُ صريحٌ (لا عرضَ ولا طلب)، وكلُّها ميّتةٌ ⇐ «الفرصةُ على السهم نفسِه» — بميزانيةٍ وبدونها؛ وعقودٌ تُتداول تُرشَّح", t1[:120])

# ٢ب بالأعداد: عقودٌ سُعّرت بآخر صفقةٍ ورُفضت (كـ‏ATR على الخادم: ستّةَ عشرَ عقداً)
cards = [{"verdict": "no", "cons": ["لا سعرَ صالحاً لهذا العقد الآن (لا طلبَ ولا عرضَ ولا صفقةً حديثة) — لا يُبنى عليه."]}] * 12 \
    + [{"verdict": "no", "cons": ["لا سيولة: العقودُ المفتوحة 0 والكمّيةُ اليوم 2 — قد لا تجد من يشتري منك."]}] * 3 \
    + [{"verdict": "no", "cons": ["الفارقُ بين العرض والطلب 40٪ (نحو 50 دولار للعقد) — خسارةٌ فوريّة."]}]
w = OA.why_none(cards, "ATR")
check(w.startswith("فُحص 16 عقداً على ATR: 12 بلا عرضٍ وطلبٍ حيّين · 3 بلا سيولة") and "1 فارقُها بين العرض والطلب فوق 15٪" in w and "على السهم نفسِه" in w,
      "٢ب وما سُعّر بآخر صفقةٍ ورُفض: السببُ بالأعداد (بلا عرضٍ وطلب · بلا سيولة · فارقٌ واسع) — كـATR على الخادم", w)

# ── ٣ ──
src = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
ep = src[src.index("async def options_advice("):src.index("@router.get(\"/econ-events\")")]
check("min_dte: int | None = None" in ep and "1 <= min_dte <= 730" in ep and "min_dte=min_dte" in ep,
      "٣ الطريقُ يقبل أقصرَ أجلٍ من الفرصة في حدوده (يومٌ إلى 730) ويمرّره إلى التحليل")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
