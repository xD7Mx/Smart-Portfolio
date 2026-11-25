#!/usr/bin/env python3
"""حارسُ D786 — مجلسُ صقر: يقرأ كلَّ شيءٍ ويربط بينه، والرسمُ عضوٌ فيه لا بوّابتُه (بأمر المالك 2026-11-22).

قال المالك: «عملُنا القديم لا يلغيه الجديد… التحليلُ الفنيّ خطوةٌ من بين الخطوات: المسارُ والمستويات، والشركةُ رابحةٌ أو خاسرة، وهل هذا
ثاني ربعِ خسارةٍ متواصلة (تأكيدٌ للبيع) أو ثاني ربعِ ربحٍ متتالٍ (فرصةٌ للشراء)، والأخبار (رئيسُ الشركة أُقيل فهبطت رغم نتائجها)، والأحداث،
وسلوكُ المستثمرين وانطباعُهم، والصفقاتُ غيرُ الاعتيادية، والحيتانُ أين يتمركزون… ويربط بينها».
يُفحص على الدوالّ نفسِها بلا شبكة: مصادرُ المجلس الشبكيةُ تُصطنع عند حدّها وحده (ياهو · العناوين · النموذج · الأحداث).

    python3 scripts/audit/chart_d786.py
"""
import asyncio
import datetime as dt
import json
import os
import pathlib
import random
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


from app.services import saqr_council as CN   # noqa: E402
from app.services import research_desk as RD   # noqa: E402

TRU = {"state": "صاعد", "close": 90, "sma50": 85, "sma200": 80, "ret3m": 14.0, "strength": 6, "hi52": 105}
BASE = {"market": "sa", "side": "long", "tr": TRU, "rs3": 10, "cr_side": None, "cr_any": None, "stt": "neutral", "stxt": "صافي الربح +5٪.",
        "yf": None, "news": {"impact": "محايد", "strength": 0, "event": ""}, "reg": {"verdict": "صاعد", "close": 11500}, "geo": {"level": "منخفض"},
        "events": [], "liq": None, "deals": None, "ops": None, "price": 90, "ccy": "ريال"}
CH_BUY = {"setup": "ارتدادٌ من الدعم", "side": "long", "quality": 72, "where": "في منطقة الدعم", "horizon": "شهران"}
CH_SELL = {"setup": "رفضٌ من المقاومة", "side": "short", "quality": 66, "where": "في منطقة المقاومة", "horizon": "شهر"}


def J(**kw):
    return CN.judge({**BASE, **kw})


def mem(bd, role):
    return next(m for m in bd["members"] if m["role"] == role)


# ١ المسار — قاعدةُ صقر القديمة نفسُها، مربوطةً بالرسم؛ والرسمُ عضوٌ لا بوّابة
b_down, b_u50, b_u50c, b_rs, b_rsc = J(tr={**TRU, "state": "هابط"}), J(tr={**TRU, "close": 80}), J(tr={**TRU, "close": 80}, cr_side=CH_BUY, cr_any=CH_BUY), \
    J(rs3=-2), J(rs3=-2, cr_side=CH_BUY, cr_any=CH_BUY)
b_flat, b_sell = J(), J(cr_any=CH_SELL)
check(b_down["veto"] and mem(b_down, "المسار")["v"] == "veto" and b_u50["veto"] and b_rs["veto"]
      and not b_u50c["veto"] and mem(b_u50c, "المسار")["v"] == "warn" and not b_rsc["veto"]
      and not b_flat["veto"] and mem(b_flat, "الرسم")["v"] == "warn" and b_sell["veto"] and mem(b_sell, "الرسم")["v"] == "veto",
      "١ المسارُ قاعدةُ صقر القديمة (لا شراءَ في مسارٍ غيرِ صاعد، ولا دون متوسّط 50 ولا أضعفَ من تاسي) — إلّا ارتداداً يؤكّده الرسمُ فتحفّظ؛ "
      "والرسمُ بلا فرصةٍ تحفّظٌ لا رفض (خطوةٌ من بين الخطوات)، ورسمٌ يقول البيعَ يرفض الشراء",
      f"{mem(b_u50c, 'المسار')['say'][:60]}")

