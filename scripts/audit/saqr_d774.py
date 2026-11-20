#!/usr/bin/env python3
"""حارسُ D774 — قائمةُ صقر لا تخرج فارغةً لأنها بدأت بالأرقّ عقوداً، وتنمو في الجلسة، وتقول لكلّ سهمٍ سببَ امتناعه.

قيس على الخادم (2026-11-20، الجلسةُ مفتوحة، ‏saqr_list_door.py): «0 عقداً من 45 ورقة — لا عقدَ طويلَ يستوفي الشروط 39 · فوق الميزانية 6».
السببُ الجذريّ: الفحصُ يبدأ بالأرخص سعراً من مجالٍ عامٍّ (602 سهماً) فكان أكثرُ ما فُحص رقيقَ العقود الطويلة، والقائمةُ دفعةٌ واحدةٌ
من 45 لا تتجاوزها، والسببُ مجملٌ لا يُعرف أهو الفارقُ أم السيولةُ أم الهدف. فـ:
  ١ الترتيب: الميسورُ السائلُ أوّلاً (الأسيلُ في «عقود الخيارات» أو تداولٌ يوميٌّ ≥ مئة مليون دولار).
  ٢ السبب: أبعدُ مرحلةٍ بلغها عقدٌ من السهم (الفارق · السيولة · الدلتا · الهدف…) أو غيابُ السلسلة أو الآجال — لكلّ سهمٍ فُحص.
  ٣ النموّ: دفعةٌ جديدةٌ كلَّ نصف ساعةٍ لما لم يُفحص، تُضمّ إلى ما قبلها حتى الخمسين — وصيغةٌ أقدمُ تُعاد بناءً فوراً.

    python3 scripts/audit/saqr_d774.py
"""
import asyncio, os, pathlib, sys, tempfile   # noqa: E401
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


from app.services import saqr_list as SL   # noqa: E402
from app.services import option_picks as OP   # noqa: E402
from app.services import saqr_universe as SU   # noqa: E402
from app.services import live_quote as LQ   # noqa: E402
from app.services import options_chain as OC   # noqa: E402

TR = lambda st, c, strength, traded=0.0: {"state": st, "close": c, "sma50": c * 0.95, "sma200": c * 0.9, "ret3m": 8.0, "strength": strength,   # noqa: E731
                                          "traded": traded}

# ١ الترتيب: الميسورُ السائلُ أوّلاً — ولو كان غيرُه أقوى مساراً
ranked = [("THIN", TR("صاعد", 9.0, 30.0, 4.0)), ("F", TR("صاعد", 11.0, 5.0)), ("LIQ", TR("صاعد", 20.0, 4.0, 250.0)),
          ("BIGLIQ", TR("صاعد", 300.0, 40.0, 900.0)), ("BIG", TR("صاعد", 400.0, 50.0, 10.0))]
o = [s for s, _ in SL.order(ranked, 150.0)]
row = {"close": 20, "SMA50": 19, "SMA200": 18, "EMA20": 19.5, "Perf.3M": 6, "Value.Traded": 2.5e8}
check(o == ["F", "LIQ", "THIN", "BIGLIQ", "BIG"] and SU.tv_trend(row)["traded"] == 250.0,
      "١ الفحصُ يبدأ بالميسور السائلة عقودُه (الأسيلُ أو تداولٌ ≥ مئة مليون دولار)، ثمّ الميسور، ثمّ السائل، ثمّ الباقي — والمُصفّي يحمل قيمةَ التداول",
      f"{o}")

# ٢ السبب: أبعدُ مرحلةٍ بلغها عقدٌ من السهم — هنا العقودُ حول السعر عرضُها وطلبُها حقيقيّان واهتمامُها كافٍ لكنّ فارقَها 26٪
BASE = {"price": 10.0, "name": "Wide", "expirations": [{"dte": 200, "t": 1, "date": "2027-06-18"}]}


def opt(K, bid, ask, oi=500):
    return {"contract": f"W{K}", "strike": K, "bid": bid, "ask": ask, "oi": oi}
CH = {"price": 10.0, "calls": [opt(9, 1.6, 2.1), opt(10, 1.0, 1.3), opt(11, 0.6, 0.8), opt(12, 0.35, 0.47)],
      "puts": [opt(9, 0.5, 0.65), opt(10, 0.9, 1.2), opt(11, 1.5, 1.95)]}


async def fake_chain(sym, t=None):
    if sym == "NONE":
        return None
    if sym == "SHORT":
        return {**BASE, "expirations": [{"dte": 40, "t": 2, "date": "2027-01-01"}]}
    return BASE if t is None else CH
OC.chain = fake_chain
dw, dn, ds = {}, {}, {}
tr = TR("صاعد", 10.0, 5.0)
kw = asyncio.run(OP.contracts_for("WIDE", True, 150, tr, diag=dw))
asyncio.run(OP.contracts_for("NONE", True, 150, tr, diag=dn))
asyncio.run(OP.contracts_for("SHORT", True, 150, tr, diag=ds))
check(kw == (None, None) and OP.STAGES[dw.get("stage", -1)] == "الفارقُ بين العرض والطلب واسع" and dn.get("why") == "لا سلسلةَ عقودٍ من المصدر"
      and "لا آجالَ" in (ds.get("why") or ""),
      "٢ سببُ امتناع كلّ سهمٍ بعينه: أبعدُ مرحلةٍ بلغها عقدٌ منه (هنا الفارق)، أو غيابُ السلسلة، أو غيابُ الآجال الطويلة — لا «لا عقدَ» مجملاً",
      f"{dw} · {dn} · {ds}")

