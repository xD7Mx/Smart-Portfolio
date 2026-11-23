#!/usr/bin/env python3
"""حارسُ D788 — التقريرُ اليوميّ وعقلُ صقر الواحد (بأمر المالك 2026-11-23).

قال المالك: «الرسمُ البيانيّ لازقٌ مرّةً في الطرف — خلِّ فراغاً من جهة اليمين أشوف الشمعةَ الأخيرة»، «الأخبارُ العالمية مكانُها ضيّقٌ جدّاً — خلِّ
لها مكاناً خاصّاً في أوّل الصفحة»، «التطبيقُ يدعم تعدّدَ المحافظ: خيارٌ بدون محفظة أو للمحافظ كاملةً أو لمحفظةٍ معيّنة»، «ما فكرةُ «شراء حذر» طولَ
المدّة؟ نظرتُنا المفروضُ يتحكّم فيها صقر»، و«صقرٌ الأمريكيّ والسعوديّ صقرٌ واحد — يعرف الأخبارَ العالمية وتأثيرَها على كلّ شركةٍ بما يخصّها».

    python3 scripts/audit/chart_d788.py
"""
import asyncio
import json
import os
import pathlib
import re
import sys
import tempfile
import datetime as dt
import random

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


from app.services import research_paper as RP   # noqa: E402
from app.services import saqr_mind as SM   # noqa: E402
from app.services import saqr_council as CN   # noqa: E402

# ١ الرسمُ اليوميّ: فراغٌ بعد آخر شمعة (إزاحةٌ يمنى كتريدنق فيو)
rnd = random.Random(3)
bars, p, d = [], 11000.0, dt.date(2025, 6, 1)
for _ in range(300):
    o = p
    c = o * (1 + rnd.gauss(0, 0.008))
    bars.append({"date": d.isoformat(), "o": o, "h": max(o, c) * 1.004, "l": min(o, c) * 0.996, "c": c, "v": 1e8})
    p, d = c, d + dt.timedelta(days=1)
svg = RP.svg_d7m(bars, w=470, h=330, title="TASI")
rights = [float(m.group(1)) + float(m.group(2)) for m in re.finditer(r'<rect x="([\d.]+)" y="[\d.]+" width="([\d.]+)" height="[\d.]+" fill="(#[0-9a-fA-F]+)"', svg)
          if m.group(3) in (RP.TV_UP, RP.TV_DN)]
gap = 470 - 54 - max(rights) if rights else 0
check(len(rights) == 120 and gap >= 15, "١ الرسمُ اليوميّ يترك فراغاً بعد آخر شمعةٍ قبل محور السعر (ستّةٌ بالمئة من الشموع، وأربعٌ على الأقلّ) — فتُرى الشمعةُ الأخيرة",
      f"{len(rights)} شمعة · الفراغ {gap:.1f}px")

# ٢ الأخبارُ العالمية رأسُ صفحتها بعرضها كلِّه في عمودين — والجداولُ تحتها
src = (ROOT / "scripts/audit/research_paper_d746.py").read_text(encoding="utf-8")
g = {"__name__": "fixture", "__file__": str(ROOT / "scripts/audit/research_paper_d746.py")}
import io, contextlib   # noqa: E402,E401
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src[:src.index('html = RP.render(rep, "all")')], "d746", "exec"), g)
rep = g["rep"]
rep["global"] = [{"text": f"خبرٌ عالميٌّ رقم {i}"} for i in range(1, 9)]
html = RP.render(rep, "all")
pg2 = html.split('<section class="page">')[2]
check('data-k="global-news"' in pg2 and pg2.index('data-k="global-news"') < pg2.index('class="cols"') and 'class="bul two"' in pg2
      and pg2.count("<li>") >= 8 and "<h1>الأخبار والأسواق العالمية</h1>" in pg2 and "<h2>الأخبار العالمية</h2>" not in html,
      "٢ الأخبارُ العالمية رأسُ صفحتها بعرضها كلِّه في عمودين («الأخبار والأسواق العالمية») والجداولُ تحتها — لا آخرَ عمودٍ ضيّق")

