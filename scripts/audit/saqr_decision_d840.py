#!/usr/bin/env python3
"""حارسُ D840 — قرارٌ واحدٌ في صقر و«عقود الخيارات» والتحليل الذكيّ (المالك 2026-11-25: «تكاملٌ في القرار لرفع نسبة النجاح»).

كان الدخولُ الآليُّ وحده يمرّ ببابه، و«عقودُ الخيارات» تُرشّح من مسار السهم ولو لم يوافق صقر، والتحليلُ الذكيّ يقول «مناسب» لعقدٍ يعاكس فرصتَه.
  ١ حكمُ صقر اليوم على السهم من مسحه الأخير: يوافق · يتحفّظ · يرفض · ليس في فرصه — ولا مسحَ حديث ⇐ «غير متوفّر».
  ٢ التحليلُ الذكيّ: «مناسب» لا يُقال إلّا لعقدٍ باتّجاه فرصة صقر الموافَق عليها، والاتّجاهُ افتراضاً اتّجاهُها.
  ٣ ما يعاكسها أو يرفضه صقر ⇐ «أمتنع» (وسببُه بالأعداد)، وما لم يوافق عليه ⇐ «بحذر» في أحسن أحواله.
  ٤ ونسبةُ النجاح بنموذج صقر دون حدّ المالك ⇐ لا «مناسب» — كالدخول الآليّ.
  ٥ الدفتر: التوصيةُ القائمةُ تنكسر إن رفض صقر سهمَها أو عاكسته فرصتُه.

    python3 scripts/audit/saqr_decision_d840.py
"""
import asyncio
import datetime as dt
import os
import pathlib
import sys
import tempfile

_SB = tempfile.mkdtemp(prefix="sp_d840_")
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
from app.services import options_chain as OC    # noqa: E402
from app.services import chart_scan as CS       # noqa: E402
from app.services import saqr_council as CN     # noqa: E402
from app.services import saqr_trader as TR      # noqa: E402

NOW = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
EXPS = [{"t": 1, "date": "2027-02-19", "dte": 86}, {"t": 2, "date": "2027-05-21", "dte": 177}, {"t": 3, "date": "2027-11-19", "dte": 359}]
SCAN = {"market": "us", "read": 50, "items": [], "rejected": []}
CS.fresh = lambda market, days=4: ({**SCAN, "at": NOW} if SCAN is not None else None)


def opp(sym, side="long", verdict="يوافق", decision=None):
    return {"symbol": sym, "side": side, "setup": "ارتدادٌ من الدعم", "horizon": "شهران",
            "council": {"verdict": verdict, "score": 82, "veto": False}, **({"link": {"decision": decision}} if decision else {})}


async def fake_chain(sym, t=None):
    if t is None:
        return {"symbol": sym, "price": 100.0, "expirations": EXPS}
    rows = []
    for k in (90, 95, 100, 105, 110):
        rows.append({"contract": f"{sym}{t}C{k}", "strike": float(k), "last": 0, "bid": 0, "ask": 0, "volume": 400, "oi": 3000})
    calls, puts = [], []
    for r in rows:
        K = r["strike"]
        for call, out in ((True, calls), (False, puts)):
            T = next(e["dte"] for e in EXPS if e["t"] == t) / 365
            px = round(OA.OP.bs_price(100.0, K, T, 0.35, call), 2)
            out.append({**r, "contract": r["contract"] if call else r["contract"].replace("C", "P"), "bid": round(px * 0.98, 2), "ask": round(px * 1.02, 2), "last": px})
    return {"symbol": sym, "price": 100.0, "calls": calls, "puts": puts}


async def fake_ctx(sym):
    return {"trend": {"state": "صاعد", "close": 100, "sma50": 95, "sma200": 90, "ret3m": 8.0, "strength": 4}, "hv": 0.3, "news": None, "earnings": None, "events": []}
OC.chain = fake_chain
OA._context = fake_ctx
run = lambda **kw: asyncio.run(OA.analyze("ABC", with_summary=False, **kw))   # noqa: E731

