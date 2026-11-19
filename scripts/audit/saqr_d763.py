#!/usr/bin/env python3
"""حارسُ D763 — صقر: وكيلُ التداول الآليّ لعقود الخيارات ومحفظتُه المستقلّة (بأمر المالك 2026-11-18).

«يبدأ من 100 دولار ويحاول أن يوصلها إلى 10,000… السوقُ الأمريكيّ كاملٌ قدّام عينه… لازم يفهم أنّ الموضوع جدّ، ما هو محاكاة ولا لعب».
يُفحص على الدوالّ نفسِها بلا شبكة: محاسبةُ الدفتر (الشراءُ بالعرض والبيعُ بالطلب والعمولةُ لكلّ عقد)، والقيمةُ بسعر الطلب، وطبقاتُ الحجم،
والوقفُ ورفعُه وجنيُ التضاعف والهدفُ والأجلُ وانكسارُ الأطروحة، وبوّاباتُ الدخول (أطرافُ الجلسة والحدثُ العالي الأثر والفيدراليُّ والقاطعُ
والحدُّ اليوميّ)، والحجرُ بعد الوقف، وأوامرُ المالك (تتقدّم على الآليّ ولا يبيع صقرٌ مركزاً يدوياً)، والتجربةُ الجديدةُ تحفظ السابقة،
وأنّ صقراً لا يمسّ محفظةَ المالك، والجدولةَ، ونقاطَ الوصول بصلاحية المالك، ونقلَ التقرير اليوميّ إلى مفكرة السوق وتبويباتِ المختبر.

    python3 scripts/audit/saqr_d763.py
"""
import asyncio, math, os, pathlib, re, sys, tempfile   # noqa: E401
from datetime import datetime, timedelta, timezone
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

# ١ الدفتر: يبدأ من 100 والهدفُ 10,000؛ الشراءُ بسعر العرض + 0.65 لكلّ عقد، والقيمةُ بسعر الطلب، والبيعُ بالطلب − العمولة
st = SQ.fresh()
K = {"contract": "F270115C00012000", "symbol": "F", "type": "call", "strike": 12.0, "expiry": "2027-01-15", "t": 1, "ask": 0.40, "bid": 0.37,
     "price": 11.5, "target": 13.2, "target_label": "قمّة السنة", "delta": 0.42, "iv": 33.0, "dte": 58}
p = SQ.buy(st, K, 1, ["اختبار"])
eq0 = SQ.equity(st)
check(st["capital"] == 100 and st["goal"] == 10_000 and st["cash"] == round(100 - 40 - 0.65, 2) and p["cost"] == 40.65 and eq0 == round(59.35 + 37, 2)
      and p["stop"] == round(0.40 * SQ.STOP, 4),
      "١ الدفترُ يبدأ من 100 دولار وهدفُه 10,000؛ الشراءُ بسعر العرض والعمولة (0.65 للعقد)، والقيمةُ بسعر الطلب (ما يُباع به فعلاً)، والوقفُ 60٪ من الشراء",
      f"نقد {st['cash']} · كلفة {p['cost']} · رأس مال {eq0} · وقف {p['stop']}")
c = SQ.sell(st, p["id"], 0.80, "take", "تضاعف")
check(c and c["proceeds"] == round(80 - 0.65, 2) and c["pl"] == round(79.35 - 40.65, 2) and st["cash"] == round(59.35 + 79.35, 2)
      and not st["positions"] and st["closed"][0]["reason_ar"].startswith("تضاعف"),
      "٢ البيعُ بسعر الطلب ناقصَ العمولة يعود نقداً، والربحُ بعد العمولتين، والمركزُ ينتقل إلى المغلقة بسببه", f"{c and c['pl']} · نقد {st['cash']}")

# ٣ طبقاتُ الحجم والكمّية
check(SQ.tier(100) == (0.5, 2) and SQ.tier(1500) == (0.3, 3) and SQ.tier(5000) == (0.2, 5) and SQ.tier(20000) == (0.1, 8)
      and SQ.size(50, 0.40) == 1 and SQ.size(50, 0.50) == 0 and SQ.size(300, 1.45) == 2,
      "٣ الحجمُ بالطبقة: دون 500 نصفُ رأس المال لمركزين … وفوق 10,000 عُشرُه لثمانية؛ والكمّيةُ ما تتّسع له الميزانيةُ مع العمولة",
      f"{SQ.size(50, 0.40)} · {SQ.size(50, 0.50)} · {SQ.size(300, 1.45)}")

