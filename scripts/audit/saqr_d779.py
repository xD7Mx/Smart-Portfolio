#!/usr/bin/env python3
"""حارسُ D779 — التداولُ الآليُّ يشتري من «عقود الخيارات» (2026-11-20).

قال المالك: «خلِّ التداولَ الآليَّ يشتري من عقود الخيارات». فالصيدُ الآليُّ يقرأ دفترَ التوصيات القائمة نفسَه الذي يراه المالك في «عقود الخيارات»
(دفترُ ميزانية العقد عند صقر، وإلا أكبرُ دفترٍ دونها)، الأعلى درجةً أوّلاً؛ ولا فحصَ لـ«قائمة صقر» في الخلفية بعد اليوم (لا قارئَ لها)؛ والدفترُ
اليوميُّ يشمل ميزانيةَ صقر وإن لم يفتحها المالك.

    python3 scripts/audit/saqr_d779.py
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
from app.services import option_picks as OP   # noqa: E402


def rec(sym, typ="call", score=60.0, strike=10.0):
    return {"contract": f"{sym}271217{'C' if typ == 'call' else 'P'}000{int(strike * 1000):05d}", "symbol": sym, "name": sym, "type": typ, "strike": strike,
            "expiry": "2027-12-17", "t": 1, "opened": "2026-11-18", "target": 15.0, "target_label": "قمّة السنة",
            "card": {"score": score, "delta": 0.6, "iv": 40.0, "reasons": [f"سببُ {sym}"]}}


# ١ أيُّ دفتر: ميزانيةُ العقد نفسُها، وإلا أكبرُ دفترٍ دونها، ولا شيءَ إن لم يكن دونها دفتر — والأعلى درجةً أوّلاً
OP.book_save(100, {"open": [rec("AAA", score=50)], "closed": []})
OP.book_save(150, {"open": [rec("LOW", score=40), rec("TOP", score=80), rec("PUT", "put", score=95)], "closed": []})
b150, r150 = SQ.book_for(150)
b200, _ = SQ.book_for(200)
b120, _ = SQ.book_for(120)
b50, r50 = SQ.book_for(50)
check(b150 == 150 and [r["symbol"] for r in r150] == ["PUT", "TOP", "LOW"] and b200 == 150 and b120 == 100 and b50 is None and r50 == [],
      "١ التداولُ الآليُّ يقرأ دفترَ «عقود الخيارات» لميزانية العقد (150 ⇐ 150 · 200 ⇐ 150 · 120 ⇐ 100 · 50 ⇐ لا دفتر) — والأعلى درجةً أوّلاً",
      f"{b150} {b200} {b120} {b50}")

# ٢ الشراء: الأعلى درجةً، والشراءُ وحده يتخطّى البيع، وما في المحفظة لا يُكرَّر — بعرضه الحيّ وبوقف المالك وجنيه، وسببُه من التوصية
Q = {"ask": 1.20}


async def fake_q(c):
    from app.services.options_chain import parse_option
    return {"o": parse_option(c), "t": 1, "dte": 392, "ask": Q["ask"], "bid": Q["ask"] - 0.05, "live": True, "price": 12.0, "name": "X"}
SQ.contract_quote = fake_q
st = SQ.fresh(capital=1000)
SQ.apply_settings(st, {"auto": True, "sides": "calls", "per_trade": 150, "opt_stop": 40, "take_x": 2})
p1 = asyncio.run(SQ._hunt(st, SQ._now()))
p2 = asyncio.run(SQ._hunt(st, SQ._now()))
st2 = SQ.fresh(capital=1000)
SQ.apply_settings(st2, {"auto": True, "sides": "both", "per_trade": 150})
p3 = asyncio.run(SQ._hunt(st2, SQ._now()))
check(p1 and p1["symbol"] == "TOP" and p1["entry_px"] == 1.2 and p1["stop"] == round(1.2 * 0.6, 4) and p1["take_x"] == 2 and "من «عقود الخيارات»" in p1["why"][0]
      and "سببُ TOP" in p1["why"] and p2 and p2["symbol"] == "LOW" and p3 and p3["symbol"] == "PUT",
      "٢ يشتري الأعلى درجةً (‏TOP)، و«الشراءُ وحده» يتخطّى البيعَ الأعلى، ولا يكرّر سهماً في المحفظة (ثمّ ‏LOW) — بعرضه الحيّ ووقف المالك وجنيه، "
      "وسببُه من التوصية نفسِها", f"{p1 and p1['symbol']} · {p2 and p2['symbol']} · {p3 and p3['symbol']}")

# ٣ لا فحصَ للقائمة في الخلفية، والدفترُ اليوميُّ يشمل ميزانيةَ صقر
src = (ROOT / "backend/app/services/saqr_trader.py").read_text(encoding="utf-8")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
job = sch[sch.index("async def job_option_book("):sch.index("async def job_saqr_cycle(")]
check("SL.kick(" not in src and "SL.kick_track(" not in src and 'SQ.cfg(SQ.load("us")).get("per_trade")' in job and "set(OP.book_budgets() or [150])" in job,
      "٣ لا فحصَ لـ«قائمة صقر» في الخلفية (لا قارئَ لها — حِملٌ بلا فائدة)، ودفترُ «عقود الخيارات» اليوميُّ يشمل ميزانيةَ العقد عند صقر")

print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