# ٢ النتائج — ثاني ربعِ خسارةٍ متواصلة تأكيدُ ضعف (رفضٌ للشراء وتأييدٌ للبيع)، وأرباعُ ربحٍ متتاليةٍ متصاعدةٌ وتجاوزُ التوقّعات تأييد
YL = {"q": [{"label": "1Q", "ni": 5e6}, {"label": "2Q", "ni": -3e6}, {"label": "3Q", "ni": -4e6}], "eps": []}
YP = {"q": [{"label": "1Q", "ni": 5e9}, {"label": "2Q", "ni": 6e9}, {"label": "3Q", "ni": 8e9}],
      "eps": [{"act": 1, "est": .9}, {"act": 1.1, "est": 1}, {"act": 1.2, "est": 1}, {"act": 1.3, "est": 1.25}]}
b_l, b_p = J(yf=YL), J(yf=YP, stt="strong", stxt="صافي الربح +28٪ عن الربع المماثل.")
m_put = CN.m_results("us", "short", None, None, YL, "$")
b_weak = J(stt="weak", stxt="خسارةٌ في آخر ربع.")
check(b_l["veto"] and "للربع الثاني على التوالي" in mem(b_l, "النتائج")["say"] and m_put["v"] == "ok"
      and mem(b_p, "النتائج")["v"] == "ok" and "3 أرباعٍ متتالية" in mem(b_p, "النتائج")["say"] and "4 من 4" in mem(b_p, "النتائج")["say"]
      and b_weak["veto"] and mem(J(yf=None, stt="unknown", stxt=None), "النتائج")["v"] == "na",
      "٢ النتائج: خسارةٌ للربع الثاني على التوالي ترفض الشراءَ وتؤيّد البيع، والربحُ المتصاعدُ في أرباعٍ متتالية وتجاوزُ التوقّعات يؤيّدان؛ "
      "وقاعدةُ صقر القديمة (مخيّبةٌ أو لم تصدر) ترفض؛ وغيابُ المصدر «غيرُ متوفّر» لا يُحسب", mem(b_p, "النتائج")["say"][:90])

# ٣ الأخبار — الخبرُ الجوهريُّ المعاكسُ يُسقط الصفقةَ ولو كانت النتائجُ قوية (إقالةُ الرئيس)
b_n = J(yf=YP, stt="strong", stxt="صافي الربح +28٪.", news={"impact": "سلبي", "strength": 3, "event": "إقالةُ الرئيس التنفيذيّ"})
check(b_n["veto"] and mem(b_n, "الأخبار")["v"] == "veto" and mem(b_n, "النتائج")["v"] == "ok" and "إقالةُ الرئيس" in b_n["veto_why"][0]
      and mem(J(news={"impact": "إيجابي", "strength": 2, "event": "عقدٌ كبير"}), "الأخبار")["v"] == "ok" and mem(J(news=None), "الأخبار")["v"] == "warn",
      "٣ الأخبار: خبرٌ جوهريٌّ معاكس (إقالةُ الرئيس) يُسقط الصفقةَ ولو أيّدتها النتائج — والمجلسُ يقول ذلك صراحةً؛ والداعمُ يؤيّد، وتعذّرُ القراءة تحفّظ",
      b_n["veto_why"][0][:80])

# ٤ الحيتان — المالُ لا العدد: تصريفٌ يرفض، وسيولةٌ داخلةٌ وصفقاتٌ خاصةٌ بعلاوةٍ تؤيّد؛ وتدفّقُ الخيارات بالمال (اليانصيبُ بسنتٍ ليس حوتاً) وجدرانُه
b_w = J(liq={"side": "down", "strength": 50, "word": "خارجةٌ للهبوط", "level": "متوسّطة", "tag": "تصريف بيعي"})
dl = CN.deals_of([{"price": 92, "quantity": 1000, "value": 92000, "at": "19-11-2026"}, {"price": 80, "quantity": 10, "value": 800, "at": "01-01-2026"}], 90,
                 today=dt.date(2026, 11, 22))
m_in = CN.m_whales("long", {"side": "up", "strength": 60, "word": "داخلةٌ للصعود", "level": "قويّة", "tag": "تجميع خفي"}, dl, None, "ريال")
CHN = {"calls": [{"contract": "X140", "strike": 140, "volume": 57656, "oi": 611, "last": 0.64}, {"contract": "X160", "strike": 160, "volume": 100, "oi": 49059, "last": 0.1}],
       "puts": [{"contract": "P120", "strike": 120, "volume": 66221, "oi": 2233, "last": 0.01}, {"contract": "P85", "strike": 85, "volume": 10, "oi": 16594, "last": 0.5}]}
