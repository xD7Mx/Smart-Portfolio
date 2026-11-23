#!/usr/bin/env python3
"""حارسُ D746 — ورقةُ التقرير اليوميّ على هيئة بيوت الأبحاث (بأمر المالك 2026-11-15).

«أبغى شيئاً طبقَ الأصل من الجزيرة كابيتال… تقسيماتٌ للمؤشّر وللقطاعات وللإحصاءات وللمعدّل… عمقُ السوق ونظرتُنا… مؤرّخة… ولا تذكر
المصادر». فيُفحص على الدوالّ نفسِها: المحورُ ودعومُه ومقاوماتُه، والقراءةُ الفنية ونظرتُنا، والاختياراتُ الانتقائية ومستوياتُها،
ومعدّلُ القيم وسجلُّ الجلسات، والقطاعاتُ بأوزانها، ونظرتُنا للمراكز من مستشار التطبيق، ثمّ الورقةُ نفسُها: صفحاتُها وتاريخُها
وأقسامُها، ولا مصدرَ ولا رقمَ هنديّ فيها.

    python3 scripts/audit/research_paper_d746.py
"""
import os, pathlib, re, sys, tempfile   # noqa: E401
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from datetime import date, timedelta   # noqa: E402
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import research_paper as RP   # noqa: E402

pv = RP.pivots(110, 100, 105)
check({k: round(v, 6) for k, v in pv.items()} == {"s3": 90, "s2": 95, "s1": 100, "p": 105, "r1": 110, "r2": 115, "r3": 120},
      "١ المحورُ الكلاسيكيّ: (أعلى+أدنى+إغلاق)÷3 ثمّ ثلاثُ مقاوماتٍ وثلاثةُ دعوم", str(pv))

bars, d, px = [], date(2025, 12, 1), 100.0
while d <= date(2026, 11, 15):
    if d.weekday() not in (4, 5):
        bars.append({"date": d.isoformat(), "open": px, "high": px + 1, "low": px - 0.5, "close": px + 0.5, "volume": 1})
        px += 0.5
    d += timedelta(days=1)
t = RP.technicals(bars)
dec_close = [b["close"] for b in bars if b["date"] < "2026-01-01"][-1]
oct_close = [b["close"] for b in bars if b["date"] < "2026-11-01"][-1]
check(t["date"] == "2026-11-15" and abs(t["sma10"] - sum(b["close"] for b in bars[-10:]) / 10) < 1e-9 and t["rsi"] == 100
      and abs(t["ytd"] - (t["close"] / dec_close - 1) * 100) < 1e-9 and abs(t["mtd"] - (t["close"] / oct_close - 1) * 100) < 1e-9
      and t["candle"] == "green" and t["view"] == "جني الأرباح",
      "٢ القراءةُ الفنية بمعادلاتها: المتوسّطُ والقوةُ النسبية والعائدُ منذ بداية الشهر والعام — وصعودٌ متّصلٌ بقوةٍ 100 «جني الأرباح»",
      f"rsi {t['rsi']} · {t['view']}")
check(RP.view_of({"close": 100, "sma50": 90, "sma200": 80, "sma10": 95, "macd_hist": 1, "rsi": 60, "chg": 1}) == "شراء"
      and RP.view_of({"close": 100, "sma50": 110, "sma200": 120, "sma10": 105, "macd_hist": -1, "rsi": 40, "chg": -1}) == "اتجاه هابط"
      and RP.view_of({"close": 100, "sma50": 90, "sma200": 120, "sma10": 95, "macd_hist": 1, "rsi": 45, "chg": -1}) == "احتفاظ",
      "٣ نظرتُنا من خمس إشاراتٍ معلنة — شراء · احتفاظ · اتجاه هابط … وعند التشبّع جني الأرباح")

row = lambda sym, **k: {"symbol": sym, "name": sym, "decision": "شراء", "fair_value_upside_pct": 18, "above_sma50": True, "above_sma200": True,   # noqa: E731
                        "macd_bullish": True, "rsi": 55, "sharia": "compliant", **k}
pc = RP.pick_candidates([row("1111.SR"), row("2222", rsi=72), row("3333", decision="احتفاظ"), row("4444", fair_value_upside_pct=6),
                         row("5555", above_sma200=False), row("6666", sharia="non_compliant"), row("7777", decision="شراء قوي", fair_value_upside_pct=30),
                         row("8888", fair_value_upside_pct=12)], held={"8888"})