# ٣ النموّ: دفعتان تُضمّان، والثانيةُ تفحص ما لم يُفحص، والأسبابُ لكلّ سهم، و«يُكمل» ما بقي
SYMS = {f"S{i}": TR("صاعد", 10.0, 50.0 - i, 200.0) for i in range(6)}
CARD = lambda s: {"contract": f"{s}C", "type": "call", "strike": 10.0, "expiry": "2027-12-17", "t": 1, "dte": 392, "ask": 1.2, "bid": 1.15,   # noqa: E731
                  "mid": 1.18, "cost": 120.0, "px_src": "ask", "spread_pct": 4.2, "spread_usd": 5, "breakeven": 11.2, "need_pct": 3.0, "target": 15.0,
                  "target_label": "قمّة السنة", "rr": 2.1, "pop": 41.0, "p_touch": 58.0, "delta": 0.62, "iv": 45.0, "oi": 4200, "score": 70.0,
                  "symbol": s, "price": 10.0}
WHY = {"S1": "الفارقُ بين العرض والطلب واسع", "S4": "اهتمامٌ مفتوحٌ قليل"}
seen = []


async def fake_universe():
    return {"tr": SYMS, "fund": {s: (85, "متين") for s in SYMS}, "names": {}, "meta": {}}


async def fake_contracts(sym, call, budget, t, diag=None):
    seen.append(sym)
    if sym in WHY:
        diag["stage"] = OP.STAGES.index(WHY[sym])
        return None, None
    return CARD(sym), None


async def no_news(items):
    return {}


async def open_sess():
    return {"us": {"state": "open"}}
SU.universe, OP.contracts_for, OP.read_news, LQ.sessions = fake_universe, fake_contracts, no_news, open_sess
SL.CANDIDATES = 3
r1 = asyncio.run(SL.build({"per_trade": 150, "sides": "both"}, set()))
b1 = list(seen)
seen.clear()
r2 = asyncio.run(SL.build({"per_trade": 150, "sides": "both"}, set()))
b2 = list(seen)
syms2 = sorted(i["symbol"] for i in r2["items"])
check(b1 == ["S0", "S1", "S2"] and b2 == ["S3", "S4", "S5"] and len(r1["items"]) == 2 and syms2 == ["S0", "S2", "S3", "S5"]
      and r2["excluded"] == {"الفارقُ بين العرض والطلب واسع": 1, "اهتمامٌ مفتوحٌ قليل": 1} and r2["scanned"] == 6 and r1["more"] and not r2["more"],
      "٣ القائمةُ تنمو دفعةً بعد دفعة: الثانيةُ تفحص ما لم يُفحص وتُضمّ إلى الأولى، ولكلّ سهمٍ ممتنعٍ سببُه بعينه، و«يُكمل» حتى يُفحص المجالُ كلُّه",
      f"{b1} → {b2} · {syms2} · {r2['excluded']}")

# ٣ب ميزانيةٌ أخرى تبدأ من جديد (لا تُضمّ عقودُ ميزانيةٍ إلى أخرى)
seen.clear()
r3 = asyncio.run(SL.build({"per_trade": 300, "sides": "both"}, set()))
check(seen == ["S0", "S1", "S2"] and r3["scanned"] == 3 and r3["budget"] == 300,
      "٣ب تغييرُ الميزانية يبدأ القائمةَ من جديد — لا تختلط عقودُ ميزانيتين", f"{seen}")

# ٤ التوقيت: نصفُ ساعةٍ ما بقي ما يُفحص والقائمةُ دون الخمسين، وساعتان إن اكتملت أو فُحص كلُّ شيء، وصيغةٌ أقدمُ تُبنى فوراً
NYZ = __import__("zoneinfo").ZoneInfo("America/New_York")
op = datetime(2026, 11, 20, 9, 30, tzinfo=NYZ)
clk = (op, op + timedelta(hours=6, minutes=30))
at = (op + timedelta(hours=1)).astimezone(timezone.utc).isoformat()
now = op + timedelta(hours=1, minutes=35)
d_more = SL.due(now, clk, {"v": SL.V, "at": at, "items": [1] * 4, "more": True})
d_full = SL.due(now, clk, {"v": SL.V, "at": at, "items": [1] * 50, "more": True})
d_all = SL.due(now, clk, {"v": SL.V, "at": at, "items": [1] * 4, "more": False})
d_legacy = SL.due(now, clk, {"at": at, "items": []})
d_soon = SL.due(op + timedelta(hours=1, minutes=10), clk, {"v": SL.V, "at": at, "items": [], "more": True})
check(d_more == (True, False) and d_full == (False, False) and d_all == (False, False) and d_legacy == (True, False) and d_soon == (False, False),
      "٤ دفعةٌ كلَّ نصف ساعةٍ ما بقي ما لم يُفحص والقائمةُ دون الخمسين (لا كلَّ دورة) · ساعتان إن اكتملت · وقائمةٌ بصيغةٍ أقدمَ تُبنى فوراً",
      f"{d_more} {d_full} {d_all} {d_legacy} {d_soon}")

print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
