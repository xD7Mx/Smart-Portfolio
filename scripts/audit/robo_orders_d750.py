#!/usr/bin/env python3
"""حارسُ D750 — أوامرُ المستشار الآليّ على منهج «سندباد» (بأمر المالك 2026-11-16).

يُفحص على الدوالّ نفسِها: الأمرُ بأرقامه من قرار الطيار، وبوّاباتُ سيولة السهم وحجم الأمر وحدّ السهم والقطاع (وهدفُ المالك يتقدّم على الحدّ)،
والبيعُ عند التخفيف وتجاوز الحدّ، والدمجُ (لا تكرار · المعلّقُ الذي زالت شروطُه ينتهي · التنفيذُ يُكتشف من الكمية)، والاعتماد، وسجلُّ الدقّة،
والمساراتُ (الإجراءاتُ للمالك وحده)، والجدولُ (بعد رأي الطيار، ويُشعر بما استجدّ).

    python3 scripts/audit/robo_orders_d750.py
"""
import os, pathlib, sys, tempfile   # noqa: E401
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


from app.services import robo_orders as R   # noqa: E402
buy = lambda sym, **k: {"symbol": sym, "name": sym, "price": 50.0, "fair_value": 65.0, "fair_value_conf": "مرتفعة", "quality": 80,   # noqa: E731
                        "monthly": {"state": "صاعد", "resistance": [60.0, 62.0]}, "weekly": {"support": [48.0, 50.5]}, "quantity": 100, "avg_cost": 45.0, "current_weight": 5.0, "target_weight": 10.0, "need": 50_000.0,
                        "sector": "البنوك", "autopilot": {"action": "اشترِ الآن", "why": ["القناعة مكتملة"], "conviction": ["أ", "ب"]}, **k}
cap = 1_000_000.0
o, h = R.plan([buy("1")], cap, 200_000, {"1": 4_000_000})
check(len(o) == 1 and o[0]["shares"] == 1000 and o[0]["amount"] == 50_000 and o[0]["confidence"] == 96 and all(c["ok"] for c in o[0]["checks"])
      and len(o[0]["checks"]) == 7,
      "١ الأمرُ بأرقامه: عددُ الأسهم والمبلغ والسعر وثقتُه (هامشٌ 30٪ 40 + ثقةٌ مرتفعة 20 + جودةٌ 80 16 + شهريٌّ صاعد 20 = 96) — وكلُّ بوّاباته السبع ظاهرة", str(o and (o[0]["shares"], o[0]["confidence"])))
o, h = R.plan([buy("1")], cap, 200_000, {"1": 2_000_000})
check(not o and h and "سيولة" in h[0]["why"], "٢ لا شراءَ في سهمٍ متوسّطُ تداوله اليوميّ دون 3 ملايين ريال")
o2, _ = R.plan([buy("1", need=200_000, current_weight=0.0, target_weight=30.0, weekly={"support": [48.8, 50.5]})], cap, 500_000, {"1": 3_200_000})
check(o2 and o2[0]["amount"] <= 3_200_000 * 0.05 + 0.01 and o2[0]["shares"] == 3200, "٣ ولا أمرَ فوق 5٪ من تداول السهم اليوميّ — يُقصّ إليه",
      str(o2 and o2[0]["shares"]))
o, h = R.plan([buy("1", current_weight=14.0, target_weight=0.0)], cap, 200_000, {"1": 1e8})
check(o and o[0]["amount"] <= 10_000 + 0.01, "٤ ولا يتجاوز الشراءُ حدَّ السهم 15٪", str(o and o[0]["amount"]))
o, h = R.plan([buy("1", current_weight=14.0, target_weight=20.0, need=60_000)], cap, 200_000, {"1": 1e8})
check(o and o[0]["amount"] == 60_000 and any("قرارُك" in (c.get("d") or "") for c in o[0]["checks"] if "حدّ السهم" in c["k"]),
      "٥ وهدفُ المالك اليدويّ يتقدّم على الحدّ — يُذكر تجاوزُه ولا يُنقض")
