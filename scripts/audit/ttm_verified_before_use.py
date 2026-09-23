#!/usr/bin/env python3
"""أرباحُ اثني عشرَ شهراً لا تُجمَع قبل أن يُتحقَّق منها (‏D414).

    python3 scripts/audit/ttm_verified_before_use.py

مضاعفُ الربحية كان يقرأ ربحيةَ سنةٍ ختامُها قبل ثلاثةِ أرباع، وعندنا
أرباعٌ أحدث. وجمعُ الأرباع صحيحٌ **إن كانت منفصلة**؛ فإن كانت تراكميةً
من أوّل السنة (‏3M · 6M · 9M · 12M) ضاعف الجمعُ الربحَ مرّتين ونصفاً،
وأنتج مضاعفاً كاذباً ثمّ سعراً عادلاً كاذباً **يبدو سليماً** — وذاك
أسوأُ من الامتناع، لأنّ الامتناعَ يُرى والرقمَ الكاذبَ يُصدَّق.

وقِيس على الكون بشاهدَين: النسبةُ المباشرةُ (‏ربعُ الختام ÷ السنويّ)
ردّت ‎0.25 و‎0.40 وصفرَ تراكمية، والشاهدُ الثاني (تصاعدُ الأرباع داخل
السنة) ردّ ‎371 غيرَ متصاعدةٍ مقابل ‎110. لكنّ الشاهدَ المباشرَ لم يبلغ
إلا ثلاثةَ رموز — ولا يُعمَّم حكمٌ على ‎273 من ثلاثة (‏D402 · D406).

فالتحقّقُ **لكلّ رمزٍ على حدة**: تُجمع أرباعُ سنةٍ كاملةٍ وتُقارَن
بسنويّها المنشور؛ فإن تطابقا في حدود العُشر فجمعُ هذا الرمز صحيح،
وإلا فلا مجموعَ له ويبقى على السنويّ — ويُقال السببُ لا يُسكَت عنه.
"""
from __future__ import annotations

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
    from app.services.fair_value import compute
    from app.services.market_data import _ttm_from
except (ModuleNotFoundError, ImportError) as e:
    print(f"⚠ بيئةٌ ناقصة ({e}) — لم يُقَس")
    sys.exit(0)

_ANN = [{"as_of": "2025-12-31", "net_income": 120.0}]

# ── ١ · أرباعٌ منفصلةٌ يُتحقَّق منها فتُقبَل ──────────────────────────
_disc = [{"as_of": "2025-03-31", "net_income": 25.0, "shares_outstanding": 100.0},
         {"as_of": "2025-06-30", "net_income": 30.0, "shares_outstanding": 100.0},
         {"as_of": "2025-09-30", "net_income": 28.0, "shares_outstanding": 100.0},
         {"as_of": "2025-12-31", "net_income": 37.0, "shares_outstanding": 100.0},
         {"as_of": "2026-03-31", "net_income": 33.0, "shares_outstanding": 100.0},
         {"as_of": "2026-06-30", "net_income": 40.0, "shares_outstanding": 100.0}]
_t = _ttm_from(_disc, _ANN)
check(isinstance(_t, dict) and not _t.get("unverified"),
      "١ أرباعٌ منفصلةٌ تُقبَل بعد التحقّق",
      f"مُتحقَّقٌ بسنة {(_t or {}).get('verified_on')}")
check((_t or {}).get("net_income") == 138.0,
      "١ب والحسابُ: سنويٌّ − نظيرُ الأرباع + أرباعُ العام الجاري",
      str((_t or {}).get("net_income")))
# والأرباعُ المعلَنةُ هي **المضافةُ من العام الجاري** لا أربعةٌ دائماً:
# الصيغةُ في هذا السوق تطرح من السنة نظيرَها وتضيف ما تحقّق (‏D417).
check(len((_t or {}).get("quarters") or []) >= 1
      and bool((_t or {}).get("basis")),
      "١ج والأرباعُ المضافةُ وأساسُ الحساب مُعلَنان في المخرَج",
      f"{(_t or {}).get('basis')} · {(_t or {}).get('quarters')}")

# ── ٢ · وتراكميةٌ تُرفَض — وهي الخطرُ كلُّه ───────────────────────────
_cum = [{"as_of": "2025-03-31", "net_income": 25.0, "shares_outstanding": 100.0},
        {"as_of": "2025-06-30", "net_income": 55.0, "shares_outstanding": 100.0},
        {"as_of": "2025-09-30", "net_income": 83.0, "shares_outstanding": 100.0},
        {"as_of": "2025-12-31", "net_income": 120.0, "shares_outstanding": 100.0}]
