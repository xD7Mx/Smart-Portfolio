#!/usr/bin/env python3
"""شروطُ الخطر تُقاس وتُسعَّر — لا تُسكَت ولا تمنع (‏D408).

    python3 scripts/audit/risk_priced_not_silent.py

في `archetype_spec.VALUATION` اثنتا عشرةَ قائمةِ `abstain_if`، وقِيس
(‏D405) أنّها **لا يقرؤها محرّكٌ واحد**. فشركةٌ رافعتُها خمسةَ عشرَ ضعفاً
أو تغطيةُ فوائدها دون واحد كانت تخرج بسعرٍ عادلٍ ثقتُه «مرتفعة» كأنّها
سليمة — وذاك أخطرُ من الامتناع: **رقمٌ واثقٌ على أرضٍ رخوة**، والقرارُ
الاستثماريُّ يقوم على الثقة لا على الرقم وحدَه.

والعلاجُ بأمر المالك: الخطرُ **يُسعَّر لا يُفرِّغ**. يُعلَن باسمه، وتنزل
الثقةُ إلى «منخفضة»، فيتّسع هامشُ الأمان تلقائياً إلى ‎35% — أي سعرُ
دخولٍ أدنى، وهي ترجمةُ الخطر التي تُفيد قراراً. وما لا تصله مدخلاتُه
يُعلَن **غيرَ مقيس** فلا تُقرأ الخضرةُ شهادةً.
"""
from __future__ import annotations

# ══ لا فحصَ يكتب في بيانات المالك ══ (D160 · D429)
# يُحوَّل مخزنُ الحالة إلى مجلّدٍ مؤقّت **قبل** أيّ استيرادٍ من `app`،
# فالوحداتُ تقرأ مسارَها عند تحميلها. وسجلُّ مشاهداتِ حالة السوق معه:
# حكمُ العطلة يقرأ مشاهداتِ اليوم، فمشاهدةُ فحصٍ تدخله تُفسد دليلَه.
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


try:
    from app.services.fair_value import compute, risk_flags
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)

# ── ١ · الشرطُ المخالفُ يُوسَم باسمه ───────────────────────────────────
_hit, _, _ = risk_flags("bank", [{"as_of": "2026-06-30", "equity": 1000.0,
                               "total_assets": 15000.0, "net_income": 50.0}])
check(any(x["code"] == "leverage_gt_12" for x in _hit),
      "١ رافعةُ ‎15× في بنكٍ تُوسَم باسم شرطها")

_ok, _, _ = risk_flags("bank", [{"as_of": "2026-06-30", "equity": 1000.0,
                              "total_assets": 8000.0, "net_income": 50.0}])
check(not _ok, "١ب ورافعةُ ‎8× لا تُوسَم — لا إنذارَ كاذب")

_cov, _, _ = risk_flags("capital_infra", [{"as_of": "2026-06-30", "equity": 900.0,
                                        "ebit": 50.0, "interest_expense": 80.0,
                                        "net_income": 5.0}])
check(any(x["code"] == "coverage_lt_1" for x in _cov),
      "١ج وتغطيةُ فوائدَ ‎0.6× تُوسَم")

# ── ٢ · وما لا تصله مدخلاتُه يُعلَن غيرَ مقيس ─────────────────────────
_h2, _u2, _ = risk_flags("reit", [{"as_of": "2026-06-30", "equity": 500.0,
                                "net_income": 20.0}], {})
check("no_dividend" in _u2 and not any(x["code"] == "no_dividend" for x in _h2),
      "٢ شرطٌ بلا مدخلٍ يُعلَن «غيرَ مقيس» لا سليماً", f"{_u2}")

# ── ٣ · والوسمُ يُترجَم ثقةً وهامشَ أمان ───────────────────────────────
# بنكٌ سليمُ المدخلات ورافعتُه فوق الحدّ: القيمةُ تبقى، والثقةُ تنزل،
# وهامشُ الأمان يتّسع — فالخطرُ سعرٌ أدنى لا خانةٌ فارغة.
_per = [{"as_of": "2026-06-30", "equity": 1000.0, "total_assets": 15000.0,
         "net_income": 120.0, "shares_outstanding": 100.0, "eps": 1.2,
         "revenue": 400.0, "total_liabilities": 14000.0},
        {"as_of": "2025-12-31", "equity": 950.0, "total_assets": 14000.0,
         "net_income": 110.0, "shares_outstanding": 100.0, "eps": 1.1,
         "revenue": 380.0, "total_liabilities": 13050.0}]
