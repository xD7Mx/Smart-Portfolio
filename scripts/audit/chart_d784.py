#!/usr/bin/env python3
"""حارسُ D784 — «مختصر» ستّةُ خطوط، وفرصُ صقر من مسح الرسم للسوق كلِّه (بأمر المالك 2026-11-22).

قال المالك: «مختصر يجب أن يكون ستّةَ خطوطٍ لا ثلاثة — كلُّ خطّين منطقة: خطّان للدعم وخطّان للمقاومة وخطّان في الوسط… مثلاً تاسي: 11486 · 11293 ·
10558 · 10330 · 9367 · 9175 — وتُطبَّق على الجميع»، و«خلِّ صقر يفهم تحليلَ الرسم ويختار بناءً عليه — الأمريكيُّ والسعوديّ… يحلّل الرسمَ لكامل
السوق فيُظهر الفرص، ويعرف جودتَها لمدّة كم: شهر · شهران · حتى الربع القادم… بشكلٍ يوميّ… والتنفيذُ عندي… وفي السوق السعوديّ بدلَ الإشارات الفرص».
يُفحص على الدوالّ نفسِها بلا شبكة (الشموعُ مصنوعةٌ بذورُها ثابتة)، ومطابقةُ حساب الخادم لحساب الواجهة في ‏chart_d784.mjs.

    python3 scripts/audit/chart_d784.py
"""
import asyncio
import datetime as dt
import json
import os
import pathlib
import random
import re
import sys
import tempfile

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


def synth(seed: int, n: int = 520, drift: float = 0.0, vol: float = 0.018, start: float = 50.0) -> list[dict]:
    rnd = random.Random(seed)
    out, p, d = [], start, dt.date(2024, 6, 3)
    for _ in range(n):
        while d.weekday() >= 5:
            d += dt.timedelta(days=1)
        o = p
        c = max(1.0, o * (1 + drift + rnd.gauss(0, vol)))
        h, lo = max(o, c) * (1 + abs(rnd.gauss(0, vol / 2))), min(o, c) * (1 - abs(rnd.gauss(0, vol / 2)))
        out.append({"date": d.isoformat(), "open": o, "high": h, "low": lo, "close": c, "volume": rnd.randint(100_000, 1_000_000)})
        p = c
        d += dt.timedelta(days=1)
    return out


from app.services import chart_tech as T   # noqa: E402
from app.services import chart_scan as CS   # noqa: E402

# ١ «مختصر» ستّة — كلُّ خطّين منطقة — وأرقامُ المالك على تاسي تخرج من ضلعه (القاع 9367.9 ⇐ القمّة 11293.9) بهذه الستّة نفسِها
d7 = (ROOT / "frontend/src/components/analysis/d7m.ts").read_text(encoding="utf-8")
fib = {"lines": {lv: 9367.9 + 1926.0 * lv for lv in T.FIB_LEVELS}}
six = sorted((round(fib["lines"][lv], 1) for lv in T.SIX), reverse=True)
zs = T.zones_of(fib)
check(T.SIX == (0, -0.1, 0.5, 0.618, 1, 1.1) and "export const FIB_SIX = [0, -0.1, 0.5, 0.618, 1, 1.1];" in d7 and len(T.FIB_LEVELS) == 14
      and six == [11486.5, 11293.9, 10558.2, 10330.9, 9367.9, 9175.3] and [z["name"] for z in zs] == ["الدعم", "الوسط", "المقاومة"]
      and [z["levels"] for z in zs] == [(0, -0.1), (0.5, 0.618), (1, 1.1)],
      "١ «مختصر» ستّةُ خطوط (0 · −0.1 · 0.5 · 0.618 · 1 · 1.1) في الخادم والواجهة، وكلُّ خطّين منطقة (الدعم · الوسط · المقاومة) — وأرقامُ المالك على تاسي "
      "(11486 · 11293 · 10558 · 10330 · 9367 · 9175) تخرج منها", str(six))

