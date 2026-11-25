#!/usr/bin/env python3
"""حارسُ D832 — بابُ صقر الواحد للدخول الآليّ في السوقين (المالك 2026-11-25).

قال المالك: «هل صقرٌ في التداول الآليّ أصبح عقليةً موحّدة… الفوليوم بروفايل… العقودُ الطويلة… السترايكاتُ الممتازة — هل وصله هذا التطوير؟
تأكّد، لأنّي لا أريد إلا اللونَ الأخضر… وأريد صقرَ الأمريكيّ والسعوديّ في مستوى نجاحٍ واختيارٍ موحَّد — صقرٌ واحد».
قيس على الخادم (‏saqr_auto_door_d832): الأمريكيُّ الآليُّ اشترى أعلى توصيات «عقود الخيارات» درجةً (49 من 100) بلا حكم صقر، متجاهلاً حدَّ النجاح
الذي ضبطه المالك (90٪) — فخسرت صفقتاه المقفلتان؛ والسعوديُّ يقبل «يوافق بتحفّظ» ويشتري إن تعذّرت قراءتُه الأخيرة، ومنبعُه الشركاتُ كلُّها لا الفرص.

  ١ المنبعُ واحد: فرصُ اليوم من مسح السوق بموافقة صقر الكاملة — و«بتحفّظ» أو قراءةٌ أخيرةٌ غيرُ الشراء لا تدخل، ولا مسحَ حديث ⇒ لا شيء.
  ٢ البابُ واحد: الرفضُ يمنع بسببه، و«بتحفّظ» يمنع، وتعذّرُ القراءة الأخيرة يمنع، و«انتظار» يمنع — و«يوافق» مع «شراء» يفتح.
  ٣ الأمريكيّ: الأعلى درجةً في الدفتر لا يُشترى إن لم يكن في الفرص، ولا عقدُ بيعٍ على فرصة صعود، ولا «بتحفّظ» لحظةَ الشراء — ويُشترى ما اجتاز،
    وفي أسبابه حكمُ صقر لحظتَه وقراءتُه ونسبةُ نجاحه؛ وكلُّ مرشّحٍ بحكمه وسببه في «قراراتُ صقر».
  ٤ حدُّ النجاح واحدٌ للسوقين (أعلى ما ضبطه المالك): بحدّ 90٪ يُرفض العقدُ بنسبته قبل أن يُسأل صقر (الأرخصُ أوّلاً)، والسعوديُّ يأخذ الحدَّ نفسَه.
  ٥ السعوديّ: من الفرص وحدها؛ «يوافق» مع «شراء» يشتري بنسبة نجاحه في أسبابه، و«بتحفّظ» يُرفض بسببه، وحدُّ 90٪ يرفض بنسبته.
  ٦ نسبةُ نجاح السهم بنموذج العقد نفسِه (حاجزان من التذبذب): هدفٌ ووقفٌ متساويان ≈ 50٪، والهدفُ الأبعد أقلّ، والمقلوبُ لا رقم.
  ٧ الواجهة: «قراراتُ صقر في آخر دورة» في السوقين، والأمريكيُّ بسطر بحثه (التوصيات · الفرص · الحدّ).

    python3 scripts/audit/saqr_auto_d832.py
"""
import asyncio
import datetime as dt
import json
import os
import pathlib
import sys
import tempfile

_SB = tempfile.mkdtemp(prefix="sp_d832_")
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


from app.services import chart_scan as CS   # noqa: E402
from app.services import option_picks as OP   # noqa: E402
from app.services import research_desk as RD   # noqa: E402
from app.services import saqr_council as CN   # noqa: E402
from app.services import saqr_sa as SA   # noqa: E402
from app.services import saqr_team as TEAM   # noqa: E402
from app.services import saqr_trader as SQ   # noqa: E402

REAL = {"collect": CN.collect, "judge": CN.judge}
OK = {"verdict": "يوافق", "score": 84, "veto": False, "veto_why": [], "oks": 6, "warns": 0,
      "members": [{"role": "المسار", "v": "ok", "say": "مسارٌ صاعد"}, {"role": "الحجم", "v": "ok", "say": "الطريقُ مفتوحٌ من قاعدة حجم"}]}
RES = {**OK, "verdict": "يوافق بتحفّظ", "score": 63, "warns": 2}
VETO = {**OK, "verdict": "يرفض", "veto": True, "veto_why": ["الأخبار: خبرٌ يعاكس"]}
BUY = {"decision": "شراء", "confidence": "متوسطة", "link": "المسارُ والحجمُ يجتمعان.", "conflict": ""}
WAIT = {**BUY, "decision": "انتظار", "link": "ينتظر تأكيدَ الاختراق."}

