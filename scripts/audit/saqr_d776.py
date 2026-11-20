#!/usr/bin/env python3
"""حارسُ D776 — فريقُ صقر: ستّةُ خبراءٍ يحكمون على كلّ عقد، ونسبةُ نجاحٍ يختار المالكُ حدَّها، وسجلٌّ يقيس الفعليّ (2026-11-20).

«نحوّل صقر إلى فريق… مسؤولٌ عن اختيار العقود ورفع نسبة النجاح — لو اخترتُ نسبةَ نجاحٍ لا تقلّ عن 90٪… ذكيٌّ وبسيط، لا يعقّد ولا يتفلسف…
عقدٌ ناضجٌ لا يتآكل مع الزمن قريباً… يقرؤون الخبرَ الذي يخصّ كلَّ شركةٍ بذاتها».

    python3 scripts/audit/saqr_d776.py
"""
import asyncio, os, pathlib, sys, tempfile   # noqa: E401
from datetime import date, datetime, timezone
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


from app.services import saqr_team as TEAM   # noqa: E402
from app.services import saqr_list as SL   # noqa: E402
from app.services import option_picks as OP   # noqa: E402
from app.services import saqr_universe as SU   # noqa: E402
from app.services import live_quote as LQ   # noqa: E402

# ١ الحسابُ: حاجزان متساويان بلا انحراف ⇐ النصف، والنجاحُ القريبُ مع وقفٍ بعيد ⇐ نحو 90٪، ووقفٌ أبعدُ يرفع النسبة
half = TEAM.first_hit(0.1, -0.1, 20, 0.3, r=0.045)               # ‏r = σ²/2 ⇐ انحرافٌ صفر — والأجلُ طويلٌ فيبلغ أحدَهما حتماً
near = TEAM.first_hit(0.05, -0.45, 20, 0.3, r=0.045)              # نظرياً 0.45 ÷ 0.50 = 0.90


def card(S=10.0, K=9.0, dte=330, iv=0.40, call=True, **kw):
    ask = round(OP.bs_price(S, K, dte / 365, iv, call), 2)
    c = {"contract": f"X{K}{dte}{call}", "type": "call" if call else "put", "strike": K, "ask": ask, "dte": dte, "iv": iv * 100,
         "delta": round(OP.bs_delta(S, K, dte / 365, iv, call), 2), "spread_pct": 3.0, "oi": 2000, "need_pct": 4.0, "cost": round(ask * 100), "score": 60,
         "px_src": "ask", "expiry": "2027-10-15", "price": S, "t": 1, "bid": ask - 0.03, "mid": ask - 0.015, "spread_usd": 3.0, "breakeven": K + ask,
         "target": S * 1.3, "target_label": "قمّة السنة", "rr": 1.2, "pop": 40.0, "p_touch": 55.0}
    c.update(kw)
    return c
c40, c70 = TEAM.odds(card(), 10.0, 0.40), TEAM.odds(card(), 10.0, 0.70)
check(0.45 <= half <= 0.55 and 0.86 <= near <= 0.94 and c40 and c70 and c70["p30"] > c40["p30"] and 25 <= c40["p30"] <= 65 and c40["decay_wk"] < 2,
      "١ نسبةُ النجاح حسابٌ لا تخمين: حاجزان متساويان ⇐ النصف · هدفٌ قريبٌ ووقفٌ بعيد ⇐ نحو 90٪ · ووقفٌ أبعدُ يرفع النسبة — والعقدُ الطويلُ يتآكل ببطء",
      f"{half:.2f} · {near:.2f} · وقف40={c40 and c40['p30']} وقف70={c70 and c70['p30']} · تآكل {c40 and c40['decay_wk']}٪")

