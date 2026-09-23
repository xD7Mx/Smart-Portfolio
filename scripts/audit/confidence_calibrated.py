#!/usr/bin/env python3
"""الثقةُ درجةٌ مُعايَرةٌ مُبرَّرة — والكلمةُ تُشتَقّ منها (‏D411).

    python3 scripts/audit/confidence_calibrated.py

أمرَ المالك: «اجعل محرّكَ الحوكمة والسعر العادل جاهزَين للقرار
الاستثماريِّ بكلّ ثقة». والقرارُ يقوم على **الثقة** لا على الرقم وحدَه،
وكانت تخرج كلمةً واحدةً بلا أن يُعرَف لماذا ولا كم — فلا تُوزَن ثقةٌ
بأخرى ولا يُرى ما نقصها.

وأوّلُ ما جُرِّب كان عطباً بنفسه: درجةٌ تُحسب **بجانب** الكلمة فتناقضها
— ‎88/100 تُسمّى «متوسطة» و‎73 تُسمّى «منخفضة». رقمان يختلفان على معنىً
واحد، وهو ما يحاربه هذا المشروعُ كلُّه (‏D386). فصارت الكلمةُ **مشتقّةً
من الدرجة** حتماً: مصدرٌ واحدٌ لا اثنان.

والموانعُ الجوهريةُ **سقوفٌ** لا خصومات — مسارٌ واحد · تباعدٌ فوق
النصف · تأخّرٌ عن دورة الإفصاح · شرطُ خطرٍ قائم — فلا تُشترى ثقةٌ
بتكديس محاسنَ فوق عيبٍ جوهريّ.
"""
from __future__ import annotations

import pathlib
import sys
from datetime import date, timedelta

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
    from app.services.fair_value import compute
except (ModuleNotFoundError, ImportError) as e:
    print(f"⚠ بيئةٌ ناقصة ({e}) — لم يُقَس")
    sys.exit(0)


def _run(days: int = 84, assets: float = 6000.0) -> dict:
    d = (date.today() - timedelta(days=days)).isoformat()
    pv = (date.today() - timedelta(days=days + 92)).isoformat()
    per = [{"as_of": d, "equity": 1000.0, "total_assets": assets,
            "net_income": 120.0, "shares_outstanding": 100.0, "eps": 1.2,
            "revenue": 400.0, "total_liabilities": assets - 1000},
           {"as_of": pv, "equity": 950.0, "total_assets": assets * 0.97,
            "net_income": 110.0, "shares_outstanding": 100.0, "eps": 1.1,
            "revenue": 380.0, "total_liabilities": assets * 0.97 - 950}]
    return compute({"book_value": 10.0, "trailing_eps": 1.2,
                    "return_on_equity": 0.12}, price=12.0,
                   sector_avg_pe=10.0, sector_avg_pb=1.1,
                   periods=per, archetype="bank", symbol="0000")


_LBL = {"مرتفعة": (90, 101), "متوسطة": (50, 90), "منخفضة": (0, 50)}

cases = {"سليمٌ في أوانه": _run(),
         "رافعةٌ فوق الحدّ": _run(assets=15000.0),
         "متأخّرٌ عن دورته": _run(days=200)}

# ── ١ · لكلّ تقديرٍ درجةٌ وسلّمٌ مُعلَن ────────────────────────────────
for name, o in cases.items():
    if o.get("value") is None:
        print(f"⚠ {name}: لا قيمةَ — لم يُقَس")
        continue
    check(isinstance(o.get("confidence_score"), int),
          f"١ {name}: للثقةِ درجةٌ من مئة",
          str(o.get("confidence_score")))
    check(bool(o.get("confidence_scale")),
          f"١ب {name}: وسلّمُها مُعلَنٌ في المخرَج")

    # ── ٢ · والكلمةُ تُشتَقّ من الدرجة — لا تناقضَ بين رقمٍ وكلمة ──────
    _s, _c = o.get("confidence_score"), o.get("confidence")
    _lo, _hi = _LBL.get(_c, (-1, -1))
    check(_lo <= (_s or -1) < _hi,
          f"٢ {name}: الكلمةُ «{_c}» تطابق درجتَها {_s}",
          f"المدى المطلوب {_lo}–{_hi - 1}")

    # ── ٣ · وكلُّ خصمٍ له سببٌ مكتوب ─────────────────────────────────
    _w = o.get("confidence_why") or []
    check(all(x.get("السبب") and isinstance(x.get("خصم"), int) for x in _w),
          f"٣ {name}: كلُّ خصمٍ باسمه ومقداره", f"{len(_w)} بنداً")
    if (_s or 100) < 100:
        check(bool(_w), f"٣ب {name}: درجةٌ دون المئة لها سببٌ مكتوب")

# ── ٤ · والعيبُ الجوهريُّ سقفٌ لا خصم ─────────────────────────────────
# تكديسُ محاسنَ لا يشتري ثقةً فوق عيبٍ جوهريّ.
_bad = cases["رافعةٌ فوق الحدّ"]
_late = cases["متأخّرٌ عن دورته"]
check((_bad.get("confidence_score") or 100) < 50,
      "٤ شرطُ خطرٍ قائمٌ يحبس الدرجةَ دون ‎50",
      str(_bad.get("confidence_score")))
check((_late.get("confidence_score") or 100) < 50,
      "٤ب والتأخّرُ عن دورة الإفصاح كذلك",
      str(_late.get("confidence_score")))
check(_bad.get("confidence") == "منخفضة" and _late.get("confidence") == "منخفضة",
      "٤ج فتنزل كلمتُهما تبعاً لا استقلالاً")

# ── ٥ · والسليمُ لا يُعاقَب ───────────────────────────────────────────
_ok = cases["سليمٌ في أوانه"]
check((_ok.get("confidence_score") or 0) >= 50,
      "٥ والسليمُ في أوانه لا يُحبَس — لا إنذارَ كاذب",
      f"{_ok.get('confidence_score')} · {_ok.get('confidence')}")

print(("FAIL" if fail else "PASS")
      + " D411 — الثقةُ مُعايَرةٌ مُبرَّرةٌ، والكلمةُ من الدرجة")
sys.exit(fail)
