#!/usr/bin/env python3
"""حارسُ D720 — درجةُ الجودة المالية تنمّ عن صدق القوائم (بلاغُ المالك 2026-10-14: «أرقامٌ ظالمة»).

قِيس على الخادم (‏finance_score_door · run 38628527640) ثلاثةُ عيوب:
  · نسبةُ المديونية بوحدتين: طبقتا «تداول» تكتبانها ×100 (‏35.21) وياهو كسراً (‏0.29)، ومنحنى الدرجة كسريّ — فقُرئت ‎35٪‎
    «3500٪»، وعُدّت الشركةُ بنكاً (‏> 0.75 بلا تغطية فوائد) فسقطت إشارتا الدين وجودةِ الربح، وصار ربحُ سنةٍ نصفَ الدرجة.
    وجدولُ القوائم يعرض «35.21» بجانب «0.29» في الصفّ نفسِه.
  · ربحُ سنةٍ واحدة ‎35٪‎ من الدرجة: الاتّصالات ‎46‎ بعائدٍ ‎18٪‎ وربحٍ مغطًّى بالنقد ‎1.21‎ لأنّ ربحَ سنةٍ نزل ‎39٪‎.
  · الريتُ يُقرأ كشركةٍ صناعية: عائدُه على الحقوق منخفضٌ بنيةً وربحُه يتقلّب بإعادة التقييم — فالراجحي ريت ‎54‎.

    python3 scripts/audit/finance_quality_d720.py
"""
import os, pathlib, re, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
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


from app.services import scores as SC                                  # noqa: E402
from app.services.statement_merge import debt_fraction                 # noqa: E402

for f in ("backend/app/services/tadawul_xbrl.py", "backend/app/services/tadawul_pdf.py"):
    src = (ROOT / f).read_text(encoding="utf-8")
    check('p["debt_ratio"] = round(tl / ta, 4)' in src and "tl / ta * 100" not in src,
          f"١ ‏{pathlib.Path(f).name} يكتب نسبةَ المديونية كسراً كبقيّة الطبقات")
check(debt_fraction(35.21) == 0.3521 and debt_fraction(0.29) == 0.29 and debt_fraction(1.2) == 1.2 and debt_fraction(None) is None,
      "٢ والمخزَّنُ قبل الإصلاح يُطبَّع عند القراءة: 35.21 ← 0.3521، والكسرُ كما هو (ولو فاق الواحدَ بحقوقٍ سالبة)")
ms = (ROOT / "backend/app/services/statement_merge.py").read_text(encoding="utf-8")
check('p["debt_ratio"] = debt_fraction(p.get("debt_ratio"))' in ms, "٢ب والتطبيعُ في مصبّ الطبقات كلّها (‏complete)")
ft = (ROOT / "frontend/src/components/analysis/FinancialsTable.tsx").read_text(encoding="utf-8")
check('field: "debt_ratio", invert: true, pct: true' in ft and "row.pct ? pctOf(v)" in ft,
      "٣ وجدولُ القوائم يعرضها نسبةً مئويةً واحدةَ الوحدة — لا «35.21» بجانب «0.29»")


def stc(debt):
    """كالاتّصالات: عائدٌ ‎18٪‎، وربحٌ مغطًّى بالنقد، ونموٌّ عبر السنوات ثمّ سنةٌ نزل ربحُها ‎39٪‎، ولا تغطيةَ فوائد منشورة."""
    nis = [10.5, 11.3, 12.2, 13.3, 21.9, 13.3]
    return [{"revenue": 52000 * 1.054 ** i, "net_income": ni * 1000, "operating_cash_flow": ni * 1000 * 1.21,
             "equity": ni * 1000 / 0.181, "debt_ratio": debt} for i, ni in enumerate(nis)]


pct, frac = SC._finance_score_from_periods(stc(45.14)), SC._finance_score_from_periods(stc(0.4514))
check(pct == frac, "٤ الوحدةُ لا تغيّر الدرجة: مديونيةٌ ‎45.14‎ مخزَّنةً قديماً = ‎0.4514‎ — لا تُعدّ الشركةُ بنكاً", f"{pct} = {frac}")
check(frac is not None and frac >= 65,
      "٥ وشركةٌ بعائدٍ ‎18٪‎ وربحٍ مغطًّى بالنقد لا تنزل «متوسطةً» لأنّ ربحَ سنةٍ نزل بعد سنةٍ استثنائيّة", f"{frac} (كانت 46)")


def reit():
    """كالراجحي ريت: دخلُ إيجارٍ ينمو ‎13.5٪‎، وتدفّقٌ تشغيليٌّ ‎60٪‎ من الإيراد، ومديونيةٌ ‎0.29‎، وتغطيةُ فوائد ‎3.9‎،
    وربحٌ محاسبيٌّ نزل ‎21٪‎ بإعادة التقييم، ووحداتٌ أُصدرت لشراء أصول."""
    rev = [260, 300, 345, 380]
    ni = [150, 175, 190, 150]
    return [{"revenue": r * 1e6, "net_income": n * 1e6, "operating_cash_flow": r * 0.6e6, "equity": n * 1e6 / 0.065,
             "debt_ratio": 0.29, "interest_coverage": 3.9, "shares_outstanding": 161e6 if i < 2 else 274e6}
            for i, (r, n) in enumerate(zip(rev, ni))]


r_gen, r_reit = SC._finance_score_from_periods(reit()), SC.reit_finance_score(reit())
check(r_reit is not None and r_reit >= 65 and r_reit > r_gen,
      "٦ والريتُ يُقرأ بما يُقرأ به الريت (دخلُ الإيجار · التدفّقُ التشغيليّ · المديونيةُ دون السقف · التغطية) — لا كشركةٍ صناعية",
      f"مسارُ الريت {r_reit} · العامّ {r_gen}")
fewer = [dict(p, shares_outstanding=161e6) for p in reit()]
check(SC.reit_finance_score(fewer) == r_reit, "٧ وإصدارُ الوحدات لشراء الأصول ليس «تخفيفاً» يُنقص درجةَ الريت")
gs = (ROOT / "backend/app/services/scores.py").read_text(encoding="utf-8")
check('reit_finance_score(periods) if arch == "reit" else _finance_score_from_periods(periods)' in gs,
      "٨ والمنتِجُ الواحد (‏governed_finance_score) يختار مسارَ الريت من نمط «تداول» الرسميّ — فالبطاقةُ والصفحةُ والجدولُ رقمٌ واحد")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