sec = R.plan([buy("1", current_weight=20.0, target_weight=25.0), buy("2", current_weight=14.0, target_weight=20.0)], cap, 500_000, {"1": 1e9, "2": 1e9})[0]
check(sum(x["amount"] for x in sec) <= 1_000 + 0.01 * cap + 1, "٦ ولا يتجاوز القطاعُ حدَّه 35٪", str([x["amount"] for x in sec]))
s, h = R.plan([buy("1", autopilot={"action": "خفّف", "why": ["وزنه فوق هدفه"]}, current_weight=13.0, target_weight=10.0, quantity=1000),
               buy("2", autopilot={"action": "احتفظ", "why": []}, current_weight=18.0, target_weight=0.0, quantity=400)], cap, 0, {})
check(len(s) == 2 and s[0]["side"] == "بيع" and s[0]["shares"] == 600 and s[1]["side"] == "بيع" and "حدّ السهم" in s[1]["checks"][0]["k"],
      "٧ والبيعُ بأرقامه: التخفيفُ إلى الهدف، وما تجاوز حدَّ السهم بلا هدفٍ أعلى", str([(x["side"], x["shares"]) for x in s]))
o, _ = R.plan([buy("1")], cap, 200_000, {"1": 4_000_000})
st, fresh = R.merge({"orders": []}, o, "2026-11-16", {"1": 100}, {"1": 50.0}, 10_000.0)
st, fresh2 = R.merge(st, o, "2026-11-17", {"1": 100}, {"1": 50.0}, 10_000.0)
check(len(st["orders"]) == 1 and len(fresh) == 1 and not fresh2 and st["orders"][0]["status"] == "pending",
      "٨ الدمج: الأمرُ القائمُ يُحدَّث ولا يتكرّر، ولا يُشعَر إلا بما استجدّ")
oid = st["orders"][0]["id"]
check(R.decide(st, oid, True)["status"] == "approved" and R.decide(st, oid, True) is None, "٩ الاعتمادُ للأمر المعلّق مرّةً واحدة")
st, _ = R.merge(st, [], "2026-11-18", {"1": 1100}, {"1": 52.0}, 10_100.0)
check(st["orders"][0]["status"] == "executed" and st["orders"][0]["exec_price"] == 52.0, "١٠ والتنفيذُ يُكتشف من تغيّر الكمية")
st2, _ = R.merge({"orders": []}, o, "2026-11-16", {"1": 100}, {}, 10_000.0)
st2, _ = R.merge(st2, [], "2026-11-17", {"1": 100}, {}, 10_000.0)
check(st2["orders"][0]["status"] == "expired" and "زالت" in st2["orders"][0]["why_closed"], "١١ والمعلّقُ الذي زالت شروطُه قبل اعتماده ينتهي")
past = [{"symbol": "1", "side": "شراء", "price_at": 50.0, "tasi_at": 10_000.0, "day": "2026-09-01"},
        {"symbol": "2", "side": "بيع", "price_at": 40.0, "tasi_at": 10_000.0, "day": "2026-09-01"},
        {"symbol": "3", "side": "شراء", "price_at": 40.0, "tasi_at": 10_000.0, "day": "2026-11-10"}]
rc = R.record(past, {"1": 55.0, "2": 39.0, "3": 50.0}, 10_200.0, "2026-11-16")
check(rc["n"] == 2 and rc["hits"] == 2 and rc["rate"] == 100, "١٢ سجلُّ الدقّة بعد شهرٍ مقابل تاسي — الشراءُ إن تفوّق والبيعُ إن تأخّر، والأحدثُ لا يُقاس بعد",
      str(rc))
ai = (ROOT / "backend/app/api/v1/endpoints/ai.py").read_text(encoding="utf-8")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
check('@router.get("/robo")' in ai and '@router.post("/robo/orders/{oid}/{decision}", dependencies=[Depends(require_owner)])' in ai
      and '@router.post("/robo/pause", dependencies=[Depends(require_owner)])' in ai and '@router.post("/robo/refresh", dependencies=[Depends(require_owner)])' in ai,
      "١٣ المسارات: العرضُ للجميع، والاعتمادُ والرفضُ والإيقافُ والبناءُ للمالك وحده")
check("robo_refresh(db, notify=True)" in sch[sch.index("async def job_autopilot"):], "١٤ وتُبنى الأوامرُ بعد رأي الطيار اليوميّ ويُشعر المالكُ بما استجدّ")

