#!/usr/bin/env python3
"""حارسُ D761 — حالةُ السوق كتريدنق فيو، والسعرُ الحيّ، والسلسلةُ باليونانيات، والتحليلُ الذكيّ، والأحداثُ الاقتصادية (بأمر المالك 2026-11-17).

يُفحص على الدوالّ نفسِها بلا شبكة: جدولُ نيويورك و«تداول» وعطلُهما، وتقديمُ المصدر الحيّ على الجدول (والإغلاقُ يومَ عملٍ عطلةٌ غيرُ مسمّاة)،
وقراءةُ ياهو وTradingView (المؤجَّلُ يُوسَم)، واليوناناتُ على قيمٍ معروفة، ورأسُ السلسلة (تذبذبُ النقود والحركةُ وألمُ الحدّ الأقصى)،
وأحكامُ التحليل (اليانصيب · بلا سيولة · عكسُ الاتجاه · التآكل · ينتهي غداً بعيداً)، والميزانيةُ التي لا تكفي وبديلُها، والأحداثُ بوقت الرياض.

    python3 scripts/audit/live_options_d761.py
"""
import asyncio, os, pathlib, sys, tempfile   # noqa: E401
from datetime import datetime, timezone
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


from app.services import market_session as MS, live_quote as LQ, option_advisor as A, option_picks as OP, econ_calendar as EC   # noqa: E402

U = lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc)   # noqa: E731
us = {t: MS.us_session(U(t))["state"] for t in ("2026-11-17T13:00:00", "2026-11-17T17:32:00", "2026-11-17T22:00:00", "2026-11-18T02:00:00",
                                                 "2026-11-21T15:00:00", "2026-11-27T19:00:00")}
th = MS.us_session(U("2026-11-26T15:00:00"))
check(list(us.values()) == ["pre", "open", "post", "closed", "closed", "post"] and th["state"] == "holiday" and th["holiday"] == "عيد الشكر",
      "١ السوقُ الأمريكيّ بجدول نيويورك: قبل الافتتاح · مفتوح · بعد الإغلاق · مغلق · السبت مغلق · الإغلاقُ المبكّرُ بعد عيد الشكر — وعيدُ الشكر عطلةٌ باسمها",
      f"{list(us.values())} · {th['state']} {th.get('holiday')}")
sa = [MS.sa_session(U(t))["state"] for t in ("2026-11-17T06:40:00", "2026-11-17T08:00:00", "2026-11-17T12:05:00", "2026-11-20T08:00:00")]
nd = MS.sa_session(U("2026-09-23T08:00:00"))
eid = MS.reconcile(MS.sa_session(U("2026-03-19T08:00:00")), "closed", "TradingView")
check(sa == ["preopen", "open", "auction", "closed"] and nd["state"] == "holiday" and nd["holiday"] == "اليوم الوطني"
      and eid["state"] == "holiday" and "holiday" not in eid,
      "٢ «تداول»: مزادُ الافتتاح · مفتوح · مزادُ الإغلاق · الجمعة مغلق · اليومُ الوطنيّ باسمه — وإغلاقٌ يومَ عملٍ يعلنه المصدرُ عطلةٌ بلا اسمٍ مخترع",
      f"{sa} · {nd['state']} · {eid['state']}")
check(MS._dur(4000) == "1 س 7 د" and MS._dur(3600 * 48) == "يومين" and MS.us_session(U("2026-11-21T14:00:00"))["detail"] == "يفتح بعد يومين",
      "٣ العدُّ التنازليّ بكلامٍ عربيّ (‏«1 س 7 د» · «يومين») — و«يفتح بعد» إلى الافتتاح الرسميّ لا إلى ما قبله")

y = LQ.from_yahoo({"marketState": "PRE", "regularMarketPrice": 154.47, "regularMarketChange": -1.69, "regularMarketChangePercent": -1.08,
                   "preMarketPrice": 156.92, "preMarketChangePercent": 1.6, "regularMarketTime": 1794936767, "earningsTimestamp": 1794949200})
