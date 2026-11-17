#!/usr/bin/env python3
"""حارسُ D759 — مُنتقي عقود الخيارات طويلة الأجل بميزانية العقد (بأمر المالك 2026-11-17).

«خانةٌ لقيمة العقد — 150 أو 100 أو 50 دولاراً — فيُخرج أفضلَ الخيارات في السوق الأمريكيّ على المسار (صاعد · هابط · عرضيّ) والأخبار
(استقال رئيسُ الشركة فالسهمُ هابط)، عقوداً طويلةَ المدى لا تتآكل، صفقاتٍ بمبرّراتها». يُفحص على الدوالّ نفسِها: رياضيّاتُ الاحتمال والدلتا،
والمسار، وقاعدةُ الخبر، وتصفيةُ العقد (الميزانية · الأجل · السيولة · الفارق · التذبذب)، والمبرّر، والتشغيلُ كلُّه ببياناتٍ مصنوعة، والمسارات.

    python3 scripts/audit/option_picks_d759.py
"""
import asyncio, math, os, pathlib, sys, tempfile   # noqa: E401
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


def bars(f):
    return [{"close": f(i)} for i in range(300)]


up, dn, flat = OP.trend_of(bars(lambda i: 50 + i * 0.3)), OP.trend_of(bars(lambda i: 200 - i * 0.3)), OP.trend_of(bars(lambda i: 100 + 5 * math.sin(i / 7)))
pull = OP.trend_of(bars(lambda i: 50 + i * 0.3 if i < 293 else 137.9 - (i - 292) * 1.2))     # ارتدادٌ دون متوسّط 50 في مسارٍ صاعد
check(up["state"] == "صاعد" and dn["state"] == "هابط" and flat["state"] == "عرضي" and OP.trend_of(bars(lambda i: 10)[:100]) is None
      and pull["state"] == "صاعد" and pull["close"] < pull["sma50"] and OP.trend_of(bars(lambda i: 0.1 + i * 1e-4)) is None,
      "٢ المسارُ من الشموع: صاعدٌ وهابطٌ وعرضيّ بترتيب متوسّطَي 50 و200 وميلِ 50 والإغلاقِ على جهة 200 — والارتدادُ دون 50 لا يلغي المسار، "
      "ولا حكمَ بأقلَّ من 210 جلسات ولا لرمزٍ دون دولارين (منتهٍ في المصدر)",
      f"{up['state']} · {dn['state']} · {flat['state']} · ارتداد {pull['state']} {pull['close']}<{pull['sma50']}")
check(OP.direction(up, None)[0] == "call" and OP.direction(dn, None)[0] == "put"
      and OP.direction(up, {"impact": "سلبي", "strength": 2})[0] is None
      and OP.direction(up, {"impact": "سلبي", "strength": 1})[0] == "call"
      and OP.direction(flat, {"impact": "سلبي", "strength": 3})[0] == "put"
      and OP.direction(flat, {"impact": "إيجابي", "strength": 2})[0] is None,
      "٣ الأخبار: الحدثُ القويُّ المعاكسُ للمسار يُسقط الصفقة، والطفيفُ لا يُسقطها، والجوهريُّ (استقالةُ رئيسٍ مثلاً) يعطي العرضيَّ اتجاهَه")
rows = [{"contract": "A", "strike": 110, "ask": 0.9, "bid": 0.8, "iv": 35, "oi": 500, "volume": 10},     # ضمن 100
        {"contract": "B", "strike": 105, "ask": 1.4, "bid": 1.3, "iv": 35, "oi": 800, "volume": 10},     # فوق الميزانية
        {"contract": "C", "strike": 112, "ask": 0.8, "bid": 0.2, "iv": 35, "oi": 900, "volume": 10},     # فارقٌ واسع
        {"contract": "D", "strike": 108, "ask": 0.95, "bid": 0.9, "iv": 35, "oi": 10, "volume": 1},     # بلا سيولة
        {"contract": "E", "strike": 140, "ask": 0.3, "bid": 0.25, "iv": 35, "oi": 2000, "volume": 50}]  # بعيدٌ جداً
k = OP.pick_contract(rows, 100.0, 200, True, 100)
check(k and k["contract"] == "A" and k["cost"] == 90.0 and k["breakeven"] == 110.9 and 0 < k["pop"] < 50 and k["dte"] == 200,
      "٤ العقد: ضمن الميزانية (سعرُ الطلب × 100)، سائلٌ (اهتمامٌ مفتوحٌ وفارقٌ معقول)، وأعلى احتمالِ ربحٍ عند الانتهاء — والبعيدُ جداً يُستبعد",
      str(k and {x: k[x] for x in ("contract", "cost", "breakeven", "pop", "delta")}))
kp = OP.pick_contract([{"contract": "P", "strike": 90, "ask": 0.8, "bid": 0.7, "iv": 40, "oi": 300}], 100.0, 250, False, 100)
check(kp and kp["type"] == "put" and kp["breakeven"] == 89.2 and kp["delta"] < 0 and kp["need_pct"] > 0,
      "٤ب وخيارُ البيع: التعادلُ تحت التنفيذ بسعره، والدلتا سالبة، والحركةُ المطلوبةُ هبوطٌ يُذكر موجباً", str(kp and kp["breakeven"]))