# ٢ الأعضاءُ الستّة: كلٌّ بسطر — والخبرُ المعاكسُ للشركة نفسِها والمسارُ المعاكسُ والتآكلُ السريعُ يرفض، وموعدُ الأرباح القريبُ يُحذَّر منه
E = {"symbol": "X", "price": 10.0, "fund": 86, "trend": {"state": "صاعد", "strength": 9, "ret3m": 11}, "news": None, "earn": None}
j_ok = TEAM.judge(card(), E)
j_news = TEAM.judge(card(), {**E, "news": {"impact": "سلبي", "event": "تحقيقٌ رسميٌّ في حسابات الشركة"}})
j_tr = TEAM.judge(card(), {**E, "trend": {"state": "هابط", "strength": 5, "ret3m": -9}})
j_dec = TEAM.judge(card(dte=40, K=10.5, iv=0.9), E)
j_earn = TEAM.judge(card(), {**E, "earn": "2026-11-28"}, today=date(2026, 11, 20))
roles = [m["role"] for m in j_ok["members"]]
risk = next(m for m in j_earn["members"] if m["role"] == "المخاطر")
check(roles == ["الأساس", "الفنّ", "الأخبار", "اليونانيات", "المخاطر", "الاحتمال"] and not j_ok["veto"] and j_news["veto"] and j_tr["veto"] and j_dec["veto"]
      and risk["v"] == "warn" and "إعلانُ الأرباح بعد 8" in risk["say"] and "يعاكسها: تحقيقٌ رسميٌّ" in next(m["say"] for m in j_news["members"] if m["role"] == "الأخبار")
      and all(len(m["say"]) < 140 for m in j_ok["members"]),
      "٢ الفريقُ ستّة (الأساس · الفنّ · الأخبار · اليونانيات · المخاطر · الاحتمال) بسطرٍ قصيرٍ لكلّ — وخبرُ الشركة المعاكس، والمسارُ المعاكس، والتآكلُ "
      "السريعُ يرفض كلٌّ منها العقد، وإعلانُ الأرباح خلال أسبوعين تحذير", f"{[m['v'] for m in j_ok['members']]} · {j_ok['p30']}")

# ٣ البناء: الفريقُ يحكم على كلّ عقد، وسهمٌ رفض الفريقُ عقودَه كلَّها يُسجَّل سببُه بعضوه — والعرضُ بنسبة النجاح الدنيا
TR = lambda st, c, r3=10.0: {"state": st, "close": c, "sma50": c * 0.95, "sma200": c * 0.9, "ret3m": r3, "strength": 9.0, "traded": 300.0, "earn": None}   # noqa: E731
SYMS = {"GOOD": TR("صاعد", 10.0), "NEAR": TR("صاعد", 10.0), "BADN": TR("صاعد", 10.0)}


async def fake_universe():
    return {"tr": SYMS, "fund": {s: (85, "متين") for s in SYMS}, "names": {}, "meta": {}}


async def fake_valid(sym, call, tr, diag=None):
    if sym == "NEAR":    # عقدٌ قريبُ الأجل سريعُ التآكل — يرفضه عضوُ اليونانيات
        return {}, [card(dte=40, K=10.5, iv=0.9, contract="NEARC", symbol=sym)]
    return {}, [card(contract=f"{sym}C", symbol=sym), card(K=8.0, contract=f"{sym}C8", symbol=sym)]


async def fake_news(items):
    return {"BADN": {"impact": "سلبي", "strength": 3, "event": "خفضُ التوقّعات"}}


async def open_sess():
    return {"us": {"state": "open"}}
SU.universe, OP.valid_contracts, OP.read_news, LQ.sessions = fake_universe, fake_valid, fake_news, open_sess
raw = asyncio.run(SL.build({"per_trade": 500, "sides": "both", "opt_stop": 40}, set()))
v0 = SL.view(raw, 500, min_win=0)
p_good = v0["items"][0]["team"]["p30"] if v0["items"] else 0
v_hi = SL.view(raw, 500, min_win=95)
check([i["symbol"] for i in v0["items"]] == ["GOOD"] and raw["done"]["BADN"]["why"] == "خبرٌ قويٌّ يعاكس المسار"
      and raw["done"]["NEAR"]["why"].startswith("رفضه الفريق") and all(m in v0["items"][0]["team"] for m in ("members", "p30", "verdict"))
      and not v_hi["items"] and v_hi["excluded"].get("نسبةُ نجاحه دون 95٪") == 1 and v0["wins"]["0"] == 1 and v0["wins"]["90"] == 0
      and v0["track"]["open"] >= (1 if p_good >= 45 else 0),
      "٣ البناء: الفريقُ يحكم على كلّ عقد (ورفضُه يُسجَّل بعضوه)، والخبرُ المعاكسُ يُسقط السهم — والعرضُ بنسبة النجاح الدنيا التي يختارها المالك "
      "(ومعها عددُ العقود عند كلّ حدّ)، وما دونها يُعدّ بسببه", f"{raw['done']} · نجاح {p_good} · {v0['wins']}")

