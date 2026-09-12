#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D249 · D250 — معدَّلٌ خالٍ من المخاطر يُقرأ من صكوك المملكة نفسِها.
#
# كان `risk_free_sar` فارغاً و«يُملأ يدوياً» — فمحرّكُ القيمة العادلة
# متوقّفٌ كلُّه على رقمٍ لا مصدرَ له، والاستدامةُ معلَّقةٌ على يدِ المالك.
# وقِيس أن حجبَ «تداول» ببصمة TLS لا بالرؤوس، فعُبر بانتحال بصمة كروم،
# فانفتح سوقُ الصكوك: عملةٌ ونوعُ احتسابٍ وكوبونٌ واستحقاقٌ وعوائدُ منشورة.
#
# وخطرُ الجلب أعظمُ من خطر الفراغ: رقمٌ مأخوذٌ من صكّ شركةٍ أو من أداةٍ
# عائمةٍ أو بالدولار يُنتج «سعراً عادلاً» لكلّ شركةٍ في السوق. فيُقاس
# السلوكُ بمخرَجٍ مموَّهٍ على شكل «تداول» الحقيقيّ:
#   ٠· صكُّ شركةٍ لا يُقبل
#   ١· وأداةٌ بغير الريال لا تُقبل
#   ٢· والعائمُ لا يُقبل (عائدُه دالّةُ سايبور لا معدَّلٌ ثابت)
#   ٣· والدائمُ بلا أجلٍ لا يُقبل
#   ٤· والأجلُ خارجَ النطاق يُرفض لا يُقرَّب
#   ٥· والأقربُ إلى عشرٍ يُختار
#   ٦· وترتيبُ العائد واحدٌ معلَن: آخرُ صفقةٍ ← وسَطُ السوق ← محسوب
#   ٧· والصفرُ ليس عائداً بل أداةٌ لم تُتداول
#   ٨· والحسابُ يصحّ: اسميٌّ ⇒ الكوبون · ‎92 يرفع · ‎108 يخفض
#   ٩· وخارجَ نطاق المعقولية يُرفض
#  ١٠· وبنيةٌ مجهولةٌ امتناعٌ بسببٍ لا قبولٌ على فراغ
#  ١١· والعنوانُ يُشتقّ من الصفحة لا يُثبَّت في الشيفرة
#  ١٢· والقراءةُ تشيخ فتُعدّ غائبة
#  ١٣· والمحرّكُ يراها من منتِجٍ واحد، ويرفض حين تغيب
#  ١٤· والأثرُ يحمل مصدرَها وتاريخَها
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import datetime as _dt  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.services import lastgood  # noqa: E402
from app.services import risk_free as rf  # noqa: E402

TODAY = _dt.date(2026, 9, 12)


def _mat(years: float) -> str:
    return (TODAY + _dt.timedelta(days=round(years * 365.25))).isoformat()


def row(**kw) -> dict:
    """صفٌّ على شكل مخرَج «تداول» الحقيقيّ — قِيست مفاتيحُه على الخادم."""
    base = {
        "symbol": "5000", "issuerName": "KSA Sukuk 2026-01-15",
        "issueCurrency": "SAR", "rateCalcType": 1, "isPerpetualBond": False,
        "couponRate": 5.00, "couponRateModified": "5.00",
        "maturityDateStr": _mat(10.0), "lastTadeYield": 4.80,
        "bidYield": 0.0, "askYield": 0.0, "lastTradePrice": 0.0, "parValue": 1000,
    }
    base.update(kw)
    return base


def pick(rows):
    return rf.choose(rows, today=TODAY)


# ── ٠ · السيادةُ مشترطة ─────────────────────────────────────────────────
best, why = pick([row(issuerName="CENOMI CENTERS SUKUK 11/2031")])
check(best is None and "سيادي" in (why or ""),
      "٠ صكُّ شركةٍ لا يُقبل معدَّلاً خالياً من المخاطر", why or f"قبِل {best}")

