#!/usr/bin/env python3
"""حارسُ D771 — صقرٌ الأمريكيّ سكرتيرٌ ومنفّذ: قائمةُ عقودٍ طويلةٍ للجلسة القادمة، وأوامرُ المالك، والتداولُ الآليُّ بأمره (2026-11-20).

«أنا ما أبغى يتعلّم الآن — أنت المتعلّم وهو فقط المنفّذ… يطلع لي مثلاً 50 عقداً وأنا أختار… لا نختار إلا طويلَ المدى… إذا كثرت السلبياتُ على
الإيجابيات نمتنع… عقودٌ تطلع 30٪ أقلَّ شيء… أشتغل اليوم حتى أدخل اليومَ التالي… زرُّ تنفيذٍ بالسعر الذي أحدّده، وأحدّد جميعَ الأوامر — جنيُ ربحٍ
30٪ 40٪، عند أمرٍ محدّدٍ يبيع أو يشتري… وزرٌّ أوقف التداولَ الآليّ».

    python3 scripts/audit/saqr_d771.py
"""
import asyncio, os, pathlib, sys, tempfile   # noqa: E401
from datetime import date
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
from app.services import saqr_list as SL   # noqa: E402
from app.services import option_picks as OP   # noqa: E402
from app.services import saqr_universe as SU   # noqa: E402
from app.services import live_quote as LQ   # noqa: E402

# ١ الجلسةُ القادمة: بعد إغلاق الجمعة ⇐ الاثنين، وفي الجلسة ⇐ اليوم — وعتبةُ الثلاثين
fri = date(2026, 11, 20)
k = {"type": "call", "strike": 12.0, "ask": 1.0, "price": 11.0}
t30 = SL.tp30(k)
check(SL.for_session("post", fri) == ("2026-11-23", "جلسة الاثنين 23/11") and SL.for_session("open", fri)[1] == "جلسة اليوم"
      and SL.for_session("closed", date(2026, 11, 18))[0] == "2026-11-19" and t30 == {"price": 13.3, "pct": 20.9},
      "١ القائمةُ تُعدّ للجلسة القادمة (بعد إغلاق الجمعة ⇐ الاثنين، وفي الجلسة ⇐ اليوم)، ومعها سعرُ السهم الذي يربح عنده العقدُ 30٪ عند انتهائه",
      f"{SL.for_session('post', fri)} · {t30}")

# ٢ البناء: المجالُ ⇐ العقدُ الطويل ⇐ الخبر ⇐ الإيجابياتُ والسلبيات — وما زادت سلبياتُه يُمتنع عنه، والخبرُ القويُّ المعاكسُ يُسقطه
TR = lambda st, c, s50, s200, r3, strength: {"state": st, "close": c, "sma50": s50, "sma200": s200, "ret3m": r3, "strength": strength}   # noqa: E731
tr = {"F": TR("صاعد", 12.0, 11.0, 10.0, 12.0, 9.0), "NIO": TR("هابط", 5.0, 6.0, 7.0, -20.0, 8.0), "BAD": TR("صاعد", 9.0, 10.0, 8.0, -4.0, 7.0),
      "NEWS": TR("صاعد", 14.0, 13.0, 12.0, 8.0, 6.0), "BIG": TR("صاعد", 400.0, 380.0, 350.0, 10.0, 5.0), "SIDE": TR("عرضي", 20.0, 20.0, 20.0, 0.0, 9.9)}
U = {"tr": tr, "fund": {"F": (85, "متانةٌ ممتازة"), "BAD": (66, "مقبول"), "NEWS": (90, "x"), "BIG": (95, "x")}, "names": {"F": "Ford Motor"}, "meta": {}}


def card(sym, call, **kw):
    c = {"contract": f"{sym}271217{'C' if call else 'P'}00010000", "type": "call" if call else "put", "strike": 10.0, "expiry": "2027-12-17", "t": 1, "dte": 392,
         "ask": 1.2, "bid": 1.15, "mid": 1.18, "cost": 120.0, "px_src": "ask", "quote_at": None, "spread_pct": 4.2, "spread_usd": 5, "breakeven": 11.2,
         "need_pct": 3.0, "target": 15.0, "target_label": "قمّة السنة", "rr": 2.1, "pop": 41.0, "p_touch": 58.0, "delta": 0.62, "iv": 45.0, "oi": 4200,
         "score": 70.0, "symbol": sym, "name": None, "price": tr[sym]["close"]}
    c.update(kw)
    return c