# ٢ قراءةُ الرسم: كلُّ فرصةٍ متّسقة — الشراءُ وقفُه تحت السعر وهدفُه فوقه والبيعُ عكسُه، والجودةُ من مئة والمدّةُ من الثلاث، ولا بيعَ في السعوديّ
# (‏D784 قيس: مرآةُ «القرب» للبيع كانت منحازةً للشراء — 35 من 539 فرصةَ بيعٍ وقفُها تحت السعر)
bad, n, kinds, sa_short = [], 0, {}, 0
for seed in range(240):
    bars = synth(seed, drift=(0.0012, 0.0004, -0.0006, -0.0012)[seed % 4])
    for cut in (520, 450, 390):
        r = T.read(bars[:cut])
        rs = T.read(bars[:cut], saudi=True, longs_only=True)
        sa_short += 1 if rs and rs.get("side") == "short" else 0
        if not r or not r.get("setup"):
            continue
        n += 1
        kinds[r["setup"]] = kinds.get(r["setup"], 0) + 1
        p = r["close"]
        ok = (r["stop"] < p < r["target"]) if r["side"] == "long" else (r["target"] < p < r["stop"])
        ok = ok and r["entry"][0] <= r["entry"][1] and 0 <= r["quality"] <= 100 and r["horizon"] == T.HORIZON[r["horizon_n"]] and r["rr"] >= 0 and r["reasons"]
        if not ok:
            bad.append((seed, cut, r["setup"], round(r["stop"], 2), round(p, 2), round(r["target"], 2)))
check(n >= 200 and not bad and sa_short == 0 and len(kinds) >= 6,
      "٢ قراءةُ الرسم: كلُّ فرصةٍ متّسقة — الشراءُ حدُّه تحت السعر وهدفُه فوقه، والبيعُ عكسُه (كان حدُّ البيع يقع تحت السعر)، والجودةُ من مئة، والمدّةُ شهرٌ أو "
      "شهران أو حتى الربع القادم، والسعوديُّ شراءٌ وحده", f"{n} فرصة · {kinds} · معيبة {len(bad)} {bad[:2]}")

# ٣ الدرجةُ الأوّلية من حقول المُصفّي: الصاعدُ بسيولةٍ داخلةٍ وتوقيتٍ منخفضٍ أعلى من الهابط، والبيعُ مرآتُه، وغيابُ الحقول ⇐ لا درجة
up = {"close": 110, "SMA50": 100, "SMA200": 90, "EMA20": 105, "ADX+DI": 30, "ADX-DI": 12, "ChaikinMoneyFlow": 0.15, "MoneyFlow": 60,
      "relative_volume_10d_calc": 1.4, "Stoch.RSI.K": 18, "Stoch.RSI.D": 25, "Stoch.RSI.K|1W": 50, "RSI|1W": 58}
dn = {**up, "close": 80, "SMA50": 90, "SMA200": 100, "EMA20": 85, "ADX+DI": 12, "ADX-DI": 30, "ChaikinMoneyFlow": -0.15, "Stoch.RSI.K": 82, "Stoch.RSI.D": 75,
      "RSI|1W": 42, "Stoch.RSI.K|1W": 60}
check(CS.pre_score(up, "long") > CS.pre_score(dn, "long") and CS.pre_score(dn, "short") > CS.pre_score(up, "short") and CS.pre_score({"close": 1}) is None,
      "٣ الدرجةُ الأوّلية للسوق كلِّه من حقول المُصفّي (المسار · السيولة · توقيتُ Stoch RSI · الأسبوعيّ): الصاعدُ للشراء والهابطُ للبيع، وغيابُ الحقول لا درجة",
      f"{CS.pre_score(up, 'long')} · {CS.pre_score(dn, 'long')} · {CS.pre_score(dn, 'short')}")

# ٤ المسحُ كلُّه على سوقٍ مصنوع: يُحفظ في مخزن الحالة، والقائمةُ مرتّبةٌ بالجودة فوق العتبة، والقراءاتُ لصقر في الخادم وحده،
#    ومسحٌ بلا مجالٍ (تعذّرُ المُصفّي) لا يمحو مسحاً سابقاً
BARS = {f"S{i:03d}": synth(1000 + i, drift=(0.0012, 0.0004, -0.0006)[i % 3]) for i in range(60)}


async def fake_rows(market):
    rows = []
    for s, b in BARS.items():
        cl = [x["close"] for x in b]
        rnd = random.Random(s)
        rows.append({"name": s, "description": s + " Inc", "close": cl[-1], "SMA50": sum(cl[-50:]) / 50, "SMA200": sum(cl[-200:]) / 200,
                     "EMA20": sum(cl[-20:]) / 20, "ADX+DI": rnd.uniform(10, 40), "ADX-DI": rnd.uniform(10, 40), "ChaikinMoneyFlow": rnd.uniform(-.2, .2),
                     "MoneyFlow": rnd.uniform(20, 80), "relative_volume_10d_calc": rnd.uniform(.5, 2), "Stoch.RSI.K": rnd.uniform(0, 100),
                     "Stoch.RSI.D": rnd.uniform(0, 100), "Stoch.RSI.K|1W": rnd.uniform(0, 100), "RSI|1W": rnd.uniform(30, 70)})
    return rows