check([p["symbol"] for p in pc] == ["8888", "7777", "1111"],
      "٤ أفضلُ اختياراتنا انتقائية: قرارُ شراء + صعودٌ ≥10٪ + فوق متوسّطَي 50 و200 + ماكد إيجابيّ + قوةٌ 45–68 + لا مخالفةَ شرعية — والمراكزُ أوّلاً",
      str([p["symbol"] for p in pc]))
lv = RP.pick_levels(bars)
check(lv and lv["buy"][0] <= lv["buy"][1] == round(lv["close"], 2) and lv["target"][0] > lv["close"] and lv["target"][1] >= lv["target"][0]
      and lv["stop"] < lv["buy"][0], "٥ مستوياتُ الاختيار: نطاقُ الشراء حتى الإغلاق، والمستهدفُ فوقه، ووقفُ الخسارة دون نطاق الشراء",
      f"{lv['buy']} → {lv['target']} · وقف {lv['stop']}" if lv else "")

st = {}
for i in range(12):
    st = RP.history_append(st, (date(2026, 11, 15) - timedelta(days=i)).isoformat(), {"value": 4e9, "volume": 2e8, "trades": 4e5, "src": "report"})
st = RP.history_append(st, "2026-11-15", {"value": 3e9, "src": "app"})
st = RP.history_append(st, "2026-11-15", {"value": 9e9, "src": "report"})
av = RP.averages(st, "2026-11-15")
check(st["2026-11-15"]["value"] == 3e9 and abs(av["value"]["a5"] - 3.8) < 1e-9 and abs(av["value"]["a10"] - 3.9) < 1e-9 and av["value"]["a20"] is None
      and av["week"]["days"] == 1 and av["prev_week"]["days"] == 7 and av["prev_value"] == 4e9,
      "٦ سجلُّ الجلسات: رقمُ التطبيق يتقدّم على المقروء، ومعدّلُ 5 و10 أيام، وما لا يكفيه السجلُّ (20) لا يُحسب، والأسبوعان بأيامهما",
      f"{av['value']} · {av['week']}")

rows = {"1": {"price": 110, "prev_close": 100, "change_pct": 10, "turnover": 5e6}, "2": {"price": 90, "prev_close": 100, "change_pct": -10, "turnover": 1e6},
        "3": {"price": 50, "prev_close": 50, "change_pct": 0, "turnover": 2e6}}
fund = {"1": {"shares": 3e6, "verified": True, "ni": 2e7, "eq": 1e8}, "2": {"shares": 1e6, "verified": True, "ni": 1e6, "eq": 5e7},
        "3": {"shares": 2e6, "verified": True, "ni": 1e6, "eq": 5e7}}
tb = RP.market_tables(rows, {"1": "أ", "2": "ب", "3": "ج"}, {"1": "البنوك", "2": "البنوك", "3": "الطاقة"}, fund, {"1": 4.0})
bank = next(s for s in tb["sectors"] if s["name"] == "البنوك")
check(abs(bank["pct"] - ((3e6 * 110 + 1e6 * 90) / (3e6 * 100 + 1e6 * 100) - 1) * 100) < 1e-9 and bank["up"] == 1 and bank["down"] == 1
      and tb["gainers"][0]["name"] == "أ" and tb["losers"][0]["name"] == "ب" and tb["heavy"][0]["name"] == "أ"
      and tb["fin"] and abs(tb["fin"]["pe"] - (3e6 * 110 + 1e6 * 90 + 2e6 * 50) / 2.2e7) < 1e-6,
      "٧ القطاعُ بأوزان قيمته السوقية (الأسهمُ من الإفصاح × السعر)، والأكثرُ ارتفاعاً وانخفاضاً ووزناً، ومكرّرُ السوق = القيمةُ ÷ الأرباح",
      f"{bank['pct']:.3f}% · مكرّر {tb['fin']['pe']:.2f}" if tb["fin"] else "")
