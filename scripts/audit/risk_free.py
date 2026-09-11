#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D249 — معدَّلٌ خالٍ من المخاطر يُقرأ من مصدرٍ مؤرَّخ، لا يُكتب بيد.
#
# كان `risk_free_sar` فارغاً و«يُملأ يدوياً» — فمحرّكُ القيمة العادلة
# متوقّفٌ كلَّه على رقمٍ لا مصدرَ له. واليدُ ليست مصدراً: رقمٌ يُكتب مرّةً
# يشيخ بلا أن يُقال إنه شاخ.
#
# وخطرُ الجلب أعظمُ من خطر الفراغ: رقمٌ مختلَقٌ من عمودٍ مجهولٍ يُنتج
# «سعراً عادلاً» لكلّ شركةٍ في السوق. فيُقاس السلوكُ بمخرَجٍ مموَّه:
#   ٠· الأعمدةُ تُقرأ بأسمائها لا بمواضعها
#   ١· والمرادفُ الأخصُّ يفوز على الأعمّ
#   ٢· وصكُّ شركةٍ لا يُقبل معدَّلاً خالياً من المخاطر
#   ٣· والأجلُ خارجَ النطاق يُرفض لا يُقرَّب
#   ٤· والأقربُ إلى عشرٍ يُختار
#   ٥· والعائدُ يُحسب حين لا يُنشَر
#   ٦· وسعرٌ دون الاسميّ يرفع العائدَ فوق الكوبون
#   ٧· وخارجَ نطاق المعقولية يُرفض
#   ٨· وترويسةٌ غيرُ مفهومةٍ امتناعٌ بسببٍ لا قبولٌ على فراغ
#   ٩· والقراءةُ تشيخ فتُعدّ غائبة
#  ١٠· والمحرّكُ يراها من منتِجٍ واحد، ويرفض حين تغيب
#  ١١· والأثرُ يحمل مصدرَها وتاريخَها
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

TODAY = _dt.date(2026, 9, 11)


def _mat(years: float) -> str:
    return (TODAY + _dt.timedelta(days=round(years * 365.25))).isoformat()


def _table(header: list[str], rows: list[list[str]]) -> str:
    h = "".join(f"<th>{c}</th>" for c in header)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{h}</tr>{body}</table>"


# ── ٠ · الأعمدةُ بأسمائها: الترويسةُ مبعثرةُ الترتيب ────────────────────
html = _table(
    ["تاريخ الاستحقاق", "آخر سعر", "اسم الأداة", "الكوبون"],
    [[_mat(10.0), "100.00", "صكوك حكومية بالريال السعودي 2036", "4.50%"]],
)
rows, why = rf.parse_instruments(html)
check(len(rows) == 1 and rows[0].get("name", "").startswith("صكوك حكومية"),
      "٠ الأعمدةُ تُقرأ بأسمائها لا بمواضعها",
      f"{rows[0] if rows else why}")

# ── ١ · المرادفُ الأخصُّ يفوز ────────────────────────────────────────────
r2, _ = rf.parse_instruments(_table(
    ["اسم الأداة", "تاريخ الاستحقاق", "الكوبون", "العائد إلى الاستحقاق"],
    [["صكوك حكومية", _mat(10.0), "4.50%", "4.80%"]]))
check(bool(r2) and r2[0].get("ytm") == "4.80%" and r2[0].get("coupon") == "4.50%",
      "١ «العائد إلى الاستحقاق» لا يُقرأ كوبوناً ولا العكس", f"{r2[0] if r2 else '—'}")

# ── ٢ · السيادةُ مشترطة ─────────────────────────────────────────────────
corp, _ = rf.parse_instruments(_table(
    ["اسم الأداة", "تاريخ الاستحقاق", "العائد"],
    [["صكوك شركة سابك 2036", _mat(10.0), "6.20%"]]))
best, why = rf.choose(corp, today=TODAY)
check(best is None and "سيادي" in (why or ""),
      "٢ صكُّ شركةٍ لا يُقبل معدَّلاً خالياً من المخاطر", why or f"قبِل {best}")

# ── ٣ · الأجلُ خارجَ النطاق يُرفض ─────────────────────────────────────────
short, _ = rf.parse_instruments(_table(
    ["اسم الأداة", "تاريخ الاستحقاق", "العائد"],
    [["صكوك حكومية 2028", _mat(2.0), "4.10%"]]))
best, why = rf.choose(short, today=TODAY)
check(best is None and "النطاق" in (why or ""),
      "٣ أجلُ سنتين ليس عشرياً — امتناعٌ لا تقريب", why or f"قبِل {best}")

# ── ٤ · الأقربُ إلى عشرٍ يُختار من بين المرشَّحات ──────────────────────────
many, _ = rf.parse_instruments(_table(
    ["اسم الأداة", "تاريخ الاستحقاق", "العائد"],
    [["صكوك حكومية أ", _mat(7.0), "4.20%"],
     ["صكوك حكومية ب", _mat(9.8), "4.55%"],
     ["صكوك حكومية ج", _mat(13.5), "5.10%"]]))
best, why = rf.choose(many, today=TODAY)
check(best is not None and best["name"].endswith("ب") and best["peers"] == 3,
      "٤ الأقربُ إلى عشر سنواتٍ هو المختار",
      f"{best and (best['name'], best['tenor_years'], best['value'])}")
check(best is not None and abs(best["value"] - 0.0455) < 1e-6,
      "٤ب والعائدُ المنشورُ يُقرأ كسراً كما هو", f"{best and best['value']}")

