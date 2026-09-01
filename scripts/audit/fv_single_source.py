"""القيمةُ العادلة مصدرٌ واحد — حارسُ D147.

كان في التطبيق رقمان يحملان اسمَ «القيمة العادلة»: قيمتُنا المحسوبة من
قوائم الشركة، و`target_mean_price` — متوسّطُ أهداف المحلّلين، تنبّؤُ
سعرٍ لسنة ورأيُ بشر. فاختلفت صفحةُ الشركة عن صفحة السوق وعن نصّ الذكاء
في رقمٍ يبني عليه المالك قرارَه.

والعلاجُ لم يكن تغييرَ الاسم — بل وضعَ الرقم الصحيح في كلّ موضع، وإبقاءَ
هدف المحلّلين حقلاً مستقلّاً بوصفه الصحيح.

    python scripts/audit/fv_single_source.py
"""

from __future__ import annotations

import inspect
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_SRC = os.path.join(_ROOT, "backend", "app")


def _read(rel: str) -> str:
    for base in (_SRC, "/app/app"):
        p = os.path.join(base, rel)
        if os.path.exists(p):
            return open(p, encoding="utf-8").read()
    return ""


def main() -> int:
    T: list[tuple[str, bool, str]] = []

    def t(n, ok, d=""):
        T.append((n, bool(ok), d))

    # ١ — لا يُسنَد هدفُ المحلّلين إلى حقل القيمة العادلة
    bad = []
    for rel in ("services/market_screener.py", "services/analysis.py",
                "services/governance.py", "api/v1/endpoints/ai.py",
                "api/v1/endpoints/market.py"):
        src = _read(rel)
        for m in re.finditer(r'\[["\']fair_value["\']\]\s*=\s*([^\n]+)', src):
            if "target_mean_price" in m.group(1):
                bad.append(f"{rel}: {m.group(1).strip()[:50]}")
    t("١ لا هدفَ محلّلين في حقل القيمة العادلة", not bad,
      "لا إسناد" if not bad else " · ".join(bad))

    # ٢ — لا يُسمّى هدفُ المحلّلين «القيمة العادلة» في نصٍّ يُعرض
    mislabel = []
    for rel in ("services/ai_content.py", "services/market_screener.py"):
        for line in _read(rel).splitlines():
            ls = line.strip()
            if ls.startswith("#"):
                continue
            if "target_mean_price" in ls and "القيمة العادلة" in ls:
                mislabel.append(f"{rel}: {ls[:60]}")
    t("٢ هدفُ المحلّلين يُسمّى باسمه", not mislabel,
      "لا تسميةَ خاطئة" if not mislabel else " · ".join(mislabel))

    # ٣ — الفرزُ ينادي المحرّكَ الموحّد نفسه
    from app.services import market_screener as ms
    fsrc = inspect.getsource(ms._fair_value)
    t("٣ الفرزُ ينادي المحرّكَ الموحّد",
      "fair_value as _fvmod" in fsrc and "_fvmod.compute(" in fsrc,
      "services/fair_value.compute — نفسُ صفحة الشركة")

    # ٤ — بلا قوائمَ مخزَّنة: لا رقمَ ولا نداء
    import asyncio
    got = asyncio.run(ms._fair_value("0000.SR", 50.0, "الاتصالات"))
    t("٤ بلا قوائمَ لا قيمةَ مختلَقة", got == (None, None, None),
      f"بلا قوائم → {got}")

    # ٥ — حقلُ هدف المحلّلين قائمٌ ومستقلّ
    ssrc = _read("services/market_screener.py")
    t("٥ هدفُ المحلّلين حقلٌ مستقلّ",
      '"analyst_target"' in ssrc and '"analyst_upside_pct"' in ssrc,
      "analyst_target · analyst_upside_pct")

    print("═" * 62)
    print("  القيمةُ العادلة — مصدرٌ واحد")
    print("═" * 62)
    for n, ok, d in T:
        print(f"  {'PASS' if ok else 'FAIL'}  {n:38} {d}")
    bad_n = [n for n, ok, _ in T if not ok]
    print("═" * 62)
    print("  ✔ رقمٌ واحدٌ باسمٍ واحد." if not bad_n
          else f"  ✖ أخفق {len(bad_n)}")
    return 0 if not bad_n else 1


if __name__ == "__main__":
    sys.exit(main())
