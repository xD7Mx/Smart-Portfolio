#!/usr/bin/env python3
"""حارسُ D759 · D762 — مُنتقي عقود الخيارات طويلة الأجل ودفترُ توصياته (بأمر المالك 2026-11-17 · 2026-11-18).

‏D759: «خانةٌ لقيمة العقد فيُخرج أفضلَ الخيارات على المسار والأخبار، عقوداً طويلةَ المدى، صفقاتٍ بمبرّراتها».
‏D762: «فارقُ العرض والطلب 30 دولاراً — خسارةٌ مباشرة… والنتائجُ كلَّ يومٍ تختلف وهي طويلةُ المدى — لازم الاختيارُ مقنع حتى السترايك».
يُفحص على الدوالّ نفسِها بلا شبكة: رياضيّاتُ الخيار، والمسار، وقاعدةُ الخبر، والفارقُ ≤ 10٪ من عرضٍ وطلبٍ حقيقيّين (حيّين أو من آخر
جلسة — لا آخرُ صفقة)، والهدفُ الفنيّ ولماذا التنفيذ، وحفظُ آخر جلسة، وقواعدُ الخروج، وثباتُ الدفتر يوماً بعد يوم.

    python3 scripts/audit/option_picks_d759.py
"""
import asyncio, json, math, os, pathlib, sys, tempfile, time   # noqa: E401
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


from app.services import option_picks as OP   # noqa: E402

d = OP.bs_delta(100, 100, 1.0, 0.3, True)
dp = OP.bs_delta(100, 100, 1.0, 0.3, False)
p_atm = OP.prob_beyond(100, 100, 0.01, 0.3, True)
p_far = OP.prob_beyond(100, 150, 0.5, 0.3, True)
check(0.55 < d < 0.65 and abs(d - dp - 1) < 1e-9 and abs(p_atm - 0.5) < 0.02 and p_far < 0.1,
      "١ رياضيّاتُ الخيار: دلتا الشراء في النقود نحو 0.6 لسنة (والبيعُ = الشراءُ − 1)، واحتمالُ تجاوز التعادل في النقود نحو النصف، والبعيدُ ضئيل",
      f"دلتا {d:.3f} · {dp:.3f} · {p_atm:.3f} · {p_far:.3f}")


def bars(f, n=300):
    return [{"close": f(i)} for i in range(n)]


up, dn, flat = OP.trend_of(bars(lambda i: 50 + i * 0.3)), OP.trend_of(bars(lambda i: 200 - i * 0.3)), OP.trend_of(bars(lambda i: 100 + 5 * math.sin(i / 7)))
pull = OP.trend_of(bars(lambda i: 50 + i * 0.3 if i < 293 else 137.9 - (i - 292) * 1.2))
check(up["state"] == "صاعد" and dn["state"] == "هابط" and flat["state"] == "عرضي" and OP.trend_of(bars(lambda i: 10)[:100]) is None
      and pull["state"] == "صاعد" and pull["close"] < pull["sma50"] and OP.trend_of(bars(lambda i: 0.1 + i * 1e-4)) is None
      and all(k in up for k in ("hi60", "hi120", "lo60", "lo120")),
      "٢ المسارُ من الشموع: صاعدٌ وهابطٌ وعرضيّ، والارتدادُ دون 50 لا يلغي المسار، ولا حكمَ بأقلَّ من 210 جلسات ولا لرمزٍ دون دولارين — "
      "ومعه قممُ 60 و120 جلسةً وقيعانُها للهدف الفنيّ", f"{up['state']} · {dn['state']} · {flat['state']} · ارتداد {pull['state']}")
check(OP.direction(up, None)[0] == "call" and OP.direction(dn, None)[0] == "put"
      and OP.direction(up, {"impact": "سلبي", "strength": 2})[0] is None
      and OP.direction(up, {"impact": "سلبي", "strength": 1})[0] == "call"
      and OP.direction(flat, {"impact": "سلبي", "strength": 3})[0] == "put"
      and OP.direction(flat, {"impact": "إيجابي", "strength": 2})[0] is None,
      "٣ الأخبار: الحدثُ القويُّ المعاكسُ للمسار يُسقط الصفقة، والطفيفُ لا يُسقطها، والجوهريُّ يعطي العرضيَّ اتجاهَه")

# ── سلسلةٌ مصنوعةٌ بأسعار بلاك-شولز (تذبذب 45٪، 270 يوماً) وفارقٍ 4٪ ──
S, DTE, IV = 20.0, 270, 0.45
T = DTE / 365
TR = {**up, "close": S, "sma50": 19.0, "sma200": 17.0, "hi60": 22.5, "hi120": 24.0, "hi52": 26.0, "lo60": 17.5, "lo120": 16.0, "lo52": 15.0}


