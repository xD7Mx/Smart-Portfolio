#!/usr/bin/env python3
"""حارسُ D816 — التقريرُ اليوميُّ كاملٌ بالتطبيق وحده حين يغيب تقريرا الجزيرة والراجحي (بأمر المالك 2026-11-24).

قال المالك: «التقريرُ يستقي معلوماته من الجزيرة والراجحي كمبدأ، ولو حصلت لهما مشكلةٌ يقوم تطبيقُنا بالعمل بنفسه — الأخبارُ المحليةُ
والعالمية وبقيةُ التقرير كاملاً، وكلُّ معلومةٍ فيه يتحمّل مسؤوليتَها التطبيقُ وحده كاحتياطٍ للظروف — مع الحفاظ على شكل التقرير».

  ١ المبدأ: مذكّراتُ البيتين أوّلاً — جدولُ الأسواق الإقليمية والفائدة منهما إن وُجدا، ولا يُسأل البديل.
  ٢ يومٌ بلا تقريرَي البيتين والنموذجُ معطّلٌ كلَّه: العنوانُ من أرقام الجلسة، والأخبارُ المحليةُ والعالمية من الوسائل الموثوقة، وما يعني
    مراكزَنا (خبرُ الشركة بنصّه أو حركتُها ونظرتُنا)، وما يُتابَع (الدعمُ والمقاومة وأحداثُ الأيام القادمة بأسمائها العربية)، والأسواقُ
    الإقليميةُ وسعرُ الفائدة الرسميّ من المسح العامّ — والشهريُّ «—» لا رقمٌ بمعنًى آخر.
  ٣ ولا مصدرَ أصلاً (لا تقريرَ ولا وسيلة): عنوانٌ من الأرقام وما يُتابَع ومراكزُنا — لا تقريرٌ فارغ.
  ٤ الورقةُ بشكلها: الصفحاتُ الأربعُ نفسُها بعناوينها، والأقسامُ ممتلئة — لا «لا أخبار» ولا اسمَ جهةٍ ناشرة.

    python3 scripts/audit/research_desk_d816.py
"""
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp_d816_")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402
from datetime import date, datetime, timedelta, timezone  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import research_desk as RD  # noqa: E402
from app.services import research_paper as RP  # noqa: E402
from app.services import live_quote as LQ  # noqa: E402
from app.services import econ_calendar as EC  # noqa: E402

DAY = date(2026, 11, 25)
tv_calls: list = []


async def fake_tv(market, tickers, cols=None):
    tv_calls.append(list(tickers))
    rows = {"DFM:DFMGI": (6123.4, 0.8, 21.3), "ADX:FADGI": (9876.5, -0.2, 3.1), "QSE:GNRI": (10567.8, 0.4, 2.2), "KSE:BKP": (8901.2, 1.1, 14.0),
            "EGX:EGX30": (41234.5, -0.6, 30.5), "ECONOMICS:SAINTR": (4.5, 0.0, None)}
    return {t: {"close": v[0], "change": v[1], "Perf.YTD": v[2]} for t, v in rows.items() if t in tickers}

LQ.tv_scan = fake_tv
now = datetime.now(timezone.utc)


async def fake_week():
    t = lambda h: (now + timedelta(hours=h)).isoformat()   # noqa: E731
    return [{"title": "FOMC Statement", "country": "USD", "impact": "High", "date": t(30)},
            {"title": "Crude Oil Inventories", "country": "USD", "impact": "Medium", "date": t(20)},
            {"title": "Some Unknown Release", "country": "USD", "impact": "High", "date": t(10)},
            {"title": "Retail Sales m/m", "country": "USD", "impact": "High", "date": (now - timedelta(hours=5)).isoformat()}]

EC.raw_week = fake_week


async def no_ai(*a, **k):
    RD.LAST["why"] = "busy"
    return None

RD._gemini = no_ai


async def fake_sleep(s, *a, **k):
    return None

_sleep0 = asyncio.sleep
PS = [{"symbol": "1120", "name": "مصرف الراجحي", "weight": 30.0, "pnl": 12.0, "price": 98.5, "fv": 110.0, "upside": 11.7, "decision": "احتفاظ"},
      {"symbol": "2222", "name": "أرامكو السعودية", "weight": 40.0, "pnl": -3.0, "price": 25.1, "fv": 30.0, "upside": 19.5, "decision": "شراء"},
      {"symbol": "7010", "name": "الاتصالات السعودية", "weight": 30.0, "pnl": 4.0, "price": 40.2, "fv": 41.0, "upside": 2.0, "decision": "احتفاظ"}]


async def fake_positions(db):
    return [dict(p) for p in PS]

RD._positions = fake_positions


async def no_picks(held):
    return []