CARDS = {"F": card("F", True), "NIO": card("NIO", False, strike=6.0, need_pct=5.0, score=60.0),
         "BAD": card("BAD", True, rr=0.8, pop=24.0, spread_pct=8.5, oi=150, dte=160, need_pct=18.0, iv=95.0, delta=0.31, p_touch=20.0, score=40.0),
         "NEWS": card("NEWS", True, score=65.0)}
seen = []


async def fake_universe():
    return U


async def fake_contracts(sym, call, t, diag=None):          # ‏D775: كلُّ العقود الصالحة بلا ميزانية
    seen.append(sym)
    if sym in CARDS:
        return {}, [CARDS[sym]]
    return ({}, [card(sym, call, cost=260.0)]) if sym in tr else ({}, [])


async def fake_news(items):
    return {"NEWS": {"impact": "سلبي", "strength": 3, "event": "تحقيقٌ رسميّ"}, "F": {"impact": "إيجابي", "strength": 2, "event": "عقدٌ كبير"}}


async def fake_sessions():
    return {"us": {"state": "post"}}
SU.universe, OP.valid_contracts, OP.read_news, LQ.sessions = fake_universe, fake_contracts, fake_news, fake_sessions
raw = asyncio.run(SL.build({"per_trade": 150, "sides": "both"}, set()))
res = SL.view(raw, 150)
items = {i["symbol"]: i for i in res["items"]}
f = items.get("F") or {}
check(set(items) == {"F", "NIO"} and "SIDE" not in seen and res["excluded"].get("سلبياتُه أكثر من إيجابياته") == 1
      and res["excluded"].get("خبرٌ قويٌّ يعاكس المسار") == 1 and res["excluded"].get("فوق الميزانية") == 1 and res["cheapest"] == 260.0
      and res["budget"] == 150 and res["label"].startswith("جلسة ") and res["items"][0]["symbol"] == "F" and f.get("gain_target") == 210
      and any("أساسٌ ماليٌّ متين" in x for x in f.get("pros", [])) and any("الخبرُ يدعمها" in x for x in f.get("pros", [])) and f.get("name") == "Ford Motor"
      and f.get("tp30", {}).get("price") == 11.56 and (SL.load() or {}).get("entries") and len(f["pros"]) > len(f["cons"]),
      "٢ القائمة: العرضيُّ لا يدخل، وما زادت سلبياتُه على إيجابياته يُمتنع عنه، والخبرُ القويُّ المعاكسُ يُسقطه، والميزانيةُ تُعلن أرخصَ صالح، "
      "والأعلى إيجابياتٍ أوّلاً بأسبابه (الأساس · الخبر · الربحُ عند الهدف) — وتُحفظ", f"{sorted(items)} · {res['excluded']}")

# ٢ب التوقيت (قيس على الخادم قبل الافتتاح: المصدرُ يُصفّر العرضَ والطلب فخرجت 0 من 70): تُبنى في الجلسة وحدها — لا قائمة أو مضت ساعتان،
#     وآخرُها قبل الإغلاق بخمسٍ وأربعين دقيقة للجلسة القادمة — وبناءٌ فارغٌ خارج الجلسة لا يمحو قائمةً صالحة
from datetime import datetime, timedelta, timezone   # noqa: E402
NYZ = __import__("zoneinfo").ZoneInfo("America/New_York")
op = datetime(2026, 11, 20, 9, 30, tzinfo=NYZ)
clk = (op, op + timedelta(hours=6, minutes=30))
fresh_l = {"v": SL.V, "at": (op + timedelta(hours=1)).astimezone(timezone.utc).isoformat(), "items": [1]}   # ‏D774: صيغةُ القائمة
d_pre = SL.due(op - timedelta(minutes=30), clk, None)
d_mid = SL.due(op + timedelta(hours=2), clk, fresh_l)
d_old = SL.due(op + timedelta(hours=3, minutes=5), clk, fresh_l)
d_fin = SL.due(clk[1] - timedelta(minutes=30), clk, fresh_l)
d_fin2 = SL.due(clk[1] - timedelta(minutes=10), clk, {"v": SL.V, "at": (clk[1] - timedelta(minutes=30)).astimezone(timezone.utc).isoformat(), "items": [1]})
good = SL.load()


async def empty_contracts(sym, call, t, diag=None):
    return None, []
OP.valid_contracts = empty_contracts
kept = asyncio.run(SL.build({"per_trade": 150, "sides": "both"}, set()))
check(d_pre == (False, False) and d_mid == (False, False) and d_old == (True, False) and d_fin == (True, True) and d_fin2 == (False, True)
      and kept.get("entries") == good.get("entries") and kept.get("retry") and SL.for_session("open", fri, final=True)[1] == "جلسة الاثنين 23/11",
      "٢ب القائمةُ تُبنى في الجلسة وحدها: كلَّ ساعتين، وآخرُها قبل الإغلاق بـ45 دقيقة للجلسة القادمة (الجمعة ⇐ الاثنين) — وبناءٌ فارغٌ خارج الجلسة "
      "لا يمحو قائمةً صالحة (قيس: المصدرُ يُصفّر العرضَ والطلبَ قبل الافتتاح)", f"{d_old} · {d_fin} · {d_fin2}")

