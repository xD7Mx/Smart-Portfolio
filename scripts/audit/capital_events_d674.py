#!/usr/bin/env python3
"""حارسُ D674 — عددُ الأسهم يُحكم بنوع حدث رأس المال وتاريخه من إفصاحات «تداول»، لا بنسبة الفرق وحدها.

قِيس (‏run 38419547711 · ‏capital_events_door run 38437807275): 15 شركةً يخالف عددُ قوائمها السوقَ بين 15٪ ومرّةٍ ونصف؛ منها منحٌ بعد
القوائم (دله)، ومنحٌ قديمةٌ سبقتها بسنوات (المتقدمة 2022 · الجزيرة تكافل 2023) فليست سببَ الفرق، واكتتاباتٌ أدخلت نقداً (ميدغلف ·
سلامة · الصقر)، وتخفيضٌ لإطفاء خسائر (المجموعة السعودية). وقاعدةُ النسبة (منحةٌ معياريّة ±1٪) سوّت القديمةَ وفاتتها غيرُ المعياريّة،
وسقطت في حارس التجميد. فالحارسُ يمنع العودة — سلوكاً على دالّة المدخلات نفسِها (‏gather) لا قراءةَ نصّ:
  · المصنِّفُ يقرأ عناوينَ «تداول» الحقيقية: منحةٌ · زيادةٌ بمقابل · تخفيض — وإعلانُ الإقرار يرث نوعَ توصيته.
  · الحدثُ النافذُ وحده (نتائجُ الجمعية · التخصيص · الكسور) — لا التوصيةُ ولا الطلب.
  · منحةٌ بعد آخر قوائم ⇒ عددُ السوق ويُعلَن؛ زيادةٌ بمقابل بعدها ⇒ لا رقم (ولا احتياطَ يملؤه)؛ حدثٌ قبلها ⇒ عددُ القوائم.
  · ولا حدثَ ⇒ الحَكَمُ القديم كما هو، ولا تُضاعَف منحةٌ سجّلها كاشفُ الأسهم المصدرة.
  · والاختبارُ التاريخيّ لا يرى أحداثَ اليوم، والحصّادُ يعمل ليلاً بتمهّل.

    python3 scripts/audit/capital_events_d674.py
"""
import asyncio, os, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))

fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


try:
    from app.services import capital_events as CE
except ImportError as e:
    check(False, "٠ وحدةُ أحداث رأس المال موجودة", str(e))
    print("\nالنتيجة: عطب ✖")
    sys.exit(1)

# عناوينُ «تداول» كما وصلت في الكاشف (‏run 38437807275)
REAL = {
    "Al Hassan Ghazi Ibrahim Shaker Co. Announces the Board’s Recommendation to Increase the Capital by Granting Bouns Shares": "bonus",
    "Al Hassan Ghazi Ibrahim Shaker Co. announces the deposit of the amounts from selling the shares fractions resulted from the company’s capital Increase": "bonus",
    "Al Hassan Ghazi Ibrahim Shaker Co. Announces updates on Increase of the Company’s Capital by Offering Right Issues File at CMA": "paid",
    "Saudi Industrial Investment Group Announces Appointment of a Financial Advisor for Capital Decrease": "reduction",
    "Rabigh Refining and Petrochemical Company (“Petro Rabigh”) announces the board’s recommendation to increase its capital through issuing and privately placing": "paid",
    "Dallah Healthcare Company announces the publication of the shareholders circular in relation to Dallah’s capital increase for the purpose of acquiring": "paid",
    "Riyadh Development Company announces the signing of an acquisition agreement of two real estate assets worth SAR 1.4 Billion by means of a capital increase": "paid",
    "Salama Cooperative Insurance Co. Announces the Results of Remaining Offering and the Allotment of Right Issues": "paid",
    "Dallah Healthcare Company Announces the Results of the Extraordinary General Assembly’s Meeting Which Includes Approving Capital Increase (First Meeting)": "increase",
    "Saudi Vitrified Clay Pipes Company Announces the Board of Directors’ Recommendation to Reduce the Company’s Share Capital": "reduction",
    "Al Rajhi Bank announces the distribution of cash dividends for the first half of 2026": None,
}
bad = [(t[:50], k, CE.classify(t)) for t, k in REAL.items() if CE.classify(t) != k]
check(not bad, "١ المصنِّفُ يقرأ عناوينَ «تداول» الحقيقية: منحةٌ · زيادةٌ بمقابل · تخفيض — والتوزيعُ ليس حدثَ رأس مال", str(bad))
dallah = CE.resolve([{"k": "paid", "d": "2025-02-20"}, {"k": "bonus", "d": "2026-03-04"}, {"k": "increase", "d": "2026-08-31"}])
check([e["k"] for e in dallah] == ["paid", "bonus", "bonus"],
      "٢ وإعلانُ الإقرار يرث نوعَ أقرب توصيةٍ قبله (دله: منحةُ 2026 لا استحواذُ 2025)", str(dallah))

