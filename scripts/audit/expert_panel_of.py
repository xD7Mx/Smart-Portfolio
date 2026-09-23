#!/usr/bin/env python3
"""مَن حكم ومَن صمت في مجلس الخبراء — ولماذا (D433).

    docker exec sp_backend python /app/scripts/audit/expert_panel_of.py

اكتشف المالكُ في اختباره «العربية للخدمات» (‏4071): سعرٌ عادلٌ 50.34
محسوبٌ من قوائمها، وبجانبه «درجة الجودة المالية: بانتظار القوائم» — والقوائمُ
وصلت. والسببُ المُعلَن في المحرّك «خبيران فقط استطاعا الحكم» والنصابُ
ثلاثة. فيُطبع هنا المجلسُ كما بُني: كلُّ خبيرٍ حكم، وكلُّ مُدخَلٍ يحتاجه
خبيرٌ صامت وهل وصل — فيُعرف أيُّ الشهود غاب ومن أين كان يأتي. قارئٌ فقط.
"""
from __future__ import annotations

import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

SYMS = ("4071", "1810", "4191", "2080")
INPUTS = ("buffett_quality_score", "buffett_applicable", "peg_ratio",
          "analyst_recommendation", "analyst_upside_pct", "roe_avg",
          "payout_ratio")


async def main() -> int:
    try:
        from app.services.analysis import analyze_company
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0
    for s in SYMS:
        a = await analyze_company(f"{s}.SR", allow_supplement=False) or {}
        fin = a.get("financial") or {}
        panel = fin.get("expert_panel") or a.get("expert_panel") or []
        feats = (a.get("features") or fin.get("features") or {})
        print(f"═ {s} · درجة={fin.get('score')} · نمط={(fin.get('spec') or {}).get('archetype')} ═")
        for e in panel:
            if not isinstance(e, dict):
                continue
            print(f"   {e.get('tone','?'):6s} {e.get('role') or '':7s} "
                  f"{e.get('expert') or e.get('name')} — {e.get('metric')}: {e.get('value')}")
        if feats:
            for k in INPUTS:
                v = feats.get(k)
                v = v.get("value") if isinstance(v, dict) else v
                print(f"   مُدخَل {k:24s} = {v}")
        sp = fin.get("spec") or {}
        print(f"   ناقصُ المواصفة: {sp.get('missing')}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
