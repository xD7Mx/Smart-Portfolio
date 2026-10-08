#!/usr/bin/env python3
"""مراجعُ InvestingPro التي يكتبها المالك (`reference_scores`) — حجمُ العيّنة وتغطيتُها للقطاعات الموسومة، وبُعدُ
قيمتنا المنشورة عنها مقابل بُعد السعر نفسِه. قارئٌ فقط: لا يحسب ولا يكتب."""
import statistics as st, sys, collections
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.services import reference_scores as ref
from app.services.content_engine import fund_store_load
from app.services.market_screener import get_cached_screener

syms = ref.all_symbols()
print(f"مراجعُ مُدخَلة: {len(syms)} · الملفّ {ref.path()}")
store = fund_store_load()
rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
by = collections.defaultdict(list)
for s in syms:
    r = ref.get(s) or {}
    ipv = r.get("fair_value") or r.get("fv") or r.get("value")
    fv, px = (store.get(s) or {}).get("fair_value"), (rows.get(s) or {}).get("price")
    sec = (MARKET_UNIVERSE.get(s) or {}).get("sector")
    print(f"  {s} {(MARKET_UNIVERSE.get(s) or {}).get('name_ar')} ({sec}) · مرجع {ipv} · قيمتنا {fv} · سعر {px} · مفاتيح {sorted(r)[:8]}")
    if isinstance(ipv, (int, float)) and ipv > 0 and isinstance(px, (int, float)) and px > 0:
        by[sec].append((abs(fv / ipv - 1) if isinstance(fv, (int, float)) and fv > 0 else None, abs(px / ipv - 1)))
for sec, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    ours = [a for a, _ in v if a is not None]
    print(f"  {sec}: n={len(v)} · قيمتُنا {st.median(ours):.0%}" if ours else f"  {sec}: n={len(v)}",
          f"· السعرُ نفسُه {st.median([b for _, b in v]):.0%}")
