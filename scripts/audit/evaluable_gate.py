#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D201 — ما امتنع التطبيقُ عن الحكم عليه لا يُرشَّح «فرصة».
#
# رأى المالكُ غازكو (‏2080) تُعرض في «تحليل الذكاء» وصفحتُها تقول «بيانات
# غير كافية». والسببُ أن مرشِّح الفرص كان يشترط وجودَ `ai_score` وحدَه،
# ولا يسأل عن الأهليّة. والدرجةُ فيها شقٌّ فنّيٌّ يُحسب من السعر وحدَه —
# فتخرج برقمٍ ولو خلت القوائمُ من كلّ بند.
#
# فحصٌ سلوكيّ: يُشغَّل المرشِّحُ على شركتين، إحداهما غيرُ مؤهَّلة، ويُنظر
# أتظهر أم تُستبعد. ولو عاد الشرطُ القديم لظهرت فيسقط الفحص.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in ("/app", str(ROOT / "backend"), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

fail = 0


def say(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")


async def main() -> int:
    from app.services import market_movers as mm

    async def _fake_analyze(symbol, name=None, db=None, **_k):
        # الأولى مؤهَّلة، والثانية درجتُها موجودةٌ وأهليّتُها منتفية —
        # وهي حالةُ غازكو بعينها.
        ok = symbol == "1111"
        return {"ai_score": 71 if ok else 69, "evaluable": ok,
                "financial": {"score": 70 if ok else None},
                "fundamentals": {}, "valuation": {}}

    class _Res:
        def all(self):
            return []

    class _DB:
        async def execute(self, *_a, **_k):
            return _Res()

    import app.services.analysis as an
    real = an.analyze_company
    an.analyze_company = _fake_analyze
    try:
        rows = [{"symbol": "1111", "name": "مؤهَّلة", "price": 10.0, "change_pct": 1.0},
                {"symbol": "2080", "name": "غيرُ مؤهَّلة", "price": 20.0, "change_pct": 2.0}]
        out = await mm.compute_investment_opportunities(_DB(), rows)
    finally:
        an.analyze_company = real

    syms = [r["symbol"] for r in out]
    say("2080" not in syms,
        "١ غيرُ المؤهَّلة لا تُرشَّح فرصةً", f"الظاهر: {syms or 'لا شيء'}")
    say("1111" in syms, "٢ والمؤهَّلةُ تبقى", f"الظاهر: {syms or 'لا شيء'}")

    print()
    print("النتيجة:", "نظيف ✔" if not fail else "فيه ملاحظات ✘")
    return fail


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