# ٣ أوامرُ المالك: يُنفَّذ الآن عند العرض أو فوقه، ودونه أو والسوقُ مغلقٌ أمرٌ معلّق — والنقدُ يحدّه، ويُنفَّذ المعلّقُ متى بلغ العرضُ سعرَه
Q = {"ask": 1.20, "live": True, "state": "open"}


async def fake_q(c):
    from app.services.options_chain import parse_option
    o = parse_option(c)
    return {"o": o, "t": 1, "dte": 392, "ask": Q["ask"], "bid": Q["ask"] - 0.05, "live": Q["live"], "price": 12.0, "name": "Ford"}


async def fake_sess():
    return {"us": {"state": Q["state"]}}
SQ.contract_quote, LQ.sessions = fake_q, fake_sess
SQ.save(SQ.fresh(capital=1000))
C = "F271217C00010000"
o1 = asyncio.run(SQ.place_order(C, 2, 1.25, 40, 40))
st = SQ.load()
p1 = st["positions"][0] if st["positions"] else {}
o2 = asyncio.run(SQ.place_order(C, 1, 1.00, 30, None))
Q["state"] = "post"
o3 = asyncio.run(SQ.place_order(C, 1, None, None, 25))
try:
    asyncio.run(SQ.place_order(C, 50, None, 40, 40))
    big = False
except ValueError as e:
    big = "النقدُ الحرّ" in str(e)
st = SQ.load()
pend = len(st.get("orders") or [])
Q.update(state="open", ask=0.98)
st = SQ.load()
n_fill = asyncio.run(SQ._fill_orders(st))
SQ.save(st)                                   # الدورةُ تحفظ بعد التنفيذ
check(p1.get("entry_px") == 1.2 and p1.get("qty") == 2 and p1.get("owner") and p1.get("take_x") == 1.4 and p1.get("stop") == 0.72 and pend == 2 and big
      and n_fill == 2 and not st["orders"] and len(st["positions"]) == 3 and st["positions"][1]["stop"] == 0.0 and st["positions"][2]["take_x"] is None,
      "٣ أمرُ المالك: العرضُ (1.20) دون سعره (1.25) ⇐ يُنفَّذ الآن بأمرَي الجني (+40٪ ⇐ 1.68) والوقف (−40٪ ⇐ 0.72)؛ ودونه أو والسوقُ مغلقٌ ⇐ أمرٌ معلّق "
      "يُنفَّذ في الجلسة متى بلغ العرضُ سعرَه — والكلفةُ فوق النقد تُرفض بسببها", f"معلّق {pend} · نُفّذ {n_fill}")

# ٤ أمرا المركز: يبيع صقر عند الجني أو الوقف كما كتبهما المالك — لا وقفاً متحرّكاً ولا قفلَ هدفٍ ولا انكسارَ أطروحة — ويُعدَّلان لكلّ مركز
p = dict(p1)
r_tp = SQ.exit_rule(dict(p), 1.70, 12.0, 300, None, None)
r_sl = SQ.exit_rule(dict(p), 0.70, 12.0, 300, None, None)
r_mid = SQ.exit_rule(dict(p), 1.50, 12.0, 300, {"state": "هابط", "close": 9, "sma50": 10, "sma200": 11, "ret3m": -9, "strength": 9}, None)
q = dict(p)
SQ.trail(q, 1.65)
st = SQ.load()
pid = st["positions"][1]["id"]
pp = asyncio.run(SQ.set_orders(pid, 30, 25))
try:
    asyncio.run(SQ.cancel_order("nope"))
    cx = False
except ValueError:
    cx = True
check(r_tp and r_tp[0] == "tp" and r_sl and r_sl[0] == "sl" and r_mid is None and q["stop"] == 0.72 and pp["take_x"] == 1.3
      and pp["stop"] == round(pp["entry_px"] * 0.75, 4) and pp["owner"] and cx,
      "٤ مركزُ المالك يُباع عند أمر الجني أو الوقف كما كتبهما — بلا وقفٍ متحرّكٍ ولا انكسارِ أطروحة — والمالكُ يضبط أمرَي أيِّ مركزٍ قائم",
      f"{r_tp} · {r_sl}")

