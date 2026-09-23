#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D278 — خلاصةٌ تحلّل الأرقام، ونموذجٌ لا يُصدَّق على كلمته.
#
# طلب المالك: «الخلاصةُ تعتمد على جيمناي ثمّ ذكاءٍ قاعديٍّ يحلّل الأرقامَ
# بشكلٍ واقعيٍّ وليس ديكوراً — للسنويّ وللربع سنويّ».
#
# وخطرُ إدخال نموذجٍ لغويٍّ في شاشةٍ ماليةٍ واحدٌ: **رقمٌ لم يُقَس**. جملةٌ
# أنيقةٌ فيها «نموٌّ 42٪» لم يحدث أخطرُ من غياب الجملة كلِّها.
#
#   ٠· الإشاراتُ تُحسب من القوائم — لا تُقدَّر
#   ١· والقاعديُّ يقول السببَ لا الصفة
#   ٢· ونقصُ بندٍ يُسكت ما يخصّه ولا يختلق بديلاً
#   ٣· وكلُّ رقمٍ في سطر النموذج يُطابَق بما قِيس
#   ٤· وما لم يُطابِق يُرَدُّ السطرُ كلُّه — لا نصفُ جملة
#   ٥· والغيابُ يُكتب قاعدياً — لا تُترك الخلاصةُ فارغة
#   ٦· واللونُ يبقى من الحكم الحتميّ لا من نصِّ النموذج
#   ٧· والربعيُّ يأخذ الخلاصةَ كالسنويّ
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
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


from app.services import financial_brief as fb  # noqa: E402

WEAK = [
    {"year": 2024, "revenue": 1.0e10, "net_income": 1.2e9,
     "operating_cash_flow": 1.5e9, "free_cash_flow": 8e8,
     "debt_ratio": 31.0, "interest_coverage": 9.0},
    {"year": 2025, "revenue": 1.1e10, "net_income": 1.0e9,
     "operating_cash_flow": 5e8, "free_cash_flow": -2e8,
     "debt_ratio": 38.0, "interest_coverage": 2.4},
]

# ── ٠ · الإشاراتُ مقيسة ─────────────────────────────────────────────────
sig = fb.signals(WEAK)
check(sig["نمو_الإيراد"] == 10.0 and sig["نمو_صافي_الربح"] == -16.7
      and sig["تحويل_النقد"] == 50.0 and sig["تغير_المديونية"] == 7.0,
      "٠ الإشاراتُ تُحسب من القوائم لا تُقدَّر", str(sig)[:90])

# ── ١ · القاعديُّ يقول السبب ────────────────────────────────────────────
line = fb.rule_line(sig, "annual")
check("10" in line and "16.7" in line and "50" in line,
      "١ والقاعديُّ يذكر الحركةَ ومقدارَها — لا «أداءٌ جيّد»", line[:90])
check("والتدفّقُ الحرُّ سالب" in line or "سالب" in line,
      "١ب ويسمّي ما يناقض الإشارةَ الحاكمة", line[:90])
for bad in ("يُنصح", "ننصح", "فرصة", "ممتاز", "رائع", "اكتشف"):
    check(bad not in line, f"١ج ولا كلمةَ ديكورٍ ولا توصية — «{bad}»")

# ── ٢ · نقصُ بندٍ يُسكت ما يخصّه ────────────────────────────────────────
thin = fb.signals([{"year": 2025, "revenue": 1.0e10}])
check("تحويل_النقد" not in thin and "المديونية" not in thin,
      "٢ بندٌ غائبٌ لا إشارةَ له — ولا يُقدَّر", str(thin))
check(fb.rule_line({}, "annual").startswith("لا تكفي"),
      "٢ب وبلا إشاراتٍ يُقال ذلك صراحةً", fb.rule_line({}, "annual"))