# ── ١ المنبع ──
now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
CS.save("us", {"at": now, "items": [
    {"symbol": "AAA", "side": "long", "council": {"verdict": "يوافق", "veto": False}, "link": BUY},
    {"symbol": "BBB", "side": "long", "council": {"verdict": "يوافق بتحفّظ", "veto": False}},
    {"symbol": "CCC", "side": "short", "council": {"verdict": "يوافق", "veto": False}, "link": {**BUY, "decision": "بيع"}},
    {"symbol": "DDD", "side": "long", "council": {"verdict": "يوافق", "veto": False}, "link": WAIT},
    {"symbol": "EEE", "side": "long", "council": {"verdict": "يوافق", "veto": False}}]})
op = CN.opportunities("us")
CS.save("sa", {"at": (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=9)).isoformat(timespec="seconds"),
               "items": [{"symbol": "1120", "side": "long", "council": {"verdict": "يوافق", "veto": False}}]})
check(sorted(op) == ["AAA", "CCC", "EEE"] and CN.opportunities("sa") == {},
      "١ المنبعُ واحد: فرصُ اليوم بموافقة صقر الكاملة (وبيعٌ على فرصة هبوط) — و«بتحفّظ» وقراءةٌ أخيرةٌ تقول «انتظار» لا تدخل، ومسحٌ قديمٌ ⇒ لا شيء",
      f"{sorted(op)}")

# ── ٢ الباب ──
g = {k: CN.gate_why(bd, lk, side) for k, (bd, lk, side) in {
    "veto": (VETO, BUY, "long"), "res": (RES, BUY, "long"), "nolink": (OK, None, "long"), "wait": (OK, WAIT, "long"),
    "ok": (OK, BUY, "long"), "short_ok": (OK, {**BUY, "decision": "بيع"}, "short"), "short_buy": (OK, BUY, "short")}.items()}
check(g["ok"] is None and g["short_ok"] is None and "خبرٌ يعاكس" in (g["veto"] or "") and "بموافقته الكاملة وحدها" in (g["res"] or "")
      and "غيرُ متوفّرة" in (g["nolink"] or "") and "انتظار" in (g["wait"] or "") and g["short_buy"] is not None,
      "٢ البابُ واحد: الرفضُ يمنع بسببه، و«بتحفّظ» يمنع، وتعذّرُ القراءة الأخيرة يمنع، و«انتظار» يمنع — و«يوافق» مع «شراء» (أو «بيع» للهبوط) يفتح",
      json.dumps(g, ensure_ascii=False)[:300])


# ── ٣ الأمريكيّ ──
def rec(sym, typ="call", score=60.0):
    return {"contract": f"{sym}271217{'C' if typ == 'call' else 'P'}00002500", "symbol": sym, "name": sym, "type": typ, "strike": 2.5, "expiry": "2027-12-17",
            "t": 1, "opened": "2026-11-20", "target": 15.0, "target_label": "قمّة السنة", "card": {"score": score, "delta": 0.6, "iv": 40.0, "reasons": [f"سببُ {sym}"]}}


OP.book_save(150, {"open": [rec("TOP", score=95), rec("PUTX", "put", score=90), rec("RES", score=80), rec("WIN", score=70)], "closed": []})


async def fake_q(c):
    from app.services.options_chain import parse_option
    return {"o": parse_option(c), "t": 1, "dte": 392, "ask": 0.9, "bid": 0.86, "live": True, "price": 3.0, "name": "X"}   # فوق قيمته الذاتية (0.5)


asked: list[str] = []


async def fake_collect(market, cands, ctx, conc=4, flow_max=20):
    asked.extend(c["symbol"] for c in cands)
    return {c["symbol"]: {"symbol": c["symbol"]} for c in cands}


async def fake_ctx(market):
    return {}


async def fake_link(sym, name, market, side, bd, chart=None, price=None):
    return BUY
SQ.contract_quote = fake_q
CN.collect, CN.context, CN.link = fake_collect, fake_ctx, fake_link
CN.judge = lambda ev: RES if ev["symbol"] == "RES" else OK
CN.opportunities = lambda m: {"PUTX": {"symbol": "PUTX", "side": "long", "tr": {}, "close": 3}, "RES": {"symbol": "RES", "side": "long", "tr": {}, "close": 3},
                              "WIN": {"symbol": "WIN", "side": "long", "tr": {}, "close": 3}} if m == "us" else {}