# ٣ «نظرتُنا» من صقر: الفنيُّ أساسٌ والشواهدُ تضيف وتنقص — فلا تبقى «شراء حذر» مهما قال العالم
T = {"close": 11500, "sma50": 11300, "sma200": 11000, "sma10": 11400, "macd_hist": 2, "rsi": 58, "chg": 0.3}
o_pos = SM.outlook_from(T, {"up": 200, "down": 40}, {"tone_sa": "إيجابي", "why_sa": "خفضُ الفائدة"}, {"tasi": {"verdict": "صاعد"}}, None, [])
o_neg = SM.outlook_from(T, {"up": 180, "down": 60}, {"tone_sa": "سلبي", "why_sa": "النفطُ يهبط"}, {"tasi": {"verdict": "صاعد"}, "brent": {"chg5": -6.2}},
                        {"level": "متوسط"}, [])
o_bad = SM.outlook_from({**T, "rsi": 45, "macd_hist": -1}, {"up": 50, "down": 200}, {"tone_sa": "سلبي"}, {"tasi": {"verdict": "هابط"}},
                        {"level": "مرتفع", "why": "حرب"}, [])
o_ob = SM.outlook_from({**T, "rsi": 74}, None, None, None, None, [])
o_ev = SM.outlook_from(T, {"up": 200, "down": 40}, {"tone_sa": "إيجابي"}, None, None, [{"impact": "High", "ar": "قرارُ الفائدة"}])
check(o_pos["view"] == "شراء" and o_neg["view"] == "شراء حذر" and o_bad["view"] == "اتجاه هابط" and o_ob["view"] == "جني الأرباح"
      and o_ev["view"] == "شراء حذر" and any("قرارُ الفائدة" in w for w in o_ev["why"]) and any("برنت" in w for w in o_neg["why"])
      and o_neg["why"][0].startswith("الإشاراتُ الفنية 5 من 5"),
      "٣ «نظرتُنا» من صقر: الإشاراتُ الفنيةُ الخمس أساس، ونبرةُ العالم ومسارُ تاسي والاتّساعُ والخطرُ والنفطُ تضيف وتنقص بأسبابها — "
      "الفنيُّ نفسُه «شراء» بعالمٍ إيجابيّ و«شراء حذر» بنفطٍ هابطٍ و«اتجاه هابط» في بيئةٍ معادية، والحدثُ عالي الأثر يحدّها",
      json.dumps([o_pos["view"], o_neg["view"], o_bad["view"], o_ob["view"], o_ev["view"]], ensure_ascii=False))

# ٤ قراءةُ العالم محروسة: لا قطاعَ من خارج القائمتين ولا رقمَ من خارج العناوين والحقائق
heads = [("برنت يتراجع 4٪ مع ارتفاع المخزونات", "x"), ("رقائق إنفيديا تقود ناسداك", "y")]
v = SM.validate({"themes": [{"name": "النفط", "dir": "سلبي", "strength": 3, "why": "برنت يتراجع 4٪ مع ارتفاع المخزونات", "sa": ["الطاقة", "قطاعٌ مخترع"],
                             "us": ["الطاقة والنفط"]},
                            {"name": "الرقائق", "dir": "إيجابي", "strength": 2, "why": "الرقائق ترتفع 12.5٪", "sa": [], "us": ["أشباه الموصلات والإلكترونيات"]},
                            {"name": "مجهول", "dir": "صاعد", "strength": 2, "why": "x", "sa": ["الطاقة"]}],
                 "tone_sa": "سلبي", "why_sa": "برنت يتراجع 4٪", "tone_us": "غريب"}, heads, {"brent": {"px": 61.2, "chg": -4.0}})