tb2 = RP.market_tables(rows, {}, {}, {"1": fund["1"]}, {})
check(tb2["fin"] is None, "٨ وإن قلّت تغطيةُ الإفصاح عن 75٪ من الشركات لا تُكتب مؤشّراتُ السوق المالية")
vs = RP.verified_shares
check(vs(250e9, 266226640, 1.06) == (250e6, True) and vs(5.625e9, 79098000, 0.14) == (562.5e6, True)
      and vs(3838261223, 8527980356, 1.91) == (3838261223, True) and abs(vs(4.5e6, 6.4e9, 2.5)[0] - 2.56e9) < 1 and vs(4.5e6, 6.4e9, 2.5)[1]
      and vs(31500000e9, 1e8, 0.1) == (None, False) and vs(2e9, None, None) == (2e9, False),
      "٨ب الأسهمُ متحقَّقٌ منها بصافي الربح ÷ ربحية السهم: وحدةُ الألف والعشرة تُصحَّح (‏الطبية التخصصية · ينبع)، والبعيدُ بلا قوّة عشرةٍ يُستبدل بالضمنية أو يُستبعد")
rows3 = {"9": {"price": 10, "prev_close": 10, "change_pct": 0, "turnover": 1}}
tb3 = RP.market_tables(rows3, {}, {"9": "التأمين"}, {"9": {"shares": 1e15, "verified": False, "ni": None, "eq": 1e9}}, {})
check(not tb3["heavy"], "٨ج وغيرُ المتحقَّق منه بمضاعف دفتريةٍ غيرِ معقول لا يدخل الأكبرَ وزناً ولا مكرّرَ السوق")
check(RP.position_view({"action": "أضف على دفعتين"}) == "شراء" and RP.position_view({"action": "خفّف", "pnl": 12}) == "جني الأرباح"
      and RP.position_view({"action": "خفّف", "pnl": -3}) == "تخفيف" and RP.position_view({"action": "احتفظ"}) == "احتفاظ",
      "٩ نظرتُنا للمركز هي موقفُ مستشار التطبيق بمفردات بيوت الأبحاث — والتخفيفُ في الربح «جني الأرباح»")
check(RP.day_label("2026-11-15") == "الأحد 15 نوفمبر 2026" and RP.day_label("2026-11-12") == "الخميس 12 نوفمبر 2026",
      "١٠ التاريخُ بيومه وشهره العربيين وأرقامه اللاتينية")

m = {"date": "2026-11-15", "tasi": {"close": t["close"], "high": t["high"], "low": t["low"], "pct": t["chg_pct"], "chg": t["chg"]},
     "mt30": {}, "tech": t, "breadth": {"up": 55, "down": 205, "unch": 13, "value": 2.7e9, "volume": 1.7e8, "trades": 320858},
     **tb, "intraday": [{"t": f"{10 + i // 12:02d}:{(i % 12) * 5:02d}", "c": 100 + i, "v": 1e6} for i in range(61)],
     "daily": [{"d": b["date"], "o": b["open"], "h": b["high"], "l": b["low"], "c": b["close"]} for b in bars[-130:]],
     "global": [{"name": "داو جونز (أمريكا)", "close": 52347.55, "d1": 0.1, "mtd": 1.1, "ytd": 8.9}], "commodities": [], "fx": [], "rates": [],
     "actions": [{"date": "2026-11-16", "company": "جرير", "type": "أحقية أرباح نقدية"}]}
rep = {"date": "2026-11-15", "portfolio_name": "محفظتي", "headline": "عنوانُ اليوم", "market": m, "averages": av, "analysis": RP.market_analysis(m, av),
       "tech_text": list(RP.tech_commentary(m)), "regional": {}, "saibor": [], "positions": [{"symbol": "1120", "name": "مصرف الراجحي", "price": 64.2, "pct": 1.2,
       "weight": 12, "fv": 75, "upside": 16, "trend": "صاعد", "view": "شراء"}], "portfolio": [], "picks": [{**pc[0], **lv}], "local": [{"text": "خبرٌ محليّ"}],
       "global": [], "watch": []}
html = RP.render(rep, "all")
pages = html.count('<section class="page">')
titles = re.findall(r"<h1>(.*?)</h1>", html)
check(pages == 4 and titles == ["التقرير اليومي", "الأخبار والأسواق العالمية", "النظرة الفنية اليومية", "محفظتنا واختياراتنا"]   # ‏D788: الأخبارُ العالمية رأسُ الصفحة الثانية
      and html.count("الأحد 15 نوفمبر 2026") >= 8,
      "١١ الورقةُ أربعُ صفحاتٍ بعناوين بيوت الأبحاث، وكلُّ صفحةٍ مؤرّخةٌ بيوم الجلسة", str(titles))
