#!/usr/bin/env python3
"""حارسُ D768 — صقرٌ الأمريكيّ «وحشٌ شرس» بأمر المالك، وكلُّ صفقةٍ بتاريخها ووقتها (2026-11-19).

«بعد إيقاف إشعارات تلغرام ضع في السجلّ أو المراكز المفتوحة تاريخَ الصفقة والوقتَ الذي بدأت فيه… صقرٌ الأمريكيّ ممتازٌ في الاصطياد لكنّه متحفّظٌ
جداً، خجول… يجب أن يكون وحشاً شرساً. نعطيه ميزانيةَ 100 دولار للعقد الواحد ويختار كما يشاء، معه السوقُ الأمريكيّ كلُّه… أبغاه كلَّ يوم يشتغل،
وأقلُّ شيءٍ 100 دولار ربحاً». وقيس على دفتره (2026-11-18): ميزانيةُ الصفقة 50 (نصفُ 100) وأرخصُ عقدٍ صالحٍ 96–111 ⇐ كسورُ سهمين.

    python3 scripts/audit/saqr_d768.py
"""
import os, pathlib, re, sys, tempfile   # noqa: E401
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
SRC = (ROOT / "backend/app/services/saqr_trader.py").read_text(encoding="utf-8")

# ١ الافتراضيّ: الأمريكيُّ هجوميٌّ بـ100$ للصفقة وهدفِ يومٍ 100$، والسعوديُّ متوازنٌ ولا يقبل الهجوم
us, sa = SQ.fresh(), SQ.fresh(market="sa")
cu, cs = SQ.cfg(us), SQ.cfg(sa)
try:
    SQ.apply_settings(SQ.fresh(market="sa"), {"mode": "attack"})
    sa_attack = True
except ValueError:
    sa_attack = False
b = SQ.fresh()
SQ.apply_settings(b, {"mode": "balanced", "day_target": None})
check(cu["mode"] == "attack" and cu["per_trade"] == 100 and cu["day_target"] == 100 and SQ.profile(us) is SQ.PROFILES["attack"]
      and cs["mode"] == "balanced" and cs["per_trade"] is None and SQ.profile(sa) is SQ.PROFILES["balanced"] and not sa_attack
      and SQ.profile(b) is SQ.PROFILES["balanced"] and SQ.cfg(b)["day_target"] is None,
      "١ الأمريكيُّ هجوميٌّ افتراضاً (100$ للصفقة · هدفُ اليوم 100$) والمالكُ يعيده متوازناً ويلغي الهدف، والسعوديُّ متوازنٌ دائماً",
      f"{cu['mode']} · {cu['per_trade']} · {cu['day_target']}")

# ٢ الميزانيةُ: أمرُ المالك لا نصفُ رأس المال — والمقاعدُ رأسُ المال على ميزانية الصفقة
st = SQ.fresh(capital=1000)
s1, b1 = SQ.seats_budget(st, 1000, 0.3, 3)
st2 = SQ.fresh()
st2["cash"] = 0.26
s2, b2 = SQ.seats_budget(st2, 99.25, 0.5, 2)
st3 = SQ.fresh(capital=1000)
SQ.apply_settings(st3, {"max_positions": 3, "per_trade": 150})
s3, b3 = SQ.seats_budget(st3, 1000, 0.3, 3)
bal = SQ.fresh()
SQ.apply_settings(bal, {"mode": "balanced", "per_trade": None})
s4, b4 = SQ.seats_budget(bal, 100, 0.5, 2)
check((s1, b1) == (10, 100) and (s2, b2) == (1, 0.26) and (s3, b3) == (3, 150) and (s4, b4) == (2, 50),
      "٢ الهجوميّ: ميزانيةُ الصفقة أمرُ المالك (100$ لا نصفُ رأس المال)، ومقعدٌ لكلّ 100$ (ألفٌ ⇐ عشرةُ مقاعد)، وأقصى المراكز بأمره يتقدّم، "
      "والنقدُ يحدّها — والمتوازنُ كما كان (نصفُ المئة ومقعدان)", f"{(s1, b1)} · {(s2, b2)} · {(s3, b3)} · {(s4, b4)}")