# الشبكةُ وحدها مصنوعة: يُستبدل نداءُ ياهو الخامُ في مُهايئه، ويمرّ المسحُ بمساره الحقيقيّ كلِّه (الخدمةُ ⇐ المُهايئ ⇐ التنظيف) —
# ‏D784 قيس على الخادم: استبدالُ الخدمة كلِّها في الحارس أخفى أنّ ‏market_service لا يملك ‏daily_base، فقرأ المسحُ الحقيقيُّ 0 رسوم
import app.services.market_data as MD   # noqa: E402
FETCHED = []


async def fake_fetch(self, symbol, range_, interval):
    FETCHED.append((symbol, range_, interval))
    return [dict(b) for b in BARS.get(symbol.replace(".SR", ""), [])]
MD.YahooFinanceAdapter._fetch_chart_points = fake_fetch
o_rows, o_uni = CS.market_rows, CS.universe
CS.market_rows = fake_rows


async def fake_uni(market, rows):
    return {r["name"]: r for r in rows}
CS.universe = fake_uni


async def no_review(market, items, kept, ai=True):           # ‏D786: مجلسُ صقر يُحرس في ‏chart_d786.py — هنا المسحُ وحده
    return items, []
o_review, CS.review = CS.review, no_review
d_us = asyncio.run(CS.scan("us", ai=False))
d_sa = asyncio.run(CS.scan("sa", ai=False))
saved = json.loads(pathlib.Path(CS._path("sa")).read_text(encoding="utf-8"))
qs = [x["quality"] for x in d_us["items"]]
v = CS.view("us")
top = d_us["items"][0] if d_us["items"] else None
flat = next((s for s, r in (saved.get("reads") or {}).items() if not r.get("setup")), None)


async def empty_rows(market):
    return []
CS.market_rows = empty_rows
d_empty = asyncio.run(CS.scan("sa", ai=False))
kept = json.loads(pathlib.Path(CS._path("sa")).read_text(encoding="utf-8"))
CS.market_rows, CS.universe = o_rows, o_uni
scan_src = (ROOT / "backend/app/services/chart_scan.py").read_text(encoding="utf-8")
check(d_us["read"] == 60 and d_sa["read"] == 60 and all(r == "2y" and i == "1d" for _, r, i in FETCHED) and any(x.endswith(".SR") for x, _, _ in FETCHED)
      and "M.daily_base(" not in scan_src and "M._yahoo()._fetch_chart_points(" in scan_src,
      "٤أ المسحُ يجلب الشموعَ بمساره الحقيقيّ (الخدمةُ ⇐ مُهايئُ ياهو ⇐ التنظيف) — يوميُّ سنتين، والسعوديُّ برمزه ‏.SR، بلا خبءٍ يُحمّل مخزنَ الخادم "
      "(كان يُنادي دالّةً ليست في الخدمة فقرأ 0 رسوم على الخادم)", f"{len(FETCHED)} نداءً · us {d_us['read']} · sa {d_sa['read']}")
check(d_us["read"] == 60 and d_us["found"] == len(d_us["items"]) and qs == sorted(qs, reverse=True) and all(q >= CS.MIN_Q for q in qs)
      and all(x["side"] == "long" for x in d_sa["items"]) and all("tr" in x for x in d_us["items"] + d_sa["items"]) and all(x["liq"].get("side") for x in d_us["items"] + d_sa["items"])
      and CS._path("sa").startswith(_SB) and "reads" in saved and "reads" not in v and v["job"]["on"] is False
      and top and CS.chart_of("us", top["symbol"])[0] == "opp" and (flat is None or CS.chart_of("sa", flat)[0] == "flat")
      and CS.chart_of("sa", "ZZZZ")[0] == "unread" and CS.summary("us")["found"] == d_us["found"]
      and d_empty.get("universe") == 0 and kept["at"] == saved["at"] and kept["found"] == saved["found"],
      "٤ المسحُ اليوميّ: يقرأ رسومَ المجال كلِّه ويحفظ الفرصَ فوق عتبة الجودة مرتّبةً بها (والسعوديُّ شراءٌ وحده، ولكلٍّ مسارُه وجهةُ سيولته للمجلس ‏D786)، "
      "وقراءاتُ كلّ رسمٍ في الخادم وحده ليقول صقرٌ لماذا لم يختر، ومسحٌ تعذّر مُصفّيه لا يمحو السابق",
      f"us {d_us['found']}/{d_us['read']} · sa {d_sa['found']}/{d_sa['read']} · {qs[:4]}")