RP.picks_for = no_picks
WIRE = [{"key": f"wire:sa:{DAY}", "date": DAY.isoformat(), "source": "وسائلُ اقتصاديةٌ موثوقة", "kind": "أخبارُ اليوم", "title": "أخبار السوق",
         "headline": "", "local_news": ["الراجحي يعلن توزيعَ أرباحٍ نقدية بـ1.25 ريال للسهم — أرقام", "تاسي يغلق مرتفعاً بدعم البنوك — العربية",
                                         "هيئةُ السوق المالية توافق على طرحٍ جديد — مال", "أرامكو توقّع اتفاقيةً للغاز المسال — رويترز"]},
        {"key": f"wire:world:{DAY}", "date": DAY.isoformat(), "source": "وكالاتٌ ووسائلُ اقتصاديةٌ موثوقة", "kind": "أخبارُ اليوم", "title": "الأسواق العالمية",
         "headline": "", "global_news": ["الفيدرالي يثبّت الفائدة — رويترز", "برنت يرتفع 1.2% — الشرق", "الذهب عند مستوى قياسي — CNBC عربية"]}]
wire_on = {"v": True}


async def fake_wire(today, hours=30):
    return [dict(w) for w in WIRE] if wire_on["v"] else []

RD.wire_sources = fake_wire
KNOW = {"notes": [], "read": {}}
RD.knowledge = lambda: KNOW


def market():
    closes = [11000 + (i % 17) * 12 - (i % 5) * 7 + i * 0.8 for i in range(260)]
    bars = [{"date": (DAY - timedelta(days=260 - i)).isoformat(), "open": c - 5, "high": c + 20, "low": c - 25, "close": c, "volume": 2e8} for i, c in enumerate(closes)]
    tech = RP.technicals(bars) or {}
    tech["view"] = "محايد"
    return {"date": DAY.isoformat(), "tasi": {"close": closes[-1], "pct": 0.62}, "breadth": {"value": 5.4e9, "up": 150, "down": 90, "volume": 3e8, "trades": 400000},
            "tech": tech, "daily": [{"d": b["date"], "o": b["open"], "h": b["high"], "l": b["low"], "c": b["close"], "v": b["volume"]} for b in bars], "sectors": [{"name": "البنوك", "pct": 1.1}, {"name": "الطاقة", "pct": -0.3}], "global": [], "commodities": [], "fx": [],
            "rates": [], "actions": [], "fin": {}}


def run(day_market):
    asyncio.sleep = fake_sleep
    try:
        r = asyncio.run(RD.compose_for(None, 1, "المحفظة الرئيسية", day_market, DAY))
    finally:
        asyncio.sleep = _sleep0
    return r


# ── ١ المبدأ: مذكّراتُ البيتين أوّلاً ──
J = {"key": "j25", "date": DAY.isoformat(), "source": "الجزيرة كابيتال", "title": "التقرير اليومي", "kind": "تقرير يوميّ", "headline": "خلاصة",
     "local_news": ["أعلنت شركة سابك عن أرباحٍ بـ2 مليار"], "global_news": ["ارتفع داو جونز 0.5%"], "risks": ["تذبذبُ النفط"],
     "regional": [{"market": m, "close": 1000.0 + i, "d1": 0.1, "mtd": 1.0, "ytd": 5.0} for i, m in enumerate(["السعودية", "دبي", "أبو ظبي", "الكويت", "قطر"])],
     "rates": [{"name": f"سايبور {n}", "value": 5.0, "d1_bp": 1, "mtd_bp": 2, "ytd_bp": 3} for n in ("شهر", "3 أشهر", "6 أشهر")]}
KNOW["notes"] = [J]
tv_calls.clear()
r1 = run(market())
reg1 = (r1.get("regional") or {}).get("rows") or []
check(r1 and len(reg1) >= 4 and reg1[1]["mtd"] == 1.0 and len(r1.get("saibor") or []) == 3 and not tv_calls and r1.get("n_house") == 1,
      "١ المبدأ: الأسواقُ الإقليميةُ وسايبور من تقرير البيت (بشهريّها) — والبديلُ لا يُسأل", f"{len(reg1)} · {len(r1.get('saibor') or [])} · tv={len(tv_calls)}")

# ── ٢ لا تقريرَ من البيتين والنموذجُ معطّل ──
KNOW["notes"] = []
tv_calls.clear()
r2 = run(market())
loc, glo = [x["text"] for x in r2.get("local") or []], [x["text"] for x in r2.get("global") or []]
port = r2.get("portfolio") or []
watch = [x["text"] for x in r2.get("watch") or []]
reg2 = (r2.get("regional") or {}).get("rows") or []
sai2 = r2.get("saibor") or []
check(r2.get("n_house") == 0 and r2.get("text_source") == "notes" and r2.get("headline") and len(loc) == 4 and len(glo) == 3
      and not any(" — رويترز" in t or " — أرقام" in t for t in loc + glo),
      "٢أ بلا تقريرَي البيتين والنموذجُ معطّل: العنوانُ من أرقام الجلسة، والأخبارُ المحليةُ والعالمية من الوسائل الموثوقة بنصّها بلا اسمِ وسيلة",
      f"{r2.get('text_source')} · {len(loc)}/{len(glo)} · {str(r2.get('headline'))[:50]}")