fl = CN.flow_of([CHN], 125.53)
m_fl = CN.m_whales("long", None, None, fl, "$")
check(b_w["veto"] and dl["n"] == 1 and round(dl["prem"], 1) == 2.2 and m_in["v"] == "ok"
      and [u["contract"] for u in fl["unusual"]] == ["X140"] and fl["wall_c"][0] == 160 and fl["wall_p"][0] == 85 and m_fl["v"] == "ok"
      and CN.m_whales("short", None, None, fl, "$")["v"] == "warn",
      "٤ الحيتان: تصريفٌ بيعيٌّ يرفض الشراء، وسيولةٌ داخلةٌ وصفقاتٌ خاصةٌ بعلاوةٍ (30 يوماً) تؤيّد؛ وتدفّقُ الخيارات بالمال — رهانُ 3.7 مليون على شراء 140 "
      "حوتٌ، وبيعُ 120 بسنتٍ يانصيبٌ لا حوت — وجدرانُ الاهتمام المفتوح (160 فوق · 85 تحت)", m_fl["say"][:100])

# ٥ المحلّلون — آخرُ رأيٍ لكلّ بيتٍ في خمسة أشهر، مصنّفاً، ووسيطُ المستهدف
ops = CN.ops_of([{"date": "2026-11-03", "house": "أ", "rating": "زيادة مراكز", "target": 110}, {"date": "2026-10-03", "house": "أ", "rating": "بيع", "target": 70},
                 {"date": "2026-11-01", "house": "ب", "rating": "شراء", "target": 105}, {"date": "2026-10-01", "house": "ج", "rating": "محايد", "target": 95},
                 {"date": "2025-01-01", "house": "د", "rating": "بيع", "target": 50}], today=dt.date(2026, 11, 22))
m_a = CN.m_analysts("long", ops, None, 90)
m_y = CN.m_analysts("long", None, {"votes": {"strongBuy": 11, "buy": 34, "hold": 16, "sell": 2}, "target": 244.18}, 125.53)
check(ops == {"n": 3, "buy": 2, "hold": 1, "sell": 0, "target": 105} and m_a["v"] == "ok" and "+17٪" in m_a["say"] and m_y["v"] == "ok"
      and CN.classify("تخفيض مراكز") == "sell" and CN.classify("تجميع") == "buy" and CN.classify("محايد") == "hold",
      "٥ المحلّلون: آخرُ رأيٍ لكلّ بيتٍ في خمسة أشهر (زيادةُ مراكز ⇐ شراء · محايد ⇐ حياد · تخفيض ⇐ بيع) ووسيطُ المستهدف وعلاوتُه — ومن ياهو للأمريكيّ",
      m_a["say"])

# ٦ الأحداث — ‏D809 (المالك 2026-11-24: «السوقُ هابطٌ فاستبعد ستّاً — الفرصُ دائماً موجودة»): تاسي الهابطُ والخطرُ المرتفعُ تحفّظٌ يُنقص الدرجة
#   لا رفضٌ لكلّ سهمٍ صاعد؛ والحدثُ العالي القريبُ وإعلانُ الأرباح تحفّظ
j_down, j_geo = J(reg={"verdict": "هابط", "close": 10000}), J(geo={"level": "مرتفع", "why": "حربٌ إقليمية"})
check(not j_down["veto"] and mem(j_down, "الأحداث")["v"] == "warn" and "الشراءُ في الصاعد وحده" in mem(j_down, "الأحداث")["say"]
      and not j_geo["veto"] and mem(j_geo, "الأحداث")["v"] == "warn"
      and mem(J(events=[{"impact": "High", "ar": "الناتجُ المحلّيّ"}]), "الأحداث")["v"] == "warn"
      and "بعد 5 أيام" in CN.m_events("us", "long", None, None, [], 5)["say"],
      "٦ الأحداث: تاسي الهابطُ والخطرُ الجيوسياسيُّ المرتفعُ تحفّظٌ يُنقص الدرجة (لا رفضٌ للسهم الصاعد — ‏D809)، والحدثُ عاليُ الأثر وإعلانُ الأرباح القريبان تحفّظ")