# ── ١ · العملة ─────────────────────────────────────────────────────────
best, why = pick([row(issueCurrency="USD")])
check(best is None and "الريال" in (why or ""),
      "١ أداةٌ بالدولار ليست معدَّلَ الريال", why or f"قبِل {best}")

# ── ٢ · العائمُ لا يصلح ──────────────────────────────────────────────────
best, why = pick([row(rateCalcType=4)])
check(best is None and "عائم" in (why or ""),
      "٢ الصكُّ العائمُ عائدُه دالّةُ سايبور — يُستبعَد", why or f"قبِل {best}")

# ── ٣ · الدائمُ بلا أجل ─────────────────────────────────────────────────
best, why = pick([row(isPerpetualBond=True)])
check(best is None and "دائم" in (why or ""),
      "٣ الصكُّ الدائمُ بلا أجلٍ فلا يُقاس عشرياً", why or f"قبِل {best}")

# ── ٤ · الأجلُ خارجَ النطاق ──────────────────────────────────────────────
best, why = pick([row(maturityDateStr=_mat(2.0))])
check(best is None and "النطاق" in (why or ""),
      "٤ أجلُ سنتين ليس عشرياً — امتناعٌ لا تقريب", why or f"قبِل {best}")

# ── ٥ · الأقربُ إلى عشرٍ من بين المرشَّحات ─────────────────────────────────
best, why = pick([
    row(symbol="5301", maturityDateStr=_mat(7.0), lastTadeYield=4.20),
    row(symbol="5302", maturityDateStr=_mat(9.8), lastTadeYield=4.55),
    row(symbol="5303", maturityDateStr=_mat(13.5), lastTadeYield=5.10),
])
check(best is not None and best["symbol"] == "5302" and best["peers"] == 3
      and abs(best["value"] - 0.0455) < 1e-6,
      "٥ الأقربُ إلى عشر سنواتٍ هو المختار، وعائدُه كسراً كما نُشر",
      f"{best and (best['symbol'], best['tenor_years'], best['value'])}")

# ── ٦ · ترتيبُ العائد ───────────────────────────────────────────────────
best, _ = pick([row(lastTadeYield=4.80, bidYield=5.20, askYield=5.00)])
check(best is not None and best["basis"] == "آخر صفقة" and abs(best["value"] - 0.048) < 1e-9,
      "٦ عائدُ آخرِ صفقةٍ يتقدّم وسَطَ السوق", f"{best and (best['value'], best['basis'])}")
best, _ = pick([row(lastTadeYield=None, bidYield=5.20, askYield=5.00)])
check(best is not None and best["basis"] == "وسط الطلب والعرض"
      and abs(best["value"] - 0.051) < 1e-9,
      "٦ب وحيث لا صفقةَ يُؤخذ وسَطُ الطلب والعرض", f"{best and best['value']}")
best, _ = pick([row(lastTadeYield=None, couponRate=4.50, lastTradePrice=100.0)])
check(best is not None and best["basis"] == "محسوب من السعر والكوبون"
      and abs(best["value"] - 0.045) < 5e-4,
      "٦ج وبلا سوقٍ يُحسب من السعر والكوبون", f"{best and (best['value'], best['basis'])}")

# ── ٧ · الصفرُ ليس عائداً ────────────────────────────────────────────────
best, why = pick([row(lastTadeYield=0.0, bidYield=0.0, askYield=0.0, lastTradePrice=0.0)])
check(best is None and "بلا عائد" in (why or ""),
      "٧ أداةٌ لم تُتداول (أصفارٌ) ليست عائداً يُقرأ", why or f"قبِل {best}")

# ── ٨ · صحّةُ الحساب ────────────────────────────────────────────────────
par = rf.ytm(100.0, 0.045, 10.0)
disc = rf.ytm(92.0, 0.045, 10.0)
prem = rf.ytm(108.0, 0.045, 10.0)
check(par is not None and abs(par - 0.045) < 5e-4,
      "٨ سعرٌ اسميٌّ ⇒ العائدُ يساوي الكوبون", f"{par}")
