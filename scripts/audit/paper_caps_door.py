#!/usr/bin/env python3
"""كاشفُ القيمة السوقية المحسوبة في ورقة التقرير (‏D746) — قارئٌ فقط.
الأسهمُ القائمة من الإفصاح × السعر: كم شركةً تُغطّى، وأكبرُ خمسَ عشرةَ بأسهمها وأرباحها وربحية سهمها والأسهمِ الضمنية (الربح ÷ ربحية السهم)
— ليُعرف أين تخطئ وحدةُ الأسهم قبل أن يُرتَّب «الأكبرُ وزناً» أو يُحسب مكرّرُ السوق."""
import os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
from app.services import tadawul_market as TM   # noqa: E402
from app.services.tadawul_xbrl import for_symbol   # noqa: E402
from app.data.universe import is_main   # noqa: E402
from app.data.market_universe import MARKET_UNIVERSE as U   # noqa: E402
rows = {s: r for s, r in (TM.usable_rows()[0] or {}).items() if is_main(s)}
out, flags, none = [], 0, 0
for s, r in rows.items():
    rs = for_symbol(s, "annual") or []
    if not rs:
        none += 1
        continue
    p = rs[-1]
    if p.get("shares_unit_gap") or p.get("shares_mismatch"):
        flags += 1
    sh, ni, eps = p.get("shares_outstanding"), p.get("net_income"), p.get("eps")
    px = r.get("price") or 0
    imp = ni / eps if isinstance(ni, (int, float)) and isinstance(eps, (int, float)) and eps else None
    out.append((s, (U.get(s) or {}).get("name_ar"), px, sh, ni, eps, imp, (sh or 0) * px, p.get("period") or p.get("year") or p.get("date")))
print(f"الرئيسي {len(rows)} · بإفصاح {len(out)} · بلا إفصاح {none} · موسومة {flags} · بأسهمٍ {sum(1 for o in out if o[3])}")
out.sort(key=lambda o: -o[7])
for o in out[:15]:
    ratio = (o[3] / o[6]) if o[3] and o[6] else None
    print(f"  {o[0]} {o[1]} سعر {o[2]} · أسهم {o[3]} · ربح {o[4]} · ربحية {o[5]} · ضمنية {o[6]} · نسبة {ratio and round(ratio, 3)} · قيمة {o[7] / 1e9:,.1f} مليار · {o[8]}")
bad = [o for o in out if o[3] and o[6] and not (0.8 < o[3] / o[6] < 1.25)]
print("نسبٌ شاذّة:", len(bad), [(o[0], round(o[3] / o[6], 3)) for o in bad[:25]])
