#!/usr/bin/env python3
"""حارسُ D767 — صقرُ التداول بلا تلغرام، وأوامرُ المالك (الميزانيةُ والخيارات)، ولوحةٌ بلا IBKR، والسعوديُّ بنبض سوقه (بأمر المالك 2026-11-18).

«لا أريد إشعاراتٍ بشراء الأسهم لصقر في التليجرام — فقط للتقارير اليومية ومهامّ صقر الأساسية… أضف خيارَ تحديد الميزانية (150 أو 100) وخلّ
فيه مرونة، أقدر أغيّر الخيارات؛ هو العقلُ المدبّر وأنا أضع الأوامر… أزل IBKR من القائمة التي فوق علامة صقر… وفي السوق السعوديّ أعد صياغتها
كاملةً بشكلٍ احترافيّ — الأحداثُ الجيوسياسية ما لها دخلٌ أن تُكتب هنا».

    python3 scripts/audit/saqr_d767.py
"""
import os, pathlib, re, sys, tempfile   # noqa: E401
from datetime import date, datetime, timedelta, timezone
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
from app.services import saqr_sa as SA   # noqa: E402
SRC = {n: (ROOT / f"backend/app/services/{n}.py").read_text(encoding="utf-8") for n in ("saqr_trader", "saqr_sa", "saqr_universe")}

# ١ لا تلغرام في صقر التداول
check(all("saqr_bot" not in s and "_notify" not in s and "bot.send" not in s for s in SRC.values()),
      "١ صقرُ التداول لا يرسل إلى تلغرام شيئاً — لا شراءَ ولا بيعَ ولا تنبيه؛ وتلغرامُ للتقارير اليومية ومهامّ صقر الأساسية وحدها")

# ٢ الميزانيةُ تُعدَّل بلا محوٍ للسجلّ: الفرقُ في النقد، والربحُ المحسوبُ لا يتغيّر
st = SQ.fresh()
p = SQ.buy(st, {"contract": "F270115C00012000", "symbol": "F", "type": "call", "strike": 12, "expiry": "2027-01-15", "ask": 0.40, "bid": 0.45}, 1, ["x"])
pl0 = SQ.equity(st) - st["capital"]
d1 = SQ.apply_settings(st, {"budget": 150})
pl1 = SQ.equity(st) - st["capital"]
cash_after_up = st["cash"]
try:
    SQ.apply_settings(st, {"budget": 10})
    over = False
except ValueError as e:
    over = "النقدُ الحرّ" in str(e)
d2 = SQ.apply_settings(st, {"budget": 120})
check(st["capital"] == 120 and st["goal"] == 12_000 and abs(pl0 - pl1) < 1e-6 and abs((SQ.equity(st) - st["capital"]) - pl0) < 1e-6 and cash_after_up == round(100 - 40.65 + 50, 2)
      and over and len(st["positions"]) == 1 and st["fundings"][-1]["delta"] == -30 and d1 and "الميزانية" in d1[0],
      "٢ الميزانيةُ تُعدَّل (150 ثمّ 120) بلا محوٍ للسجلّ ولا للمراكز: الفرقُ يُضاف إلى النقد أو يُسحب منه، والربحُ المحسوبُ كما هو، والهدفُ مئةُ ضعفها — "
      "والسحبُ فوق النقد الحرّ يُرفض بسببه", f"{d1} · {d2} · ربح {pl0:.2f}={pl1:.2f}")

# ٣ أوامرُ المالك الأخرى وحدودُها
st = SQ.fresh()
SQ.apply_settings(st, {"per_trade": 30, "max_positions": 3, "instruments": "options", "sides": "calls", "opt_stop": 35, "stock_stop": 5, "take_x": 2.5})
seats, budget = SQ.seats_budget(st, SQ.equity(st), 0.5, 2)
bad = []
for upd in ({"opt_stop": 90}, {"take_x": 9}, {"max_positions": 40}, {"instruments": "crypto"}, {"budget": 5}):
    try:
        SQ.apply_settings(SQ.fresh(), upd)
        bad.append(upd)
    except ValueError:
        pass
