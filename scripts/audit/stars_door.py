"""كاشفُ «نجوم تاسي» (D522): كم شركةً تعبر كلَّ بوّابة، ومن السلّةُ، وأداؤها.

    docker exec sp_backend python /app/scripts/audit/stars_door.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from app.services import tasi_stars as S  # noqa: E402
from app.services.market_screener import get_cached_screener  # noqa: E402

rows = get_cached_screener() or []
print("صفوفُ الفرز:", len(rows))
gates = [("عادل ≥15٪", lambda r: (r.get("fair_value_upside_pct") or -1) >= S.MIN_UPSIDE),
         ("ثقةٌ غيرُ منخفضة", lambda r: r.get("fair_value_conf") not in (None, "منخفضة")),
         ("درجة ≥70", lambda r: (r.get("finance_score") or 0) >= S.MIN_SCORE),
         ("بلا خطٍّ أحمر", lambda r: not (r.get("red_lines") or 0)),
         ("قوائم ≤270ي", lambda r: (r.get("stmt_age_days") or 9999) <= S.MAX_STMT_DAYS),
         ("غيرُ «غير متوافقة»", lambda r: r.get("sharia") != "NON_COMPLIANT")]
left = [r for r in rows if S._main_share(r.get("symbol"))]
for name, f in gates:
    left = [r for r in left if f(r)]
    print(f"  بعد {name}: {len(left)}")
rec = asyncio.run(S.build(force=True))
print("تاسي 12ش:", rec.get("tasi_ret_12m"), "· السلّة:", len(rec.get("members") or []), rec.get("error") or "")
for m in rec.get("members") or []:
    print(f"  {m['symbol']} {m.get('name')} · عادل {m['upside']}% · 12ش {m['ret_12m']}% (+{m['excess']}) · درجة {m['finance_score']} · {m['score']}")
