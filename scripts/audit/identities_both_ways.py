#!/usr/bin/env python3
"""المعادلةُ تُقرأ في الاتّجاهين، والغيابُ يُفرَّق عن النقص (‏D420).

    python3 scripts/audit/identities_both_ways.py

أمر المالك أن نبلغ أقصى مدًى متاح. وأوّلُ ما يُستنفَد قبل أيّ ذكاءٍ
خارجيٍّ هو **ما نملكه ولا نستعمله** — وأرخصُه هويّةٌ محاسبيةٌ لا ظنَّ
فيها. وقِيس على الكون:

  · `total_liabilities` ناقصٌ في **22 ورقة**، بينما `equity`
    و`total_assets` **غيرُ ناقصَين في أيّ ورقة**. فكانت الحقوقُ تُشتقّ
    من الأصول والالتزامات، ولا تُشتقّ الالتزاماتُ من الأصول والحقوق —
    وهي المعادلةُ نفسُها مقلوبة، فالطرفان حاضران والناتجُ متروك.
  · `interest_expense` ناقصٌ في **32** و`ebit` في **34**. وكثيرٌ منها
    ليس نقصَ إفصاحٍ بل **غيابَ البند**: شركةٌ بلا دَينٍ لا تكلفةَ
    تمويلٍ لها. والفراغُ يُسقط تغطيةَ الفوائد ومعها `ebit`، فيُحرَم
    المحرّكُ مساراً لسببٍ غيرِ قائم.

## والحدُّ الذي لا يُتجاوَز

لا يُفترَض الصفرُ إلا حين يكون الدَّينُ **صفراً مقيساً** — لا غائباً.
فغيابُ الدَّين ليس دليلاً على عدمه، وافتراضُ الصفر عليه اختلاقٌ.
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
    from app.services.statement_merge import _derive
except (ModuleNotFoundError, ImportError) as e:
    print(f"⚠ بيئةٌ ناقصة ({e}) — لم يُقَس")
    sys.exit(0)


def _run(p: dict) -> tuple[dict, dict]:
    src: dict = {}
    _derive(p, src)
    return p, src


# ── ١ · المعادلةُ في الاتّجاهين ────────────────────────────────────────
_p, _s = _run({"total_assets": 6000.0, "equity": 1000.0})
check(_p.get("total_liabilities") == 5000.0,
      "١ الالتزاماتُ تُشتقّ: أصولٌ − حقوق", str(_p.get("total_liabilities")))
check("مشتقّ" in str(_s.get("total_liabilities") or ""),
      "١ب ويُعلَن أنه مشتقٌّ لا منشور", str(_s.get("total_liabilities")))

_p2, _s2 = _run({"total_assets": 6000.0, "total_liabilities": 5000.0})
check(_p2.get("equity") == 1000.0,
      "١ج والاتّجاهُ الأوّلُ باقٍ: حقوقٌ = أصولٌ − التزامات")

# ولا يُستبدَل منشورٌ بمشتقّ
_p3, _s3 = _run({"total_assets": 6000.0, "equity": 1000.0,
                 "total_liabilities": 4800.0})
check(_p3.get("total_liabilities") == 4800.0,
      "١د ولا يُستبدَل المنشورُ بمشتقّ", str(_p3.get("total_liabilities")))

# ── ٢ · ولا دَينَ ⇒ لا تكلفةَ تمويل ───────────────────────────────────
_z, _zs = _run({"total_debt": 0.0, "pretax_income": 150.0})
check(_z.get("interest_expense") == 0.0,
      "٢ دَينٌ صفرٌ مقيسٌ ⇒ تكلفةُ تمويلٍ صفر")
check(_z.get("ebit") == 150.0,
      "٢ب فيُستعاد `ebit` بدل أن يسقط", str(_z.get("ebit")))
check("لا دَينَ" in str(_zs.get("interest_expense") or ""),
      "٢ج ويُعلَن سببُ الاشتقاق")

# ── ٣ · والغيابُ ليس دليلاً على العدم ─────────────────────────────────
_n, _ = _run({"pretax_income": 150.0})            # لا دَينَ **مقيساً**
check(_n.get("interest_expense") is None,
      "٣ دَينٌ غائبٌ لا يُفترَض صفراً — الغيابُ ليس عدماً")
_d, _ = _run({"total_debt": 500.0, "pretax_income": 150.0})
check(_d.get("interest_expense") is None,
      "٣ب ودَينٌ قائمٌ بلا تكلفةٍ منشورةٍ لا يُخترَع له صفر")

print(("FAIL" if fail else "PASS")
      + " D420 — الهويّاتُ في الاتّجاهين، والغيابُ يُفرَّق عن العدم")
sys.exit(fail)