auto = SQ.fresh()
SQ.apply_settings(auto, {"per_trade": 30})
SQ.apply_settings(auto, {"per_trade": None})
c = SQ.cfg(st)
check(seats == 3 and budget == 30 and c["instruments"] == "options" and c["sides"] == "calls" and c["opt_stop"] == 35 and c["take_x"] == 2.5 and not bad
      and SQ.cfg(auto)["per_trade"] is None and SQ.cfg(SQ.fresh(market="sa"))["stock_stop"] == 6 and SQ.cfg(SQ.fresh())["stock_stop"] == 7,
      "٣ أوامرُ المالك: حدُّ الصفقة وأقصى المراكز يحكمان الميزانيةَ والمقاعد، والأداةُ والاتجاهُ والوقفان والجنيُ تُحفظ، والفارغُ يعود تلقائياً، وما خرج عن "
      "حدوده يُرفض — والافتراضيُّ لكلّ سوق (وقفُ السهم السعوديّ −6٪ والأمريكيّ −7٪)", f"{seats} · {budget} · مرفوضٌ خطأً: {bad}")

# ٤ الأوامرُ تحكم الصيدَ والخروج
hunt = SRC["saqr_trader"][SRC["saqr_trader"].index("async def _hunt("):SRC["saqr_trader"].index("async def cycle(")]
P = {"type": "call", "entry_px": 1.0, "stop": 0.6, "peak": 1.0, "target": 999, "take_x": 2.5}
check('c["sides"] == "calls"' in hunt and 'c["instruments"] == "stocks"' in hunt and 'c["instruments"] != "options"' in hunt
      and 'chosen["stop"] = round(chosen["ask"] * (1 - c["opt_stop"] / 100), 4)' in hunt and 'c["stock_stop"] / 100' in hunt
      and SQ.exit_rule(dict(P), 2.1, 10, 60, None, None) is None and SQ.exit_rule(dict(P), 2.55, 10, 60, None, None)[0] == "take"
      and "seats_budget(" in SRC["saqr_sa"] and 'c["stock_stop"] / 100' in SRC["saqr_sa"],
      "٤ الأوامرُ تحكم الصيد (شراءٌ فقط يرفض البيع، وأسهمٌ فقط تتخطّى العقود، وعقودٌ فقط بلا بديلِ السهم) والوقفَ عند الدخول، والجنيُ بمضاعف المالك "
      "المحفوظ في المركز (×2.5 لا ×2) — في السوقين")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
check('@router.post("/saqr/settings", dependencies=[Depends(require_owner)])' in mk and "await SQ.settings(p, m)" in mk,
      "٤ب أمرُ الإعدادات بصلاحية المالك وحده، ولكلّ سوقٍ إعداداتُه")

# ٥ نبضُ السوق السعوديّ — مقاييسُ احترافية من لقطة «تداول»
snap = {"1120": {"change_pct": 1.4, "turnover": 6e8}, "1180": {"change_pct": 0.8, "turnover": 4e8}, "2222": {"change_pct": -0.6, "turnover": 9e8},
        "2010": {"change_pct": -1.2, "turnover": 3e8}, "7010": {"change_pct": 0.0, "turnover": 1e8}}
orig = SA.results_of
SA.results_of = lambda s, t: {"1120": ("strong", "", 30), "2222": ("weak", "", -20)}.get(s, ("neutral", "", 1))
try:
    pu = SA.pulse(snap, date(2026, 11, 18), {"px": 88.5, "chg": -4.9, "chg5": -4.5})
finally:
    SA.results_of = orig
check(pu["adv"] == 2 and pu["dec"] == 2 and pu["unch"] == 1 and pu["turnover"] == 23e8 and pu["leaders"][0][0] == "البنوك" and pu["leaders"][0][1] == 1.16
      and pu["laggards"][0][0] in ("المواد الأساسية", "الطاقة") and pu["results"]["strong"] == 1 and pu["results"]["weak"] == 1 and pu["quarter"] == "2026-09-30"
      and pu["brent"]["px"] == 88.5,
      "٥ نبضُ السوق السعوديّ: اتّساعُ السوق (صاعدةٌ · هابطةٌ · ثابتة)، وقيمةُ التداول، والقطاعاتُ القائدةُ والمتأخّرةُ بأسمائها العربية مرجّحةً بالتداول، "
      "وموسمُ النتائج، وخامُ برنت", f"{pu['adv']}/{pu['dec']}/{pu['unch']} · {pu['leaders'][:1]} · {pu['laggards'][:1]}")