# ══ ‏D754 (المالك 2026-11-16): «كأنه كتالوج — أريده بمستوى الموثوقية، أعتمد عليه في الحياة الواقعية» — الأمرُ خطّةُ صفقةٍ كاملة ══
check(R.on_tick(63.37) == 63.3 and R.on_tick(24.99) == 24.98 and R.on_tick(9.999) == 9.99 and R.on_tick(260.3) == 260.0 and R.on_tick(46.56) == 46.55
      and R.on_tick(46.51, up=True) == 46.55 and R.on_tick(612.4) == 612.0,
      "١٥ السعرُ المحدَّد على وحدة تداول السوق: 0.01 دون 10 · 0.02 دون 25 · 0.05 دون 50 · 0.10 دون 100 · 0.20 دون 250 · 0.50 دون 500 · ثمّ 1")
bars = [{"high": 10 + (i % 2), "low": 9, "close": 9.5 + (i % 2)} for i in range(30)]
check(abs((R.atr_of(bars) or 0) - 2.0) < 1e-9 or abs((R.atr_of(bars) or 0) - 1.5) < 0.6, "١٦ المدى الحقيقيّ اليوميّ (‏ATR) من الشموع", str(R.atr_of(bars)))
sf = R.stop_for(buy("1"), 1.0)
sfar = R.stop_for(buy("1", weekly={"support": [30.0, 31.0]}), 1.0)
snone = R.stop_for(buy("1", weekly={}), None)
check(sf == (46.55, "تحت الدعم الأسبوعيّ 48.00") and sfar[0] == 47.0 and "المدى" in sfar[1] and snone[0] is None,
      "١٧ وقفُ الخسارة تحت الدعم الأسبوعيّ بـ3٪ إن كان على 3–20٪ من السعر، وإلا ثلاثةُ أضعاف المدى، وإلا لا وقف (فلا شراء)", f"{sf} · {sfar} · {snone}")
check(R.target_for(buy("1"))[0] == 65.0 and R.target_for(buy("1", fair_value_conf="منخفضة"))[0] == 60.0
      and R.target_for(buy("1", fair_value=50.5, monthly={"resistance": [50.6, 51]}))[0] is None,
      "١٨ الهدفُ القيمةُ العادلة الموثوقة، وإلا المقاومةُ الشهرية، وإلا لا هدف — ولا يُخترع")
near = R.target_for(buy("1", fair_value_conf="منخفضة", weekly={"support": [48.0, 50.5], "resistance": [54.0, 55.0]},
                        monthly={"state": "صاعد", "resistance": [110.0, 120.0]}))
check(near == (54.0, "المقاومة الأسبوعية"), "١٨ب وحين لا قيمةَ موثوقة فأقربُ مقاومةٍ فوق السعر — لا مقاومةٌ شهريةٌ على ضعف السعر", str(near))
o, h = R.plan([buy("1", fair_value=55.0, monthly={"state": "صاعد", "resistance": [53.0, 54.0]})], cap, 200_000, {"1": 4e6})
check(not o and h and "العائدُ" in h[0]["why"], "١٩ لا شراءَ ما لم يبلغ العائدُ ضعفَي المخاطرة", h and h[0]["why"])
o, h = R.plan([buy("1", weekly={}, need=900_000)], cap, 900_000, {"1": 1e9}, atr={})
check(not o and h and "وقف" in h[0]["why"], "٢٠ ولا شراءَ بلا وقفِ خسارةٍ محسوب — لا دخولَ بلا مخرج", h and h[0]["why"])
o, _ = R.plan([buy("1", need=900_000, current_weight=0.0, target_weight=40.0)], cap, 900_000, {"1": 1e9})
lo = o and o[0]
check(lo and lo["shares"] == 2898 and lo["risk"] <= 10_000 + 0.01 and "مخاطرة" in lo["sizing"] and lo["stop"] == 46.55 and lo["target"] == 65.0
      and lo["rr"] == 4.35 and lo["type"] == "محدَّد" and lo["after"]["weight"] > 0,
      "٢١ الحجمُ من المخاطرة لا من الرغبة: لا يخسر أمرٌ لو ضُرب وقفُه فوق 1٪ من المحفظة — ويُسمّى القيدُ الذي حكم الحجم",
      lo and f"{lo['shares']} سهم · مخاطرة {lo['risk']:,.0f} · {lo['sizing']} · 1:{lo['rr']}")