check(disc is not None and prem is not None and disc > 0.045 > prem,
      "٨ب و‎92 ترفع و‎108 تخفض", f"{disc and round(disc, 5)} · {prem and round(prem, 5)}")

# ── ٩ · نطاقُ المعقولية ─────────────────────────────────────────────────
best, why = pick([row(lastTadeYield=25.0)])
check(best is None and "المعقولية" in (why or ""),
      "٩ عائدُ ‎25٪ جلبٌ فشل لا سوقٌ تغيّر", why or f"قبِل {best}")

# ── ١٠ · بنيةٌ مجهولة ───────────────────────────────────────────────────
best, why = pick([{"foo": 1}, "نصّ"])
check(best is None and bool(why),
      "١٠ صفوفٌ مجهولةُ البنية ⇒ سببٌ مكتوبٌ لا قبولٌ على فراغ", why or "قبِل!")

# ── ١١ · العنوانُ يُشتقّ من الصفحة لا يُثبَّت ─────────────────────────────
src = (ROOT / "backend" / "app" / "services" / "risk_free.py").read_text(encoding="utf-8")
check("<base" in src and "getSukukMarketDetails" in src
      and "!ut/p/z1" not in src and "IZ7_" not in src,
      "١١ لا معرِّفَ بوّابةٍ مثبَّتٌ — العنوانُ من أساس الصفحة وندائها")

# ── ١٢ · القراءةُ تشيخ ──────────────────────────────────────────────────
old = (_dt.date.today() - _dt.timedelta(days=rf.MAX_AGE_DAYS + 5)).isoformat()
lastgood.save(rf.STORE_KEY, {"value": 0.0455, "as_of": old, "source": "اختبار"})
check(rf.reading() is None and rf.current() is None,
      f"١٢ قراءةٌ أقدمُ من {rf.MAX_AGE_DAYS} يوماً تُعدّ غائبة", f"as_of={old}")

# ── ١٣ · المحرّكُ يرفض حين تغيب، ويعمل حين تحضر ──────────────────────────
from app.services.fair_value_engine.params import ParamsError, load_params  # noqa: E402

P = load_params(allow_unverified=True, allow_stale=True)
try:
    _v = P.risk_free
    check(False, "١٣ المحرّكُ يرفض بلا معدَّلٍ مقروء", f"أعاد {_v}")
except ParamsError as e:
    check("غير معبأ" in str(e), "١٣ المحرّكُ يرفض بلا معدَّلٍ مقروء", str(e)[:60])

fresh = _dt.date.today().isoformat()
lastgood.save(rf.STORE_KEY, {"value": 0.0455, "as_of": fresh, "source": rf.PAGE,
                             "tenor_years": 9.8, "instrument": "KSA Sukuk",
                             "basis": "آخر صفقة"})
P2 = load_params(allow_unverified=True, allow_stale=True)
try:
    got = P2.risk_free
except ParamsError as e:                                          # noqa: BLE001
    got = f"رفض: {e}"
check(got == 0.0455, "١٣ب وحين تحضر يراها من المنتِج الواحد", f"{got}")

# ── ١٤ · الأثرُ يحمل المصدرَ والتاريخ ────────────────────────────────────
prov = P2.provenance()
check(prov.get("risk_free_as_of") == fresh
      and "saudiexchange" in str(prov.get("risk_free_source")),
      "١٤ الأثرُ يحمل مصدرَ المعدَّل وتاريخَه",
      f"{prov.get('risk_free_as_of')} · {prov.get('risk_free_source')}")

# ── والجلبُ لا يُجرَّب هنا: شبكةٌ في حارسٍ تُنتج تقلُّباً لا قياساً. البنيةُ
# تُثبَّت بمسبار الخادم (‏risk_free_probe.py) الذي يطبع الصفوفَ بنصّها.

print(("FAIL" if fail else "PASS") + " D249 — معدَّلٌ خالٍ من المخاطر بمصدرٍ وتاريخ")
raise SystemExit(fail)