# ٥ التداولُ الآليّ: موقوفٌ افتراضاً؛ وإن شغّله المالك فمن القائمة وحدها (عقودٌ طويلة، الأعلى أوّلاً، شراءٌ فقط يتخطّى البيع) بوقفه وجنيه
src = (ROOT / "backend/app/services/saqr_trader.py").read_text(encoding="utf-8")
hunt = src[src.index("async def _hunt("):src.index("# ══ أوامرُ المالك (‏D771)")]
# ‏D779 (المالك): «خلِّ التداولَ الآليَّ يشتري من عقود الخيارات» — دفترُ التوصيات القائمة بميزانية العقد
OP.book_save(150, {"open": [{"contract": C, "symbol": "F", "name": "Ford", "type": "call", "strike": 10.0, "expiry": "2027-12-17", "t": 1, "opened": "2026-11-18",
                             "target": 15.0, "target_label": "قمّة السنة", "card": {"score": 70.0, "delta": 0.62, "iv": 45.0, "reasons": ["المسارُ صاعد"]}},
                            {"contract": "NIO271217P00006000", "symbol": "NIO", "type": "put", "strike": 6.0, "expiry": "2027-12-17", "t": 1, "opened": "2026-11-18",
                             "target": 4.0, "card": {"score": 90.0, "reasons": ["المسارُ هابط"]}}], "closed": []})
st = SQ.fresh(capital=1000)
SQ.apply_settings(st, {"auto": True, "sides": "calls"})
pos = asyncio.run(SQ._hunt(st, SQ._now()))
check(SQ.cfg(SQ.fresh())["auto"] is False and 'due and cfg(st).get("auto")' in src and pos and pos["symbol"] == "F" and pos["type"] == "call"
      and pos["stop"] == round(0.98 * 0.6, 4) and "من «عقود الخيارات»" in pos["why"][0] and "stock_pick(" not in hunt and SQ.cfg(st)["auto"] is True,
      "٥ التداولُ الآليُّ موقوفٌ حتى يشغّله المالك، وإن شغّله فمن «عقود الخيارات» وحدها (‏D779) — الأعلى درجةً أوّلاً، وشراءٌ فقط يتخطّى البيع، "
      "وبوقفه وجنيه — لا أسهمَ ولا قصيرة",
      f"{pos and pos['contract']}")

# ٦ التوقيتُ والنقاطُ والواجهة
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
desk = (ROOT / "frontend/src/components/saqr/SaqrDesk.tsx").read_text(encoding="utf-8")
opk = (ROOT / "frontend/src/components/market/OptionPicks.tsx").read_text(encoding="utf-8")
of = (ROOT / "frontend/src/components/saqr/OrderForm.tsx").read_text(encoding="utf-8")
pf = (ROOT / "frontend/src/components/saqr/SaqrPortfolio.tsx").read_text(encoding="utf-8")
check("SL.kick(" not in src and "job_saqr_list" not in sch   # ‏D779: لا فحصَ للقائمة في الخلفية and '@router.get("/saqr/list")' in mk
      # ‏D778 (المالك): «قائمةُ العقود لا فايدة منها — نكتفي بعقود الخيارات، وفي بطاقتها شراء»: لا تبويبَ للقائمة، والتنفيذُ من بطاقة التوصية
      and "<SaqrList" not in desk and '!(sa && k === "options")' in desk and '["opps", "الفرص", Crosshair]' in desk and '"signals", "الإشارات"' not in desk and 'data-role="sq-auto"' in desk and "أوقف التداول الآليّ" in desk
      and all(x in opk for x in ('data-role="op-buy"', "<OrderForm contract={p.contract} ask={p.ask} bid={p.bid} />"))
      and all(x in of for x in ('data-role="of-limit"', 'role={`${role}-tp`}', 'role={`${role}-sl`}', '<ExitFields ex={ex} set={setEx} base={ref} role="of" />',
                                "marketApi.saqrOrder("))   # ‏D777: الجنيُ والوقفُ في «الأمر المرفق» المشترك
      and all(x in pf for x in ('data-role="sp-orders"', 'data-role="sp-order-cancel"', 'data-role="sp-ord"', 'data-role="sp-ord-edit"')),
      "٦ لا قائمةَ في الخلفية (‏D779 — التداولُ الآليُّ من «عقود الخيارات»)، والتنفيذُ من بطاقة «عقود الخيارات» (‏D778)، وزرُّ التداول الآليّ، ونموذجُ الأمر "
      "(السعر · الجني · الوقف)، والأوامرُ المعلّقةُ وأمرا كلّ مركزٍ في المحفظة")

print("\nالنتيجة:", "عطب ✖" if fail else "نظيف ✔")
sys.exit(fail)