P1 = [buy("1", autopilot={"action": "احتفظ"})]
pr, sv = R.protect(P1, {"1": 1.0}, {"1": {"stop": 40.0, "qty": 100}}, "2026-11-17")
pr2, _ = R.protect(P1, {"1": 1.0}, {"1": {"stop": 47.0, "qty": 100, "basis": "س"}}, "2026-11-17")
check(pr[0]["stop"] == 46.55 and pr[0]["trail"] and pr2[0]["stop"] == 47.0 and not pr2[0]["trail"],
      "٢٢ وقفُ المركز يُرفع مع صعود الدعم ولا يُخفض أبداً", f"{pr[0]['stop']} · {pr2[0]['stop']}")
pb, _ = R.protect([buy("1", price=46.0, autopilot={"action": "احتفظ"})], {"1": 1.0}, {"1": {"stop": 46.55, "qty": 100}}, "2026-11-18")
pn, _ = R.protect([buy("1", price=47.5, autopilot={"action": "احتفظ"})], {"1": 1.0}, {"1": {"stop": 46.55, "qty": 100}}, "2026-11-18")
sell, _ = R.plan([buy("1", price=46.0, autopilot={"action": "احتفظ"})], cap, 0, {}, prot=pb)
check(pb[0]["state"] == "كُسر الوقف" and pn[0]["state"] == "قريب من الوقف" and sell and sell[0]["kind"] == "stop" and sell[0]["shares"] == 100
      and sell[0]["side"] == "بيع",
      "٢٣ إغلاقُ السعر تحت الوقف «كسر» يصير أمرَ خروجٍ بالمركز كلّه ينتظر اعتمادك، واقترابُه دون 3٪ «قريب من الوقف»",
      f"{pb[0]['state']} · {pn[0]['state']} · {sell and sell[0]['shares']}")
pe, se = R.protect([buy("1", price=58.0, avg_cost=50.0, weekly={"support": [55.0, 57.0]}, autopilot={"action": "احتفظ"})], {"1": 1.0},
                   {"1": {"stop": 47.0, "qty": 100, "r0": 3.0}}, "2026-11-19")
check(pe[0]["stop"] == 53.3 and pe[0]["trail"] and "الدعم" in pe[0]["stop_basis"], "٢٤ والوقفُ يتبع الدعمَ الصاعد فوق التكلفة — 47 ← 53.30",
      f"{pe[0]['stop']} {pe[0]['stop_basis']}")
pe2, _ = R.protect([buy("1", price=57.0, avg_cost=50.0, weekly={"support": [40.0, 41.0]}, autopilot={"action": "احتفظ"})], {},
                   {"1": {"stop": 47.0, "qty": 100, "r0": 3.0}}, "2026-11-19")
check(pe2[0]["breakeven"] and pe2[0]["stop"] == 50.0 and "التكلفة" in pe2[0]["stop_basis"], "٢٤ب وبعد ربحٍ يعادل ضعفَي المخاطرة لا ينزل الوقفُ عن التكلفة — الربحُ محميّ",
      f"{pe2[0]['stop']} {pe2[0]['stop_basis']}")
st = {"orders": [], "stops": {"1": {"stop": 46.55, "qty": 100}}}
st, _ = R.merge(st, sell, "2026-11-18", {"1": 100}, {"1": 46.0}, 10_000.0)
oid = st["orders"][-1]["id"]
R.decide(st, oid, False)
# ‏D773: القرارُ يُختم بساعة الجهاز — والحارسُ يجري على تاريخٍ ثابت (18 نوفمبر)؛ فلمّا صار «اليومُ» 20 نوفمبر وقع اختبارُ «بعد أسبوع» (27) على
# حدّ الأسبوع نفسِه فسقط بلا عطبٍ في الشيفرة. فيُختم القرارُ بيوم الحارس لا بساعة الجهاز.
next(o for o in st["orders"] if o["id"] == oid)["decided"] = "2026-11-18T10:00"
pk, _ = R.protect([buy("1", price=46.0, autopilot={"action": "احتفظ"})], {"1": 1.0}, st["stops"], "2026-11-19")
st, fr = R.merge(st, sell, "2026-11-19", {"1": 100}, {"1": 46.0}, 10_000.0)
check(pk[0]["state"] != "كُسر الوقف" and pk[0]["stop"] < 46.0 and not fr and any("رفضتَه" in x["why"] for x in st["respected"]),
      "٢٥ قرارُك يُحترم: أبقيتَ المركزَ بعد الكسر فوقفٌ جديدٌ تحت السعر، والأمرُ المرفوضُ لا يُعاد قبل أسبوع", f"وقف جديد {pk[0]['stop']}")