t = LQ.from_tv({"close": 154.45, "change": -1.08, "change_abs": -1.69, "update_mode": "delayed_streaming_900", "current_session": "post_market",
                "postmarket_close": 153.9, "postmarket_change": -0.35})
check(y["price"] == 154.47 and y["delayed"] == 0 and y["_state"] == "pre" and y["ext"]["kind"] == "pre" and y["ext"]["price"] == 156.92 and y["earnings"]
      and t["delayed"] == 15 and t["_state"] == "post" and t["ext"]["kind"] == "post" and abs(t["prev_close"] - 156.14) < 1e-6,
      "٤ السعرُ الحيّ: ياهو مباشرٌ بما قبل الافتتاح وموعدِ الأرباح، وTradingView احتياطٌ مؤجَّلٌ ربعَ ساعةٍ يُوسَم بتأجيله وما بعد الإغلاق")

g = A.greeks(100, 100, 0.5, 0.3, True)
gp = A.greeks(100, 100, 0.5, 0.3, False)
check(abs(g["delta"] - 0.5794) < 1e-3 and abs(g["gamma"] - 0.0184) < 1e-3 and abs(g["theta"] + 0.028) < 1e-3 and abs(g["vega"] - 0.2765) < 1e-3
      and abs(g["delta"] - gp["delta"] - 1) < 1e-9 and gp["theta"] < 0,
      "٥ اليونانيات على قيمٍ معروفة: الدلتا 0.58 والغاما 0.018 والثيتا −0.028 يومياً والفيغا 0.28 لعقدٍ في النقود ستةَ أشهر بتذبذب 30٪",
      str({k: round(v, 4) for k, v in g.items()}))

S = 100.0
mk = lambda K, call, iv=0.3, oi=900, T=60 / 365: (lambda px: {"contract": f"X{K}{'C' if call else 'P'}", "strike": float(K), "ask": round(px * 1.02, 2),   # noqa: E731
                                                             "bid": round(px * 0.98, 2), "last": px, "oi": oi, "volume": 40})(round(OP.bs_price(S, K, T, iv, call), 2))
ch = {"calls": [mk(k, True) for k in range(80, 125, 5)], "puts": [mk(k, False, oi=1500) for k in range(80, 125, 5)]}
st = A.stats(ch, S, 60)
A.enrich_rows(ch["calls"], S, 60, True)
c100 = next(r for r in ch["calls"] if r["strike"] == 100)
check(st["atm_iv"] and abs(st["atm_iv"] - 30) < 1.5 and st["move"] and 11 < st["move"] < 13 and st["pcr_oi"] == round(1500 * 9 / (900 * 9), 2) and 95 <= st["max_pain"] <= 105
      and c100["g"] and abs(c100["g"]["iv"] - 30) < 1.5 and c100["g"]["theta"] < 0 and 0.5 < c100["g"]["delta"] < 0.6,
      "٦ رأسُ السلسلة: تذبذبُ النقود والحركةُ المتوقّعةُ حتى الانتهاء ونسبةُ البيع للشراء وألمُ الحدّ الأقصى — ولكلّ عقدٍ تذبذبُه من سعره ويونانياتُه",
      f"{st['atm_iv']} · ±{st['move']} · {st['pcr_oi']} · {st['max_pain']} · Δ{c100['g']['delta']}")

