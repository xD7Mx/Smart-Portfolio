#!/usr/bin/env python3
"""حارسُ D777 — محاكاةُ المحفظة كإنتراكتف بروكرز بالعربية، و«عقودُ الخيارات» داخل صقر (2026-11-20).

«محاكاةُ المحفظة مثل إنتراكتف بروكرز — عند فتح أمرٍ جديد: سعرُ الشراء بأمرٍ محدّد، وسعرُ البيع بأمرٍ محدّد، والوقفُ المطارِد… بالعربي عشان نتعلّم
عليها… وما نلخبط أنفسنا بين عقود الخيارات وبين صقر — خلِّ عقود الخيارات داخل صقر، ويكون التبويبُ السوقَ الأمريكيّ والسعوديّ فقط».

    python3 scripts/audit/saqr_d777.py
"""
import asyncio, os, pathlib, sys, tempfile   # noqa: E401
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
from app.services import live_quote as LQ   # noqa: E402


def bad(t, ask=1.20):
    try:
        SQ.ticket(t, ask)
        return None
    except ValueError as e:
        return str(e)


# ١ التذكرة: كلُّ نوعٍ بحقوله، وكلُّ خطأٍ برسالةٍ عربيةٍ تشرحه
ok_b = SQ.ticket({"qty": 2, "otype": "lmt", "limit": 1.25, "tp_px": 1.75, "sl_px": 0.75, "tif": "day"}, 1.20)
ok_t = SQ.ticket({"qty": 1, "otype": "stp_lmt", "stop": 1.30, "limit": 1.35, "trail_pct": 20}, 1.20)
old = SQ.ticket({"qty": 1, "limit": 1.0, "tp_pct": 40, "sl_pct": 40}, 1.20)            # ‏D771: الصيغةُ القديمة تبقى صالحة
errs = {k: bad(t) for k, t in {
    "lmt": {"qty": 1, "otype": "lmt"}, "stp": {"qty": 1, "otype": "stp"}, "sl_order": {"qty": 1, "otype": "stp_lmt", "stop": 1.4, "limit": 1.3},
    "tp_low": {"qty": 1, "otype": "lmt", "limit": 1.2, "tp_px": 1.1}, "sl_high": {"qty": 1, "otype": "lmt", "limit": 1.2, "sl_px": 1.3},
    "two_stops": {"qty": 1, "sl_px": 0.8, "trail_pct": 20}, "trail_rng": {"qty": 1, "trail_pct": 2}, "type": {"qty": 1, "otype": "moc"},
    "tif": {"qty": 1, "tif": "week"}}.items()}
check(ok_b["otype"] == "lmt" and ok_b["tp_px"] == 1.75 and ok_b["sl_px"] == 0.75 and ok_b["tif"] == "day" and ok_b["stop"] is None
      and ok_t["otype"] == "stp_lmt" and ok_t["stop"] == 1.3 and ok_t["limit"] == 1.35 and ok_t["trail_pct"] == 20 and ok_t["tif"] == "gtc"
      and old["otype"] == "lmt" and old["tp_pct"] == 40 and old["sl_pct"] == 40 and all(errs.values())
      and "سعرَ الحدّ" in errs["lmt"] and "سعرَ التفعيل" in errs["stp"] and "لا يقلّ عن سعر التفعيل" in errs["sl_order"] and "يعلو" in errs["tp_low"]
      and "دون سعر الشراء" in errs["sl_high"] and "وقفاً واحداً" in errs["two_stops"],
      "١ التذكرة: سوق · محدَّد · إيقاف · إيقافٌ محدَّد، ومدّةُ اليوم أو حتى الإلغاء، وأوامرُ البيع المرفقة بسعرها أو المطارِدُ بنسبته — والصيغةُ القديمةُ صالحة، "
      "وكلُّ خطأٍ برسالةٍ عربيةٍ تشرحه", f"{ {k: (v or '')[:30] for k, v in errs.items()} }")