# ٧ الحكمُ والأسطر
b_ok = J(yf=YP, stt="strong", stxt="صافي الربح +28٪.", cr_side=CH_BUY, cr_any=CH_BUY, ops=ops,
         liq={"side": "up", "strength": 60, "word": "داخلةٌ للصعود", "level": "قويّة", "tag": None})
ls = CN.lines(b_ok)
check(b_ok["verdict"] == "يوافق" and b_ok["score"] >= 80 and len(b_ok["members"]) == 8 and [m["role"] for m in b_ok["members"]] == list(CN.ROLES)
      and len(ls) == 8 and ls[0].startswith("المسار (يوافق)") and b_down["verdict"] == "يرفض",
      "٧ الحكم: ثمانيةُ أعضاءٍ بالترتيب (والحجمُ ثالثُهم — ‏D818)، ورفضُ عضوٍ يُسقط، والتحفّظاتُ تُنقص الدرجة — وأسطرُ المجلس في أسباب الشراء", f"{b_ok['verdict']} {b_ok['score']}")

# ٨ «الرابط» محروس: لا رقمَ إلّا من الشواهد، ولا شراءَ رفضه عضو، وتعذّرُ النموذج None (لا قراءةَ بديلة)
CALLS = []


async def fake_gemini(parts, max_tokens=0, temperature=0, **k):   # ‏D806: ومهلةُ النداء
    t = parts[-1]["text"]
    CALLS.append(t)
    if "شواهدَك الثمانيةَ" in t:   # ‏D807: صقرٌ واحدٌ يقرأ شواهده
        return {"decision": "شراء", "confidence": "متوسطة", "link": "المسارُ والنتائجُ يجتمعان عند منطقة الدعم.", "conflict": "",
                "watch": "إغلاقٌ دون 77.77 يُبطلها"}
    return {"S2": {"impact": "سلبي", "strength": 3, "event": "إقالةُ الرئيس التنفيذيّ"}}
o_g = RD._gemini
RD._gemini = fake_gemini
lk_ok = asyncio.run(CN.link("1120", "مصرف الراجحي", "sa", "long", b_ok, chart=CH_BUY, price=90))
lk_veto = asyncio.run(CN.link("2010", "سابك", "sa", "long", b_down, chart=CH_BUY, price=90))


async def none_gemini(*a, **k):
    return None
RD._gemini = none_gemini
lk_none = asyncio.run(CN.link("4030", "البحري", "sa", "long", b_flat, price=91))
RD._gemini = fake_gemini
check(lk_ok and lk_ok["decision"] == "شراء" and lk_ok["watch"] == "" and lk_ok["dropped"] == 1 and lk_veto["decision"] == "تجنّب" and lk_none is None,
      "٨ «الرابط» يقرأ المجلسَ كلَّه محروساً: جملةٌ برقمٍ ليس في الشواهد تُسقط (77.77)، ولا «شراء» لما رفضه عضو، وتعذّرُ النموذج لا قراءةَ بديلة",
      json.dumps({k: lk_ok.get(k) for k in ("decision", "watch", "dropped")}, ensure_ascii=False) if lk_ok else "None")

# ٩ المسحُ يعرض كلَّ فرصةٍ على المجلس: ما رفضه عضوٌ يُستبعد بسببه، والباقي بترتيب المجلس، و«الرابط» للمقبول وحده
from app.services import chart_scan as CS   # noqa: E402
import app.services.market_data as MD   # noqa: E402


def synth(seed, n=520, drift=0.0, vol=0.018, start=50.0):
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
BARS = {f"S{i}": synth(2000 + i, drift=(0.0012, 0.0004, -0.0006)[i % 3]) for i in range(60)}


async def fake_fetch(self, symbol, range_, interval):
    return [dict(b) for b in BARS.get(symbol.replace(".SR", ""), [])]


async def fake_rows(market):
    rows = []
    for s, b in BARS.items():
        cl = [x["close"] for x in b]
        rnd = random.Random(s)
        rows.append({"name": s, "description": s, "close": cl[-1], "SMA50": sum(cl[-50:]) / 50, "SMA200": sum(cl[-200:]) / 200, "EMA20": sum(cl[-20:]) / 20,
                     "ADX+DI": rnd.uniform(10, 40), "ADX-DI": rnd.uniform(10, 40), "ChaikinMoneyFlow": rnd.uniform(-.2, .2), "MoneyFlow": rnd.uniform(20, 80),
                     "relative_volume_10d_calc": rnd.uniform(.5, 2), "Stoch.RSI.K": rnd.uniform(0, 100), "Stoch.RSI.D": rnd.uniform(0, 100),
                     "Stoch.RSI.K|1W": rnd.uniform(0, 100), "RSI|1W": rnd.uniform(30, 70)})
    return rows