def row(K, call, spread=0.04, oi=800, **kw):
    m = OP.bs_price(S, K, T, IV, call)
    return {"contract": f"X{K:g}{'C' if call else 'P'}", "strike": float(K), "bid": round(m * (1 - spread / 2), 2), "ask": round(m * (1 + spread / 2), 2),
            "last": round(m, 2), "oi": oi, "volume": 50, **kw}


calls = [row(k, True) for k in (14, 16, 18, 20, 22, 24, 26, 30)]
ref = OP.atm_iv({"calls": calls, "puts": [row(k, False) for k in (18, 20, 22)]}, S, T)
k = OP.pick_contract(calls, S, DTE, True, 400, TR, ref_iv=ref)
allc = OP.candidates(calls, S, DTE, True, TR, ref_iv=ref)
check(k and k["target"] == 26.0 and k["target_label"] == "قمّة السنة" and k["breakeven"] < k["target"] and k["rr"] >= OP.MIN_RR
      and OP.MIN_DELTA <= k["delta"] <= OP.MAX_DELTA and k["spread_pct"] <= 10 and k["cost"] <= 400 and k["px_src"] == "ask"
      and all(c["breakeven"] < c["target"] and c["rr"] >= OP.MIN_RR and abs(c["delta"]) >= OP.MIN_DELTA for c in allc),
      "٤ التنفيذ على هدفٍ فنيّ على أفق العقد: أبعدُ قمّةٍ ضمن الحركة المتوقّعة (قمّةُ السنة)، والتعادلُ دونه، والعائدُ عنده ≥ 0.75 من الكلفة، والدلتا 0.30–0.85، "
      "والفارقُ ≤ 10٪ — ولا يبقى في المرشّحين ما يخالفها",
      str(k and {x: k[x] for x in ("contract", "strike", "cost", "target", "breakeven", "rr", "delta", "pop", "p_touch")}))
wide = row(20, True, spread=0.30)
lastonly = {**row(20, True), "bid": 0.0, "ask": 0.0, "last_trade": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())}
snap = {**row(20, True), "bid": 0.0, "ask": 0.0, "sbid": row(20, True)["bid"], "sask": row(20, True)["ask"], "sat": "2026-11-17T20:40"}
ew, why_w = OP.evaluate(wide, S, DTE, True, TR, ref)
el, why_l = OP.evaluate(lastonly, S, DTE, True, TR, ref)
es, _ = OP.evaluate(snap, S, DTE, True, TR, ref)
check(ew is None and "الفارق" in why_w and el is None and "حقيقيّين" in why_l and es and es["px_src"] == "snap" and es["spread_pct"] <= 10
      and OP.quote(lastonly, S, T, True) and OP.quote(lastonly, S, T, True)["src"] == "last",
      "٤ب الفارق (‏D762 — عقدُ NIO بفارق 30 دولاراً): فارقُ 30٪ يُرفض، وآخرُ صفقةٍ بفارقٍ مجهولٍ لا تُبنى عليها توصية (وتبقى للعرض وحده)، "
      "وطلبُ آخر جلسةٍ وعرضُها يُقبلان موسومَين «آخر جلسة»", f"{why_w} · {why_l} · {es and es['px_src']}")
tp, lp = OP.target_for({**TR, "hi60": 20.5, "hi120": 20.8, "hi52": 20.9}, S, True, 0.45, T)
tfar, lfar = OP.target_for({**TR, "hi60": 40.0, "hi120": 45.0, "hi52": 50.0}, S, True, 0.45, T)
tdn, ldn = OP.target_for(TR, S, False, 0.45, T)
cap = S * math.exp(0.45 * math.sqrt(T))
check(abs(tp - cap) < 0.02 and "انحرافٍ واحد" in lp and abs(tfar - cap) < 0.02 and tdn == 15.0 and ldn == "قاع السنة",
      "٤ج الهدفُ على أفق العقد: عند القمم أو إن تجاوزت القممُ الحركةَ المتوقّعة فالهدفُ حدُّ الحركة بانحرافٍ واحد حتى الانتهاء — "
      "وللبيع أبعدُ قاعٍ ضمنها", f"{tp} {lp} · {tfar} · {tdn} {ldn}")