# ٢ التنفيذ: المحدَّدُ عند سعره أو أقلّ، والإيقافُ يُفعَّل مرّةً متى بلغ العرضُ سعرَه، والإيقافُ المحدَّدُ بعد تفعيله محدَّد
o_l = {"otype": "lmt", "limit": 1.25}
o_s = {"otype": "stp", "stop": 1.30}
o_sl = {"otype": "stp_lmt", "stop": 1.30, "limit": 1.35}
r = [SQ.trigger(o_l, 1.30)[0], SQ.trigger(o_l, 1.25)[0], SQ.trigger(o_s, 1.20)[0], SQ.trigger(o_s, 1.31)[0],
     SQ.trigger(o_sl, 1.20)[0], SQ.trigger(o_sl, 1.40)[0], bool(o_sl.get("triggered")), SQ.trigger(o_sl, 1.33)[0], SQ.trigger({"otype": "mkt"}, 9.9)[0]]
check(r == [False, True, False, True, False, False, True, True, True],
      "٢ التنفيذ: المحدَّدُ بسعرك أو أقلّ، والإيقافُ ينتظر حتى يبلغ العرضُ سعرَ التفعيل ثمّ بالسوق، والإيقافُ المحدَّدُ يُفعَّل ثمّ لا يدفع فوق حدّه، "
      "والسوقُ فوراً", f"{r}")

# ٣ من الأمر إلى المركز: إيقافٌ معلّقٌ يُنفَّذ حين يرتفع العرض، وأمرُ «اليوم» ينتهي بجلسته، والبراكتُ بسعريه، والمطارِدُ يتبع القمّةَ ويبيع
Q = {"ask": 1.20, "state": "open"}


async def fake_q(c):
    from app.services.options_chain import parse_option
    return {"o": parse_option(c), "t": 1, "dte": 392, "ask": Q["ask"], "bid": Q["ask"] - 0.05, "live": True, "price": 12.0, "name": "Ford"}


async def fake_sess():
    return {"us": {"state": Q["state"]}}
SQ.contract_quote, LQ.sessions = fake_q, fake_sess
SQ.save(SQ.fresh(capital=2000))
C = "F271217C00010000"
asyncio.run(SQ.place_order(C, 1, None, None, None, otype="stp", stop=1.30, trail_pct=20))          # العرضُ دون التفعيل ⇐ معلّق
asyncio.run(SQ.place_order("F271217C00012000", 1, 1.0, None, None, otype="lmt", tif="day"))         # محدَّدٌ دون العرض ⇐ معلّق لليوم
asyncio.run(SQ.place_order("F271217C00011000", 1, 1.25, None, None, otype="lmt", tp_px=1.80, sl_px=0.90))   # براكتٌ يُنفَّذ الآن
st = SQ.load()
pend0 = [(o["otype"], o.get("note", "")[:40]) for o in st["orders"]]
br = next(p for p in st["positions"] if p["contract"] == "F271217C00011000")
st["orders"][1]["for"] = "2026-01-02"                                                                # أمرُ «اليوم» من جلسةٍ مضت
Q["ask"] = 1.32
n = asyncio.run(SQ._fill_orders(st))
tr_p = next((p for p in st["positions"] if p["contract"] == C), {})
expired = any("انتهت مدّةُ أمر الشراء" in x["text"] for x in st["log"])
SQ.trail(tr_p, 1.80)
stop_after = tr_p.get("stop")
ex = SQ.exit_rule(dict(tr_p), 1.40, 12.0, 300, None, None)
check(len(pend0) == 2 and pend0[0][0] == "stp" and "دون سعر التفعيل" in pend0[0][1] and br["entry_px"] == 1.2 and round(br["entry_px"] * br["take_x"], 2) == 1.8
      and br["stop"] == 0.9 and n == 1 and not st["orders"] and expired and tr_p.get("entry_px") == 1.32 and tr_p.get("trail_pct") == 20
      and tr_p.get("stop0") == round(1.32 * 0.8, 4) and stop_after == round(1.80 * 0.8, 4) and ex and ex[0] == "trail" and "المطارِد" in ex[1],
      "٣ من الأمر إلى المركز: الإيقافُ يُعلَّق حتى يرتفع العرضُ ثمّ يُنفَّذ، وأمرُ «اليوم» يُلغى بانتهاء جلسته، والبراكتُ بجنيه ووقفه، والمطارِدُ يرتفع "
      "مع القمّة (1.80 ⇐ 1.44) ويبيع إن هبط الطلبُ إليه", f"{pend0} · نُفّذ {n} · وقفٌ {stop_after} · {ex}")