# ٤ السجلّ: يُسجَّل ما اختاره الفريقُ بسعر عرضه، ويُتابَع بالطلب الحيّ — نجح عند +30٪ · أُوقف عند −40٪ · حان الخروج — والنسبةُ من المغلقة
TEAM.track_save({"open": [], "closed": [], "marked": None})
mk = lambda s, p30=60.0, veto=False, warns=1, src="ask": {"symbol": s, "contract": f"{s}C", "type": "call", "strike": 9.0, "expiry": "2027-10-15",   # noqa: E731
                                                         "ask": 1.0, "px_src": src, "team": {"p30": p30, "veto": veto, "warns": warns}}
n_add = TEAM.track_add([mk("A"), mk("B"), mk("C"), mk("D", p30=30), mk("E", veto=True), mk("F", src="snap"), mk("A")], datetime(2026, 11, 20, 16, tzinfo=timezone.utc))
t = TEAM.track_load()
t["open"][2]["exit_by"] = "2026-11-19"
TEAM.track_save(t)
Q = {"AC": 1.31, "BC": 0.59, "CC": 1.10}


async def fake_q(c):
    return {"bid": Q.get(c), "live": True}
t2 = asyncio.run(TEAM.track_mark(datetime(2026, 11, 20, 17, tzinfo=timezone.utc), fake_q))
stt = TEAM.track_stats(t2)
res = {r["symbol"]: r["result"] for r in t2["closed"]}
check(n_add == 3 and res == {"A": "win", "B": "stop", "C": "time"} and stt["closed"] == 3 and stt["wins"] == 1 and stt["rate"] == 33.3 and stt["open"] == 0,
      "٤ سجلُّ الفريق: يُسجَّل ما اختاره (نسبةُ نجاحٍ ≥ 45٪ بلا رفضٍ وبسعرٍ حيّ، سهمٌ لا يتكرّر) ويُتابَع بالطلب الحيّ — نجح عند +30٪، وأُوقف عند −40٪، "
      "وحان خروجُه — والنسبةُ الفعليةُ من المغلقة", f"{res} · {stt}")

# ٥ الأوصال: الحدُّ الأدنى في أوامر المالك، والتداولُ الآليُّ والنقطةُ يقرآنه، والسجلُّ يُتابَع من دورة صقر، والمُصفّي يحمل موعدَ الأرباح، والواجهة
from app.services import saqr_trader as SQ   # noqa: E402
st = SQ.fresh(capital=1000)
SQ.apply_settings(st, {"min_win": 70})
try:
    SQ.apply_settings(SQ.fresh(capital=1000), {"min_win": 99})
    bad = False
except ValueError:
    bad = True
tr = (ROOT / "backend/app/services/saqr_trader.py").read_text(encoding="utf-8")
mkp = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
ui = (ROOT / "frontend/src/components/saqr/SaqrList.tsx").read_text(encoding="utf-8")
hunt = tr[tr.index("async def _hunt("):tr.index("# ══ أوامرُ المالك (‏D771)")]
row = {"close": 20, "SMA50": 19, "SMA200": 18, "EMA20": 19.5, "Perf.3M": 6, "Value.Traded": 2e8, "earnings_release_next_date": 1795478400}
check(SQ.cfg(st)["min_win"] == 70 and SQ.cfg(SQ.fresh())["min_win"] == 0 and bad and 'float(c.get("min_win") or 0)' in hunt
      and "SL.kick_track(now, us_clock(now))" in tr and 'float(c.get("min_win") or 0)' in mkp and SU.tv_trend(row)["earn"] == "2026-11-24"
      and all(x in ui for x in ('data-role="sl-team"', 'data-role="sl-mem"', 'data-role="sl-win"', 'data-role="sl-winbar"', 'data-role="sl-win-lv"',
                                'data-role="sl-track"', "marketApi.saqrSettings({ min_win: w }", "<WinBar L={L} owner={owner} />")),
      "٥ نسبةُ النجاح الدنيا أمرٌ للمالك (0–95)، والتداولُ الآليُّ ونقطةُ القائمة يقرآنها، والسجلُّ يُتابَع من دورة صقر، وموعدُ الأرباح من المُصفّي — "
      "والبطاقةُ بفريقها ونسبة نجاحها، ورأسُ القائمة بالحدّ الأدنى وعدد عقوده والسجلّ")

print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