ctx_up = {"trend": {"state": "صاعد", "close": 100, "sma50": 95, "sma200": 90, "ret3m": 8}, "news": {"impact": "إيجابي", "strength": 2}, "hv": 0.3, "events": [], "earnings": None}
good = {**c100}
lv, pros, cons = A.judge(good, True, S, 60, ctx_up, "2027-01-15")
far = {"contract": "F", "strike": 140.0, "ask": 0.06, "bid": 0.05, "last": 0.05, "oi": 900, "volume": 30}
A.enrich_rows([far], S, 60, True)
lv2, _, cons2 = A.judge(far, True, S, 60, ctx_up, "2027-01-15")
dry = {**c100, "oi": 10, "volume": 2}
lv3, _, cons3 = A.judge(dry, True, S, 60, ctx_up, "2027-01-15")
put = next(r for r in ch["puts"] if r["strike"] == 100)
A.enrich_rows([put], S, 60, False)
lv4, _, cons4 = A.judge(put, False, S, 60, ctx_up, "2027-01-15")
o1 = {"contract": "Z", "strike": 112.0, "ask": 0.3, "bid": 0.28, "last": 0.29, "oi": 900, "volume": 300}
A.enrich_rows([o1], S, 1, True)
lv5, _, cons5 = A.judge(o1, True, S, 1, ctx_up, "2026-11-18")
check(lv == "ok" and any("مع الاتجاه" in x for x in pros) and lv2 == "no" and any("اليانصيب" in x for x in cons2) and lv3 == "no" and any("سيولة" in x for x in cons3)
      and lv4 == "no" and any("عكسُ الاتجاه" in x for x in cons4) and lv5 == "no" and any("يتبخّر" in x for x in cons5),
      "٧ الحكم: العقدُ مع الاتجاه «مناسب»، ويُمتنع عن اليانصيب وعديم السيولة وعكسِ الاتجاه بخبرٍ قويّ والبعيدِ المنتهي غداً — وتُذكر الأسباب",
      f"{lv} · {lv2} · {lv3} · {lv4} · {lv5}")

# ٨ التحليلُ كلُّه ببياناتٍ مصنوعة: الميزانيةُ لا تكفي على ‏^SPX فيُقترح SPY
import app.services.options_chain as OC   # noqa: E402
BIG, SMALL = 6000.0, 30.0


def fake_chain_for(price, t=0):
    exps = [{"t": i, "date": f"2027-0{i}-15", "dte": d} for i, d in ((1, 30), (2, 60), (3, 120))]

    def rows(call):
        out = []
        for k in [price * (0.8 + 0.025 * j) for j in range(17)]:
            p = round(OP.bs_price(price, k, 60 / 365, 0.25, call), 2)
            if p > 0.05:
                out.append({"contract": f"X{t}K{k:.2f}{'C' if call else 'P'}", "strike": round(k, 2), "ask": round(p * 1.01, 2), "bid": round(p * 0.99, 2),
                            "last": p, "oi": 2000, "volume": 300})
        return out
    return {"symbol": "X", "price": price, "expirations": exps, "expiry": 1, "calls": rows(True), "puts": rows(False)}


async def fake_chain(sym, t=None):
    return fake_chain_for(BIG if sym == "^SPX" else SMALL, t or 0)


async def fake_ctx(sym):
    return {**ctx_up, "events": []}


OC.chain, A._context = fake_chain, fake_ctx


async def no_sum(res):
    return None
A.summary = no_sum
r1 = asyncio.run(A.analyze("^SPX", budget=150))
r2 = asyncio.run(A.analyze("^SPX", budget=150000 / 20))
check(r1["fit"] and not r1["fit"]["ok"] and "لا تكفي" in r1["fit"]["text"] and "SPX" in r1["fit"]["text"] and "^" not in r1["fit"]["text"]
      and r1["fit"]["min_cost"] and (r1["fit"].get("alt") or {}).get("symbol") == "SPY" and "تأخذه على SPY" in r1["fit"]["alt"]["text"]
      and r1["fit"]["alt"]["card"]["cost"] <= 150,
      "٨ «150 دولاراً لا تأخذه على SPX — تأخذه على SPY»: الميزانيةُ التي لا تكفي تُقال بأرخص عقدٍ مقبول، ويُقترح الصندوقُ المقابل",
      f"{(r1['fit'] or {}).get('text')} · {((r1['fit'] or {}).get('alt') or {}).get('text')}")