# ٣ البوّاباتُ بعتبات النمط: عشرُ دقائق وربعُ ساعة، وعشرُ صفقات، وقاطعُ 20٪، والفيدراليُّ قبله بأربع ساعات، وحجرُ يومين
NY = __import__("zoneinfo").ZoneInfo("America/New_York")
d0 = datetime(2026, 11, 19, tzinfo=NY).date()
op, cl = (datetime.combine(d0, datetime.min.time().replace(hour=9, minute=30), NY), datetime.combine(d0, datetime.min.time().replace(hour=16), NY))
clock, mid = (op, cl), op + timedelta(hours=2)
a = SQ.fresh()
g_open5, g_open12 = SQ.gates(a, op + timedelta(minutes=5), clock, []), SQ.gates(a, op + timedelta(minutes=12), clock, [])
g_cl10, g_cl17 = SQ.gates(a, cl - timedelta(minutes=10), clock, []), SQ.gates(a, cl - timedelta(minutes=17), clock, [])
fed = lambda h: [{"impact": "High", "title": "FOMC Statement", "at": (mid + timedelta(hours=h)).astimezone(timezone.utc).isoformat(), "riyadh": "x"}]
g_fed5, g_fed3 = SQ.gates(a, mid, clock, fed(5)), SQ.gates(a, mid, clock, fed(3))
a["day"] = {"date": "2026-11-19", "start_eq": 100.0, "new": 9}
a["cash"] = 85.0
g_9 = SQ.gates(a, mid, clock, [])
a["day"]["new"], a["cash"] = 10, 79.0
g_10 = SQ.gates(a, mid, clock, [])
a["closed"] = [{"symbol": "NIO", "reason": "stop", "closed": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()},
               {"symbol": "AAL", "reason": "stop", "closed": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}]
now = datetime.now(timezone.utc)
check(g_open5 and not g_open12 and g_cl10 and not g_cl17 and not g_fed5 and g_fed3 and not g_9
      and any("قاطعُ اليوم" in x for x in g_10) and any("حدُّه اليوميّ" in x for x in g_10)
      and not SQ.cooling(a, "NIO", now) and SQ.cooling(a, "AAL", now),
      "٣ بوّاباتُ الهجوميّ: لا دخولَ في أوّل عشر دقائق ولا آخرِ ربع ساعة، والفيدراليُّ يحجب أربعَ ساعاتٍ قبله لا يوماً، وعشرُ صفقاتٍ يومياً، "
      "وقاطعُ اليوم عند خسارة 20٪ (15٪ تمرّ)، والحجرُ بعد الوقف يومان — فيعمل كلَّ يوم", " | ".join(g_10)[:120])

# ٤ العقد: آجالُ 7–60 (14 · 30 · 45)، وتحفّظُ المستشار يُقبل ويُكتب، و«لا» تُسقط
exps = [{"dte": d, "t": d, "date": str(d)} for d in (3, 8, 15, 29, 46, 75, 130, 190)]
ea, eb = SQ.pick_expiries(exps, SQ.PROFILES["attack"]), SQ.pick_expiries(exps)
k = {"delta": 0.4, "iv": 50, "theta": -0.05, "pop": 30, "spread_pct": 6, "target": 12, "target_label": "x", "breakeven": 11, "rr": 1.2,
     "verdict": "warn", "cons": ["العقدُ غالٍ: تذبذبُه الضمنيّ 80٪ فوق التاريخيّ 45٪."], "pros": []}
th = SQ.thesis("F", True, {"state": "صاعد", "close": 11, "sma200": 10, "ret3m": 5}, None, k, 0.5)
check([e["dte"] for e in ea] == [15, 29, 46] and [e["dte"] for e in eb] == [29, 46, 130]
      and 'if lvl == "no" or (lvl == "warn" and not pf["warn_ok"]):' in SRC and any("تحفّظُ المستشار" in x for x in th)
      and SQ.PROFILES["attack"]["warn_ok"] and not SQ.PROFILES["balanced"]["warn_ok"],
      "٤ العقدُ في الهجوميّ: آجالٌ أقصرُ أسرعُ حركة (15 · 29 · 46 لا 29 · 46 · 130)، وتحفّظُ المستشار يُقبل ويُكتب في المبرّر، وحكمُ «لا» يُسقط دائماً",
      f"{[e['dte'] for e in ea]} · {[e['dte'] for e in eb]}")

# ٥ الخروج: وقفٌ متحرّكٌ أبكر وأجلُ خروجٍ محفوظان في المركز (والقديمُ بقواعده)
p = SQ.buy(SQ.fresh(capital=1000), {"contract": "F261204C00012000", "symbol": "F", "type": "call", "ask": 1.0, "bid": 0.98,
                                    "trail": [1.3, 1.5, 0.8], "exit_dte": 3}, 1, ["x"])
SQ.trail(p, 1.31)
be = p["stop"]
SQ.trail(p, 1.6)
old = {"type": "call", "entry_px": 1.0, "stop": 0.6, "peak": 1.0, "target": 999}
check(be == 1.0 and p["stop"] == 1.28 and SQ.exit_rule(dict(p), 1.4, 10, 5, None, None) is None and SQ.exit_rule(dict(p), 1.2, 10, 5, None, None)[0] == "trail" and SQ.exit_rule(dict(p), 1.6, 10, 3, None, None)[0] == "time"
      and SQ.exit_rule(dict(old), 0.9, 10, 14, None, None)[0] == "time" and SQ.exit_rule(dict(old), 0.9, 10, 15, None, None) is None,
      "٥ الهجوميّ يحمي الربحَ أبكر: من +30٪ إلى الدخول ومن +50٪ إلى 80٪ من القمّة، ويخرج قبل 3 أيامٍ من الانتهاء — محفوظاً في المركز، والقديمُ بقواعده (14 يوماً)",
      f"{be} · {p['stop']}")