check("sym in SUSPENDED" in SRC["saqr_sa"] and "SYMBOL_TO_NAME" in SRC["saqr_sa"] and 'st["pulse"] = pulse(snap' in SRC["saqr_sa"],
      "٥ب الشركاتُ الموقوفةُ مستبعَدةٌ من الصيد، والأسماءُ عربية، والنبضُ يُكتب كلَّ دورة")

# ٥ج قراءةُ الإغلاق: النبضُ يُكتب بعد المزاد وبعد الإقلاع فلا تخلو اللوحةُ خارج الجلسة — قراءةٌ لا تمسّ الدفتر
import asyncio   # noqa: E402
from app.services import tadawul_market as TM   # noqa: E402
st0 = SQ.fresh(market="sa")
st0["positions"] = [{"id": "x1", "symbol": "1120", "kind": "stock", "qty": 3}]
SQ.save(st0)
saved = (TM.ensure_fresh, TM.snapshot, SA.regime, SA.brent)
TM.ensure_fresh, TM.snapshot = (lambda *a, **k: True), (lambda: snap)
SA.regime = lambda: asyncio.sleep(0, {"verdict": "صاعد", "state": "up", "close": 11500, "sma50": 11300, "sma200": 11000, "ret3m": 4.2, "chg": 0.35})
SA.brent = lambda: asyncio.sleep(0, {"px": 88.5, "chg": -4.9, "chg5": -4.5})
try:
    ok_read = asyncio.run(SA.close_read())
finally:
    TM.ensure_fresh, TM.snapshot, SA.regime, SA.brent = saved
after = SQ.load("sa")
body = (ROOT / "backend/app/services/saqr_sa.py").read_text(encoding="utf-8")
cr = body[body.index("async def close_read("):body.index("async def cycle(")]
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
check(ok_read and (after.get("pulse") or {}).get("adv") == 2 and (after.get("regime") or {}).get("close") == 11500 and after["positions"] == st0["positions"]
      and after["cash"] == st0["cash"] and "_hunt(" not in cr and "_review(" not in cr
      and 'add_job(job_saqr_sa_close, CronTrigger(day_of_week=TRADING_DAYS, hour=15, minute=25)' in sch and 'id="saqr_sa_close_boot"' in sch,
      "٥ج قراءةُ الإغلاق: نبضُ السوق ومؤشّرُه يُكتبان بعد مزاد الإغلاق (15:25 أيامَ التداول) وبعد كلّ إقلاع — فلا تقول اللوحةُ «غير متوفّر» "
      "خارجَ الجلسة — قراءةٌ وحدها لا صيدَ فيها ولا مراجعة، والمراكزُ والنقدُ كما هما")

# ٦ الواجهة: لا IBKR فوق علامة صقر، ولا «الأحداث الجيوسياسية» في السعوديّ، وأوامرُ المالك في تبويبها وفي المحفظة
desk = re.sub(r"/\*.*?\*/", "", (ROOT / "frontend/src/components/saqr/SaqrDesk.tsx").read_text(encoding="utf-8"), flags=re.S)   # الشيفرةُ لا التعليق
pf = (ROOT / "frontend/src/components/saqr/SaqrPortfolio.tsx").read_text(encoding="utf-8")
nodes = desk[desk.index("function nodes("):desk.index("function Hub(")]
check('k: "broker"' not in nodes and "IBKR" not in desk and "Unlink" not in desk and 'k: "fund"' in nodes and 'k: "breadth"' in nodes
      and "جيوسياس" not in desk and "SaRead" not in desk and 'data-role="sq-pulse"' in desk and "تلغرام" not in desk
      and 'data-role="sq-settings"' in desk and 'data-role="sq-budget"' in desk and '"الإعدادات"' in desk and 'data-role="sp-budget"' in pf,
      "٦ اللوحة: لا IBKR فوق علامة صقر (ومكانَه في الأمريكيّ «الفرزُ الأساسيّ»)، والسعوديُّ بنبض سوقه (تاسي · الاتّساع · التداول · القطاعات · النتائج · برنت) "
      "بلا «الأحداث الجيوسياسية»، ولا ذكرَ لتلغرام، وأوامرُ المالك في «الإعدادات» والميزانيةُ في المحفظة")

print("\nالنتيجة:", "عطب ✖" if fail else "نظيف ✔")
sys.exit(fail)
