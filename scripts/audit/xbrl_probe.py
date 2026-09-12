#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D263 — قراءةُ قوائم XBRL على الخادم: يُرى المخرَجُ قبل أن يُعتمد.
#
#   docker exec sp_backend python /app/scripts/audit/xbrl_probe.py 2010
#   docker exec sp_backend python /app/scripts/audit/xbrl_probe.py 2010 --apply
#   docker exec sp_backend python /app/scripts/audit/xbrl_probe.py --market 20 --apply
#
# الملفُّ الواحد ميجاباتٌ عدّة، فالمسحُ **مرحليّ** لا دفعةً واحدة. وبلا
# `--apply` لا يُكتب شيء: تُطبع الفتراتُ وبنودُها ليُرى ما فُهم.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import sys

for _p in ("/app", "backend", "."):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ARGS = sys.argv[1:]
APPLY = "--apply" in ARGS
N = None
if "--market" in ARGS:
    i = ARGS.index("--market")
    N = int(ARGS[i + 1]) if i + 1 < len(ARGS) and ARGS[i + 1].isdigit() else 10
SYMS = [a for a in ARGS if a.isdigit() and len(a) == 4]

FIELDS = ("revenue", "net_income", "eps", "equity", "total_assets",
          "total_liabilities", "debt_ratio", "operating_cash_flow",
          "capex", "free_cash_flow", "ending_cash", "interest_expense")


def show(rec):
    for kind in ("annual", "quarterly"):
        rows = rec.get(kind) or []
        print(f"   {kind}: {len(rows)} فترة")
        for p in rows[-3:]:
            got = [f for f in FIELDS if p.get(f) is not None]
            print(f"     · {p.get('as_of')} — {len(got)} بنداً: "
                  + "، ".join(f"{f}={p[f]:,.0f}" if isinstance(p[f], float) and abs(p[f]) > 1000
                              else f"{f}={p[f]}" for f in got[:6]))
    for f in rec.get("files") or []:
        print(f"   ملفّ: {f}")


async def main() -> int:
    from app.services import tadawul_xbrl as xb
    from app.services.tadawul_market import snapshot

    syms = SYMS
    if N:
        snap = snapshot() or {}
        if not snap:
            print("… لا لقطةَ سوقٍ محفوظة — شغّلها أوّلاً أو مرّر رموزاً.")
            return 1
        syms = list(snap)[:N]
    if not syms:
        print("… مرّر رمزاً (‏2010) أو ‎--market N")
        return 2

    if not APPLY:
        for s in syms:
            print("========", s)
            files = await xb.filings_for(s)
            print(f"   ملفّاتُ XBRL: {len(files)}"
                  + (f" · الأحدث {files[0]['filed']}" if files else ""))
            if not files:
                continue
            rec = await xb.read_symbol(s)
            if not rec:
                print("   ✖ لم يُفهم أيُّ ملفّ")
                continue
            show(rec)
        print("\nلم يُكتب شيء. للاعتماد: أضف ‎--apply")
        return 0

    rep = await xb.refresh(syms)
    print("التقرير:", rep)
    for s in syms[:3]:
        rows = xb.for_symbol(s)
        print(f"   {s}: {len(rows)} فترةً سنويةً محفوظة"
              f" · {len(xb.for_symbol(s, 'quarterly'))} ربعية")
    return 0


raise SystemExit(asyncio.run(main()))