check(v and len(v["themes"]) == 1 and v["themes"][0]["sa"] == ["الطاقة"] and v["dropped"] == 1 and v["tone_us"] == "محايد" and v["tone_sa"] == "سلبي"
      and SM.hits(v, "sa", "الطاقة") and not SM.hits(v, "sa", "البنوك") and SM.hits(v, "us", "الطاقة والنفط")
      and SM.sector_of("NVDA", "us", "Electronic Technology") == "أشباه الموصلات والإلكترونيات",
      "٤ قراءةُ العالم محروسة: قطاعاتُها من قائمتَي السوقين وحدهما، ومحورٌ برقمٍ ليس في العناوين يسقط، والنبرةُ المجهولةُ «محايد» — ولكلّ شركةٍ ما يخصّ قطاعَها",
      json.dumps({k: v[k] for k in ("tone_sa", "tone_us", "dropped")} if v else None, ensure_ascii=False))

# ٥ المجلسُ يقرأ العالم: عضوُ «الأحداث» يتحفّظ بمحورٍ قويٍّ يعاكس الصفقة ويذكر الداعم
W = [{"name": "النفط", "dir": "سلبي", "strength": 3, "why": "برنت يتراجع 4٪ مع ارتفاع المخزونات", "sa": ["الطاقة"], "us": []}]
e1 = CN.m_events("sa", "long", {"verdict": "صاعد", "close": 11500}, None, [], None, W, "سلبي")
e2 = CN.m_events("sa", "short", {"verdict": "صاعد", "close": 11500}, None, [], None, W, "سلبي")
e3 = CN.m_events("us", "long", None, None, [], None, [], "إيجابي")
cs = (ROOT / "backend/app/services/saqr_council.py").read_text(encoding="utf-8")
sa = (ROOT / "backend/app/services/saqr_sa.py").read_text(encoding="utf-8")
check(e1["v"] == "warn" and "العالم يعاكسها" in e1["say"] and e2["v"] == "ok" and "العالم يدعمها" in e2["say"] and "إيجابي" in e3["say"]
      and 'ctx["world"] = await SM.world()' in cs and 'ev["world"] = SM.hits(' in cs and '"world": w}' in sa,
      "٥ صقرٌ واحدٌ للسوقين: المجلسُ في المسح وفي صيد السعوديّ يقرأ العالمَ نفسَه، وعضوُ «الأحداث» يتحفّظ بمحورٍ قويٍّ يعاكس الصفقةَ ويذكر الداعم",
      e1["say"][:80])

# ٦ مبدّلُ محفظة التقرير: بلا محفظة · كلّ المحافظ · محفظةٌ بعينها — وما لم يُكتب مجتمعاً ليومٍ مضى صفحاتُ السوق وحدها
from app.api.v1.endpoints import market as EP   # noqa: E402
from app.services import research_desk as RD   # noqa: E402
import app.core.portfolio_scope as PS   # noqa: E402
REPS = {(1, "2026-11-22"): {"date": "2026-11-22", "portfolio_id": 1, "market": {"tech": {}}, "positions": [{"symbol": "1120"}]},
        (2, "2026-11-22"): {"date": "2026-11-22", "portfolio_id": 2, "market": {"tech": {}}, "positions": [{"symbol": "2222"}]},
        ("all", "2026-11-23"): {"date": "2026-11-23", "portfolio_id": "all", "market": {"tech": {}}, "positions": [{"symbol": "1120"}, {"symbol": "2222"}]},
        (1, "2026-11-23"): {"date": "2026-11-23", "portfolio_id": 1, "market": {"tech": {}}, "positions": [{"symbol": "1120"}]}}
o_load, o_pid = RD.load_report, PS.active_pid


def fake_load(pid, day=None):
    days = sorted({k[1] for k in REPS if k[0] == pid}, reverse=True)
    day = day if day in days else (days[0] if days else None)
    return REPS.get((pid, day))