# ── ٥ · العائدُ يُحسب حين لا يُنشَر ───────────────────────────────────────
par = rf.ytm(100.0, 0.045, 10.0)
check(par is not None and abs(par - 0.045) < 5e-4,
      "٥ سعرٌ اسميٌّ ⇒ العائدُ يساوي الكوبون", f"{par}")
nc, _ = rf.parse_instruments(_table(
    ["اسم الأداة", "تاريخ الاستحقاق", "الكوبون", "آخر سعر"],
    [["صكوك حكومية", _mat(10.0), "4.50%", "100.00"]]))
best, why = rf.choose(nc, today=TODAY)
check(best is not None and best["basis"] == "محسوب"
      and abs(best["value"] - 0.045) < 5e-4,
      "٥ب وغيابُ عمودِ العائد يُحسَب من السعر والكوبون لا يُسكت عنه",
      f"{best or why}")

# ── ٦ · سعرٌ دون الاسميّ يرفع العائد ─────────────────────────────────────
disc = rf.ytm(92.0, 0.045, 10.0)
check(disc is not None and disc > 0.045,
      "٦ سعرٌ ‎92 يرفع العائدَ فوق الكوبون", f"{disc and round(disc, 5)}")
prem = rf.ytm(108.0, 0.045, 10.0)
check(prem is not None and prem < 0.045,
      "٦ب وسعرٌ ‎108 يخفضه دونه", f"{prem and round(prem, 5)}")

# ── ٧ · نطاقُ المعقولية ─────────────────────────────────────────────────
wild, _ = rf.parse_instruments(_table(
    ["اسم الأداة", "تاريخ الاستحقاق", "العائد"],
    [["صكوك حكومية", _mat(10.0), "25.00%"]]))
best, why = rf.choose(wild, today=TODAY)
check(best is None and "المعقولية" in (why or ""),
      "٧ عائدُ ‎25٪ جلبٌ فشل لا سوقٌ تغيّر", why or f"قبِل {best}")

# ── ٨ · ترويسةٌ غيرُ مفهومةٍ: امتناعٌ بسبب ────────────────────────────────
rowsx, whyx = rf.parse_instruments(_table(["ع1", "ع2"], [["س", "ص"]]))
check(not rowsx and bool(whyx),
      "٨ ترويسةٌ مجهولةٌ ⇒ سببٌ مكتوبٌ لا قبولٌ على فراغ", whyx or "قبِل!")
rowsy, whyy = rf.parse_instruments("<html>لا جدول</html>")
check(not rowsy and "جدول" in (whyy or ""),
      "٨ب وصفحةٌ بلا جدولٍ تُسمّى بما هي", whyy or "قبِل!")

# ── ٩ · القراءةُ تشيخ ───────────────────────────────────────────────────
old = (_dt.date.today() - _dt.timedelta(days=rf.MAX_AGE_DAYS + 5)).isoformat()
lastgood.save(rf.STORE_KEY, {"value": 0.0455, "as_of": old, "source": "اختبار"})
check(rf.reading() is None and rf.current() is None,
      f"٩ قراءةٌ أقدمُ من {rf.MAX_AGE_DAYS} يوماً تُعدّ غائبة", f"as_of={old}")

# ── ١٠ · المحرّكُ يرفض حين تغيب، ويعمل حين تحضر ──────────────────────────
from app.services.fair_value_engine.params import ParamsError, load_params  # noqa: E402

P = load_params(allow_unverified=True, allow_stale=True)
try:
    _v = P.risk_free
    check(False, "١٠ المحرّكُ يرفض بلا معدَّلٍ مقروء", f"أعاد {_v}")
except ParamsError as e:
    check("غير معبأ" in str(e), "١٠ المحرّكُ يرفض بلا معدَّلٍ مقروء", str(e)[:60])

fresh = _dt.date.today().isoformat()
lastgood.save(rf.STORE_KEY, {"value": 0.0455, "as_of": fresh,
                             "source": rf.SOURCES[0], "tenor_years": 9.8,
                             "instrument": "صكوك حكومية ب", "basis": "منشور"})
P2 = load_params(allow_unverified=True, allow_stale=True)
try:
    got = P2.risk_free
except ParamsError as e:                                          # noqa: BLE001
    got = f"رفض: {e}"
check(got == 0.0455, "١٠ب وحين تحضر يراها من المنتِج الواحد", f"{got}")

# ── ١١ · الأثرُ يحمل المصدرَ والتاريخ ────────────────────────────────────
prov = P2.provenance()
check(prov.get("risk_free_as_of") == fresh
      and "saudiexchange" in str(prov.get("risk_free_source")),
      "١١ الأثرُ يحمل مصدرَ المعدَّل وتاريخَه",
      f"{prov.get('risk_free_as_of')} · {prov.get('risk_free_source')}")

# ── والجلبُ لا يُجرَّب هنا: المضيفُ محجوبٌ عن بيئة التطوير، والشبكةُ في
# حارسٍ تُنتج تقلُّباً لا قياساً. البنيةُ تُثبَّت بمسبار الخادم
# (‏risk_free_probe.py)، وهذا الحارسُ يقيس الفهمَ والاختيارَ والحساب.

print(("FAIL" if fail else "PASS") + " D249 — معدَّلٌ خالٍ من المخاطر بمصدرٍ وتاريخ")
raise SystemExit(fail)