# ── ٣ · ٤ · رقمٌ لم يُقَس يردّ السطر ────────────────────────────────────
ok, why = fb.verify("إيرادٌ يرتفع 10٪ وربحٌ يتراجع 16.7٪.", sig)
check(ok, "٣ سطرٌ كلُّ أرقامه مقيسةٌ يُقبل", why)
ok2, why2 = fb.verify("الإيراد نما 42٪ بقوة.", sig)
check(not ok2 and "لم يُقَس" in why2,
      "٤ ورقمٌ لم يُقَس يردُّ السطرَ كلَّه — لا يُصحَّح نصفُ جملة", why2)
check(not fb.verify("سطرٌ\nثانٍ 10٪", sig)[0], "٤ب وأكثرُ من سطرٍ مردود")
check(not fb.verify("", sig)[0], "٤ج والفارغُ مردود")
check(fb.verify("إيرادٌ يرتفع 10٪ ومديونيةٌ عند 38٪.", sig)[0],
      "٤د والتقريبُ المطابقُ مقبولٌ — لا تشدّدَ بلا معنى")

# ── ٥ · الغيابُ يُكتب قاعدياً ───────────────────────────────────────────
async def _none(*a, **k):
    return None


fb.ai_line = _none                                               # type: ignore[assignment]
out = asyncio.run(fb.brief(WEAK, kind="annual", symbol="T1"))
check(out["by"] == "قاعدي" and len(out["line"]) > 20,
      "٥ بلا جيمناي تُكتب الخلاصةُ قاعدياً — لا تُترك فارغة", out["line"][:70])


async def _good(sig_, kind, name):
    return "إيرادٌ يرتفع 10٪ وربحٌ يتراجع 16.7٪."


fb.ai_line = _good                                               # type: ignore[assignment]
# ‏D447: الطلبُ لا ينتظر النموذج — سطرُه يُكتب في الخلفية ويُقرأ في الفتح
# التالي. فيُنادى مرّتين في حلقةٍ واحدة، والثانيةُ هي ما يراه القارئ.
async def _twice():
    await fb.brief(WEAK, kind="annual", symbol="T2")
    await asyncio.sleep(0.2)
    return await fb.brief(WEAK, kind="annual", symbol="T2")
out2 = asyncio.run(_twice())
check(out2["by"] == "جيمناي" and "16.7" in out2["line"],
      "٥ب ومع جيمناي يُعلَن أنه كاتبُها", str(out2)[:80])

# ── ٦ · اللونُ من الحكم الحتميّ ─────────────────────────────────────────
MK = (ROOT / "backend" / "app" / "api" / "v1" / "endpoints"
      / "market.py").read_text(encoding="utf-8")
check('"verdict_tone": verdict_tone' in MK and '"verdict": _b["line"]' in MK,
      "٦ الجملةُ من الخلاصة واللونُ من الحكم الحتميّ — لا يُلوَّن شريطٌ برأي نموذج")
check('"verdict_rule": verdict' in MK,
      "٦ب والحكمُ الحتميُّ يبقى في الاستجابة — لا يُفقَد بإدخال النموذج")

# ── ٧ · الربعيُّ كالسنويّ ───────────────────────────────────────────────
check('kind="quarterly"' in MK,
      "٧ والربعيُّ يأخذ الخلاصةَ كالسنويّ — بأمر المالك")
qi = MK.index('kind="quarterly"')
check("_vt(_fv(_qp))" in MK,
      "٧ب وللربعيّ لونُه من حكمه لا من فراغ")

# ── ٨ · ولا حاشيةَ مصدرٍ لم يأذن بها المالك ─────────────────────────────
FT = (ROOT / "frontend" / "src" / "components" / "analysis"
      / "FinancialsTable.tsx").read_text(encoding="utf-8")
check("المصدر {data.source}" not in FT and "{data.source}" not in FT,
      "٨ وحاشيةُ «المصدر …» أُزيلت — لم يأذن بها المالك")

print(("FAIL" if fail else "PASS") + " D278 — خلاصةٌ تحلّل، ونموذجٌ يُطابَق")
raise SystemExit(fail)