# ٥ ‏D786 (المالك: «التحليلُ الفنيّ خطوةٌ من بين الخطوات… وعملُنا القديم لا يلغيه الجديد»): الرسمُ لم يعد بوّابةً في صيد صقر السعوديّ —
#    صار عضواً في مجلسه (‏saqr_council) مع المسار والنتائج والأخبار والأحداث والحيتان والمحلّلين؛ وسلوكُ الصيد يُحرس في ‏chart_d786.py
sas = (ROOT / "backend/app/services/saqr_sa.py").read_text(encoding="utf-8")
check("CS.chart_of(" not in sas and "CN.judge(evs[sym])" in sas and "CN.chart_sa(sym)" in sas,
      "٥ الرسمُ عضوٌ في مجلس صقر لا بوّابتُه: لا يُرفض سهمٌ لأنّ الرسمَ بلا فرصةٍ وحده (‏D786 نقض بوّابةَ ‏D784 بأمر المالك)")
from app.services import research_desk as RD   # noqa: E402
CS.save("sa", {"market": "sa", "at": "2020-01-01T00:00:00+00:00", "read": 3, "items": [], "reads": {}})
old_none = CS.chart_of("sa", "2010")[0]
CS.save("sa", {"market": "sa", "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "universe": 271, "read": 0, "found": 0, "items": [], "reads": {}})
zero_none = CS.chart_of("sa", "2010")[0]


async def no_bars(self, symbol, range_, interval):
    return []
o_fetch = MD.YahooFinanceAdapter._fetch_chart_points
MD.YahooFinanceAdapter._fetch_chart_points = no_bars
CS.market_rows, CS.universe = fake_rows, fake_uni
before = json.loads(pathlib.Path(CS._path("us")).read_text(encoding="utf-8"))
d_nobars = asyncio.run(CS.scan("us", ai=False))
after = json.loads(pathlib.Path(CS._path("us")).read_text(encoding="utf-8"))
CS.market_rows, CS.universe = o_rows, o_uni
CS.review = o_review
MD.YahooFinanceAdapter._fetch_chart_points = o_fetch
sch_src = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
check(old_none == "none" and zero_none == "none" and d_nobars["read"] == 0 and after["at"] == before["at"] and after["read"] == before["read"]
      and 'if not d or not d.get("read"):' in sch_src,
      "٥ب ومسحٌ قديمٌ (فوق أربعة أيام) أو لم يقرأ رسماً لا يحكم — فقواعدُ صقر السابقة وحدها؛ ومسحٌ تعذّرت شموعُه لا يُحفظ فوق السابق، والإقلاعُ يعيده "
      "(قيس على الخادم: مسحُ الإقلاع 0 رسوم حُفظ حديثاً فرفض صقرٌ كلَّ شركة)", f"{old_none} · {zero_none} · {d_nobars['read']}")

# ٦ دفترُ «عقود الخيارات» يبدأ بفرص الرسم: جهتُها جهةُ العقد، وسطرُها في المبرّر، وتنكسر التوصيةُ بكسر حدّها
from app.services import option_picks as OP   # noqa: E402
src = (ROOT / "backend/app/services/option_picks.py").read_text(encoding="utf-8")
e = {"type": "call", "entry_mid": 2.0, "target": 130.0, "thesis": {"state": "صاعد", "close": 100, "sma200": 90, "chart_stop": 95.0, "chart_setup": "ارتدادٌ من الدعم"}}
v_br = OP.verdict(e, 94.0, 1.9, 200, None, None)
v_ok = OP.verdict(e, 99.0, 1.9, 200, None, None)
OPP = {"symbol": "NVDA", "name": "NVIDIA", "setup": "ارتدادٌ من الدعم", "side": "long", "quality": 72, "horizon": "شهران", "horizon_n": 2,
       "entry": [68.0, 69.5], "target": 78.0, "stop": 66.9, "rr": 2.1, "zone": "الدعم", "where": "في منطقة الدعم", "close": 70.0}
x = dict(OPP)
lines = OP.with_chart(["الأطروحة", "الأخبار"], x, None)
lines2 = OP.with_chart(["الأطروحة", "الأخبار"], None, ("flat", {"setup": None, "quality": None, "where": "بين الوسط والمقاومة"}))
check(v_br[0] == "broken" and "حدِّها 95.00" in v_br[1] and v_ok[0] == "hold" and lines[1].startswith("قراءةُ الرسم: ارتدادٌ من الدعم") and "لا فرصةَ الآن" in lines2[1]
      and OP.chart_card(x)["quality"] == 72 and 'CS.fresh("us")' in src and 'side = "call" if x["side"] == "long" else "put"' in src
      and "for s, x in list(opps.items())[:CHART_MAX]:" in src and "if s in held or s in opps:" in src
      and '"chart_stop": (k.get("chart") or {}).get("stop")' in src and "CHART_W * x[\"chart\"][\"quality\"]" in src,
      "٦ «عقودُ الخيارات» تبدأ بفرص مسح الرسم (الشراءُ عقدُ شراء والبيعُ عقدُ بيع، والخبرُ القويُّ المعاكسُ يُسقطها)، وجودتُها تُرجّح الترتيب، وسطرُها في المبرّر، "
      "وتنكسر التوصيةُ بكسر حدّها على الرسم", f"{v_br[0]} · {v_ok[0]}")

# ٧ «تحليلُ الرسم»: قراءةُ الحجم لم تعد تُسقط (الواجهةُ تسمّيه «volume» ومفتاحُه «vol» — قيس: كانت تُسقط دائماً)؛ والمستوى برقم اللقطة يبقى
from app.services.chart_read import validate   # noqa: E402
b0 = BARS["S001"][-120:]
f0 = {"tf": "1d", "tf_ar": "يوم", "price": round(b0[-1]["close"], 2),
      "bars": [[x["date"], round(x["open"], 2), round(x["high"], 2), round(x["low"], 2), round(x["close"], 2), x["volume"]] for x in b0],
      "levels": [{"kind": "fib", "label": "فيبوناتشي 0", "price": round(b0[-30]["low"], 2)}], "shown": ["volume", "stochrsi", "d7m"],
      "ind": {"Stoch RSI": {"k": 18.0, "d": 22.0}}}
obj = {"bias": "صاعد", "headline": f"السعرُ {f0['price']} قرب المنطقة", "indicators": [{"name": "الحجم", "reading": "حجمٌ فوق متوسّطه"},
                                                                                     {"name": "Stoch RSI", "reading": "يتقاطع صاعداً"}],
       "levels": [{"kind": "دعم", "price": f0["levels"][0]["price"], "from": "فيبوناتشي", "note": ""}]}
rv = validate(obj, {"frames": [f0]})
check([i["name"] for i in rv["indicators"]] == ["الحجم", "Stoch RSI"] and len(rv["levels"]) == 1 and rv["dropped"] == 0,
      "٧ «تحليلُ الرسم»: قراءةُ الحجم تُعرض (كانت تُسقط دائماً)، والمستوى برقم اللقطة يبقى", f"{[i['name'] for i in rv['indicators']]}")

# ٨ الجدولةُ والنقاطُ والواجهة
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
desk = (ROOT / "frontend/src/components/saqr/SaqrDesk.tsx").read_text(encoding="utf-8")
opps = (ROOT / "frontend/src/components/saqr/SaqrOpps.tsx").read_text(encoding="utf-8")
api = (ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")
check('CronTrigger(day_of_week=TRADING_DAYS, hour=15, minute=50), args=["sa"], id="chart_scan_sa"' in sch
      and 'CronTrigger(day_of_week="tue,wed,thu,fri,sat", hour=0, minute=40), args=["us"], id="chart_scan_us"' in sch and 'id="chart_scan_boot"' in sch
      and '@router.get("/saqr/opportunities")' in mk and '@router.post("/saqr/opportunities/run", dependencies=[Depends(require_owner)])' in mk
      and "saqrOpps:" in api and "saqrOppsRun:" in api and '["opps", "الفرص", Crosshair]' in desk and '"signals", "الإشارات"' not in desk
      and "<SaqrOpps market={market} />" in desk and 'data-role="so-card"' in opps and "saqrOrder" not in opps,
      "٨ المسحُ كلَّ يومٍ بعد إغلاق كلّ سوق (السعوديُّ 15:50 · الأمريكيّ 00:40 بالرياض) وبعد الإقلاع إن قدم، وتبويبُ «الفرص» بدلَ «الإشارات» للسوقين، "
      "والمسحُ الآن بصلاحية المالك وحده — ولا تنفيذَ من القائمة (المالكُ يختار)")
print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