_c = _ttm_from(_cum, _ANN)
check(isinstance(_c, dict) and _c.get("unverified") is True,
      "٢ وتراكميةٌ تُرفَض — جمعُها 283 والسنويُّ 120")
check(bool((_c or {}).get("note")),
      "٢ب ويُقال سببُ الرفض — لا صمت")

# ── ٣ · ولا مجموعَ بلا سنةِ تحقّق ─────────────────────────────────────
_no = _ttm_from(_disc, [])
check(isinstance(_no, dict) and _no.get("unverified") is True,
      "٣ وبلا سنويٍّ يُتحقَّق به لا يُجمَع شيء")

# ── ٤ · والمحرّكُ يستعمل المُتحقَّقَ وحدَه ويُسمّيه ──────────────────
_per = [{"as_of": "2025-12-31", "equity": 1000.0, "total_assets": 6000.0,
         "net_income": 120.0, "shares_outstanding": 100.0, "eps": 1.2,
         "revenue": 400.0, "total_liabilities": 5000.0},
        {"as_of": "2024-12-31", "equity": 950.0, "total_assets": 5800.0,
         "net_income": 110.0, "shares_outstanding": 100.0, "eps": 1.1,
         "revenue": 380.0, "total_liabilities": 4850.0}]
_kw = dict(price=12.0, sector_avg_pe=10.0, sector_avg_pb=1.1,
           periods=_per, archetype="consumer_cyclical", symbol="0000")
_info = {"book_value": 10.0, "eps": 1.2, "return_on_equity": 0.12}

_base = compute(_info, **_kw)
_with = compute(_info, ttm=_t, **_kw)
check(_with.get("eps_ttm") is not None,
      "٤ المحرّكُ يقرأ ربحيةَ اثني عشرَ شهراً", str(_with.get("eps_ttm")))
check(bool(_with.get("eps_source")),
      "٤ب ويُسمّي مصدرَها ومدّتَها", str(_with.get("eps_source")))
_rej = compute(_info, ttm=_c, **_kw)
check(_rej.get("eps_ttm") is None,
      "٤ج ولا يقرأ ما رُفض — لا رقمَ مضاعَفٌ يمرّ")
check(bool(_rej.get("eps_ttm_note")),
      "٤د ويُعلن لماذا لم يُستعمَل")

# ── ٥ · والأثرُ يبلغ القرار ───────────────────────────────────────────
if _base.get("value") and _with.get("value"):
    check(_with["value"] != _base["value"],
          "٥ فالقيمةُ تتغيّر بأحدثِ ربحية",
          f"{_base['value']} ← {_with['value']}")

# ── ٦ · وبوّابةُ معقوليةٍ على الربحية نفسِها ─────────────────── (D415)
# قِيس على الكون: المسارُ نال ‎3 من ‎273، وأحدُ الثلاثة ربحيةُ سهمه
# ‎7,184.76 — مستحيلةٌ في سهمٍ سعرُه عشرات، وسببُها عددُ أسهمٍ بوحدةٍ
# مغلوطة. فالتحقّقُ من **الجمع** لا يكفي: رقمٌ صحيحُ الجمعِ قد يكون
# معطوبَ المقام.
_wild = compute(_info, ttm={"as_of": "2026-06-30", "eps": 7184.76,
                            "verified_on": "2025",
                            "quarters": ["a", "b", "c", "d"]}, **_kw)
check(_wild.get("eps_ttm") is None,
      "٦ ربحيةٌ تفوق السعرَ أضعافاً تُرفَض — خطأُ وحدةٍ لا ربحية")
check(bool(_wild.get("eps_ttm_rejected")),
      "٦ب ويُسمّى الرفضُ ومقدارُه", (_wild.get("eps_ttm_rejected") or "")[:60])
_fine = compute(_info, ttm={"as_of": "2026-06-30", "eps": 1.38,
                            "verified_on": "2025",
                            "quarters": ["a", "b", "c", "d"]}, **_kw)
check(_fine.get("eps_ttm") == 1.38,
      "٦ج والسليمةُ تمرّ — لا رفضَ شامل")

print(("FAIL" if fail else "PASS")
      + " D414 — لا جمعَ قبل تحقّق، ولا رقمَ مضاعَفٌ يمرّ")
sys.exit(fail)