import app.services.options_chain as OC   # noqa: E402
opn = {"expiry": 1800000000, "calls": [row(k, True) for k in (18, 20, 22)], "puts": [row(k, False) for k in (18, 20, 22)]}
OC.snapshot("ZZ", opn, now=1795000000)
shut = {"expiry": 1800000000, "calls": [{**r, "bid": 0.0, "ask": 0.0} for r in opn["calls"]], "puts": [{**r, "bid": 0.0, "ask": 0.0} for r in opn["puts"]]}
OC.snapshot("ZZ", shut)
r0 = shut["calls"][1]
check(r0.get("sbid") == opn["calls"][1]["bid"] and r0.get("sask") == opn["calls"][1]["ask"] and r0.get("sat", "").startswith("2026-")
      and OP.quote(r0, S, T, True, allow_last=False)["src"] == "snap",
      "٤د السلسلةُ تحفظ طلبَ الجلسة وعرضَها والسوقُ مفتوح، وتُلحقهما بالعقد والسوقُ مغلق (يصفّرهما المصدر) — فيُعرف الفارقُ الحقيقيّ",
      f"{r0.get('sbid')}/{r0.get('sask')} · {r0.get('sat')}")
k["expiry"] = "2027-08-20"
rs = OP.reasons("XYZ", TR, {"impact": "إيجابي", "strength": 1, "event": "ترقيةٌ من بيت خبرة"}, k, "")
check(any("الهدفُ الفنيّ" in x and "قمّة السنة" in x and "العائدُ إلى المخاطرة" in x for x in rs) and any(x.startswith("لماذا تنفيذ") for x in rs)
      and any("الفارقُ بين العرض والطلب" in x and "دولار للعقد" in x for x in rs) and any("خطّةُ الخروج" in x and "نصف كلفته" in x for x in rs)
      and not any("مضمون" in x for x in rs),
      "٥ المبرّر: الأطروحةُ والهدفُ الفنيّ ولماذا هذا التنفيذ والفارقُ بالدولار والاحتمالاتُ تقديراً وخطّةُ الخروج — لا وعدَ بربح")

E = {"type": "call", "entry_mid": 2.0, "target": 26.0}
v = {"hold": OP.verdict(E, 20.5, 2.2, 200, TR, None)[0], "stop": OP.verdict(E, 19.0, 0.95, 200, TR, None)[0],
     "profit_t": OP.verdict(E, 26.1, 3.0, 200, TR, None)[0], "profit_x2": OP.verdict(E, 21.0, 4.1, 200, TR, None)[0],
     "broken": OP.verdict(E, 16.0, 1.5, 200, {**TR, "state": "هابط", "close": 16.0}, None)[0],
     "broken_news": OP.verdict(E, 20.0, 1.9, 200, TR, {"impact": "سلبي", "strength": 2, "event": "تحقيق"})[0],
     "wobble": OP.verdict(E, 19.5, 1.7, 200, {**TR, "state": "عرضي", "close": 19.5}, None)[0], "time": OP.verdict(E, 20.0, 2.0, 55, TR, None)[0]}
check(v == {"hold": "hold", "stop": "stop", "profit_t": "profit", "profit_x2": "profit", "broken": "broken", "broken_news": "broken", "wobble": "hold", "time": "time"},
      "٦ قواعدُ الخروج: احتفظ · وقفٌ عند نصف سعر الدخول · جنيٌ عند الهدف أو تضاعف العقد · انكسارُ الأطروحة بانقلاب المسار أو خبرٍ قويٍّ معاكس · "
      "ستون يوماً قبل الانتهاء — والتذبذبُ إلى «عرضيّ» لا يُخرج (ثبوتٌ مقصود)", str(v))

# ٧ الدفتر: يومٌ بعد يومٍ بالقائمة نفسِها، والخروجُ بقاعدته، والمقعدُ الشاغرُ وحدَه يُملأ
SC = {"UP": {**TR, "strength": 9}, "UP2": {**TR, "strength": 8}, "FL": {**flat, "strength": 7}}
MARK = {}


async def fake_scan():
    return SC


async def fake_news(items):
    return {s: {"impact": "محايد", "strength": 0, "event": ""} for s in items}


async def fake_contracts(sym, call, budget, tr):
    c = OP.pick_contract(calls, S, DTE, True, budget, tr, ref_iv=ref)
    return ({**c, "contract": f"{sym}-{c['contract']}", "expiry": "2027-08-20", "t": 1, "symbol": sym, "name": sym, "price": S}, c["cost"]) if c else (None, None)


async def fake_mark(e):
    return MARK.get(e["symbol"], (S, e["entry_mid"], 270))