need = ("مؤشر السوق السعودي", "أداء القطاعات", "معدّل القيم", "الأخبار المحلية", "تحليل السوق", "الأكثر ارتفاعاً", "الأكثر انخفاضاً",
        "الشركات الأكبر وزناً بالمؤشر", "الأسواق العالمية", "إجراءات الشركات السعودية", "التعليق على مؤشر السوق الرئيسي", "التوقعات الفنية",
        "المقاومة والدعم للمؤشر", "ملاحظات فنية", "بيانات السوق", "الإحصاءات الرئيسية", "نظرتنا", "عمق السوق", "نظرتنا لمراكز المحفظة",
        "أفضل اختياراتنا لليوم", "نطاق الشراء", "وقف الخسارة")
miss = [x for x in need if x not in html]
check(not miss, "١٢ وأقسامُها كأقسام التقرير المرجعيّ: المؤشّرُ والقطاعاتُ والمعدّلُ والإحصاءاتُ والأخبارُ والنظرةُ الفنية وعمقُ السوق ونظرتُنا والاختيارات", str(miss))
body = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
check(not re.search(r"[٠-٩]", body) and not any(x in body for x in ("الجزيرة كابيتال", "الراجحي المالية", "جدوى", "المصدر", "المصادر", "None", "nan")),
      "١٣ ولا مصدرَ مذكوراً ولا رقمَ هنديّاً ولا «None» في الورقة")
mk, pf = RP.render(rep, "market"), RP.render(rep, "portfolio")
check(mk.count('<section class="page">') == 3 and pf.count('<section class="page">') == 1 and "أفضل اختياراتنا" in pf and "أفضل اختياراتنا" not in mk,
      "١٤ والصفحتان في التطبيق: «التقرير اليومي» صفحاتُ السوق، و«التوصيات» صفحةُ المحفظة")
check("@page{size:A4;margin:0}" in html and "max-width:820px" in html and 'dir="rtl"' in html and 'direction="ltr"' in html,
      "١٥ وثيقةٌ واحدةٌ للطباعة (A4) وللهاتف (عمودٌ واحد)، عربيةُ الاتجاه، ورسومُها لا تنقلب")
rd = (ROOT / "backend/app/services/research_desk.py").read_text(encoding="utf-8")
check("send_file(data, f\"daily-report-{r['date']}.pdf\", caption(r))" in rd and "RP.gather(today)" in rd and "if not market:" in rd,
      "١٦ تُرسَل الورقةُ ملفَّ PDF مؤرَّخاً إلى تلغرام — ولا تقريرَ في يومٍ بلا جلسة")
from app.services import saqr_report as SR   # noqa: E402
check(all(getattr(RP, k) == getattr(SR, k) for k in ("NAVY", "NAVY_2", "GOLD", "GOLD_L", "GREEN", "RED", "PAPER", "INK", "LINE", "ZEBRA", "MUTED"))
      and f"linear-gradient(135deg,{SR.NAVY},{SR.NAVY_2})" in html and f"background:{SR.PAPER}" in html and "Thmanyah Serif Display" in html
      and not any(c in html for c in ("#323f48", "#b27e58", "#9a6a45")),
      "١٧ ‏D752 الورقةُ بهويّة تقارير التطبيق نفسِها: ألوانُها من مصدرها الواحد (‏saqr_report) وخطُّها، ولا بقيّةَ من ألوان الهيئة المستعارة")
svg = RP.svg_candles([{"d": f"2026-0{1 + i // 28}-{1 + i % 28:02d}", "o": 10 + i * .1, "h": 10.5 + i * .1, "l": 9.8 + i * .1, "c": 10.2 + i * .1, "v": 100 + i}
                      for i in range(60)], levels={"s1": 12, "r1": 15.5}, label="تاسي · يومي")
check(RP.TV_UP in svg and RP.TV_DN not in svg.split("<polyline")[0][:200] and "SMA 10" in svg and "RSI 14" in svg and " O " in svg and "تاسي · يومي" in svg
      and svg.count('rx="2"') >= 3, "١٨ ‏D752 والرسمُ اليوميّ بهيئة تريدنق فيو كرسم التقرير المرجعيّ: شموعُه وألوانُه، وسطرُ O H L C، والمتوسّطان، وبطاقاتُ المحور، ولوحةُ RSI")
print(("FAIL" if fail else "PASS") + " D746 — ورقةُ التقرير اليوميّ على هيئة بيوت الأبحاث: مؤرّخةٌ، بأرقامٍ محسوبة، ونظرتِنا واختياراتِنا، وبلا مصادر")
sys.exit(fail)