# ٤ قواعدُ الخروج
P = {"type": "call", "entry_px": 1.0, "stop": 0.6, "peak": 1.0, "target": 50.0}
TR = {"state": "صاعد", "close": 45.0, "sma200": 40.0, "sma50": 43.0}
r_stop = SQ.exit_rule(dict(P), 0.59, 45, 60, TR, None)
r_take = SQ.exit_rule(dict(P), 2.05, 45, 60, TR, None)
r_tgt = SQ.exit_rule(dict(P), 1.30, 50.5, 60, TR, None)
r_time = SQ.exit_rule(dict(P), 1.30, 45, 14, TR, None)
r_brk = SQ.exit_rule(dict(P), 1.10, 45, 60, {**TR, "state": "هابط"}, None)
r_hold = SQ.exit_rule(dict(P), 0.95, 45, 60, TR, None)
r_nobid = SQ.exit_rule(dict(P), None, 45, 60, TR, None)
check(r_stop[0] == "stop" and r_take[0] == "take" and r_tgt[0] == "target" and r_time[0] == "time" and r_brk[0] == "broken" and r_hold is None and r_nobid is None,
      "٤ الخروج: وقفٌ عند 60٪ من الشراء، وجنيٌ عند التضاعف، وعند بلوغ السهم الهدف، وقبل 14 يوماً من الانتهاء، وعند انكسار الأطروحة — "
      "وتذبذبٌ عاديٌّ أو غيابُ الطلب لا يُخرج", f"{r_stop[0]} {r_take[0]} {r_tgt[0]} {r_time[0]} {r_brk[0]} {r_hold}")
q = dict(P)
SQ.trail(q, 1.55)
be = q["stop"]
SQ.trail(q, 1.90)
hi = q["stop"]
SQ.trail(q, 1.20)
r_tr = SQ.exit_rule(q, 1.40, 45, 60, TR, None)
check(be == 1.0 and abs(hi - 1.9 * 0.75) < 1e-6 and q["stop"] == hi and r_tr and r_tr[0] == "trail",
      "٤ب الوقفُ المتحرّك: من +50٪ إلى سعر الدخول، ومن +80٪ إلى 75٪ من القمّة، ولا ينزل أبداً — وكسرُه «وقفٌ متحرّكٌ يحمي الربح»",
      f"{be} ⇐ {hi} ⇐ {q['stop']} · {r_tr}")

# ٥ البوّابات
NY = __import__("zoneinfo").ZoneInfo("America/New_York")
d0 = datetime(2026, 11, 18, tzinfo=NY).date()
op, cl = datetime.combine(d0, datetime.min.time().replace(hour=9, minute=30), NY), datetime.combine(d0, datetime.min.time().replace(hour=16), NY)
clock = (op, cl)
st = SQ.fresh()
st["settings"] = {"mode": "balanced"}   # ‏D768: هذه عتباتُ النمط المتوازن — والهجوميُّ في saqr_d768.py
mid = op + timedelta(hours=2)
g_ok = SQ.gates(st, mid, clock, [])
g_open = SQ.gates(st, op + timedelta(minutes=5), clock, [])
g_close = SQ.gates(st, cl - timedelta(minutes=10), clock, [])
g_out = SQ.gates(st, cl + timedelta(hours=1), clock, [])
ev_cpi = [{"impact": "High", "title": "CPI m/m", "at": (mid + timedelta(minutes=90)).astimezone(timezone.utc).isoformat(), "riyadh": "2026-11-18 21:30"}]
ev_far = [{"impact": "High", "title": "CPI m/m", "at": (mid + timedelta(hours=5)).astimezone(timezone.utc).isoformat(), "riyadh": "x"}]
ev_fed = [{"impact": "High", "title": "FOMC Statement", "at": (mid + timedelta(hours=20)).astimezone(timezone.utc).isoformat(), "riyadh": "x"}]
ev_med = [{"impact": "Medium", "title": "Retail", "at": (mid + timedelta(minutes=30)).astimezone(timezone.utc).isoformat(), "riyadh": "x"}]
g_cpi, g_far, g_fed, g_med = (SQ.gates(st, mid, clock, e) for e in (ev_cpi, ev_far, ev_fed, ev_med))
check(not g_ok and g_open and "ربع ساعة" in g_open[0] and g_close and "عشرين" in g_close[0] and g_out and g_cpi and "CPI" in g_cpi[0]
      and not g_far and g_fed and not g_med,
      "٥ البوّابات: لا دخولَ في أوّل ربع ساعةٍ ولا آخرِ عشرين دقيقة ولا خارج الجلسة، ولا قبل حدثٍ عالي الأثر بساعتين (والفيدراليُّ بيوم) — "
      "والبعيدُ والمتوسّطُ الأثر لا يمنعان", f"{len(g_ok)} · {g_open[:1]} · {g_cpi[:1]}")