RD.load_report = fake_load
PS.active_pid = lambda: 1
k1, r1, m1 = EP._report_for("all", "2026-11-23")
k2, r2, m2 = EP._report_for("all", "2026-11-22")
k3, r3, m3 = EP._report_for("2", None)
k4, r4, m4 = EP._report_for(None, "2026-11-22")
RD.load_report, PS.active_pid = o_load, o_pid
check(k1 == "all" and r1["portfolio_id"] == "all" and not m1 and m2 and r2["portfolio_id"] == 1 and k3 == 2 and r3["portfolio_id"] == 2 and not m3
      and r4["portfolio_id"] == 1,
      "٦ مبدّلُ محفظة التقرير: «كلّ المحافظ» تقريرُها المجمَّع، وليومٍ مضى قبله صفحاتُ السوق وحدها بلا ادّعاء؛ ومحفظةٌ برقمها؛ وبلا اختيارٍ المحفظةُ النشطة")
rd = (ROOT / "backend/app/services/research_desk.py").read_text(encoding="utf-8")
ep = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
check('r = await compose_for(db, ALL, "كلّ المحافظ", market, today)' in rd and "set_scope(None, True)" in rd and 'part = "market" if (pf == "none" or market_only)' in ep
      and 'market["tech"]["view"] = o["view"]' in rd and 'market["tech"]["view_tech"]' in rd,
      "٦ب تقريرُ المحافظ مجتمعةً يُكتب كلَّ جلسةٍ بقراءةٍ موحَّدة (ولا يُرسَل)، و«بلا محفظة» صفحاتُ السوق وحدها، و«نظرتُنا» تُكتب من صقر ويبقى الفنيُّ للمقارنة")

# ٧ لماذا هذه النظرة — شواهدُ صقر تحت المقياس، والفنيُّ إن خالفها
m = rep["market"]
m["tech"]["view_tech"], m["tech"]["view"] = "جني الأرباح", "احتفاظ"
m["saqr"] = {"view": "احتفاظ", "why": ["الإشاراتُ الفنية 4 من 5", "العالم: برنت يتراجع"], "themes": ["النفط (سلبي): برنت يتراجع"]}
h2 = RP.render(rep, "all")
check('data-k="saqr-why"' in h2 and "قراءةُ صقر" in h2 and "والفنيُّ وحده «جني الأرباح»" in h2 and "العالم: برنت يتراجع" in h2,
      "٧ «نظرتنا» في التقرير بقراءة صقر وشواهدها تحت المقياس — والفنيُّ وحده يُذكر إن خالفها")

# ٨ المُصفّي: عمودُ القطاع للمحاور، وإن رُدّ فالأعمدةُ السابقة — لا يتعطّل المسح
from app.services import chart_scan as CS   # noqa: E402
CALLS = []


class FakeResp:
    def __init__(self, code, data):
        self.status_code, self.text = code, json.dumps({"data": data})


class FakeSession:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, data=None, **k):
        cols = json.loads(data)["columns"]
        CALLS.append(len(cols))
        if "sector" in cols:
            return FakeResp(400, [])
        return FakeResp(200, [{"s": "NASDAQ:NVDA", "d": ["NVDA"] + [None] * (len(cols) - 1)}])
import curl_cffi.requests as CR   # noqa: E402
o_s = CR.Session
CR.Session = FakeSession
rows = CS._tv_blocking("us")
CR.Session = o_s
check("sector" in CS.TECH and CALLS == [len(CS.TECH), len(CS.TECH) - 1] and rows and rows[0]["name"] == "NVDA" and "sector" not in rows[0],
      "٨ المُصفّي يطلب قطاعَ الشركة لمحاور العالم، وإن رُدّ العمودُ أعاد الطلبَ بالأعمدة السابقة — فلا يتعطّل المسحُ اليوميّ لأجله", str(CALLS))
print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
