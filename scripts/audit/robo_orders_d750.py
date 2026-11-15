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
                        "monthly": {"state": "صاعد"}, "quantity": 100, "current_weight": 5.0, "target_weight": 10.0, "need": 50_000.0,
                        "sector": "البنوك", "autopilot": {"action": "اشترِ الآن", "why": ["القناعة مكتملة"], "conviction": ["أ", "ب"]}, **k}
cap = 1_000_000.0
o, h = R.plan([buy("1")], cap, 200_000, {"1": 4_000_000})
check(len(o) == 1 and o[0]["shares"] == 1000 and o[0]["amount"] == 50_000 and o[0]["confidence"] == 96 and all(c["ok"] for c in o[0]["checks"]),
      "١ الأمرُ بأرقامه: عددُ الأسهم والمبلغ والسعر وثقتُه (هامشٌ 30٪ 40 + ثقةٌ مرتفعة 20 + جودةٌ 80 16 + شهريٌّ صاعد 20 = 96) — وكلُّ بوّاباته ظاهرة", str(o and (o[0]["shares"], o[0]["confidence"])))
o, h = R.plan([buy("1")], cap, 200_000, {"1": 2_000_000})
check(not o and h and "سيولة" in h[0]["why"], "٢ لا شراءَ في سهمٍ متوسّطُ تداوله اليوميّ دون 3 ملايين ريال")
o2, _ = R.plan([buy("1", need=200_000, current_weight=0.0, target_weight=30.0)], cap, 500_000, {"1": 3_200_000})
check(o2 and o2[0]["amount"] <= 3_200_000 * 0.05 + 0.01 and o2[0]["shares"] == 3200, "٣ ولا أمرَ فوق 5٪ من تداول السهم اليوميّ — يُقصّ إليه",
      str(o2 and o2[0]["shares"]))
o, h = R.plan([buy("1", current_weight=14.0, target_weight=0.0)], cap, 200_000, {"1": 1e8})
check(o and o[0]["amount"] <= 10_000 + 0.01, "٤ ولا يتجاوز الشراءُ حدَّ السهم 15٪", str(o and o[0]["amount"]))
o, h = R.plan([buy("1", current_weight=14.0, target_weight=20.0, need=60_000)], cap, 200_000, {"1": 1e8})
check(o and o[0]["amount"] == 60_000 and "قرارُك" in o[0]["checks"][3]["d"], "٥ وهدفُ المالك اليدويّ يتقدّم على الحدّ — يُذكر تجاوزُه ولا يُنقض")
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
print(("FAIL" if fail else "PASS") + " D750 — أوامرُ المستشار الآليّ: بأرقامها وبوّاباتها، وباعتماد المالك، وبسجلّ دقّة")
sys.exit(fail)