# ٦ هدفُ اليوم: بلوغُه يحمي كلَّ رابحٍ لصقر عند سعر دخوله مرّةً ويُكتب، والصيدُ مستمرّ؛ ودونه لا شيء
d = SQ.fresh(capital=1000)
d["day"] = {"date": "2026-11-19", "start_eq": 1000.0, "new": 2, "hit": None}
win = SQ.buy(d, {"contract": "A", "symbol": "A", "type": "call", "ask": 1.0, "bid": 1.0}, 1, ["x"])
lose = SQ.buy(d, {"contract": "B", "symbol": "B", "type": "call", "ask": 1.0, "bid": 1.0}, 1, ["x"])
man = SQ.buy(d, {"contract": "C", "symbol": "C", "type": "call", "ask": 1.0, "bid": 1.0}, 1, ["x"], src="manual")
win["bid"], lose["bid"], man["bid"] = 1.5, 0.9, 1.5
below = SQ.day_lock(d)
win["bid"] = 2.2
n1 = SQ.day_lock(d)
n2 = SQ.day_lock(d)
ds = SQ.day_status(d)
check(below == 0 and n1 == 1 and n2 == 0 and win["stop"] == 1.0 and lose["stop"] == 0.6 and man["stop"] == 0.6 and ds["hit"] and ds["pl"] >= 100
      and sum(1 for x in d["log"] if "بلغ هدفَ اليوم" in x["text"]) == 1 and ds["progress"] == 100.0,
      "٦ هدفُ اليوم: دونه لا يتغيّر شيء، وبلوغُه يحمي رابحاتِ صقر عند دخولها (لا الخاسرةَ ولا مراكزَ المالك) ويُكتب مرّةً — والصيدُ مستمرّ بلا سقف",
      f"{ds}")

# ٧ الدورةُ واللوحة: المسحُ بإيقاع النمط (خمسُ دقائق)، وقفلُ الهدف كلَّ دورة، واللوحةُ تحمل اليومَ والنمطَ وعتباتِه
cyc = SRC[SRC.index("async def cycle("):SRC.index("# ══ أوامرُ المالك")]
hunt = SRC[SRC.index("async def _hunt("):SRC.index("async def cycle(")]
v = SQ.view("us")
check('profile(st)["scan"] - 30' in cyc and "day_lock(st)" in cyc and 'pf["fight"]' in hunt and "best_for(s, side == \"call\", budget, tr_all[s], ctx, pf)" in hunt
      and 'chosen["trail"], chosen["exit_dte"] = list(pf["trail"]), pf["exit_dte"]' in hunt and SQ.PROFILES["attack"]["scan"] == 300
      and v["day"]["target"] == 100 and v["rules"]["mode"] == "attack" and v["rules"]["dte"] == [7, 60] and v["rules"]["max_new_day"] == 10 and v["settings"]["per_trade"] == 100,
      "٧ صقرٌ يمسح كلَّ خمس دقائق ويحرس هدفَ اليوم كلَّ دورة، والصيدُ بعتبات النمط — واللوحةُ تعرض اليومَ والنمطَ وعتباتِه الحقيقية",
      f"{v['day']} · {v['rules']['dte']}")

# ٨ الواجهة: كلُّ مركزٍ بتاريخ فتحه ووقته ومدّته، والمغلقةُ بوقتَي الدخول والخروج، وهدفُ اليوم، والنمطُ في الأوامر
pf_src = (ROOT / "frontend/src/components/saqr/SaqrPortfolio.tsx").read_text(encoding="utf-8")
desk = (ROOT / "frontend/src/components/saqr/SaqrDesk.tsx").read_text(encoding="utf-8")
ts = (ROOT / "frontend/src/components/saqr/saqr.ts").read_text(encoding="utf-8")
check('data-role="sp-opened"' in pf_src and "stamp(p.opened)" in pf_src and "held(p.opened)" in pf_src and 'data-role="sp-closed-time"' in pf_src
      and "stamp(c.opened)" in pf_src and "held(c.opened, c.closed)" in pf_src and "<Dur v={held(p.opened)} />" in pf_src and 'data-role="sp-day"' in pf_src
      and 'data-role="sq-day"' in desk and 'k="mode"' in desk and 'data-role="sq-day-target"' in desk and "export const stamp" in ts and "export const held" in ts,
      "٨ الواجهة: «فُتحت 19/11 17:42 · منذ 3 س» لكلّ مركز، والمغلقةُ بوقتَي دخولها وخروجها ومدّتها، وهدفُ اليوم في اللوحة والمحفظة، والنمطُ وهدفُ اليوم في الأوامر")

print("\nالنتيجة:", "عطب ✖" if fail else "نظيف ✔")
sys.exit(fail)