st = SQ.fresh(capital=1000)
SQ.apply_settings(st, {"auto": True, "sides": "both", "per_trade": 150, "opt_stop": 40, "take_x": 2})
pos = asyncio.run(SQ._hunt(st, SQ._now()))
sg = {x["sym"]: x for x in st["signals"]}
check(pos and pos["symbol"] == "WIN" and any("حكمُ صقر لحظةَ الشراء: يوافق" in w for w in pos["why"]) and any(w.startswith("قراءةُ صقر الأخيرة (شراء") for w in pos["why"])
      and any(w.startswith("نسبةُ النجاح") for w in pos["why"]) and "ليس في فرص اليوم" in sg["TOP"]["why"] and "اتّجاهان مختلفان" in sg["PUTX"]["why"]
      and "بموافقته الكاملة وحدها" in sg["RES"]["why"] and sg["WIN"]["verdict"] == "chosen" and st["signals"][0]["verdict"] == "chosen"
      and (st.get("hunt_meta") or {}).get("opps") == 3,
      "٣ الأمريكيّ: الأعلى درجةً في الدفتر لا يُشترى إن لم يكن في الفرص، ولا عقدُ بيعٍ على فرصة صعود، ولا «بتحفّظ» لحظةَ الشراء — ويُشترى ما اجتاز "
      "بحكم صقر لحظتَه وقراءتِه ونسبةِ نجاحه، وكلُّ مرشّحٍ بحكمه وسببه في «قراراتُ صقر»",
      json.dumps({k: (v["verdict"], v["why"][:40]) for k, v in sg.items()}, ensure_ascii=False))

# ── ٤ حدُّ النجاح الواحد ──
asked.clear()
st4 = SQ.fresh(capital=1000)
SQ.apply_settings(st4, {"auto": True, "sides": "both", "per_trade": 150, "min_win": 90})
SQ.save(st4)
sa0 = SQ.fresh(capital=1000, market="sa")
SQ.save(sa0)
fl = SQ.win_floor()
p4 = asyncio.run(SQ._hunt(st4, SQ._now()))
sg4 = {x["sym"]: x for x in st4["signals"]}
od = TEAM.odds({"contract": "WIN271217C00002500", "type": "call", "strike": 2.5, "iv": 40.0, "ask": 0.9, "dte": 392}, 3.0, 0.40)
check(fl == 90 and p4 is None and "دون حدّك 90٪" in sg4["WIN"]["why"] and asked == [] and od and od["p30"] < 90,
      "٤ حدُّ النجاح واحدٌ للسوقين (أعلى ما ضبطه المالك): بحدّ 90٪ يُرفض العقدُ بنسبته قبل أن يُسأل صقر — والسعوديُّ بلا حدٍّ يأخذه",
      f"حدّ {fl} · نسبةُ العقد {od and od['p30']} · {sg4['WIN']['why'][:60]}")
CN.judge = REAL["judge"]

# ── ٥ السعوديّ ──
TRU = {"state": "صاعد", "close": 90, "sma50": 85, "sma200": 80, "ret3m": 14.0, "strength": 6, "hi52": 105}
CH_BUY = {"setup": "ارتدادٌ من الدعم", "side": "long", "quality": 72, "where": "في منطقة الدعم", "horizon": "شهران"}
FLAT = {"setup": None, "side": None, "quality": None, "where": "بين الوسط والمقاومة", "liq": {"side": "flat", "strength": 20, "word": "متوازنة", "level": "ضعيفة"}}
REG = {"verdict": "صاعد", "state": "صاعد", "close": 11500, "sma50": 11300, "sma200": 11000, "ret3m": 4.0, "chg": 0.4, "slope50": 1}
YF = {"q": [{"label": "1Q", "ni": 3e6}, {"label": "2Q", "ni": 4e6}, {"label": "3Q", "ni": 5e6}], "eps": [],
      "votes": {"strongBuy": 8, "buy": 10, "hold": 3, "sell": 0}, "target": 110.0}


async def sa_hunt(opps, chart=CH_BUY, floor=0, judge=None):
    async def fake_trend(sym):
        return dict(TRU)

    async def fake_chart(sym):
        return chart, chart, dict(TRU)

    async def yf(ysym):
        return YF

    async def heads(sym, name=None):
        return []

    async def no_events(market, hours=48):
        return []

    async def vol(sym):
        return 0.25

    async def lk(*a, **k):
        return BUY
    o = (SA.trend, SA.results_of, CN.chart_sa, CN.yf, CN.heads_sa, CN.events, CN.opportunities, SA.vol_of, CN.link, CN.collect)
    SA.trend, CN.chart_sa, CN.yf, CN.heads_sa, CN.events, SA.vol_of, CN.link = fake_trend, fake_chart, yf, heads, no_events, vol, lk
    CN.collect = REAL["collect"]
    CN.judge = judge or REAL["judge"]
    CN.opportunities = lambda m: {s: {"symbol": s, "side": "long"} for s in opps}
    SA.results_of = lambda s, t: ("strong", "صافي الربح +28٪ عن الربع المماثل.", 28.0)
    us = SQ.fresh(capital=1000)
    SQ.apply_settings(us, {"min_win": floor})
    SQ.save(us)
    try:
        snap = {s: {"price": 90.0, "bid": 89.98, "ask": 90.02, "turnover": 3e7, "change_pct": 1.2, "name_en": s} for s in ("1120", "2010")}
        stt = SQ.fresh(market="sa")
        p = await SA._hunt(stt, dt.datetime.now(dt.timezone.utc), snap, REG, {"level": "منخفض", "why": "هدوء"})
        return p, {x["sym"]: x for x in stt["signals"]}, stt
    finally:
        SA.trend, SA.results_of, CN.chart_sa, CN.yf, CN.heads_sa, CN.events, CN.opportunities, SA.vol_of, CN.link, CN.collect = o
        CN.judge = REAL["judge"]