async def fake_uni(market, rows):
    return {r["name"]: r for r in rows}


async def fake_yf(ysym):
    return {"q": [{"label": "1Q", "ni": 5e6}, {"label": "2Q", "ni": 6e6}], "eps": [], "votes": {"buy": 3, "hold": 1}, "target": None}


async def fake_heads(sym, name=None):
    return [{"at": "2026-11-20", "title": f"خبرٌ عن {sym}", "src": "مصدر"}]


async def no_flow(sym):
    return None


async def no_events(market, hours=48):
    return []


async def fake_ctx(market):
    return {"events": [], "reg": {"verdict": "صاعد", "close": 11500, "ret3m": 0.0}, "geo": {"level": "منخفض"}}
MD.YahooFinanceAdapter._fetch_chart_points = fake_fetch
CS.market_rows, CS.universe = fake_rows, fake_uni
CN.yf, CN.heads_sa, CN.heads_us, CN.flow, CN.events, CN.context = fake_yf, fake_heads, fake_heads, no_flow, no_events, fake_ctx
import app.services.saqr_sa as SA   # noqa: E402
o_res = SA.results_of
SA.results_of = lambda s, t: ("neutral", "صافي الربح +4٪.", 4.0)
CALLS.clear()
d_us = asyncio.run(CS.scan("us"))
links = [x for x in d_us["items"] if x.get("link")]
rank = {"يوافق": 0, "يوافق بتحفّظ": 1}
keys = [(rank[x["council"]["verdict"]], -x["council"]["score"]) for x in d_us["items"]]
saved = json.loads(pathlib.Path(CS._path("us")).read_text(encoding="utf-8"))
check(d_us["items"] and all(x.get("council") and len(x["council"]["members"]) == 8 and not x["council"]["veto"] for x in d_us["items"])
      and all(r["why"] for r in d_us.get("rejected") or []) and keys == sorted(keys) and links and all(x in d_us["items"][:CS.AI_TOP] for x in links)
      and saved.get("rejected") == d_us.get("rejected") and d_us["found"] == len(d_us["items"]),
      "٩ المسحُ يعرض كلَّ فرصةٍ على مجلس صقر: المقبولُ بأعضائه الثمانية مرتّباً بحكم المجلس ثمّ درجته، وما رفضه عضوٌ في «استبعدها المجلس» بسببه، "
      "و«الرابط» لأفضل المقبول وحده", f"{len(d_us['items'])} مقبولة · {len(d_us.get('rejected') or [])} مستبعَدة · {len(links)} رابطاً")

# ١٠ صقرٌ السعوديّ يصطاد بالمجلس: خبرٌ جوهريٌّ معاكسٌ وثاني ربعِ خسارةٍ يرفضان، و«الرابط» يقول الكلمةَ الأخيرة.
#    ‏D832 (المالك: «مستوى النجاح والاختيار موحّد في السوقين — لا أريد إلا الأخضر»): المنبعُ فرصُ اليوم بموافقة صقر الكاملة، والشراءُ الآليُّ
#    بـ«يوافق» كاملةً لحظتَه — فالرسمُ هنا فرصةُ شراءٍ كما في فرص اليوم (والتحفّظُ وبابُه في saqr_auto_d832)
from app.services import saqr_trader as SQ   # noqa: E402
REG = {"verdict": "صاعد", "state": "صاعد", "close": 11500, "sma50": 11300, "sma200": 11000, "ret3m": 4.0, "chg": 0.4, "slope50": 1}
FLAT = {"setup": None, "side": None, "quality": None, "where": "بين الوسط والمقاومة", "liq": {"side": "flat", "strength": 20, "word": "متوازنة", "level": "ضعيفة"}}