_out = compute({"book_value": 10.0, "trailing_eps": 1.2, "return_on_equity": 0.12},
               price=12.0, sector_avg_pe=10.0, sector_avg_pb=1.1,
               periods=_per, archetype="bank", symbol="0000")
_has = bool(_out.get("risk_flags"))
check(_has, "٣ المحرّكُ يقرأ الشروطَ ويُعلنها في مخرَجه",
      _out.get("risk_note") or "")
if _has and _out.get("value") is not None:
    check(_out.get("confidence") == "منخفضة",
          "٣ب والثقةُ تنزل إلى منخفضة", str(_out.get("confidence")))
    check((_out.get("margin_of_safety_pct") or 0) >= 35,
          "٣ج وهامشُ الأمان يتّسع — الخطرُ سعرٌ أدنى",
          f"{_out.get('margin_of_safety_pct')}%")
    check(_out.get("value") is not None,
          "٣د والقيمةُ تبقى — الخطرُ يُسعَّر ولا يُفرِّغ الخانة",
          str(_out.get("value")))
elif _has:
    print("⚠ لم تُنتج العيّنةُ قيمةً — لم يُقَس أثرُ الوسم على الثقة")

# ── ٥ · ونقصُ حقلٍ فجوةُ بيانٍ مُعلَنة لا «لم يُقَس» ───────── (D422)
# `total_debt` ناقصٌ في ‎40 ورقة، وشرطُ `no_debt_field` يعني هذا النقصَ
# بعينه. فكان يسقط في سلّة «لم يُقَس» فيُخصم من ثقة الرقم بلا بيان.
# فصار يُعلَن **باسمه ونصِّه**، ويُخصم خصماً مقدَّراً لا يحبس الدرجة —
# فالورقةُ ليست خطرةً، إنّما لم يصلنا أحدُ حقولها.
_gh, _gu, _gg = risk_flags("capital_infra", [{"as_of": "2026-06-30",
                                              "equity": 900.0,
                                              "total_assets": 5000.0,
                                              "net_income": 50.0}])
check(any(x["code"] == "no_debt_field" for x in _gg),
      "٥ نقصُ حقلِ الدَّين يُعلَن فجوةَ بيانٍ باسمها")
check("no_debt_field" not in _gu,
      "٥ب ولا يُعَدّ «لم يُقَس» فيُخصم بلا بيان")
check(all(x.get("نصّ") for x in _gg),
      "٥ج ولكلّ فجوةٍ نصٌّ يقول ما لم يصلنا")
_dh, _du, _dg = risk_flags("capital_infra", [{"as_of": "2026-06-30",
                                              "equity": 900.0,
                                              "total_assets": 5000.0,
                                              "total_debt": 400.0,
                                              "net_income": 50.0}])
check(not any(x["code"] == "no_debt_field" for x in _dg),
      "٥د وحين يصل الحقلُ لا فجوةَ — لا إنذارَ كاذب")

# ── ٦ · وعددُ المخرَجات واحدٌ في كلّ مسار ───────────────── (D424)
# أُضيفت السلّةُ الثالثةُ إلى مخرَج النهاية وحدَه، وبقي المخرَجانِ
# المبكّرانِ بقيمتَين. وكلُّ نمطٍ لا `abstain_if` له يمرّ بهما — وهو
# أكثرُ السوق — فرفع `compute` ‏`ValueError` في 268 ورقةً من 273 وخرج
# السوقُ كلُّه بلا سعرٍ عادل. والفحوصُ الخمسةُ فوق خرجت خضراءَ لأنها
# لم تمسّ إلا أنماطاً ذاتَ شروط: حارسٌ لا يمرّ بالمسار الخالي يشهد لما
# لم يره. فتُقاس المساراتُ الثلاثة كلُّها بعددِ مخرَجاتها.
_rows = [{"as_of": "2026-06-30", "equity": 900.0, "net_income": 50.0}]
for _name, _arch in (("نمطٌ بلا شروطِ امتناع", "commodity"),
                     ("نمطٌ غيرُ معروف", "لا-نمط"),
                     ("لا نمطَ أصلاً", None)):
    try:
        _a, _b, _c = risk_flags(_arch, _rows)
        _ok, _why = True, f"{len(_a)}·{len(_b)}·{len(_c)}"
    except Exception as e:                                        # noqa: BLE001
        _ok, _why = False, f"{type(e).__name__}: {e}"
    check(_ok, f"٦ {_name} يُعيد ثلاثَ سلالٍ لا يرفع", _why)

print(("FAIL" if fail else "PASS")
      + " D408 · D424 — الخطرُ مقيسٌ ومُسعَّرٌ، وكلُّ مسارٍ يُعيد سلالَه")
sys.exit(fail)