# ٤ أوامرُ البيع لمركزٍ قائم: بيعٌ محدَّدٌ بسعره، ووقفٌ بسعره، أو مطارِدٌ من قمّته — والبيعُ دون سعر الشراء يُرفض بسببه
pid = br["id"]
p1 = asyncio.run(SQ.set_orders(pid, tp_px=1.60, sl_px=1.00))
p2 = asyncio.run(SQ.set_orders(pid, trail_pct=25))
try:
    asyncio.run(SQ.set_orders(pid, tp_px=1.10))
    low = None
except ValueError as e:
    low = str(e)
check(round(p1["entry_px"] * p1["take_x"], 2) == 1.6 and p1["stop"] == 1.0 and p1["tp_px"] == 1.6 and p2["trail_pct"] == 25 and p2["take_x"] is None
      and p2["stop"] == round(max(p2["peak"], p2["entry_px"]) * 0.75, 4) and low and "أغلق بسعر السوق" in low,
      "٤ أوامرُ البيع لمركزٍ قائم كالوسيط: بيعٌ محدَّدٌ بسعره، ووقفٌ بسعره، أو وقفٌ مطارِدٌ يبدأ من قمّته — والبيعُ المحدَّدُ دون سعر الشراء يُرفض "
      "ويُدلّ على «أغلق بسعر السوق»", f"{p1.get('take_x')} · {p2.get('stop')}")

# ٥ الواجهة: المختبرُ صقرٌ وحده (سوقان) و«عقودُ الخيارات» داخله، والتذكرةُ بالعربية لكلّ خيارٍ سطرٌ يشرحه، والمحفظةُ بالأمر المرفق نفسِه
lab = (ROOT / "frontend/src/pages/ResearchLab.tsx").read_text(encoding="utf-8")
desk = (ROOT / "frontend/src/components/saqr/SaqrDesk.tsx").read_text(encoding="utf-8")
of = (ROOT / "frontend/src/components/saqr/OrderForm.tsx").read_text(encoding="utf-8")
pf = (ROOT / "frontend/src/components/saqr/SaqrPortfolio.tsx").read_text(encoding="utf-8")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
check('data-role="rl-views"' not in lab and "<SaqrDesk />" in lab and "OptionPicks" not in lab and '["options", "عقود الخيارات", Layers]' in desk
      and '{tab === "options" && !sa && <OptionPicks />}' in desk and '!(sa && k === "options")' in desk
      and all(x in of for x in ('["mkt", "سوق"', '["lmt", "محدَّد"', '["stp", "إيقاف"', '["stp_lmt", "إيقافٌ محدَّد"', '["day", "اليوم"', '["gtc", "حتى الإلغاء"',
                                '["none", "لا شيء"', '["tp", "جنيُ ربح"', '["sl", "وقفُ خسارة"', '["trail", "وقفٌ مطارِد"', '["bracket", "براكت"', 'data-role={`${role}-hint`}'))
      and '<ExitFields ex={ex} set={setEx} base={p.entry_px} role="sp-ord" />' in pf and "ordDesc(o)" in pf
      and '**{k: p.get(k) for k in ("otype", "stop", "tif", "tp_px", "sl_px", "trail_pct")}' in mk and 'p.get("tp_px"), p.get("sl_px"), p.get("trail_pct")' in mk,
      "٥ المختبرُ صقرٌ وحده (السوقُ الأمريكيّ · السعوديّ) و«عقودُ الخيارات» تبويبٌ داخله للأمريكيّ؛ والتذكرةُ بالعربية (أنواعٌ أربعة · مدّتان · مرفقٌ خماسيّ) "
      "لكلّ خيارٍ سطرٌ يشرحه، وأوامرُ المركز القائم بالمرفق نفسِه، والنقطتان تمرّران التذكرةَ كاملة")

print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
