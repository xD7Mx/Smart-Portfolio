#!/usr/bin/env python3
"""حارسُ D764 — صقر للسوقين وشعارُه (بأمر المالك 2026-11-18).

«اعتمد هذا العملَ الآليّ… وجهُه للأمام، فيه هيبةٌ ونظراتٌ حادّة ودقّة… ونطوّر صقر للسوق السعوديّ والأمريكيّ: الأمريكيّ عقودٌ وأسهم وكلُّ
شيء، والسعوديّ شركاتٌ فقط — ولكلٍّ استراتيجيتُه. السعوديّ يتأثّر بالنتائج الربعية والأحداث الجيوسياسية وبهبوط تاسي».
يُفحص على الدوالّ نفسِها بلا شبكة: دفترٌ لكلّ سوقٍ بعملته وهدفِه، والعمولاتُ (العقد · السهم الأمريكيّ المتدرّجة · السعوديّ 0.155٪)، وقواعدُ
السهم (الوقفُ والمتحرّكُ والركودُ والهدف)، والسهمُ بدل العقد، والنتائجُ الربعية (محفّزٌ · مخيّبٌ · لم تصدر بعد)، وبوّاباتُ تاسي والأحداث،
ونصفُ الحجم، وفرزُ الشركات، ومراجعةُ المراكز وصيدُها على لقطةٍ مصنوعة، والجدولةُ والنقاطُ، والشعارُ.

    python3 scripts/audit/saqr_d764.py
"""
import asyncio, os, pathlib, re, sys, tempfile   # noqa: E401
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

# ١ دفترٌ لكلّ سوق
us, sa = SQ.fresh(), SQ.fresh(market="sa")
SQ.save(us)
SQ.save(sa)
check(us["ccy"] == "USD" and us["capital"] == 100 and us["goal"] == 10_000 and sa["ccy"] == "SAR" and sa["capital"] == 1000 and sa["goal"] == 100_000
      and SQ._path("sa").endswith("saqr/ledger_sa.json") and SQ._path("us").endswith("saqr/ledger.json") and SQ.load("sa")["market"] == "sa",
      "١ دفترٌ لكلّ سوقٍ بعملته: الأمريكيّ من 100 دولار إلى 10,000، والسعوديّ من 1,000 ريال إلى 100,000 — ملفّان مستقلّان")

# ٢ العمولات
f_opt, f_s1, f_s2, f_s3, f_sa = (SQ.fee_of("us", "option", 2, 1.0), SQ.fee_of("us", "stock", 10, 50), SQ.fee_of("us", "stock", 1000, 50),
                                 SQ.fee_of("us", "stock", 0.5, 20), SQ.fee_of("sa", "stock", 100, 30))
check(f_opt == 1.3 and f_s1 == 0.35 and f_s2 == 3.5 and f_s3 == 0.1 and f_sa == round(3000 * 0.00155, 2),
      "٢ العمولات: العقدُ 0.65 لكلّ عقد، والسهمُ الأمريكيّ 0.0035 للسهم لا تقلّ عن 0.35 ولا تزيد على 1٪، والسعوديّ 0.155٪ من القيمة",
      f"{f_opt} · {f_s1} · {f_s2} · {f_s3} · {f_sa}")

# ٣ السهمُ في الدفتر: الكلفةُ والقيمةُ والبيع
st = SQ.fresh(market="sa")
p = SQ.buy(st, {"contract": "2222", "symbol": "2222", "type": "stock", "ask": 25.10, "bid": 25.08, "price": 25.09, "stop": 25.10 * SA.STOP}, 9, ["x"], kind="stock")
v0 = SQ.mark_of(p)
c = SQ.sell(st, p["id"], 27.0, "target")
check(p["cost"] == round(25.10 * 9 + 25.10 * 9 * 0.00155, 2) and v0 == round(25.08 * 9, 2) and c["proceeds"] == round(27 * 9 - 27 * 9 * 0.00155, 2)
      and c["pl"] == round(c["proceeds"] - p["cost"], 2) and SQ.kind_of(p) == "stock" and SQ.mult(p) == 1,
      "٣ السهمُ: الكلفةُ بالعرض مع العمولة، والقيمةُ بالطلب سهماً لسهم (لا ×100)، والربحُ بعد العمولتين", f"{p['cost']} · {v0} · {c['pl']}")