by = {p["symbol"]: p for p in port}
check("1120" in by and "الراجحي" in by["1120"]["text"] and by["1120"]["src"] and by["1120"]["src"][0] >= 1 and "7010" not in by,
      "٢ب ما يعني مراكزَنا: خبرُ اليوم الذي يذكر الشركة بنصّه من مصدره — ولا سطرَ لمركزٍ بلا خبرٍ ولا حركة", str([(p["symbol"], p["text"][:40]) for p in port]))
check(len(watch) >= 2 and any("الدعم الأول" in w and "المقاومة الأولى" in w for w in watch) and any("بتوقيت الرياض" in w for w in watch)
      and not any("Unknown" in w or "Retail" in w for w in watch),
      "٢ج ما يُتابَع: الدعمُ والمقاومةُ الأوليان لتاسي وأحداثُ الأيام القادمة بأسمائها العربية وموعدها — لا حدثٌ مضى ولا اسمٌ إنجليزيّ", " | ".join(w[:50] for w in watch))
check(len(reg2) == 5 and reg2[0]["market"] == "دبي" and all(x["mtd"] is None and x["d1"] is not None and x["ytd"] is not None for x in reg2)
      and (r2.get("regional") or {}).get("self") and len(sai2) == 1 and "البنك المركزي" in sai2[0]["name"] and sai2[0]["value"] == 4.5,
      "٢د الأسواقُ الإقليمية (دبي · أبو ظبي · قطر · الكويت · مصر) وسعرُ الفائدة الرسميّ من المسح العامّ — والشهريُّ «—» لا أداءُ شهرٍ متحرّك",
      f"{[x['market'] for x in reg2]} · {sai2[:1]}")

# ── ٣ لا مصدرَ أصلاً ──
wire_on["v"] = False
r3 = run(market())
check(r3.get("headline") and r3.get("watch") and (r3.get("regional") or {}).get("rows") and r3.get("text_source") == "none",
      "٣ ولا مصدرَ أصلاً: عنوانٌ من الأرقام وما يُتابَع والأسواقُ الإقليمية — لا تقريرٌ فارغ", f"{r3.get('text_source')} · {len(r3.get('watch') or [])}")
wire_on["v"] = True

# ── ٤ الورقةُ بشكلها ──
html = RP.render(r2)
titles = ["التقرير اليومي", "الأخبار والأسواق العالمية", "النظرة الفنية اليومية", "محفظتنا واختياراتنا"]
check(all(t in html for t in titles) and "لا أخبارَ محليةً جديدة" not in html and "لا أخبارَ عالميةً جديدة" not in html and "دبي" in html
      and "سعر إعادة الشراء" in html and "ما يعني مراكزنا اليوم" in html and "للمتابعة" in html and "الجزيرة كابيتال" not in html,
      "٤ الورقةُ بشكلها: الصفحاتُ الأربعُ بعناوينها، والأخبارُ والأسواقُ الإقليميةُ والفائدةُ ومراكزُنا وما يُتابَع ممتلئة — بلا اسمِ جهةٍ ناشرة")

# ── ورقةٌ بأقصى ما تحمله عادةً — يقرؤها حارسُ العرض (‏report_d815.mjs): الجداولُ بصفوفها كلّها وثمانيةَ عشرَ إجراءً ──
OUT = _os.environ.get("SP_PAPER_OUT")
if OUT:
    full = dict(r2)
    mk = full["market"] = dict(full["market"])
    q = lambda n, k: [{"name": f"{k} {i + 1}", "close": 1000.0 + i * 7, "d1": 0.3 - i * 0.05, "mtd": 1.2, "ytd": 4.5} for i in range(n)]   # noqa: E731
    mk.update({"global": q(15, "مؤشّر"), "commodities": q(10, "سلعة"), "fx": q(11, "عملة"), "rates": q(3, "عائد"),
               "sectors": [{"name": f"قطاع {i + 1}", "pct": 1.2 - i * 0.1, "value": 3e8, "weight": 4.0, "pe": 18.0} for i in range(22)],
               "gainers": [{"name": f"رابحة {i}", "price": 20.0, "pct": 4.0} for i in range(5)], "losers": [{"name": f"خاسرة {i}", "price": 20.0, "pct": -3.0} for i in range(5)],
               "heavy": [{"name": f"قيادية {i}", "price": 30.0, "pct": 0.5} for i in range(5)],
               "actions": [{"date": (DAY + timedelta(days=i % 14)).isoformat(), "company": f"شركة اختبار رقم {i + 1} للصناعة", "type": "توزيع أرباح نقدية"}
                           for i in range(18)]})
    full["local"] = [{"text": f"خبرٌ محليٌّ رقم {i + 1} بتفاصيلَ وأرقامٍ عن السوق السعودي والشركات المدرجة اليوم", "src": [1]} for i in range(6)]
    full["global"] = [{"text": f"خبرٌ عالميٌّ رقم {i + 1} عن الأسواق والاقتصاد العالميّ وأثره", "src": [2]} for i in range(5)]
    pathlib.Path(OUT).write_text(RP.render(full), encoding="utf-8")
    print("كُتبت الورقة:", OUT)

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