from app.services import cache   # noqa: E402
for k in list(cache._store):
    if k.startswith("council:"):
        cache._store.pop(k, None)
p5, s5, st5 = asyncio.run(sa_hunt(["1120"]))
p5n, s5n, _ = asyncio.run(sa_hunt([]))
for k in list(cache._store):
    if k.startswith("council:"):
        cache._store.pop(k, None)
# «بتحفّظ»: حكمُ الشواهد الحقيقيّ نفسُه بتحفّظين (الرسمُ بلا فرصةٍ تحفّظٌ واحدٌ يبقيها «يوافق» بقواعد صقر)
p5r, s5r, _ = asyncio.run(sa_hunt(["1120"], chart=FLAT, judge=lambda ev: {**REAL["judge"](ev), "verdict": "يوافق بتحفّظ", "warns": 2}))
p5f, s5f, st5f = asyncio.run(sa_hunt(["1120"], floor=90))
check(p5 and p5["symbol"] == "1120" and "2010" not in s5 and any(w.startswith("نسبةُ النجاح") for w in p5["why"]) and any(w.startswith("قراءةُ صقر الأخيرة (شراء") for w in p5["why"])
      and p5n is None and s5n == {} and p5r is None and "بموافقته الكاملة وحدها" in s5r["1120"]["why"]
      and p5f is None and "دون حدّك 90٪" in s5f["1120"]["why"] and (st5f.get("scan_meta") or {}).get("floor") == 90,
      "٥ السعوديّ: من الفرص وحدها (‏2010 ليس فيها فلا يُقرأ، ولا فرصَ ⇒ لا شيء)؛ «يوافق» مع «شراء» يشتري ونسبةُ نجاحه في أسبابه، و«بتحفّظ» يُرفض بسببه، "
      "وحدُّ 90٪ يرفض بنسبته",
      json.dumps({"شراء": p5 and p5["symbol"], "تحفّظ": (s5r.get("1120") or {}).get("why", "")[:50], "حدّ": (s5f.get("1120") or {}).get("why", "")[:70]},
                 ensure_ascii=False))

# ── ٦ نسبةُ نجاح السهم ──
eq = TEAM.odds_stock(100, 90, 110, 0.25)
near = TEAM.odds_stock(100, 90, 105, 0.25)
far = TEAM.odds_stock(100, 94, 125, 0.25)
bad = TEAM.odds_stock(100, 101, 110, 0.25)
long_h = TEAM.odds_stock(100, 90, 110, 0.25, days=3650)
check(eq is not None and 35 <= eq < 50 and long_h is not None and 47 <= long_h <= 58 and near > eq > far and bad is None and TEAM.odds_stock(100, 90, 110, None) is None,
      "٦ نسبةُ نجاح السهم بنموذج العقد نفسِه: هدفٌ ووقفٌ متساويان دون النصف في ثلاثة أشهر (بعضُ المسارات لا يبلغ أيّاً منهما) ونحو النصف بأفقٍ طويل، "
      "والهدفُ الأقربُ أعلى والأبعدُ أقلّ، والمقلوبُ أو بلا تذبذبٍ لا رقم", f"{eq} · طويل {long_h} · {near} · {far} · {bad}")

# ── ٧ الواجهة ──
desk = (ROOT / "frontend/src/components/saqr/SaqrDesk.tsx").read_text(encoding="utf-8")
blk = desk[desk.index('data-role="sq-signals"') - 200:desk.index('data-role="sq-signals"')]
check('{tab === "opps" && (sa || s.hunt) && (' in blk and 'data-role="sq-hunt"' in desk and '"hunt": st.get("hunt_meta")' in (ROOT / "backend/app/services/saqr_trader.py").read_text(encoding="utf-8"),
      "٧ الواجهة: «قراراتُ صقر في آخر دورة» في السوقين، والأمريكيُّ بسطر بحثه (التوصيات · الفرص · حدُّ النجاح)")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
