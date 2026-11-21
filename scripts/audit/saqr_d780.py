#!/usr/bin/env python3
"""حارسُ D780 — «أغلق الآن» و«أغلق بسعرٍ محدَّد» للمركز القائم (2026-11-21).

قال المالك: «عند الضغط على زرّ إغلاق المركز المفتوح ضع خيار أغلق الآن كما هو موجود، وضع خيار أغلق بسعرٍ محدَّد». فأمرُ بيعٍ محدَّدٌ للمركز كلِّه:
يُباع متى بلغ الطلبُ سعرَه — وإن كان الطلبُ فوقه الآن والسوقُ مفتوح بِيع الآن بالطلب (كأمر الوسيط المحدَّد) — ويبقى حتى يُنفَّذ أو يلغيه المالك.

    python3 scripts/audit/saqr_d780.py
"""
import asyncio, os, pathlib, sys, tempfile   # noqa: E401
_SB = tempfile.mkdtemp()
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


from app.services import saqr_trader as SQ   # noqa: E402
from app.services import live_quote as LQ   # noqa: E402

# ١ القاعدة: يُباع متى بلغ الطلبُ سعرَ الإغلاق — لمركز المالك ولمركز صقر — ولا يُباع دونه
P = {"type": "call", "entry_px": 1.0, "stop": 0.6, "peak": 1.0, "target": 999, "take_x": 3.0, "close_px": 1.25}
own = {**P, "owner": True, "stop": 0.0, "take_x": None}
r = [SQ.exit_rule(dict(P), 1.24, 10, 300, None, None), SQ.exit_rule(dict(P), 1.26, 10, 300, None, None), SQ.exit_rule(dict(own), 1.30, 10, 300, None, None)]
check(r[0] is None and r[1] and r[1][0] == "lmt" and "1.25" in r[1][1] and r[2] and r[2][0] == "lmt" and SQ.REASON_AR["lmt"] == "أمرُ الإغلاق بسعرٍ محدَّد",
      "١ أمرُ الإغلاق المحدَّد يبيع متى بلغ الطلبُ سعرَه (1.26 ≥ 1.25) لا قبله (1.24) — لمركز صقر ولمركز المالك", f"{r}")

# ٢ الأمر: يُسجَّل ويبقى، ويُلغى بفراغه — وإن كان الطلبُ فوقه والسوقُ مفتوح بِيع الآن
Q = {"bid": 1.10, "state": "open"}


async def fake_qp(p):
    return Q["bid"], Q["bid"] + 0.05, 12.0, 300


async def fake_sess():
    return {"us": {"state": Q["state"]}}
SQ.quote_position, LQ.sessions = fake_qp, fake_sess
st = SQ.fresh(capital=1000)
k = {"contract": "F271217C00010000", "symbol": "F", "type": "call", "strike": 10.0, "expiry": "2027-12-17", "t": 1, "ask": 1.0, "bid": 0.95, "price": 12.0}
pos = SQ.buy(st, k, 1, ["اختبار"], src="manual", px=1.0)
SQ.save(st)
a = asyncio.run(SQ.close_limit(pos["id"], 1.30))
held = SQ.load()["positions"][0].get("close_px")
b = asyncio.run(SQ.close_limit(pos["id"], None))
gone = "close_px" not in SQ.load()["positions"][0]
Q["bid"] = 1.35
c = asyncio.run(SQ.close_limit(pos["id"], 1.30))
st2 = SQ.load()
try:
    asyncio.run(SQ.close_limit("nope", 1.0))
    bad = False
except ValueError:
    bad = True
check(a["closed"] is None and held == 1.3 and b["closed"] is None and gone and c["closed"] and c["closed"]["exit_px"] == 1.35 and c["closed"]["reason"] == "lmt"
      and not st2["positions"] and bad,
      "٢ «أغلق بسعرٍ محدَّد»: الطلبُ دونه ⇐ يُسجَّل ويبقى، وفراغُه يلغيه، والطلبُ فوقه والسوقُ مفتوح ⇐ يُباع الآن بالطلب (1.35) — والمعرّفُ المجهولُ يُرفض",
      f"{held} · {c['closed'] and c['closed']['exit_px']}")

# ٣ الواجهة والنقطة: «أغلق الآن» و«بسعرٍ محدَّد» في لوحة الإغلاق، والأمرُ ظاهرٌ على المركز بزرّ إلغاء
pf = (ROOT / "frontend/src/components/saqr/SaqrPortfolio.tsx").read_text(encoding="utf-8")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
check(all(x in pf for x in ('data-role="sp-close-how"', '>أغلق الآن</button>', '>بسعرٍ محدَّد</button>', 'data-role="sp-close-px"', 'data-role="sp-close-lmt"',
                            'data-role="sp-closelim"', 'data-role="sp-closelim-cancel"', "marketApi.saqrCloseLimit(p.id, v, market)", 'data-role="sp-close-ok"'))
      and '@router.post("/saqr/close-limit/{pid}", dependencies=[Depends(require_owner)])' in mk,
      "٣ لوحةُ الإغلاق: «أغلق الآن» (كما كان) و«بسعرٍ محدَّد» بسعره ونتيجته عنده، والأمرُ ظاهرٌ على المركز بزرّ إلغاء — بصلاحية المالك وحده")

print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