check(r2["best"] and all(c["verdict"] != "no" and c["cost"] <= 7500 and c["type"] == "call" for c in r2["best"]) and len({c["expiry"] for c in r2["best"]}) == len(r2["best"])
      and r2["fit"]["ok"] and r2["lean"] == "call",
      "٩ الأنسبُ ضمن الميزانية مع الاتجاه (شراءٌ لمسارٍ صاعد)، أجلٌ مختلفٌ لكلّ توصية، ولا ممتنَعَ عنه بينها",
      str([(c["contract"], c["cost"], c["verdict"]) for c in r2["best"]]))

# ١٢ المسارُ العرضيّ: نصيحةُ الامتناع صريحةً و«إن أصررت» — والتآكلُ الفادحُ (‏>12٪ يومياً) امتناع
async def flat_ctx(sym):
    return {**ctx_up, "trend": {**ctx_up["trend"], "state": "عرضي"}, "news": {"impact": "محايد", "strength": 0}}
A._context = flat_ctx
r3 = asyncio.run(A.analyze("^SPX", budget=7500))
burn = {"contract": "B", "strike": 101.0, "ask": 0.42, "bid": 0.4, "last": 0.41, "oi": 900, "volume": 300}
A.enrich_rows([burn], S, 2, True)
lv6, _, cons6 = A.judge(burn, True, S, 2, ctx_up, "2026-11-19")
check(r3["lean"] is None and r3["abstain"] and "لا أنصح" in r3["abstain"] and lv6 == "no" and any("يذوب" in x for x in cons6),
      "١٢ المسارُ العرضيّ: «لا أنصح بشراء عقدٍ مكشوفٍ الآن» صراحةً وما بقي «إن أصررت»، والتآكلُ اليوميُّ الفادحُ امتناعٌ لا حذر",
      f"{(r3['abstain'] or '')[:40]} · {lv6} · {cons6[:1]}")

ev = EC.shape([{"title": "FOMC Meeting Minutes", "country": "USD", "date": "2026-11-18T14:00:00-05:00", "impact": "High", "forecast": "", "previous": ""},
               {"title": "CPI m/m", "country": "CAD", "date": "2026-11-16T08:30:00-05:00", "impact": "High"},
               {"title": "Retail Sales m/m", "country": "USD", "date": "2026-11-17T08:30:00-05:00", "impact": "High", "forecast": "0.1%", "previous": "0.8%"},
               {"title": "Crude Oil Inventories", "country": "USD", "date": "2026-11-18T10:30:00-05:00", "impact": "Low"}], now=U("2026-11-17T17:00:00"))
check([e["title"] for e in ev] == ["Retail Sales m/m", "FOMC Meeting Minutes"] and ev[0]["past"] and ev[0]["day"] == "اليوم" and ev[1]["riyadh"] == "2026-11-18 22:00"
      and ev[1]["day"] == "غداً" and ev[0]["forecast"] == "0.1%" and ev[1]["forecast"] is None and EC.before(ev, U("2026-11-20T00:00:00"))[0]["title"] == "FOMC Meeting Minutes",
      "١٠ الأحداثُ الأمريكيةُ المهمّةُ وحدَها بوقت الرياض (محضرُ الفيدرالي 22:00 غداً) وحالُها، والتوقّعُ الفارغُ لا يُدّعى، وما يقع قبل انتهاء عقد")
mk_ = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
ut = (ROOT / "backend/app/services/usage_tracker.py").read_text(encoding="utf-8")
check('@router.get("/live/{symbol}")' in mk_ and '@router.get("/options-advice")' in mk_ and '@router.get("/econ-events")' in mk_
      and '"yahoo_live"' in ut and "enrich_rows(got[\"calls\"]" in mk_,
      "١١ المسارات: السعرُ الحيّ وحالةُ السوق، والتحليلُ الذكيّ، والأحداثُ الاقتصادية، والسلسلةُ باليونانيات — والسعرُ الحيُّ بعدّادٍ مستقلٍّ لا يستنزف حصّةَ التقييم")
print("\nالنتيجة:", "عطب ✖" if fail else "نظيف ✔")
sys.exit(fail)