from app.services import lastgood, fair_value_models as F
from app.services import tadawul_market as TM, tadawul_xbrl as XB, split_watch as SW, tadawul_financials as TF
from app.services import results_announcements as RA, tadawul_dividends as TD, cache as C

STMT, MKT = 100e6, 125e6       # القوائمُ 100 مليون سهم والسوقُ 125 (فرق 25٪ — دون حدّ المرّة والنصف)
PRICE = 20.0
ANNUAL = [{"year": str(y), "as_of": f"{y}-12-31", "revenue": 2e9 * 1.05 ** k, "net_income": 2e8 * 1.05 ** k,
           "eps": 2e8 * 1.05 ** k / STMT, "equity": 2e9, "total_debt": 3e8, "ending_cash": 2e8, "total_assets": 4e9,
           "operating_cash_flow": 2.5e8, "capex": -8e7, "free_cash_flow": 1.7e8, "ebit": 2.6e8}
          for k, y in enumerate(range(2021, 2026))]
LAST = "2025-12-31"
F._peer_yields = lambda *a, **k: asyncio.sleep(0, result={})
F._hist_multiples = lambda *a, **k: asyncio.sleep(0, result={})
TD.read = lambda *a, **k: asyncio.sleep(0, result={})
TF.page_pe = lambda *a, **k: None
TF.issued_shares = lambda *a, **k: None
RA.latest = lambda *a, **k: None
XB.for_symbol = lambda s, kind="annual": [dict(p) for p in ANNUAL] if kind == "annual" else []


def run(events, mkt=MKT, ledger=None):
    C.clear() if hasattr(C, "clear") else None
    TM.usable_rows = lambda *a, **k: ({"9999": {"price": PRICE, "market_cap": mkt * PRICE, "sector_en": "Test"}}, None)
    lastgood.save(CE.STORE, {"9999": {"h": "2026-10-14", "ev": events}})
    lastgood.save(SW.LEDGER, {"9999": ledger or []})
    return asyncio.run(F.gather("9999"))


i = run([{"k": "bonus", "d": "2026-04-20", "t": "Maharah Human Resources Company announces the deposit of the proceeds from the sale of fractional shares resulting from the capital increase"}])
check(i and abs(i.shares - MKT) < 1 and any("منحةٌ أو تجزئة" in n and "إفصاحات «تداول»" in n for n in i.notes),
      "٣ منحةٌ بعد آخر قوائم ⇒ عددُ السوق ويُعلَن بتاريخها ومصدرها", f"{i and i.shares / 1e6:.1f} مليون")
i = run([{"k": "bonus", "d": "2022-04-17", "t": "Maharah Human Resources Company announces the deposit of the proceeds from the sale of fractional shares resulting from the capital increase"}])
check(i and abs(i.shares - STMT) < 1 and not i.capital_pending,
      "٤ ومنحةٌ قبل القوائم ليست سببَ الفرق ⇒ عددُ القوائم (المتقدمة 2022 · الجزيرة تكافل 2023)", f"{i and i.shares / 1e6:.1f} مليون")
