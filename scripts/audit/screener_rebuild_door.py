#!/usr/bin/env python3
"""إعادةُ بناء الفرز الآن (ما يفعله المجدوِلُ يومياً) — بعد إصلاحٍ يغيّر صفوفه (D645: المشطوبُ يخرج · القصيرُ يظهر)."""
import asyncio, sys
sys.path.insert(0, "/app")
from app.services.market_screener import compute_screener
rows = asyncio.run(compute_screener()) or []
syms = {str(r.get("symbol")).replace(".SR", "") for r in rows}
print(f"صفوفُ الفرز {len(rows)} · أرماح {'6022' in syms} · بتروكيم {'2002' in syms} · بروج {'8270' in syms} · دور {'4010' in syms}")