async def hunt(link_decision="شراء", yfs=None):
    async def fake_trend(sym):
        return dict(TRU)

    async def chart_flat(sym):
        return CH_BUY, CH_BUY, dict(TRU)

    async def yf_by(ysym):
        return (yfs or {}).get(ysym.replace(".SR", ""))

    async def gem(parts, max_tokens=0, temperature=0, **k):
        t = parts[-1]["text"]
        if "شواهدَك الثمانيةَ" in t:   # ‏D807: صقرٌ واحدٌ يقرأ شواهده
            return {"decision": link_decision, "confidence": "متوسطة", "link": "قراءةٌ تربط الأعضاء.", "conflict": "", "watch": ""}
        return {"2010": {"impact": "سلبي", "strength": 3, "event": "إقالةُ الرئيس التنفيذيّ"}}
    async def vol(sym):
        return 0.25
    o = (SA.trend, SA.results_of, CN.chart_sa, CN.yf, CN.heads_sa, CN.events, RD._gemini, CN.opportunities, SA.vol_of)
    SA.trend, CN.chart_sa, CN.yf, CN.heads_sa, CN.events, RD._gemini = fake_trend, chart_flat, yf_by, fake_heads, no_events, gem
    CN.opportunities, SA.vol_of = (lambda m: {s: {"symbol": s, "side": "long", **CH_BUY} for s in ("1120", "2010", "7010")}), vol
    SA.results_of = lambda s, t: ("strong", "صافي الربح +28٪ عن الربع المماثل.", 28.0)
    try:
        snap = {s: {"price": 90.0, "bid": 89.98, "ask": 90.02, "turnover": 3e7, "change_pct": 1.2, "name_en": s} for s in ("1120", "2010", "7010")}
        st = SQ.fresh(market="sa")
        pos = await SA._hunt(st, dt.datetime.now(dt.timezone.utc), snap, REG, {"level": "منخفض", "why": "هدوء"})
        return pos, {x["sym"]: x for x in st["signals"]}
    finally:
        SA.trend, SA.results_of, CN.chart_sa, CN.yf, CN.heads_sa, CN.events, RD._gemini, CN.opportunities, SA.vol_of = o
from app.services import cache   # noqa: E402
for k in list(cache._store):
    if k.startswith("council:"):
        cache._store.pop(k, None)
pos, sg = asyncio.run(hunt(yfs={"7010": YL}))
for k in list(cache._store):
    if k.startswith("council:link"):
        cache._store.pop(k, None)
pos_w, sg_w = asyncio.run(hunt(link_decision="انتظار", yfs={"7010": YL}))
check(pos and pos["symbol"] == "1120" and any(w.startswith("المسار (يوافق)") for w in pos["why"]) and any("الرسم (يوافق)" in w for w in pos["why"])
      and any(w.startswith("قراءةُ صقر الأخيرة (شراء") for w in pos["why"])
      and sg["2010"]["verdict"] == "refused" and "إقالةُ الرئيس" in sg["2010"]["why"] and sg["7010"]["verdict"] == "refused" and "الثاني على التوالي" in sg["7010"]["why"]
      and pos_w is None and "قراءةُ صقر الأخيرة: انتظار" in sg_w["1120"]["why"] and len(sg["1120"]["council"]["members"]) == 8,
      "١٠ صقرٌ السعوديّ يصطاد بالمجلس من فرص اليوم: فرصةٌ بموافقته الكاملة يشتريها (وفي أسبابه سطرُ كلّ شاهدٍ وقراءتُه الأخيرة)، ويرفض خبرَ إقالة الرئيس "
      "وثاني ربعِ خسارةٍ بسببهما — وقراءتُه الأخيرة إن قالت انتظر لا يشتري ويذكر لماذا", json.dumps({k: (v["verdict"], v["why"][:50]) for k, v in sg.items()}, ensure_ascii=False))
SA.results_of = o_res

# ١١ دفترُ «عقود الخيارات»: فرصُ الرسم بعد المجلس، وما رفضه المجلسُ لا يدخل الدفترَ من قائمته الثابتة، وحكمُ المجلس في بطاقته
from app.services import option_picks as OP   # noqa: E402
src = (ROOT / "backend/app/services/option_picks.py").read_text(encoding="utf-8")
card = OP.chart_card({**CH_BUY, "entry": [1, 2], "target": 3, "stop": 0.5, "rr": 2, "council": CN.compact(b_ok), "link": lk_ok})
# ‏D807 (المالك 2026-11-24): «صقرٌ واحد — لا مجلسَ ولا أعضاء»
check('approved = CN.opportunities("us")' in src and 'CN.stance(s)["text"]' in src and "مجلسُ صقر" not in src.split('"""')[-1]
      and card["council"]["verdict"] == "يوافق" and card["link"]["decision"] == "شراء" and "وحكمُ صقر يوافق" in OP.with_chart(["أ", "ب"], {**CH_BUY, "entry": [1, 2],
                                                                                                   "target": 3, "stop": 0.5, "council": CN.compact(b_ok)}, None)[1],
      "١١ «عقودُ الخيارات» من فرص الرسم التي وافق عليها صقرٌ وحدها (‏D840 — لا قائمةَ ثابتةَ بمسارها)، وحكمُ صقر و«الرابط» في البطاقة والمبرّر")