# ٤ج السوقُ مغلق (مقيسٌ 2026-11-17 قبل الافتتاح: الطلبُ والعرضُ والتذبذبُ صفرٌ في أغلب العقود)
import time as _t   # noqa: E402
iv0 = OP.implied_vol(OP.bs_price(14.0, 12.0, 0.5, 0.55, False), 14.0, 12.0, 0.5, False)
now = _t.time()
fresh = _t.strftime("%Y-%m-%dT%H:%M:%S+00:00", _t.gmtime(now - 86400))
stale = _t.strftime("%Y-%m-%dT%H:%M:%S+00:00", _t.gmtime(now - 9 * 86400))
closed = [{"contract": "Q1", "strike": 12.0, "ask": 0.0, "bid": 0.0, "last": 0.85, "iv": 0.0, "oi": 900, "last_trade": fresh},
          {"contract": "Q2", "strike": 13.0, "ask": 0.0, "bid": 0.0, "last": 0.95, "iv": 0.0, "oi": 900, "last_trade": stale}]
kc = OP.pick_contract(closed, 14.0, 180, False, 100, now)
check(iv0 and abs(iv0 - 0.55) < 1e-4 and kc and kc["contract"] == "Q1" and kc["px_src"] == "last" and kc["cost"] == 85.0 and 5 < kc["iv"] < 300
      and kc["spread_pct"] is None and OP.quote(closed[1], 14.0, 0.5, False, now) is None
      and OP.quote({"strike": 12.0, "ask": 0.0, "bid": 0.0, "last": 0.0, "oi": 900}, 14.0, 0.5, False, now) is None,
      "٤ج السوقُ مغلق: الطلبُ والعرضُ صفرٌ فيُؤخذ سعرُ آخر صفقةٍ حديثة ويُستخرج التذبذبُ منه (بلاك-شولز معكوساً) ويُوسَم «آخر صفقة» — "
      "والصفقةُ الأقدمُ من خمسة أيامٍ أو بلا سعرٍ لا يُبنى عليها",
      f"iv {iv0 and round(iv0, 4)} · {kc and {x: kc[x] for x in ('contract', 'px_src', 'cost', 'iv', 'pop')}}")
rs = OP.reasons("NVDA", up, {"impact": "سلبي", "strength": 1, "event": "تخفيضٌ طفيف"}, k, "")
check(any("المسار صاعد" in x for x in rs) and any("الأخبار" in x for x in rs) and any("يبطؤ تآكلُه" in x for x in rs)
      and any("أقصى الخسارة" in x for x in rs) and not any("مضمون" in x for x in rs),
      "٥ المبرّرُ بالعربية: المسارُ بأرقامه، والخبرُ، ولماذا العقدُ طويلُ الأجل، واحتمالُ الربح تقديراً، وأقصى الخسارة — لا وعدَ بربح")

# ٦ التشغيلُ كلُّه ببياناتٍ مصنوعة
async def fake_scan():
    return {"UP": {**up, "strength": 9}, "DN": {**dn, "strength": 8}, "FL": {**flat, "strength": 7}, "BAD": {**up, "strength": 6}}


async def fake_news(items):
    return {s: ({"impact": "سلبي", "strength": 3, "event": "استقالةُ الرئيس التنفيذيّ"} if s == "BAD" else {"impact": "محايد", "strength": 0, "event": ""}) for s in items}


async def fake_contracts(sym, call, budget):
    if sym == "DN":
        return None, 240.0
    return ({**OP.pick_contract(rows, 100.0, 200, call, budget), "expiry": "2027-06-18", "symbol": sym, "name": sym, "price": 100.0}, 90.0) if call else (None, None)


OP.scan, OP.read_news, OP.contracts_for = fake_scan, fake_news, fake_contracts
res = asyncio.run(OP.run(100))
sk = {x["symbol"]: x["why"] for x in res["skipped"]}
check([p["symbol"] for p in res["picks"]] == ["UP"] and "BAD" in sk and "تعاكس" in sk["BAD"] and "FL" in sk and "عرضيّ" in sk["FL"]
      and "DN" in sk and "240" in sk["DN"] and res["skipped"][0]["symbol"] == "DN" and res["closed"] is False
      and OP.cached(100) and OP.cached(100)["picks"][0]["contract"] == "A" and not OP._JOB["on"],
      "٦ التشغيل: الصاعدُ صفقةُ شراء، والهابطُ بلا عقدٍ ضمن الميزانية تُذكر كلفةُ أرخصِ عقدٍ صالحٍ له (أوّلَ المستبعَد)، والعرضيُّ يُستبعد، والصاعدُ بخبرٍ جوهريٍّ سلبيّ يُسقَط — وتُخبَّأ النتيجة",
      f"{[p['symbol'] for p in res['picks']]} · {sk}")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
check('@router.get("/options-picks")' in mk and '@router.post("/options-picks/run", dependencies=[Depends(require_owner)])' in mk
      and "10 <= b <= 10000" in mk,
      "٧ المسارات: الصفقاتُ تُقرأ، والبحثُ للمالك وحده، والميزانيةُ بين 10 و10,000 دولار")
src = (ROOT / "backend/app/services/option_picks.py").read_text(encoding="utf-8")
check("MIN_DTE, MAX_DTE = 120, 430" in src and "READ_NEWS" in src and "اقرأ العناوين وحدها" in src,
      "٨ العقودُ طويلةُ الأجل (120–430 يوماً)، والأخبارُ تُقرأ من عناوينها وحدها — لا يُضاف من خارجها")
print("\nالنتيجة:", "عطب ✖" if fail else "نظيف ✔")
sys.exit(fail)