st = SQ.fresh()
st["settings"] = {"mode": "balanced"}
st["day"] = {"date": "2026-11-18", "start_eq": 200.0, "new": 0}
st["cash"] = 165.0
g_brk = SQ.gates(st, mid, clock, [])
st["cash"], st["day"]["new"] = 199.0, SQ.MAX_NEW_DAY
g_max = SQ.gates(st, mid, clock, [])
st["on"] = False
g_off = SQ.gates(st, mid, clock, [])
check(any("قاطعُ اليوم" in x for x in g_brk) and any("حدُّه اليوميّ" in x for x in g_max) and any("موقوف" in x for x in g_off),
      "٥ب قاطعُ اليوم عند خسارة 15٪، والحدُّ ثلاثُ صفقاتٍ يومياً، وصقرٌ الموقوفُ لا يدخل", " | ".join(g_brk + g_max)[:120])
st = SQ.fresh()
st["settings"] = {"mode": "balanced"}
st["closed"] = [{"symbol": "NIO", "reason": "stop", "closed": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()},
                {"symbol": "F", "reason": "take", "closed": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()},
                {"symbol": "AAL", "reason": "stop", "closed": (datetime.now(timezone.utc) - timedelta(days=9)).isoformat()}]
now = datetime.now(timezone.utc)
check(SQ.cooling(st, "NIO", now) and not SQ.cooling(st, "F", now) and not SQ.cooling(st, "AAL", now),
      "٥ج لا عودةَ إلى سهمٍ خرج بوقفٍ قبل خمسة أيام — والجنيُ لا يحجر")

# ٦ آجالُ صقر وقواعدُ عقده أضيقُ من المُنتقي الطويل
ex = SQ.pick_expiries([{"dte": d, "t": d, "date": str(d)} for d in (3, 10, 24, 31, 59, 66, 122, 185, 240, 400)])
check([e["dte"] for e in ex] == [31, 59, 122] and SQ.RULES["max_spread"] == 0.08 and SQ.RULES["min_delta"] == 0.35 and SQ.MAX_BURN == 0.03,
      "٦ صقرٌ يتداول آجالَ 21–200 يوماً (نحو شهرٍ وشهرين وأربعة) بفارقٍ ≤ 8٪ ودلتا ≥ 0.35 وتآكلٍ ≤ 3٪ يومياً", str([e["dte"] for e in ex]))
from app.services import option_picks as OP   # noqa: E402
row = {"contract": "X", "strike": 12.0, "ask": 0.42, "bid": 0.385, "oi": 500, "volume": 50}
TRx = {"state": "صاعد", "close": 11.5, "sma200": 10.0, "hi60": 13.5, "hi120": 13.5, "hi52": 13.5, "lo60": 9, "lo120": 9, "lo52": 9}
k_def, why_def = OP.evaluate(row, 11.5, 60, True, TRx, 0.35)
k_sq, why_sq = OP.evaluate(row, 11.5, 60, True, TRx, 0.35, rules=SQ.RULES)
check((k_def is not None) and (k_sq is None) and "الفارق" in why_sq,
      "٦ب قواعدُ صقر تمرّ على المقيِّم نفسِه: عقدٌ بفارق 8.7٪ يقبله المُنتقي الطويل (≤ 10٪) ويرفضه صقر (≤ 8٪)", f"{why_def or 'مقبول'} · {why_sq}")

# ٧ أوامرُ المالك: مركزٌ يدويٌّ لا يبيعه صقر — يُنبَّه عليه؛ والتجربةُ الجديدة تحفظ السابقة؛ والدفترُ في ملفٍّ مستقلّ


async def manual_flow():
    st = SQ.fresh()
    m = SQ.buy(st, {**K, "contract": "NIO270115P00004000", "symbol": "NIO", "type": "put", "strike": 4.0, "ask": 0.30, "bid": 0.28}, 1, ["يدويّ"], src="manual")
    SQ.save(st)

    async def fake_q(p):
        return 0.15, 0.17, 4.4, 50
    SQ.quote_position, orig = fake_q, SQ.quote_position
    # ‏D767: صقرُ التداول لا يرسل إلى تلغرام شيئاً — يُرصد مُرسِلُ البوت نفسُه (مفعّلاً) فلا يُنادى
    from app.services.saqr_bot import bot
    sent = []

    async def fake_send(t, *a, **k):
        sent.append(t)
    orig_n = (bot.send, bot.enabled)
    bot.send, bot.enabled = fake_send, True
    try:
        st2 = SQ.load()
        out = await SQ._review(st2, datetime.now(timezone.utc), {})
    finally:
        SQ.quote_position = orig
        bot.send, bot.enabled = orig_n
    SQ.save(st2)
    st3 = await SQ.set_capital(250)
    return out, st2, sent, st3