i = run([{"k": "paid", "d": "2026-05-10", "t": "Naseej International Trading Company Announces the Results of Rump Offering and the Allocation of the Right Issues"}])
r = F.value(i) if i else {}
b = F.blend(dict(r), {"value": 30.0, "low": 25.0, "high": 35.0}, i.archetype if i else None, 0.03) if i else {}
check(i and i.capital_pending and r.get("value") is None and r.get("capital_pending") and "بمقابل" in str(r.get("reason"))
      and b.get("value") is None,
      "٥ وزيادةٌ بمقابل بعدها ⇒ لا رقمَ حتى تُنشر قوائمُ تشملها — ولا يملؤه المحرّكُ الاحتياطيّ", str(r.get("reason"))[:90])
src = open(os.path.join(ROOT, "backend/app/services/analysis.py"), encoding="utf-8").read()
check('_new.get("capital_pending")' in src, "٦ والصفحةُ لا تملأ الامتناعَ برقم الاحتياطيّ كذلك")
i = run([], mkt=STMT * 1.6)
check(i and abs(i.shares - STMT * 1.6) < 1, "٧ ولا حدثَ ⇒ الحَكَمُ القديم كما هو (فرقٌ فوق المرّة والنصف يأخذ عددَ السوق)")
i = run([], mkt=MKT)
check(i and abs(i.shares - STMT) < 1, "٨ ولا حدثَ وفرقٌ دونها ⇒ عددُ القوائم كما كان")
i = run([{"k": "bonus", "d": "2026-04-20", "t": "Maharah Human Resources Company announces the deposit of the proceeds from the sale of fractional shares resulting from the capital increase"}], ledger=[{"d": "2026-04-21", "f": 1.25}])
check(i and abs(i.shares - MKT) < 1, "٩ ومنحةٌ سجّلها كاشفُ الأسهم المصدرة لا تُضاعَف (‏D621 بعد التصحيح)", f"{i and i.shares / 1e6:.1f} مليون")

# ‏الحصادُ الأوّل (run 38491266548): «ميثانول» و«البحر الأحمر» حُجبتا بطلب حقوق أولويةٍ لم يُنفَّذ — والمعلَنُ لا يغيّر عدداً
i = run([{"k": "paid", "d": "2026-09-30", "t": "Methanol Chemicals Co. Announces the Submission of the Increase of the Company’s Capital "
                                              "by Offering Right Issues Application File to CMA"},
         {"k": "bonus", "d": "2026-08-01", "t": "Al Hassan Ghazi Ibrahim Shaker Co. Announces the Board’s Recommendation to Increase "
                                               "the Capital by Granting Bouns Shares"}])
check(i and not i.capital_pending and abs(i.shares - STMT) < 1,
      "٩ب والحدثُ المعلَنُ الذي لم يُنفَّذ (طلبٌ · توصية) لا يحجب الرقمَ ولا يغيّر العدد — النافذُ وحده (نتائجُ الجمعية · التخصيص · الكسور)",
      f"{i and i.capital_pending}")
bt = open(os.path.join(ROOT, "scripts/audit/fv_backtest_d699.py"), encoding="utf-8").read()
check("_CE.kind_after = lambda *a, **k: None" in bt, "١٠ والاختبارُ التاريخيّ لا يرى أحداثَ اليوم (ما كان معلوماً يومها وحده)")
sch = open(os.path.join(ROOT, "backend/app/scheduler/scheduler.py"), encoding="utf-8").read()
check("from app.services.capital_events import harvest" in sch and "harvest(limit=60)" in sch,
      "١١ والحصّادُ ليليٌّ بتمهّل: ستون شركةً في الليلة، والسوقُ كلُّه أسبوعياً")
sys.path.insert(0, os.path.join(ROOT, "scripts/audit"))
import engine_freeze_d635 as FZ
from app.services import engine_identity as EI
_rel = "backend/app/services/capital_events.py"
check(any(f.relative_to(FZ.ROOT).as_posix() == _rel for f in FZ.FILES) and _rel in EI.FILES
      and _rel in getattr(FZ, "LATER", ()) and _rel in getattr(EI, "LATER", ()) and FZ.fingerprint() == EI.fingerprint(),
      "١٢ وأحداثُ رأس المال في بصمة المحرّك (تعديلُها يمرّ بحارس التجميد) — وغيابُها في شيفرة الأساس لا يغيّر هويّتها")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
