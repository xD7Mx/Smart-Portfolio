#!/usr/bin/env python3
"""حارسُ D674 — عددُ الأسهم يُسوّى بالسوق دون المرّة ونصف حين تشهد القوائمُ بمنحة: نسبةٌ معياريّةٌ وحقوقٌ لم تقفز.

قِيس (‏d674_shares_door · run 38419547711) خمسَ عشرةَ شركةً بين 15٪ ومرّةٍ ونصف: منحٌ (الرمز ×1.429 = 10/7 · دله ×1.248)،
واكتتاباتٌ أدخلت نقداً (ميدغلف الحقوقُ +51.8٪ · بترو رابغ +18.4٪ · الدرع العربي +24.5٪)، وفرقُ تعريف ربحٍ (سابك ×1.367 والحقوقُ
ثابتة — تسويتُه تُنقص سعرَها العادل 27٪ بلا سبب). ولا إعلانَ يحمل ربحيةَ السهم لأيٍّ منها. فيُحاكى كلٌّ بأرقامه المقيسة.

    python3 scripts/audit/d674_bonus.py
"""
import os, pathlib, sys, tempfile
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


from app.services import fair_value_models as M   # noqa: E402
msc = M.market_shares_check


def run(st, mkt, g):
    n = []
    try:
        s = msc(st, mkt * 10.0, 10.0, n, equity_growth=g)
    except TypeError:                                              # قبل D674: لا شاهدَ حقوق
        s = msc(st, mkt * 10.0, 10.0, n)
    return s, n


s, n = run(30.0e6, 42.857e6, -0.026)
check(abs(s - 42.857e6) < 1e3 and n, "١ الرمز: نسبةُ منحةٍ معياريّة (10/7) والحقوقُ لم تقفز ⇒ عددُ السوق ويُعلَن", f"{s/1e6:.1f}م")
s, n = run(97.7e6, 121.89e6, 0.005)
check(abs(s - 121.89e6) < 1e3 and n, "٢ دله: ×1.248 قريبٌ من 1.25 (±1٪) والحقوقُ ثابتة ⇒ عددُ السوق", f"{s/1e6:.1f}م")
s, n = run(2194.8e6, 3000e6, -0.003)
check(s == 2194.8e6 and not n, "٣ سابك: ×1.367 لا نسبةَ منحةٍ معياريّة — فرقُ تعريفِ ربحٍ لا يُسوّى (وإلّا نقص سعرُها 27٪)", f"{s/1e6:.1f}م")
s, n = run(104.8e6, 138.16e6, 0.518)
check(s == 104.8e6 and not n, "٤ ميدغلف: ×1.318 والحقوقُ +51.8٪ — اكتتابٌ أدخل نقداً لا يُعامَل منحةً")
s, n = run(59.8e6, 79.82e6, 0.245)
check(s == 59.8e6 and not n, "٥ الدرع العربي: ×1.334 قريبٌ من 4/3 لكنّ الحقوقَ +24.5٪ — اكتتابٌ لا منحة")
s, n = run(100e6, 112e6, 0.0)
check(s == 100e6 and not n, "٦ ودون 15٪ لا يُمَسّ شيء")
s, n = run(25e6, 250e6, 0.0)
check(abs(s - 250e6) < 1e3 and n, "٧ وما فوق المرّة ونصف يُسوّى كما كان (‏D594 — المتحدة الدولية عشراً)")
src = (ROOT / "backend/app/services/fair_value_models.py").read_text(encoding="utf-8")
check("equity_growth=equity_growth_of(quarterly, annual)" in src and "if _f > 1 and shares and _sh0 and shares == _sh0:" in src
      and 'f"fvm:v42:{sym}"' in src,
      "٨ وشاهدُ الحقوق من آخر فترتين في القوائم، ولا تُضرب المنحةُ مرّتين بسجلّ التجزئة (‏D621)، والكاشُ v42 يُجدَّد")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