out, st2, sent, st3 = asyncio.run(manual_flow())
check(out == [] and len(st2["positions"]) == 1 and st2["positions"][0].get("alert") == "stop" and not sent
      and st2["log"][0]["kind"] == "alert" and "إشارةُ خروج" in st2["log"][0]["text"],
      "٧ مركزُ المالك اليدويّ لا يبيعه صقر (تعديلاتُ المالك تتقدّم) — يكتب إشارةَ خروجٍ في سجلّ التطبيق، ولا يرسل إلى تلغرام شيئاً (‏D767)",
      f"{len(st2['positions'])} · تلغرام {len(sent)}")
check(st3["capital"] == 250 and st3["cash"] == 250 and not st3["positions"] and st3["runs"] and st3["runs"][0]["capital"] == 100
      and SQ._path().startswith(_SB) and SQ._path().endswith("saqr/ledger.json"),
      "٧ب تجربةٌ جديدةٌ برأس مالٍ يحدّده المالك تحفظ السابقةَ ملخّصة — والدفترُ ملفٌّ مستقلٌّ لا يمسّ محفظةَ المالك", f"{st3['runs'][:1]}")
v = SQ.view()
check(all(x in v for x in ("equity", "cash", "positions", "closed", "win_rate", "exposure", "equity_curve", "signals", "log", "gates", "health", "broker", "today", "rules"))
      and v["broker"]["linked"] is False,
      "٧ج اللوحةُ تقرأ الملخّصَ والمراكزَ والمغلقةَ ونسبةَ النجاح والتعرّضَ والمنحنى والإشاراتِ والسجلَّ والبوّاباتِ وحالَ الأنظمة — والوسيطُ «غيرُ مربوط» صراحةً")

# ٨ المصدرُ: صقرٌ لا يمسّ قاعدةَ بيانات المحفظة، ولا يتداول خارج الجلسة، والجدولةُ والنقاطُ بصلاحية المالك
src = (ROOT / "backend/app/services/saqr_trader.py").read_text(encoding="utf-8")
check(not re.search(r"from app\.models|AsyncSessionLocal|portfolio_service|Transaction\b", src) and 'ses.get("state") != "open"' in src
      and 'k["px_src"] != "ask"' in src,
      "٨ صقرٌ لا يمسّ قاعدةَ بيانات المحفظة، ولا يعمل خارج الجلسة الرسمية، ولا يشتري إلا بعرضٍ وطلبٍ حيّين")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
owner_eps = re.findall(r'@router\.post\("/saqr/[^"]*"(, dependencies=\[Depends\(require_owner\)\])?\)', mk)
check('add_job(job_saqr_cycle, CronTrigger(day_of_week=US_TRADING_DAYS, hour="16-23", minute="*/5")' in sch and len(owner_eps) == 6 and all(owner_eps) and '"/saqr/settings"' in mk,
      "٨ب دورةُ صقر كلَّ خمس دقائق في نافذة الجلسة الأمريكية، وأوامرُه الستّة (دورة · تشغيل · رأس مال · إعدادات ‏D767 · فتح · إغلاق) بصلاحية المالك وحده",
      f"{len(owner_eps)} نقطة")

# ٩ الواجهة: التقريرُ اليوميّ في مفكرة السوق بجانب التوقعات، والمختبرُ: عقودُ الخيارات · صقر (والمحفظةُ داخل صقر — ‏D769)
lab = (ROOT / "frontend/src/pages/ResearchLab.tsx").read_text(encoding="utf-8")
ev = (ROOT / "frontend/src/components/market/EventsList.tsx").read_text(encoding="utf-8")
rep = (ROOT / "frontend/src/components/research/DailyReport.tsx").read_text(encoding="utf-8")
desk9 = (ROOT / "frontend/src/components/saqr/SaqrDesk.tsx").read_text(encoding="utf-8")
# ‏D769 (المالك): «خلّنا نوحّد كلَّ تفاصيل صقر — المحفظةُ داخل صقر بجانب لوحة المعلومات والسجل»: تبويبان في المختبر والمحفظةُ تبويبٌ في صقر
check('["options", "عقود الخيارات"], ["saqr", "صقر"]' in lab and '["portfolio", "المحفظة", Wallet]' in desk9 and "<SaqrPortfolio market={market} />" in desk9
      and "SaqrPortfolio" not in lab and "التقرير اليومي" not in lab and "researchDesk(" not in lab
      and "<DailyReport />" in ev and 'setView("rep")' in ev and "researchDesk(" in rep and 'data-role="rl-doc"' in rep,
      "٩ التقريرُ اليوميّ انتقل إلى مفكرة السوق (بجانب التوقعات حيث الجزيرة والراجحي)، والمختبرُ: عقودُ الخيارات · صقر — والمحفظةُ تبويبٌ داخل صقر (‏D769)")

print("\nالنتيجة:", "عطب ✖" if fail else "نظيف ✔")
sys.exit(fail)
