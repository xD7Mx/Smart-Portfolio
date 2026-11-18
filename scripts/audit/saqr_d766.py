#!/usr/bin/env python3
"""حارسُ D766 — صقر يغطّي السوقَ الأمريكيّ كلَّه، والأساسُ قبل الفنّ (بأمر المالك 2026-11-18).

«يجب أن تكون التغطيةُ كاملة، ويختار شركاتٍ ذاتَ أساسٍ ماليٍّ ممتاز — ليست ركيكةً أو عليها شطبٌ أو مشاكل — لأنّ التحليلَ الفنيَّ يجب أن يكون
بعد التحليل الأساسيّ». يُفحص على الدوالّ نفسِها بلا شبكة: توحيدُ الرموز بين المصادر، والفرزُ الأساسيّ بأسبابه (الشطبُ والحجمُ والضيقُ
والمتانةُ والخسارةُ المحترقة والدينُ والسيولةُ والصندوقُ المرفوع) ودرجةُ المتانة، والمسارُ من حقول المُصفّي، والمجالُ = دليلُ سيبوي ∩ السوقُ
السائل بأعداد المستبعَد، وأنّ الصيدَ يقرأ المجالَ الكامل ويكتب الأساسَ في مبرّر الصفقة.

    python3 scripts/audit/saqr_d766.py
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


from app.services import saqr_universe as SU   # noqa: E402

check(SU.canon("BRK.B") == SU.canon("BRK/B") == SU.canon("brk-b") == "BRK-B",
      "١ الرمزُ واحدُ الصيغة بين سيبوي وTradingView وياهو (‏BRK.B · BRK/B ⇐ BRK-B)")

# ٢ الفرزُ الأساسيّ — بأرقامٍ قيست على الخادم (آبل وفورد)
STRONG = {"type": "stock", "subtype": "common", "is_primary": True, "close": 353.0, "market_cap_basic": 5.1e12, "sector": "Electronic Technology",
          "altman_z_score_ttm": 12.7, "piotroski_f_score_ttm": 9, "net_income_ttm": 1.3e11, "free_cash_flow_ttm": 1.36e11, "debt_to_equity": 0.77,
          "current_ratio": 1.02, "return_on_equity": 142, "total_revenue_yoy_growth_ttm": 15}
FORD = {"type": "stock", "subtype": "common", "is_primary": True, "close": 11.35, "market_cap_basic": 4.5e10, "sector": "Consumer Durables",
        "altman_z_score_ttm": 0.95, "piotroski_f_score_ttm": 3, "net_income_ttm": -7.8e9, "free_cash_flow_ttm": 5.1e9, "debt_to_equity": 4.48, "current_ratio": 1.08}
cases = {
    "متين": SU.fundamentals(STRONG),
    "ضيق": SU.fundamentals(FORD),
    "شطب": SU.fundamentals({**STRONG, "close": 3.2}),
    "صغير": SU.fundamentals({**STRONG, "market_cap_basic": 8e8}),
    "ضعيف": SU.fundamentals({**STRONG, "piotroski_f_score_ttm": 2}),
    "محترق": SU.fundamentals({**STRONG, "net_income_ttm": -1e8, "free_cash_flow_ttm": -2e8}),
    "دين": SU.fundamentals({**STRONG, "debt_to_equity": 5.2}),
    "حقوق سالبة": SU.fundamentals({**STRONG, "debt_to_equity": -3.0}),
    "سيولة": SU.fundamentals({**STRONG, "current_ratio": 0.5}),
    "ممتاز سهم": SU.fundamentals({**STRONG, "subtype": "preferred"}),
    "ثانويّ": SU.fundamentals({**STRONG, "is_primary": False}),
    "دون الممتاز": SU.fundamentals({**STRONG, "piotroski_f_score_ttm": 5, "altman_z_score_ttm": 2.0, "return_on_equity": 4, "free_cash_flow_ttm": -1,
                                    "total_revenue_yoy_growth_ttm": -3}),
    "بنك": SU.fundamentals({**STRONG, "sector": "Finance", "altman_z_score_ttm": 0.2, "debt_to_equity": 9.0, "current_ratio": None, "piotroski_f_score_ttm": 7}),
    "صندوق": SU.fundamentals({"type": "fund", "subtype": "etf", "close": 590.0, "description": "SPDR S&P 500 ETF Trust"}),
    "مرفوع": SU.fundamentals({"type": "fund", "subtype": "etf", "close": 70.0, "description": "ProShares UltraPro QQQ 3x Shares"}),
    "مغلق": SU.fundamentals({"type": "fund", "subtype": "closedend", "close": 12.0, "description": "Income Fund"}),
}
want = {"متين": True, "ضيق": False, "شطب": False, "صغير": False, "ضعيف": False, "محترق": False, "دين": False, "حقوق سالبة": False, "سيولة": False,
        "ممتاز سهم": False, "ثانويّ": False, "دون الممتاز": False, "بنك": True, "صندوق": True, "مرفوع": False, "مغلق": False}
bad = [k for k, v in want.items() if cases[k][0] is not v]
check(not bad and cases["متين"][1] == 100 and "Altman" in cases["ضيق"][2] and "الشطب" in cases["شطب"][2] and "Piotroski" in cases["ضعيف"][2],
      "٢ الأساسُ قبل الفنّ: يُقبل المتين (آبل 100/100) والصندوقُ المتداول والبنكُ بمقاييسه، ويُستبعد بسببه: فورد (ضيقٌ ماليّ Altman ‏0.95)، "
      "وما دون 5 دولارات (الشطب)، والصغير، وضعيفُ المتانة، والخاسرُ المحترقُ للنقد، والمثقلُ بالدين، وسالبُ الحقوق، وضعيفُ السيولة، والممتازُ "
      "والثانويّ، وما دون درجة 60، والصندوقُ المرفوعُ والمغلق", f"خطأ في: {bad}" if bad else " · ".join(f"{k}:{'✓' if v[0] else '✗'}" for k, v in cases.items()))

# ٣ المسارُ من حقول المُصفّي
ROW = {"close": 353.0, "SMA50": 341.0, "SMA200": 302.0, "EMA20": 348.0, "Perf.3M": 11.3, "price_52_week_high": 360.0, "price_52_week_low": 243.0,
       "High.3M": 360.0, "Low.3M": 307.0, "High.6M": 360.0, "Low.6M": 273.0}
up = SU.tv_trend(ROW)
dn = SU.tv_trend({**ROW, "close": 151.5, "SMA50": 190.0, "SMA200": 205.0, "EMA20": 175.0, "Perf.3M": -30.6})
nvda = SU.tv_trend({**ROW, "close": 151.5, "SMA50": 210.3, "SMA200": 203.7, "EMA20": 183.1, "Perf.3M": -30.6})   # قيس على الخادم 2026-11-18
pull = SU.tv_trend({**ROW, "close": 336.0})                                                                     # ارتدادٌ دون 50 فوق 200
flat = SU.tv_trend({**ROW, "SMA50": 303.0, "SMA200": 302.0})
keys = {"close", "sma50", "sma200", "slope50", "ret3m", "hi52", "lo52", "hi60", "lo60", "hi120", "lo120", "state", "strength"}
check(up["state"] == "صاعد" and dn["state"] == "هابط" and nvda["state"] == "عرضي" and pull["state"] == "صاعد" and flat["state"] == "عرضي"
      and keys <= set(up) and up["hi60"] == 360.0 and up["lo120"] == 273.0 and SU.tv_trend({"close": 1}) is None,
      "٣ المسارُ من حقول المُصفّي بقاعدة مسار التطبيق نفسِها (المتوسّطان بفرقٍ فوق 1٪ والميلُ والإغلاقُ على جهة 200 — والارتدادُ دون 50 لا يلغيه؛ "
      "وإنفيديا قيس: 50 فوق 200 فعرضيٌّ بعدُ لا هابط)، وقممُ 3 و6 أشهر والسنة للهدف — بلا شموعٍ لكلّ رمز",
      f"{up['state']} {dn['state']} {nvda['state']} {pull['state']} {flat['state']}")

# ٤ المجال = دليلُ سيبوي ∩ السوقُ السائل، بأعداد المستبعَد
async def uni(cboe):
    async def fake_cboe():
        return cboe

    async def fake_tv():
        return [{**STRONG, **ROW, "name": "AAPL", "description": "Apple"}, {**FORD, **ROW, "close": 11.35, "name": "F"},
                {**STRONG, **ROW, "name": "BRK.B", "description": "Berkshire"}, {**STRONG, **ROW, "name": "NOOPT"},
                {"type": "fund", "subtype": "etf", "description": "SPDR S&P 500", "name": "SPY", **ROW}]
    o1, o2 = SU.cboe_symbols, SU.tv_market
    SU.cboe_symbols, SU.tv_market = fake_cboe, fake_tv
    try:
        return await SU.universe()
    finally:
        SU.cboe_symbols, SU.tv_market = o1, o2
U = asyncio.run(uni({"AAPL", "F", "BRK-B", "SPY"}))
U2 = asyncio.run(uni(None))
check(set(U["tr"]) == {"AAPL", "BRK-B", "SPY"} and U["meta"]["optionable"] == 4 and U["meta"]["passed"] == 3 and U["meta"]["market"] == 5
      and sum(U["meta"]["excluded"].values()) == 1 and "NOOPT" not in U["tr"] and U["fund"]["AAPL"][0] == 100 and "NOOPT" in U2["tr"] and U2["meta"]["cboe"] is None,
      "٤ المجالُ كلُّ ورقةٍ في دليل سيبوي (لها عقودُ خيارات) وسائلة، والأساسُ قبلها — ومعه أعدادُ المستبعَد بأسبابه؛ وإن تعذّر الدليلُ فالسوقُ "
      "السائلُ كلُّه (والعقدُ يُتحقَّق منه في الفحص العميق)", f"{sorted(U['tr'])} · {U['meta']['excluded']}")

# ٥ الصيدُ يقرأ المجالَ الكامل ويكتب الأساسَ في المبرّر، والمراجعةُ تقرأ مسارَه
src = (ROOT / "backend/app/services/saqr_trader.py").read_text(encoding="utf-8")
hunt = src[src.index("async def _hunt("):src.index("async def cycle(")]
check("await SU.universe()" in hunt and 'why.insert(0, f"الأساس: {fund[' in hunt and hunt.count("الأساس:") >= 2 and '"full": umeta' in hunt
      and 'cache.get(f"saqr:tr:{p[\'symbol\']}") or' in src,
      "٥ الصيدُ يقرأ المجالَ الكامل (لا القائمةَ المحدودة إلا احتياطاً موسوماً)، ويكتب سببَ الأساس أوّلَ مبرّر الصفقة — عقداً أو سهماً — ومراجعةُ "
      "المراكز تقرأ مسارَ المجال")

# ٦ المصادرُ مقيسة: الدليلُ والحقول
door = (ROOT / "scripts/audit/us_universe_door.py").read_text(encoding="utf-8")
check(SU.CBOE_URL in door and all(f in door for f in ("piotroski_f_score_ttm", "altman_z_score_ttm", "debt_to_equity", "current_ratio", "free_cash_flow_ttm"))
      and all(f in SU.COLS for f in ("piotroski_f_score_ttm", "altman_z_score_ttm", "debt_to_equity", "current_ratio", "net_income_ttm", "free_cash_flow_ttm")),
      "٦ المصدران مقيسان على الخادم بكاشفهما (دليلُ سيبوي وحقولُ المُصفّي الأساسية) قبل أن يُبنى عليهما")

# ٧ اللوحة تقول المجالَ الكاملَ وأسبابَ الاستبعاد، والقواعدُ تقول الأساسَ قبل الفنّ
desk = (ROOT / "frontend/src/components/saqr/SaqrDesk.tsx").read_text(encoding="utf-8")
check("لها عقودُ خيارات (من دليل سيبوي)" in desk and 'data-role="sq-fund"' in desk and "الأساسُ قبل الفنّ" in desk and "Altman دون 1.81" in desk,
      "٧ لوحةُ صقر تقول كم ورقةً لها عقودُ خيارات قرأ وكم اجتاز الأساس، وأعدادَ المستبعَد بأسبابه، والقواعدُ تقول الأساسَ قبل الفنّ")

print("\nالنتيجة:", "عطب ✖" if fail else "نظيف ✔")
sys.exit(fail)
