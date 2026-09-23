"""السعرُ العادل مصدرٌ واحد في التطبيق كلِّه، وكلُّ رقمٍ باسمه — حارسُ D147 · D386.

## القاعدة المعتمدة (‏D386 · بأمر المالك)

«هدفُ المحللين شيءٌ من ياهو، والسعرُ العادل شيءٌ آخرُ من صنعنا».

  · **السعرُ العادل = تقديرُ محرّكنا** من قوائم الشركة (`fair_value`)،
    وهو هو في صفحة الشركة والفرز ونصِّ الذكاء.
  · **هدفُ المحللين** حقلٌ مستقلٌّ باسمه (`analyst_target`) — مسانِدٌ
    لا منافس، ولا يلبس اسمَ السعر العادل ولا يلبسه السعرُ العادل.

وكان هذا الحارسُ يحرس القاعدةَ **السابقة** (السعرُ العادل = إجماعُ
المحللين) بعد أن نقضها المالك — فسقط أربعاً على شفرةٍ صحيحة، وبقي
فحصُه الرابعُ أخضرَ لأنّه يطابق **عبارةً**: «متوسط تقديرات بيوت الخبرة»
في توجيه النموذج. والعبارةُ كانت موضوعةً فوق `fair_value` — سعرِ
محرّكنا — فأُخبر النموذجُ أنّ المحللين يرون رقماً لم يقله محلّل (‏D428).
فالفحصُ الآن **سلوكيّ** في المواضع كلِّها: يُبنى التوجيهُ فعلاً ويُقرأ
أيُّ رقمٍ وُضع تحت أيّ اسم.

    python scripts/audit/fv_single_source.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import types

# ══ فحصٌ لا يكتب في بيانات المالك ══
# هذا السكربتُ يشغّل مسارَ التحليل كاملاً، وهو يحفظ ما يقرؤه في
# `lastgood` و`storage` — فكان يلوّث ملفَّ تشغيلٍ متتبَّعاً في المستودع
# ويمنع بناءَ الحزمة. وسكربتُ فحصٍ يغيّر حالةً ليس فحصاً.
# فيُوجَّه إلى مجلّدٍ مؤقّت **قبل أيّ استيراد** — لأنّ الوحداتِ تقرأ
# المسارَ عند تحميلها لا عند استعمالها.
import tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SANDBOX, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SANDBOX

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

TARGET = 88.5
PRICE = 35.0   # D449: سعرٌ يقع التقديرُ (20.46) ضمن مداه المعقول فيُنشر


def _stub() -> None:
    """مصدرٌ صناعيّ: هدفُ محلّلين معلومٌ وسعرٌ معلوم."""
    mod = types.ModuleType("app.services.market_data")
    per = [{"year": 2019 + k, "revenue": 9e9, "net_income": 1e9,
            "equity": 1e10, "eps": 3.0, "operating_cash_flow": 1.2e9,
            "capex": -2e8, "depreciation": 2e8, "total_debt": 1e9,
            "ending_cash": 5e8, "shares_outstanding": 3.3e8,
            "operating_income": 1.3e9, "total_assets": 1.4e10,
            "dividends_paid": -3e8} for k in range(5)]

    class MS:
        async def get_financials(self, t, allow_supplement=False):
            return {"periods": per}

        async def get_company_info(self, t):
            return {"name": "شركةُ فحص", "sector": "الاتصالات",
                    "target_mean_price": TARGET, "beta": 1.0,
                    "current_price": PRICE}

        async def get_price(self, t):
            return {"price": PRICE, "change_pct": 0.0}

        async def get_history(self, *a, **k):
            return []

    mod.market_service = MS()
    sys.modules["app.services.market_data"] = mod


def main() -> int:
    T: list[tuple[str, bool, str]] = []

    def t(n, ok, d=""):
        T.append((n, bool(ok), d))

    _stub()
    from app.services.analysis import analyze_company
    from app.services import cache
    cache.clear()
    res = asyncio.run(analyze_company("9999.SR", "شركةُ فحص")) or {}

    got = res.get("fair_value")
    det = res.get("fair_value_detail") or {}
    t("١ السعرُ العادل = تقديرُ محرّكنا",
      got is not None and got == det.get("value") and got != TARGET,
      f"المعروض {got} · المحرّك {det.get('value')} · هدفُ المحللين {TARGET}")

    up = res.get("fair_value_upside_pct")
    want = (round((got - PRICE) / PRICE * 100, 1)
            if isinstance(got, (int, float)) else None)
    t("٢ الفجوةُ محسوبةٌ من الرقم نفسِه", up is not None and up == want,
      f"المتوقَّع {want}% · المخرَج {up}%")

    t("٣ هدفُ المحللين حقلٌ باسمه لا يلبس السعرَ العادل",
      res.get("analyst_target") == TARGET,
      f"analyst_target={res.get('analyst_target')}")

    # ٤ — نصُّ الذكاء: يُبنى التوجيهُ فعلاً ويُقرأ أيُّ رقمٍ تحت أيّ اسم
    from app.services import ai_content
    _vl = getattr(ai_content, "value_lines", None)
    if not callable(_vl):
        t("٤ نصُّ الذكاء يضع كلَّ رقمٍ تحت اسمه", False,
          "لا دالّةَ تبني سطرَي القيمة — فلا يُقاس ما يُقال للنموذج")
    else:
        L = _vl(res)
        _an = [x for x in L if "هدف المحللين" in x]
        _fv = [x for x in L if "السعر العادل" in x]
        ok4 = (len(_an) == 1 and str(TARGET) in _an[0]
               and str(got) not in _an[0]
               and len(_fv) == 1 and str(got) in _fv[0]
               and str(TARGET) not in _fv[0])
        t("٤ نصُّ الذكاء يضع كلَّ رقمٍ تحت اسمه", ok4,
          " | ".join(L)[:120])

    # ٥ — الفرزُ على المصدرَين نفسَيهما، كلٌّ باسمه
    ssrc = open(os.path.join(_ROOT, "backend", "app", "services",
                             "market_screener.py"), encoding="utf-8").read() \
        if os.path.exists(os.path.join(_ROOT, "backend", "app", "services",
                                       "market_screener.py")) else \
        open("/app/app/services/market_screener.py", encoding="utf-8").read()
    t("٥ الفرزُ: سعرُنا من مخزن المحرّك وهدفُ المحللين باسمه",
      'r["fair_value"] = stored.get("fair_value")' in ssrc
      and 'r["analyst_target"] = pick("target_mean_price")' in ssrc,
      "fair_value ← المحرّك · analyst_target ← target_mean_price")

    print("═" * 60)
    print("  السعرُ العادل — مصدرٌ واحد")
    print("═" * 60)
    for n, ok, d in T:
        print(f"  {'PASS' if ok else 'FAIL'}  {n:36} {d}")
    bad = [n for n, ok, _ in T if not ok]
    print("═" * 60)
    print("  ✔ كلُّ رقمٍ باسمه ومصدرِه في كلّ قسم." if not bad
          else f"  ✖ أخفق {len(bad)}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