# ── ١ ──
SCAN["items"] = [opp("ABC"), opp("CAU", verdict="يوافق بتحفّظ"), opp("FLP", decision="انتظار")]
SCAN["rejected"] = [{"symbol": "VET", "side": "long", "why": ["إقالةُ الرئيس التنفيذيّ"]}]
st = {s: CN.stance(s) for s in ("ABC", "CAU", "FLP", "VET", "ZZZ")}
SCAN_bak, SCAN = SCAN, None
st_none = CN.stance("ABC")
SCAN = SCAN_bak
check([st[s]["state"] for s in ("ABC", "CAU", "FLP", "VET", "ZZZ")] == ["approve", "caution", "caution", "veto", "none"]
      and st["ABC"]["text"].startswith("صقر يوافق") and "إقالةُ الرئيس" in st["VET"]["text"] and "ليس في فرص صقر" in st["ZZZ"]["text"]
      and st_none["state"] == "none" and "غيرُ متوفّر" in st_none["text"] and set(CN.opportunities("us")) == {"ABC"},
      "١ حكمُ صقر اليوم من مسحه: يوافق · يتحفّظ (بتحفّظ أو قراءةٍ أخيرةٍ مخالفة) · يرفض بسببه · ليس في فرصه — وبلا مسحٍ «غيرُ متوفّر»",
      " · ".join(f"{s}:{v['state']}" for s, v in st.items()))

# ── ٢ ──
TR.win_floor = lambda: 0.0
r = run(budget=2000)
ok = [c for c in r["best"] if c["verdict"] == "ok"]
check(r["saqr"]["state"] == "approve" and ok and all(c["type"] == "call" for c in r["best"]) and all(c["pros"][0].startswith("صقر يوافق") for c in ok)
      and all((c.get("saqr") or {}).get("p30") is not None for c in r["best"]),
      "٢ التحليلُ الذكيّ باتّجاه فرصة صقر افتراضاً، و«مناسب» عليه موافقتُه ونسبةُ نجاحه بنموذجه",
      f"{[(c['contract'], c['verdict'], (c.get('saqr') or {}).get('p30')) for c in r['best']]}")

# ── ٣ ──
r_put = run(budget=2000, side="put")
SCAN["items"] = [opp("ABC", verdict="يوافق بتحفّظ")]
r_cau = run(budget=2000)
SCAN["items"], SCAN["rejected"] = [], [{"symbol": "ABC", "side": "long", "why": ["إقالةُ الرئيس التنفيذيّ"]}]
r_vet = run(budget=2000)
SCAN["rejected"] = []
r_non = run(budget=2000)
check(not r_put["best"] and all("يعاكس صقر" in c["cons"][0] for c in r_put["refused"]) and "يرفضها صقر" in (r_put.get("fit") or {}).get("text", "")
      and r_cau["best"] and all(c["verdict"] == "warn" for c in r_cau["best"]) and "صقر يتحفّظ" in r_cau["best"][0]["cons"][0]
      and not r_vet["best"] and all("صقر يرفضه اليوم" in c["cons"][0] for c in r_vet["refused"])
      and r_non["best"] and all(c["verdict"] == "warn" for c in r_non["best"]) and r_non["saqr"]["state"] == "none",
      "٣ ما يعاكس فرصةَ صقر أو يرفضه صقر ⇐ «أمتنع» وسببُه بالأعداد؛ وما تحفّظ عليه أو ليس في فرصه ⇐ «بحذر» لا «مناسب»",
      (r_put.get("fit") or {}).get("text", "")[:110])

# ── ٤ ──
SCAN["items"] = [opp("ABC")]
TR.win_floor = lambda: 99.0
r_hi = run(budget=2000)
check(r_hi["best"] and all(c["verdict"] == "warn" for c in r_hi["best"]) and any("دون حدّك 99٪" in " ".join(c["cons"]) or "وحدُّك 99٪" in " ".join(c["cons"]) for c in r_hi["best"]),
      "٤ نسبةُ النجاح دون حدّ المالك ⇐ لا «مناسب» — كالدخول الآليّ تماماً", " | ".join(r_hi["best"][0]["cons"][-2:]) if r_hi["best"] else "")
TR.win_floor = lambda: 0.0

# ── ٥ ──
src = (ROOT / "backend/app/services/option_picks.py").read_text(encoding="utf-8")
lv1 = CN.rule(CN.stance("ABC"), False)[0]
SCAN["items"], SCAN["rejected"] = [], [{"symbol": "ABC", "side": "long", "why": ["تحقيقٌ رسميّ"]}]
lv2 = CN.rule(CN.stance("ABC"), True)[0]
check(lv1 == "no" and lv2 == "no" and 'lv, sw = CN.rule(CN.stance(e["symbol"]), e["type"] == "call")' in src and 'st, why = "broken"' in src
      and "if s not in approved:" in src and 'dc = CN.decide(stc, k, k.get("price"))' in src,
      "٥ الدفتر: التوصيةُ القائمةُ تنكسر إن رفض صقر سهمَها أو عاكسته فرصتُه، والجديدةُ من فرصه الموافَق عليها بنسبة نجاحٍ لا تقلّ عن الحدّ")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
