#!/usr/bin/env python3
"""حارسُ D769 — صقرٌ موحَّد: المحفظةُ داخله، والإغلاقُ بسعر السوق الآن، وقيمةُ المحفظة يضبطها المالك، واختر عقداً بنفسك (2026-11-19).

«خلّنا نوحّد كلَّ تفاصيل صقر — المحفظةُ داخل صقر بجانب لوحة المعلومات والسجل. والمراكزُ واضحة: إمّا تُقفل إلين تحقّق هدفها، أو أنا لما أضغط
إغلاق تُقفل بنفس السعر الذي هي عليه الآن — وإن كانت بالناقص تُحفظ بالناقص. والمحفظةُ إذا صارت مثلاً 100 أرجعُ أعدّلها من جديد. وخلّ خياراً أنّي
أختار عقداً بنفسي، وفيه تحليلُ السترايك الذي أختاره — مبسّطةً واضحة».

    python3 scripts/audit/saqr_d769.py
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
from app.services import options_chain as OC   # noqa: E402

# سلسلةٌ مصطنعةٌ للعقد AAPL261218C00235000 — عرضٌ 3.10 وطلبٌ 2.90
ROW = {"contract": "AAPL261218C00235000", "strike": 235.0, "bid": 2.9, "ask": 3.1}
BASE = {"price": 230.5, "expirations": [{"t": 1, "date": "2026-12-18", "dte": 29}], "calls": [], "puts": []}


async def fake_chain(sym, t=None):
    return {**BASE, "calls": [dict(ROW)]} if t else dict(BASE)
OC.chain = fake_chain

# ١ الإغلاقُ بأمر المالك: بسعر الطلب الآن، والخسارةُ تُحفظ خسارةً في المحقَّق — وبلا سعرٍ حيٍّ فبآخر طلبٍ معروف
st = SQ.fresh(capital=1000)
SQ.save(st)
p = asyncio.run(SQ.manual_open("AAPL261218C00235000", 2, None, "us"))
live = {"bid": 1.85}


async def fake_quote(pos):
    return live["bid"], None, 228.0, 29
SQ.quote_position = fake_quote
c = asyncio.run(SQ.manual_close(p["id"], None, "us"))
v = SQ.view("us")
p2 = asyncio.run(SQ.manual_open("AAPL261218C00235000", 1, None, "us"))
st2 = SQ.load("us")
next(x for x in st2["positions"] if x["id"] == p2["id"])["bid"] = 3.4
SQ.save(st2)
live["bid"] = None
c2 = asyncio.run(SQ.manual_close(p2["id"], None, "us"))
check(p["entry_px"] == 3.1 and c["exit_px"] == 1.85 and c["pl"] < 0 and c["pl"] == round(1.85 * 200 - 1.3 - (3.1 * 200 + 1.3), 2) and c["reason"] == "manual"
      and v["realized"] == c["pl"] and v["n_closed"] == 1 and not v["positions"] and c2["exit_px"] == 3.4,
      "١ «إغلاق» يبيع بسعر الطلب الآن (1.85) والخسارةُ تُحفظ خسارةً في المحقَّق — وبلا طلبٍ حيٍّ فبآخر طلبٍ معروف (3.40)",
      f"{c['pl']:+.2f} · {c2['exit_px']}")

# ٢ قيمةُ المحفظة الآن يضبطها المالك: الفرقُ تمويلٌ (يُضاف إلى النقد أو يُسحب) والربحُ المحسوبُ كما هو، والسحبُ فوق النقد يُرفض
st = SQ.fresh(capital=100)
SQ.buy(st, {"contract": "F270115C00012000", "symbol": "F", "type": "call", "ask": 0.4, "bid": 0.2}, 1, ["x"])
st["positions"][0]["bid"] = 0.2
pl0 = SQ.equity(st) - st["capital"]
d1 = SQ.apply_settings(st, {"equity_to": 100})
eq1, pl1 = SQ.equity(st), SQ.equity(st) - st["capital"]
try:
    SQ.apply_settings(st, {"equity_to": 15})
    over = False
except ValueError:
    over = True
check(abs(eq1 - 100) < 0.01 and abs(pl1 - pl0) < 1e-6 and over and d1 and "الميزانية" in d1[0] and len(st["positions"]) == 1,
      "٢ «اجعل المحفظةَ الآن 100»: تصير قيمتُها 100 بالفرق تمويلاً، والربحُ المحسوبُ كما هو، والمراكزُ باقية — والسحبُ فوق النقد الحرّ يُرفض",
      f"{eq1:.2f} · ربح {pl0:.2f}={pl1:.2f} · {d1}")

# ٣ العقدُ الذي يختاره المالك: يديره صقر (وقفٌ وجنيٌ ووقفٌ متحرّكٌ بأوامره) ويبيعه عند الوقف — ولا يُباع بـ«انكسار أطروحةٍ» ليست لصقر
st = SQ.fresh(capital=1000)
SQ.save(st)
m = asyncio.run(SQ.manual_open("AAPL261218C00235000", 1, None, "us", managed=True))
cfg, pf = SQ.cfg(st), SQ.profile(st)
broken_tr = {"state": "هابط", "close": 200, "sma50": 220, "sma200": 230, "ret3m": -12, "strength": 80}
plain = asyncio.run(SQ.manual_open("AAPL261218C00235000", 1, None, "us"))
check(m["auto"] and m["managed"] and m["src"] == "manual" and m["stop"] == round(3.1 * (1 - cfg["opt_stop"] / 100), 4) and m["take_x"] == cfg["take_x"]
      and m["trail"] == list(pf["trail"]) and m["exit_dte"] == pf["exit_dte"] and "يديره صقر" in m["why"][0]
      and SQ.exit_rule(dict(m), m["stop"] - 0.01, 230, 29, None, None)[0] == "stop"
      and SQ.exit_rule(dict(m), 3.2, 230, 29, broken_tr, None) is None
      and not plain.get("auto") and not plain.get("managed") and "يدوياً" in plain["why"][0],
      "٣ العقدُ الذي يختاره المالك ويديره صقر: وقفٌ (−40٪) وجنيٌ (×2) ووقفٌ متحرّكٌ بأوامره، ويبيعه عند الوقف، ولا يُباع بانكسار أطروحةٍ ليست لصقر — "
      "وبلا إدارةٍ يبقى للمالك وحده", f"{m['stop']} · {m['take_x']} · {m['trail']}")

# ٤ الأمرُ يحمل «يديره صقر» من الواجهة إلى المحرّك
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
api = (ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")
check('managed=bool(p.get("managed"))' in mk and "{ contract, qty, price: price ?? null, market, managed }" in api,
      "٤ أمرُ الشراء يحمل «يديره صقر» من الواجهة إلى المحرّك")

# ٥ الواجهة: المحفظةُ تبويبٌ في صقر، والإغلاقُ بسعر السوق بعد رؤية النتيجة، وقيمةُ المحفظة الآن، واختر عقداً بنفسك بتحليله
lab = (ROOT / "frontend/src/pages/ResearchLab.tsx").read_text(encoding="utf-8")
desk = (ROOT / "frontend/src/components/saqr/SaqrDesk.tsx").read_text(encoding="utf-8")
pf_src = (ROOT / "frontend/src/components/saqr/SaqrPortfolio.tsx").read_text(encoding="utf-8")
pk = (ROOT / "frontend/src/components/saqr/ContractPicker.tsx").read_text(encoding="utf-8")
check('["portfolio", "المحفظة", Wallet]' in desk and "<SaqrPortfolio market={market} />" in desk and '"portfolio"' not in lab.split("const VIEWS")[1].split("\n")[0]
      and 'data-role="sp-closef"' in pf_src and "يُغلق الآن بسعر السوق" in pf_src and "marketApi.saqrClose(p.id, null, market)" in pf_src
      and "equity_to: b" in pf_src and "equity_to: f.budget" in desk and "budDirty" in desk and 'data-role="sp-pick"' in pf_src
      and all(x in pk for x in ('data-role="pk-exp"', 'data-role="pk-strike"', 'data-role="pk-analysis"', "التعادل عند الانتهاء", "احتمالُ الربح", "التآكلُ اليوميّ",
                                 "marketApi.optionAdvice", "marketApi.optionChain", "<OrderForm contract={k!} ask={ask}")),   # ‏D771: التنفيذُ بأمر المالك
      "٥ الواجهة: المحفظةُ تبويبٌ في صقر (لا في المختبر)، والإغلاقُ بسعر السوق بعد رؤية السعر والنتيجة، وقيمةُ المحفظة الآن تُرسل إن غيّرها المالك وحدها، "
      "و«اختر عقداً بنفسك»: السهمُ ⇐ الأجل ⇐ السترايك ⇐ تحليلٌ مختصر ⇐ تنفيذٌ بأمر المالك (سعرُه وجنيُه ووقفُه — ‏D771)")

print("\nالنتيجة:", "عطب ✖" if fail else "نظيف ✔")
sys.exit(fail)