# ٤ قواعدُ خروج السهم
S0 = {"kind": "stock", "type": "stock", "entry_px": 100.0, "stop": 94.0, "stop0": 94.0, "peak": 100.0, "target": 115.0,
      "opened": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()}
r_stop = SQ.exit_rule(dict(S0), 93.9, 94, 999, None, None)
q = dict(S0)
SQ.trail(q, 108.5)
be = q["stop"]
SQ.trail(q, 113.0)
hi = q["stop"]
r_tr = SQ.exit_rule(q, 106.0, 106, 999, None, None)
r_tgt = SQ.exit_rule(dict(S0), 115.5, 115.6, 999, None, None)
old = {**S0, "opened": (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()}
r_stale = SQ.exit_rule(dict(old), 101.0, 101, 999, None, None)
r_ok = SQ.exit_rule(dict(old), 104.0, 104, 999, None, None)
check(r_stop[0] == "stop" and "94٪" in r_stop[1] and be == 100.0 and abs(hi - 113 * 0.94) < 1e-6 and r_tr[0] == "trail" and r_tgt[0] == "target"
      and r_stale[0] == "stale" and r_ok is None,
      "٤ السهم: الوقفُ من سعره المحفوظ (−6٪ للسعوديّ)، ومن +8٪ إلى الدخول ومن +12٪ إلى 94٪ من القمّة، والهدف، وستّةُ أسابيع بلا 3٪ تُحرّر المال",
      f"{r_stop[1][:40]} · {be} ⇐ {hi} · {r_stale[0]}")

UP = {"state": "صاعد", "close": 104, "sma200": 90, "sma50": 100}
DN = {"state": "هابط", "close": 96, "sma200": 99, "sma50": 98}
r_up = SQ.exit_rule(dict(S0), 104.0, 104, 999, UP, None)
r_dn = SQ.exit_rule(dict(S0), 99.0, 99, 999, DN, None)
check(r_up is None and r_dn and r_dn[0] == "broken",
      "٤ب السهمُ مركزُ شراء: مسارُه الصاعد يُبقيه، وانقلابُه هابطاً يكسر الأطروحة (كان يُقرأ «stock» بيعاً فيُباع مع كلّ مسارٍ صاعد — قيس في الحارس)",
      f"{r_up} · {r_dn and r_dn[0]}")

# ٥ السهمُ الأمريكيّ بدل العقد
TR = {"state": "صاعد", "close": 50, "sma200": 40, "ret3m": 12.0, "hi52": 60.0}
k = SQ.stock_pick("SOFI", {"regularMarketPrice": 50.0, "bid": 49.98, "ask": 50.02, "shortName": "SoFi"}, TR, 50.0)
k2 = SQ.stock_pick("SOFI", {"regularMarketPrice": 59.0}, {**TR, "hi52": 60.0}, 50.0)
k3 = SQ.stock_pick("SOFI", {"regularMarketPrice": 50.0}, TR, 4.0)
check(k and 0 < k["qty"] < 1 and k["qty"] * k["ask"] + SQ.fee_of("us", "stock", k["qty"], k["ask"]) <= 50 and k["stop"] == round(50.02 * SQ.STOCK_STOP, 4)
      and k["target"] == 60.0 and k2 and k2["target_label"] == "+15٪" and k3 is None,
      "٥ السهمُ بدل العقد: جزءٌ من السهم يتّسع للميزانية مع العمولة، ووقفٌ −7٪، والهدفُ قمّةُ السنة إن بعدت 5٪ وإلا +15٪ — ولا صفقةَ دون 5 دولارات",
      f"{k and k['qty']} · {k2 and k2['target']}")
src = (ROOT / "backend/app/services/saqr_trader.py").read_text(encoding="utf-8")
# ‏D771 (المالك 2026-11-20): «دائماً يختار أسهماً لا عقودَ خيارات… لا نختار إلا طويلَ المدى»: البديلُ بالسهم أُلغي من الصيد الآليّ — صقرٌ
# يشتري من قائمته (عقودٌ طويلةٌ وحدها)، والسهمُ يُدخله المالك بنفسه إن شاء (مركزٌ نفّذتُه)
hunt = src[src.index("async def _hunt("):src.index("# ══ أوامرُ المالك (‏D771)")]
check("stock_pick(" not in hunt and 'kind="stock"' not in hunt and "book_for(budget)" in hunt and 'kind="stock"' in src,   # ‏D779: من «عقود الخيارات»
      "٥ب الصيدُ الآليُّ الأمريكيّ عقودٌ طويلةٌ من «عقود الخيارات» وحدها (‏D779) — لا بديلَ بالسهم (‏D771)، والسهمُ يُدخله المالك بنفسه")

# ٥ج قرارُ الفيدراليّ يومٌ كامل، ومحضرُه ساعتان (قيس على الخادم: المحضرُ كان يحجب يومَ التداول كلَّه)
NOW = datetime(2026, 11, 18, 15, 0, tzinfo=timezone.utc)
ev = lambda t, h: [{"impact": "High", "title": t, "at": (NOW + timedelta(hours=h)).isoformat()}]   # noqa: E731
blk = {"قرار بعد 20 ساعة": SQ.event_block(ev("FOMC Statement", 20), NOW), "فائدة بعد 20 ساعة": SQ.event_block(ev("Federal Funds Rate", 20), NOW),
       "محضر بعد 7 ساعات": SQ.event_block(ev("FOMC Meeting Minutes", 7), NOW), "محضر بعد ساعة": SQ.event_block(ev("FOMC Meeting Minutes", 1), NOW),
       "خطاب بعد 5 ساعات": SQ.event_block(ev("Fed Chair Powell Speaks", 5), NOW)}
check(blk["قرار بعد 20 ساعة"] and blk["فائدة بعد 20 ساعة"] and not blk["محضر بعد 7 ساعات"] and blk["محضر بعد ساعة"] and not blk["خطاب بعد 5 ساعات"],
      "٥ج قرارُ الفيدراليّ وبيانُه يحجبان يوماً كاملاً، ومحضرُه وخطاباتُه ساعتين كسائر الأحداث — لا يُحجب يومُ تداولٍ كاملٌ لمحضر",
      " · ".join(f"{k}:{'يحجب' if v else 'لا'}" for k, v in blk.items()))

# ٥د القائمةُ القصيرة: ذوو الاتجاه وحدهم، ومقاعدُ إضافيةٌ لمن تتّسع الميزانيةُ لعقوده (قيس: كانت تذهب للعرضيّ وللكبير الذي لا يُشترى عقدُه)
TRS = {f"BIG{i}": {"state": "هابط", "close": 300.0 + i, "strength": 50 - i} for i in range(30)}
TRS.update({"SIDE": {"state": "عرضي", "close": 10.0, "strength": 99}, "F": {"state": "صاعد", "close": 11.5, "strength": 3},
            "NIO": {"state": "هابط", "close": 4.4, "strength": 2}, "HELD": {"state": "صاعد", "close": 9, "strength": 98}, "COOL": {"state": "صاعد", "close": 8, "strength": 97}})
sl = SQ.shortlist(TRS, {"HELD"}, lambda x: x == "COOL", 50.0)
check("SIDE" not in sl and "HELD" not in sl and "COOL" not in sl and len([x for x in sl if x.startswith("BIG")]) == SQ.SHORTLIST and "F" in sl and "NIO" in sl
      and SQ.affordable(11.5, 50) and not SQ.affordable(300, 50),
      "٥د القائمةُ القصيرة لذوي الاتجاه وحدهم (لا العرضيّ ولا المملوك ولا المحجور)، ومعها الأسهمُ التي تتّسع الميزانيةُ لعقودها وإن ضعفت قوّتُها "
      "— ويُفحص الميسورُ أوّلاً", f"{len(sl)} · {sl[-2:]}")

# ٦ النتائجُ الربعية
T = date(2026, 11, 18)
cases = {
    "strong": SA.results_state({"date": "27/10/2026", "current": 130, "change_pct": 30.0}, None, T),
    "weak_loss": SA.results_state({"date": "2026-10-27", "current": -5, "change_pct": 10.0}, None, T),
    "weak_drop": SA.results_state({"date": "2026/10/27", "current": 50, "change_pct": -40.0}, None, T),
    "neutral": SA.results_state({"date": "2026-10-27", "current": 50, "change_pct": 5.0}, None, T),
    "pending": SA.results_state({"date": "2026-07-27", "current": 50, "change_pct": 30.0}, {"as_of": "2026-06-30", "announced": "2026-07-27"}, date(2026, 10, 12)),
    "late_ok": SA.results_state({"date": "2026-07-27", "current": 50, "change_pct": 30.0}, {"as_of": "2026-06-30"}, T),
    "unknown": SA.results_state(None, None, T),
    "q4_window": SA.results_state({"date": "2026-10-27", "change_pct": 30.0, "current": 9}, {"as_of": "2026-09-30"}, date(2027, 2, 20)),
}
check(cases["strong"][0] == "strong" and cases["weak_loss"][0] == "weak" and cases["weak_drop"][0] == "weak" and cases["neutral"][0] == "neutral"
      and cases["pending"][0] == "pending" and cases["late_ok"][0] == "neutral" and cases["unknown"][0] == "unknown" and cases["q4_window"][0] == "pending"
      and SA.quarter_end(T) == date(2026, 9, 30) and SA.quarter_end(date(2027, 2, 20)) == date(2026, 12, 31),
      "٦ النتائجُ الربعية: نموُّ صافي الربح ≥ 15٪ بإعلانٍ حديث محفّز، والخسارةُ والتراجعُ 15٪ مخيّبان، وربعٌ لم تصدر نتائجُه في مهلته (30 يوماً، "
      "والسنويُّ 90) «لم تصدر بعد» — وبعد المهلة لا يُحجر", " · ".join(f"{a}:{b[0]}" for a, b in cases.items()))

# ٧ البوّابات ونصفُ الحجم
RY = __import__("zoneinfo").ZoneInfo("Asia/Riyadh")
d0 = date(2026, 11, 18)
clock = (datetime(2026, 11, 18, 10, 0, tzinfo=RY), datetime(2026, 11, 18, 15, 0, tzinfo=RY))
mid = datetime(2026, 11, 18, 12, 0, tzinfo=RY)
REG = {"verdict": "صاعد", "state": "صاعد", "close": 11500, "sma50": 11300, "sma200": 11000, "ret3m": 4.0, "chg": 0.4, "slope50": 1}
st = SQ.fresh(market="sa")
g_ok = SA.gates(st, mid, clock, REG, {"level": "منخفض"})
g_down = SA.gates(st, mid, clock, {**REG, "verdict": "هابط"}, {"level": "منخفض"})
g_panic = SA.gates(st, mid, clock, {**REG, "chg": -1.8}, {"level": "منخفض"})
g_geo = SA.gates(st, mid, clock, REG, {"level": "مرتفع", "why": "تصعيدٌ إقليميّ"})
g_none = SA.gates(st, mid, clock, None, {"level": "منخفض"})
g_open = SA.gates(st, clock[0] + timedelta(minutes=5), clock, REG, None)
g_close = SA.gates(st, clock[1] - timedelta(minutes=10), clock, REG, None)
f1, f2, f3, f4 = SA.size_factor(REG, {"level": "منخفض"}), SA.size_factor({**REG, "verdict": "عرضي"}, {"level": "منخفض"}), SA.size_factor(REG, None), SA.size_factor(REG, {"level": "متوسط"})
check(not g_ok and any("تاسي هابط" in x for x in g_down) and any("هلع" in x for x in g_panic) and any("جيوسياسيّ" in x for x in g_geo)
      and any("تاسي غيرُ متوفّر" in x for x in g_none) and g_open and g_close and f1[0] == 1.0 and f2[0] == 0.5 and f3[0] == 0.5 and f4[0] == 0.5,
      "٧ بوّاباتُ السعوديّ: تاسي هابطٌ أو يومُ هلعٍ (−1.5٪) أو خطرٌ جيوسياسيّ مرتفع أو تاسي غيرُ مقروء ⇐ لا دخول، ولا في أطراف الجلسة؛ "
      "وتاسي العرضيّ والخطرُ المتوسّط وتعذّرُ قراءة الأحداث ⇐ نصفُ الحجم", f"{g_down[:1]} · {f2[1]}")

# ٨ فرزُ الشركات
base = {"price": 30.0, "bid": 29.98, "ask": 30.02, "turnover": 2e7, "change_pct": 1.0}
scr = {"ok": SA.screen(base, 0.2), "cheap": SA.screen({**base, "price": 4.0}, 0), "thin": SA.screen({**base, "turnover": 1e6}, 0),
       "wide": SA.screen({**base, "bid": 29.5, "ask": 30.5}, 0), "chase": SA.screen({**base, "change_pct": 7.5}, 0),
       "fall": SA.screen({**base, "change_pct": -3.0}, 0), "nobook": SA.screen({**base, "bid": None}, 0)}
check(scr["ok"] is None and all(scr[k] for k in ("cheap", "thin", "wide", "chase", "fall", "nobook")) and SA.shares(1000, 30.02) == 33,
      "٨ الشركة: سعرٌ ≥ 5 ريالات، وسيولةُ اليوم ≥ 5 ملايين، وعرضٌ وطلبٌ بفارقٍ ≤ 0.6٪، ولا مطاردةَ فوق +6٪ ولا دخولَ دون −2٪ — وأسهمٌ صحيحة",
      " · ".join(f"{k}:{'✓' if v is None else v[:18]}" for k, v in scr.items()))


# ٩ المراجعةُ والصيد على لقطةٍ مصنوعة
async def flow():
    async def fake_trend(sym):
        return {"1120": {"state": "صاعد", "close": 90, "sma50": 85, "sma200": 80, "ret3m": 14.0, "strength": 6, "hi52": 105},
                "2010": {"state": "صاعد", "close": 70, "sma50": 66, "sma200": 64, "ret3m": 2.0, "strength": 4, "hi52": 80},
                "7010": {"state": "هابط", "close": 40, "sma50": 42, "sma200": 45, "ret3m": -8.0, "strength": 5, "hi52": 50},
                "2222": {"state": "صاعد", "close": 25, "sma50": 24, "sma200": 24, "ret3m": 3.0, "strength": 2, "hi52": 28}}.get(sym)
    res = {"1120": ("strong", "صافي الربح +28٪ عن الربع المماثل.", 28.0), "2010": ("neutral", "صافي الربح +4٪.", 4.0),
           "7010": ("neutral", "x", 1.0), "4190": ("pending", "نتائجُ الربع لم تصدر بعد.", None), "2222": ("weak", "صافي الربح −20٪.", -20.0)}
    SA.trend, o_tr = fake_trend, SA.trend
    SA.results_of, o_res = (lambda s, t: res.get(s, ("unknown", "—", None))), SA.results_of
    # ‏D786: الصيدُ يمرّ بمجلس صقر — مصادرُه الشبكيةُ تُعطَّل هنا (لا شبكة في الحارس): لا رسمَ ولا ياهو ولا عناوين ولا نموذج، فيحكم المسارُ والنتائجُ كما كانا
    from app.services import saqr_council as CN
    from app.services import research_desk as RD

    async def none3(sym):
        return None, None, None

    async def none1(*a, **k):
        return None

    async def empty(*a, **k):
        return []
    o_cn = (CN.chart_sa, CN.yf, CN.heads_sa, CN.events, RD._gemini)
    CN.chart_sa, CN.yf, CN.heads_sa, CN.events, RD._gemini = none3, none1, empty, empty, none1
    # ‏D832: بابُ صقر الواحد (فرصُ اليوم · «يوافق» كاملةً · قراءتُه الأخيرة · حدُّ النجاح) يُختبر في saqr_auto_d832 — ويُفتح هنا (الرفضُ وحده يمنع)
    # ليبقى هذا الحارسُ على ما وُضع له: الاختيارُ بالنتائج والمسار والقوّة النسبية، والحجمُ والوقف
    async def link_buy(*a, **k):
        return {"decision": "شراء", "confidence": "متوسطة", "link": "قراءةٌ تربط الشواهد.", "conflict": "", "watch": ""}

    async def vol(sym):
        return 0.25
    o_gate = (CN.opportunities, CN.gate_why, CN.link, SA.vol_of)
    CN.opportunities = lambda m: {s: {"symbol": s, "side": "long"} for s in ("1120", "2010", "7010", "4190", "2222")}
    CN.gate_why = lambda bd, lk, side, need_link=True: ("صقر لا يشتريه الآن — " + " · ".join(bd.get("veto_why") or [])) if bd.get("veto") else None
    CN.link, SA.vol_of = link_buy, vol
    from app.services.saqr_bot import bot
    sent = []

    async def fake_send(t, *a, **k):
        sent.append(t)
    o_n = (bot.send, bot.enabled)
    bot.send, bot.enabled = fake_send, True
    try:
        snap = {s: {"price": px, "bid": round(px - .02, 2), "ask": round(px + .02, 2), "turnover": 3e7, "change_pct": 1.2, "name_en": s}
                for s, px in (("1120", 90.0), ("2010", 70.0), ("7010", 40.0), ("4190", 60.0), ("2222", 25.0))}
        st = SQ.fresh(market="sa")
        now = datetime.now(timezone.utc)
        pos = await SA._hunt(st, now, snap, REG, {"level": "منخفض", "why": "هدوء"})
        verdicts = {x["sym"]: x["verdict"] for x in st["signals"]}
        # مراجعة: مركزُ صقر خاسرٌ وتاسي ينقلب ⇐ خروج؛ ومركزُ المالك اليدويّ ⇐ تنبيهٌ فقط
        SQ.buy(st, {"contract": "2010", "symbol": "2010", "type": "stock", "ask": 72.0, "bid": 71.9, "price": 72, "stop": 72 * SA.STOP}, 2, ["x"], kind="stock")
        SQ.buy(st, {"contract": "7010", "symbol": "7010", "type": "stock", "ask": 41.0, "bid": 40.9, "price": 41, "stop": 41 * SA.STOP}, 3, ["x"], src="manual", kind="stock")
        down = {**REG, "verdict": "هابط"}
        out = await SA._review(st, now, snap, down, {"level": "منخفض"})
        return pos, verdicts, st, out, sent
    finally:
        SA.trend, SA.results_of = o_tr, o_res
        CN.chart_sa, CN.yf, CN.heads_sa, CN.events, RD._gemini = o_cn
        CN.opportunities, CN.gate_why, CN.link, SA.vol_of = o_gate
        bot.send, bot.enabled = o_n
pos, verdicts, st9, out9, sent9 = asyncio.run(flow())
check(pos and pos["symbol"] == "1120" and pos["qty"] == SA.shares(min(1000, 1000 * 0.25), 90.02) and pos["stop"] == round(90.02 * SA.STOP, 3)
      and verdicts.get("1120") == "chosen" and verdicts.get("4190") == "refused" and verdicts.get("2222") == "refused" and verdicts.get("7010") == "refused"
      and verdicts.get("2010") == "refused" and st9["signals"][0]["verdict"] == "chosen",
      "٩ الصيد: يختار الشركةَ ذات النتائج القوية والمسار الصاعد والأقوى من تاسي (أسهمٌ صحيحةٌ بربع رأس المال ووقفٍ −6٪)، ويرفض ما لم تصدر نتائجُه "
      "والمخيّبَ والهابطَ والأضعفَ من تاسي — كلٌّ بسببه", f"{pos and (pos['symbol'], pos['qty'])} · {verdicts}")
manual = next((p for p in st9["positions"] if p["symbol"] == "7010"), None)
check(any(c["symbol"] == "2010" and c["reason"] == "regime" for c in out9) and manual and manual.get("alert") and not sent9,
      "٩ب المراجعة: تاسي ينقلب هابطاً ومركزُ صقر خاسر ⇐ يبيعه؛ ومركزُ المالك اليدويّ يُنبَّه عليه في السجلّ ولا يُمسّ — ولا تلغرام (‏D767)",
      f"{[(c['symbol'], c['reason']) for c in out9]} · {manual and manual.get('alert')}")

# ١٠ الجدولةُ والنقاطُ والمصدر
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
sas = (ROOT / "backend/app/services/saqr_sa.py").read_text(encoding="utf-8")
check('add_job(job_saqr_sa_cycle, CronTrigger(day_of_week=TRADING_DAYS, hour="10-14", minute="*/5")' in sch and 'def _mkt(v)' in mk
      and mk.count('m = _mkt(') >= 5 and not re.search(r"\.add\(|\.commit\(|delete\(|\.merge\(|insert\(", sas) and "MarketNews.published_at >= since" in sas,
      "١٠ دورةُ السعوديّ كلَّ خمس دقائق في ساعات تداول (الأحد–الخميس)، والنقاطُ كلُّها بسوقها، وصقرُ السعوديّ يقرأ الأخبارَ من قاعدة البيانات ولا يكتب فيها")

# ١١ الشعار — صورةُ المالك نفسُها بشفافيتها («هذا المرفقُ أجمل» ثمّ «هكذا أجملُ بدون خلفية»)
em = (ROOT / "frontend/src/components/saqr/SaqrEmblem.tsx").read_text(encoding="utf-8")
desk = (ROOT / "frontend/src/components/saqr/SaqrDesk.tsx").read_text(encoding="utf-8")
css = (ROOT / "frontend/src/styles/globals.css").read_text(encoding="utf-8")
A = ROOT / "frontend/src/assets/saqr"
big, small = A / "saqr-emblem-512.webp", A / "saqr-emblem-160.webp"
light = css[css.index("html.light {\n  --sq-plate"):]
sqe = css[css.index(".sqe { position: relative;"):css.index("@keyframes sqeGlow")]
check(big.exists() and small.exists() and big.stat().st_size < 80_000 and small.stat().st_size < 15_000
      and big.read_bytes()[8:12] == b"WEBP" and b"ALPH" in big.read_bytes()[:400] + big.read_bytes()[:4000] and 'alt="صقر"' in em
      and "961 / 1014" in em and "background" not in sqe and "border-radius" not in sqe
      and "Bird" not in desk and desk.count("<SaqrEmblem") == 2 and all(t + ":" in light[:300] for t in ("--sq-seam", "--sq-glow"))
      and "prefers-reduced-motion: reduce) { .sqe.live, .sqe.live img { animation: none; } }" in css,
      "١١ شعارُ صقر صورةُ المالك نفسُها بشفافيتها — بلا قرصٍ ولا أرضية، بنسبتها، مضغوطةً (webp ‏512 · 160)، يتوهّج حين يعمل ويسكن مع تقليل الحركة — "
      "ولا أيقونةَ طائرٍ عامّة", f"{big.stat().st_size // 1024}KB · {small.stat().st_size // 1024}KB")

print("\nالنتيجة:", "عطب ✖" if fail else "نظيف ✔")
sys.exit(fail)
