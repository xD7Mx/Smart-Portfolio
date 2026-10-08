#!/usr/bin/env python3
"""قياسُ الإصدار المرشَّح قبل نشره (‏D642) — طريقُ الإصدار الثاني عبر حارس التجميد.

البوابةُ تقرأ المخزنَ الذي تكتبه مسحةُ الإنتاج، فقياسُها كما هي يعني نشرَ المرشَّح قبل اعتماده. فهذا الكاشف:
  ١ يحسب كلَّ شركةٍ بشيفرة المرشَّح داخل عمليّته (`_one` من المسحة — بلا كتابةٍ في أيّ مخزن)،
  ٢ يبني مخزناً ومخزنَ أحكامٍ في الذاكرة فوق الحاليَّين،
  ٣ يُشغّل البوابتين عليهما — فتخرج مقاييسُ المرشَّح وأرقامُ الإنتاج على الإصدار المجمَّد لم تُمسّ.

    docker exec sp_backend python /app/scripts/audit/candidate_gate.py

ثمّ: `engine_report_save.py <مخرَج السعر العادل> <مخرَج المحرّكات ٢–٥>` لبصمة المرشَّح، ويحكم حارسُ التجميد."""
import asyncio, runpy, sys
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.data.universe import is_nomu
from app.services import content_engine, lastgood
from app.services.market_valuation_sweep import _one


async def compute():
    syms = sorted(s for s in main_market(MARKET_UNIVERSE) if not is_nomu(s))
    sem = asyncio.Semaphore(8)
    res = await asyncio.gather(*(_one(s, sem) for s in syms), return_exceptions=True)
    return {r[0]: r[1] for r in res if isinstance(r, tuple)}


done = asyncio.run(compute())
store0 = content_engine.fund_store_load()
store = {k: dict(v) for k, v in store0.items()}
deep = {k: (dict(v) if isinstance(v, dict) else v) for k, v in (lastgood.load("governance:deep") or {}).items()}
for s, v in done.items():
    vd = v.pop("_verdict", None) or {}
    v.pop("_failed", None)
    store[s] = {**(store.get(s) or {}), **v}
    if vd.get("decision") is not None or "red_lines" in vd:
        deep[s] = {**(deep.get(s) or {}), **({"decision": vd["decision"]} if vd.get("decision") is not None else {}),
                   **({"red_lines": vd["red_lines"]} if "red_lines" in vd else {})}

_orig_load = lastgood.load
content_engine.fund_store_load = lambda: store
lastgood.load = lambda key, *a, **k: deep if key == "governance:deep" else _orig_load(key, *a, **k)
print(f"@@CANDIDATE@@ حُسبت {len(done)} شركةً بشيفرة المرشَّح — بلا كتابةٍ في المخزن\n")
print("════ بوابةُ السعر العادل ════")
runpy.run_path("/app/scripts/audit/engine_gate.py", run_name="__main__")
print("\n════ بوابةُ المحرّكات ٢–٥ ════")
runpy.run_path("/app/scripts/audit/engines_gate_v1.py", run_name="__main__")