# ١٢ قراءةُ الأخبار دفعةً واحدة: رمزٌ بلا عناوين لا حدثَ له بلا نداء، ودفعةٌ تعذّرت «غيرُ متوفّرة»، والمقروءُ مخبّأ
for k in list(cache._store):
    if k.startswith("council:news"):
        cache._store.pop(k, None)
CALLS.clear()
RD._gemini = fake_gemini
rn = asyncio.run(CN.read_news("sa", {"S1": [], "S2": [{"at": "2026-11-21", "title": "إقالةُ الرئيس", "src": "إفصاح"}]}, {"S2": "شركة"}))
n1 = len(CALLS)
rn2 = asyncio.run(CN.read_news("sa", {"S2": [{"at": "2026-11-21", "title": "إقالةُ الرئيس", "src": "إفصاح"}]}))
RD._gemini = none_gemini
rn3 = asyncio.run(CN.read_news("sa", {"S9": [{"at": "2026-11-21", "title": "خبر", "src": "x"}]}))
RD._gemini = o_g
check(rn["S1"]["strength"] == 0 and rn["S2"]["strength"] == 3 and n1 == 1 and len(CALLS) == 1 and rn2["S2"]["impact"] == "سلبي" and rn3["S9"] is None,
      "١٢ الأخبارُ تُقرأ دفعةً واحدة: بلا عناوين لا حدثَ بلا نداء، والمقروءُ مخبّأٌ ساعتين، ودفعةٌ تعذّرت «غيرُ متوفّرة» لا محايدة")

# ١٣ المصادرُ مقيسةٌ على الخادم بكاشفها، والواجهةُ تعرض المجلس
door = (ROOT / "scripts/audit/saqr_council_door.py").read_text(encoding="utf-8")
opps = (ROOT / "frontend/src/components/saqr/SaqrOpps.tsx").read_text(encoding="utf-8")
sas = (ROOT / "backend/app/services/saqr_sa.py").read_text(encoding="utf-8")
check(all(x in door for x in ("earnings,earningsHistory,financialData,recommendationTrend", "special_deals", "analyst_opinions", "_collect(", "chain(sym"))
      and 'data-role="so-council"' in opps and 'data-role="so-rejected"' in opps and 'data-role="so-link"' in opps
      and "CN.link(" in sas and "CS.chart_of(" not in sas,
      "١٣ مصادرُ المجلس قِيست على الخادم بكاشفها (نتائجُ ياهو الربعية · الصفقاتُ الخاصة · آراءُ البيوت · الأخبار · تدفّقُ الخيارات)، والواجهةُ تعرض المجلسَ و«الرابط» والمستبعَد")
# ١٤ الإقلاعُ يعيد مسحاً سبق المجلسَ (فرصُه بلا حكم) — فلا ينتظر المالكُ إغلاقَ الغد ليرى المجلس، ولا يُعاد مسحٌ فيه المجلس
from app.scheduler import scheduler as SCH   # noqa: E402
now_iso = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
CS.save("sa", {"market": "sa", "at": now_iso, "read": 260, "items": [{"symbol": "2222", "quality": 70}], "found": 1})
CS.save("us", {"market": "us", "at": now_iso, "read": 150, "items": [{"symbol": "NVDA", "quality": 70, "council": CN.compact(b_ok)}], "found": 1})
RUNS = []


async def rec_scan(m):
    RUNS.append(m)
o_job = SCH.job_chart_scan
SCH.job_chart_scan = rec_scan
asyncio.run(SCH.job_chart_scan_boot())
SCH.job_chart_scan = o_job
check(RUNS == ["sa"], "١٤ الإقلاعُ يعيد مسحاً سبق مجلسَ صقر (فرصُه بلا حكم) مرّةً — ولا يعيد مسحاً حكم فيه المجلس", str(RUNS))
print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