st, fr = R.merge(st, sell, "2026-11-27", {"1": 100}, {"1": 46.0}, 10_000.0)
check(len(fr) == 1, "٢٥ب وبعد أسبوعٍ من قرارك يُعرض من جديد إن بقيت شروطُه")
ords = [{"symbol": "1", "side": "شراء", "stop": 46.55, "target": 65.0, "rr": 4.35, "price_at": 50.0, "tasi_at": 1e4, "day": "2026-11-01"},
        {"symbol": "2", "side": "شراء", "stop": 20.0, "target": 30.0, "rr": 2.5, "price_at": 22.0, "tasi_at": 1e4, "day": "2026-11-01"},
        {"symbol": "3", "side": "شراء", "stop": 9.0, "target": 13.0, "rr": 3.0, "price_at": 10.0, "tasi_at": 1e4, "day": "2026-11-10"}]
R.outcomes(ords, {"1": 66.0, "2": 19.5, "3": 10.5}, "2026-11-20")
R.outcomes(ords, {"1": 40.0, "2": 31.0, "3": 10.5}, "2026-11-21")
rc = R.record(ords, {"1": 66.0, "2": 19.5, "3": 10.5}, 1e4, "2026-11-20")["plans"]
check(ords[0]["outcome"]["k"] == "target" and ords[1]["outcome"]["k"] == "stop" and "outcome" not in ords[2]
      and rc == {"n": 3, "target": 1, "stop": 1, "open": 1, "avg_r": round((4.35 - 1) / 2, 2)},
      "٢٦ سجلُّ الخطط: أوّلُ ما يبلغه السعرُ — الهدفُ أو الوقف — يُسجَّل ولا يتغيّر، ومتوسّطُ الناتج بوحدة المخاطرة", str(rc))
rb = R.risk_board(pr + pb, [buy("1", current_weight=9.0), buy("2", current_weight=4.0, sector="الطاقة")], cap, 100_000)
check(abs(rb["heat"] - sum(x["risk"] or 0 for x in pr + pb)) < 0.01 and rb["top_stock"]["w"] == 9.0 and rb["top_sector"]["name"] == "البنوك"
      and rb["broken"] == 1 and rb["cash_pct"] == 10.0,
      "٢٧ لوحةُ المخاطر: ما تخسره المحفظةُ لو ضُربت الوقوفُ كلُّها، والنقد، وأكبرُ سهمٍ وقطاع، والمكسور", str({k: rb[k] for k in ("heat", "heat_pct", "broken")}))
src = (ROOT / "backend/app/services/robo_orders.py").read_text(encoding="utf-8")
check("وقف {o['stop']:.2f}" in src and "هدف {o['target']:.2f}" in src and '"كُسر الوقف", "قريب من الوقف"' in src,
      "٢٨ والإشعارُ يحمل خطّةَ الأمر (دخول · وقف · هدف · عائد · مخاطرة) وتنبيهَ كلّ وقفٍ كُسر أو اقترب لأوّل مرّة")
print(("FAIL" if fail else "PASS") + " D754 — المستشارُ الآليّ خطّةُ صفقةٍ كاملة: دخولٌ محدَّدٌ ووقفٌ وهدفٌ وحجمٌ من المخاطرة، وحمايةُ كلّ مركز، ولوحةُ المخاطر")
print(("FAIL" if fail else "PASS") + " D750 — أوامرُ المستشار الآليّ: بأرقامها وبوّاباتها، وباعتماد المالك، وبسجلّ دقّة")
sys.exit(fail)