# ‏D840 (المالك 2026-11-25: «تكاملٌ في القرار»): التوصيةُ الجديدةُ من فرص صقر الموافَق عليها وحدها — فالمسحُ هنا فرصٌ بموافقته (وFL بتحفّظ)
from app.services import chart_scan as CS   # noqa: E402
import datetime as _dt   # noqa: E402


def _opp(sym, verdict="يوافق"):
    return {"symbol": sym, "name": sym, "side": "long", "setup": "ارتدادٌ من الدعم", "quality": 70, "horizon": "شهران", "where": "في منطقة الدعم",
            "entry": [19.5, 20.5], "target": 26.0, "stop": 18.0, "rr": 2.0, "close": S, "tr": SC.get(sym) or TR,
            "council": {"verdict": verdict, "score": 80, "oks": 6, "warns": 0, "veto": False, "members": []}}


SCAN = {"market": "us", "read": 10, "items": []}
CS.fresh = lambda market, days=4: {**SCAN, "at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}
SCAN["items"] = [_opp("UP"), _opp("UP2"), _opp("FL", "يوافق بتحفّظ")]
OP.scan, OP.read_news, OP.contracts_for, OP._mark = fake_scan, fake_news, fake_contracts, fake_mark
r1 = asyncio.run(OP.run(400))
r2 = asyncio.run(OP.run(400))
c1, c2 = [p["contract"] for p in r1["picks"]], [p["contract"] for p in r2["picks"]]
MARK["UP"] = (S, 0.5, 260)                                   # هبط العقدُ دون نصف دخوله
SC["UP3"] = {**TR, "strength": 7.5}
SCAN["items"].append(_opp("UP3"))
r3 = asyncio.run(OP.run(400))
c3 = [p["contract"] for p in r3["picks"]]
ex = {x["symbol"]: x["status"] for x in r3["exits"]}
check(c1 and c1 == c2 and len(set(c1)) == len(c1) and all(p["new"] for p in r1["picks"]) and "FL" not in {p["symbol"] for p in r1["picks"]}
      and ex.get("UP") == "stop" and "UP" not in {p["symbol"] for p in r3["picks"]} and any(x.startswith("UP2-") for x in c3) and any(x.startswith("UP3-") for x in c3)
      and OP.book_budgets() == [400] and OP.cached(400)["picks"] == r3["picks"],
      "٧ الدفتر: البحثُ الثاني يُعيد القائمةَ نفسَها (لا تتبدّل كلَّ يوم)، والتوصيةُ التي بلغت وقفَها تخرج إلى «إشارات خروج» بسببها، "
      "والمقعدُ الشاغرُ وحدَه يُملأ من فرص صقر الموافَق عليها ولا يعود السهمُ الخارجُ قبل أسبوع — وما تحفّظ عليه صقر لا يدخل", f"{c1} ⇐ {c3} · {ex}")
sk = {x["symbol"]: x["why"] for x in r1["skipped"]}
check(all((p.get("saqr") or {}).get("state") == "approve" for p in r1["picks"]) and r1["picks"] and "صقر يتحفّظ" in sk.get("FL", "")
      and r1["gate"]["approved"] == 2 and "فرص صقر الموافَق عليها" in r1["gate"]["text"],
      "٧ب ‏D840 القرارُ الواحد: كلُّ توصيةٍ جديدةٍ عليها موافقةُ صقر ونسبةُ نجاحها، وما تحفّظ عليه يُذكر سببُه في «لم يدخل»", json.dumps(sk, ensure_ascii=False)[:200])
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
check('@router.get("/options-picks")' in mk and '@router.post("/options-picks/run", dependencies=[Depends(require_owner)])' in mk
      and "10 <= b <= 10000" in mk and "job_option_book" in sch and 'id="option_book_daily"' in sch,
      "٨ المسارات: الصفقاتُ تُقرأ والمراجعةُ للمالك وحده — ومراجعةُ الدفتر يوميّاً منتصفَ الجلسة الأمريكية")
src = (ROOT / "backend/app/services/option_picks.py").read_text(encoding="utf-8")
check("MIN_DTE, MAX_DTE = 150, 430" in src and "MAX_SPREAD = 0.10" in src and "اقرأ العناوين وحدها" in src,
      "٩ العقودُ طويلةُ الأجل (150–430 يوماً) بفارقٍ ≤ 10٪، والأخبارُ تُقرأ من عناوينها وحدها")
print("\nالنتيجة:", "عطب ✖" if fail else "نظيف ✔")
sys.exit(fail)
