#!/usr/bin/env python3
"""السوقُ الرئيسيُّ وحدَه: ‎273 شركةً · ‎22 قطاعاً · صفرُ «نمو» (D387).

    python3 scripts/audit/main_market_only.py

قضى المالك: «عند مسح السوق يكون بالمعطيات الرسمية: القطاعات ‎23
والشركات ‎273… نمو لا أريده، فدمجُ الاثنين يجعل المحرّكَ ضعيفاً».
والعلّةُ مقيسة: «نمو» سوقٌ موازٍ لا يُلزَم بما يُلزَم به الرئيسيّ —
‎54% منها فقط لها قوائمُ محفوظة مقابل ‎90% في الرئيسيّ — فقياسُ
مسطرةٍ واحدةٍ على صنفَين يُرخي المسطرةَ لا يوسّعها.

ويُحرَس ثلاثةٌ: كونُ المسحة هو **الدليلُ الرسميّ** لا اللقطة، وأن
رمزَ «نمو» لا يتسلّل ولو مُرّر بالوسيط، وأن عددَ الشركات والقطاعات
هو ما أقرّه المالكُ بعينه — فرقمٌ يتغيّر بلا إذنٍ يُكتشَف هنا.
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
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    _mm = main_market(MARKET_UNIVERSE)
except ModuleNotFoundError as e:
    print(f"⚠ حزمةٌ غيرُ منصَّبة: {e.name} — لم يُقَس (يُشغَّل في الحاوية)")
    sys.exit(0)

_secs = {(m or {}).get("sector") or "—" for m in _mm.values()}
check(len(_mm) == 273, "١ الدليلُ الرسميُّ ‎273 شركة — كما أقرّ المالك",
      f"{len(_mm)} شركة")
check(len(_secs) == 22,
      "١ب و‎22 قطاعاً (والثالثُ والعشرون صناديقُ مؤشراتٍ: أوراقٌ لا شركات)",
      f"{len(_secs)} قطاعاً")
check(not [s for s in _mm if str(s).startswith("9")],
      "١ج ولا رمزَ «نمو» في الدليل")

# ── ٢ · ومسحةُ التقييم تقرأ الدليلَ لا اللقطة ──────────────────────────
_sw = None
for c in (ROOT / "backend/app/services/market_valuation_sweep.py",
          pathlib.Path("/app/app/services/market_valuation_sweep.py")):
    if c.exists():
        _sw = c
        break
if _sw is None:
    print("⚠ لا مسحةَ تقييمٍ في مسارٍ معروفٍ — لم يُقَس")
else:
    T = _sw.read_text("utf-8")
    check("main_market(MARKET_UNIVERSE)" in T and "usable_rows()" not in T,
          "٢ كونُ المسحة من الدليل الرسميّ — لا من اللقطة (التي تحمل نمو)")
    check('if not s.startswith("9")' in T,
          "٢ب ورمزُ «نمو» لا يتسلّل ولو مُرّر بالوسيط")

# ── ٣ · وسلوكُ المسحة يُقاس لا يُقرأ نصّاً ─────────────────────────────
try:
    import asyncio

    from app.services import market_valuation_sweep as SW
    _seen: list[str] = []

    async def _fake(sym, sem):                                    # noqa: ANN001
        _seen.append(sym)
        return None

    _real = SW._one
    SW._one = _fake                                               # type: ignore
    try:
        rep = asyncio.run(SW.sweep(["1120", "9515", "2050.SR"]))
    finally:
        SW._one = _real                                           # type: ignore
    check("9515" not in _seen and set(_seen) == {"1120", "2050"},
          "٣ تُمرَّر ثلاثةٌ فيها رمزُ نمو فتُمسَح اثنتان فقط",
          f"مُسحت: {_seen}")
    check("الرئيسيّ" in str(rep.get("السوقُ") or ""),
          "٣ب والتقريرُ يقول صريحاً إن نمو مستثنىً", str(rep.get("السوقُ")))
except Exception as e:                                            # noqa: BLE001
    check(False, "٣ سلوكُ المسحة لم يُقَس", f"{type(e).__name__}: {e}")

print(("FAIL" if fail else "PASS")
      + " D387 — السوقُ الرئيسيُّ وحدَه، بمعطياته الرسمية")
sys.exit(fail)
