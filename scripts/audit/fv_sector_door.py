"""كاشف (قراءةٌ فقط): السعرُ العادل قطاعاً قطاعاً — التغطيةُ والثقةُ والشواذّ، والانحرافُ عن متوسّط أهداف بيوت الخبرة
(شاهدٌ مستقلّ حيث يوجد). الريتات ثمّ البتروكيماويات ثمّ التأمين ثمّ البنوك ثمّ البقية.

    docker exec sp_backend python /app/scripts/audit/fv_sector_door.py
"""
import json
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, "/app")
from app.services.market_screener import get_cached_screener
from app.services.statement_merge import archetype_of

rows = get_cached_screener() or []
# ما تعرضه الشاشةُ فعلاً: السعرُ العادل من مخزن المسحة لا من نسخة الصفّ المحفوظة (D458)
from app.services.content_engine import fund_store_load
_store = fund_store_load() or {}
for r in rows:
    st = _store.get(r.get("symbol")) or _store.get(str(r.get("symbol")).replace(".SR", "")) or {}
    if "fair_value" in st:
        r["fair_value"] = st.get("fair_value") if isinstance(st.get("fair_value"), (int, float)) and st["fair_value"] > 0 else None
        r["fair_value_conf"] = st.get("fair_value_conf")
GROUP = {"reit": "الريتات", "insurance": "التأمين", "bank": "البنوك"}
# البتروكيماويات صناعةٌ داخل «المواد الأساسية» لا نمطَ لها — فبرموزها في «تداول»
PETRO = {"2001", "2002", "2010", "2020", "2060", "2170", "2210", "2250", "2290", "2310", "2330", "2350", "2380"}
by = defaultdict(list)
for r in rows:
    s = str(r.get("symbol")).replace(".SR", "")
    try:
        a = archetype_of(s) or ""
    except Exception:                                             # noqa: BLE001
        a = ""
    g = "البتروكيماويات" if s in PETRO else next((v for k, v in GROUP.items() if k == str(a)), None)
    if not g and str(r.get("name") or "").strip().endswith("ريت"):     # «سينومي ريتيل» ليس ريتاً
        g = "الريتات"
    by[g or "بقية القطاعات"].append((a, r))
out = {}
for g in ["الريتات", "البتروكيماويات", "التأمين", "البنوك", "بقية القطاعات"]:
    L = [r for _, r in by.get(g, [])]
    has = [r for r in L if r.get("fair_value") and r.get("price")]
    ups = [float(r["fair_value"]) / float(r["price"]) * 100 - 100 for r in has]
    vs = []
    for r in has:
        t = r.get("analyst_target")
        if t:
            vs.append((r["symbol"], r.get("name"), round(float(r["fair_value"]), 2), round(float(t), 2),
                       round((float(r["fair_value"]) / float(t) - 1) * 100, 1)))
    dev = [abs(x[4]) for x in vs]
    out[g] = {"n": len(L), "with_fv": len(has),
              "conf": dict((c, sum(1 for r in has if str(r.get("fair_value_conf")) == c)) for c in {str(r.get("fair_value_conf")) for r in has}),
              "upside_median": round(statistics.median(ups), 1) if ups else None,
              "outliers": [(r["symbol"], r.get("name"), r.get("price"), r.get("fair_value"), round(u, 1)) for r, u in zip(has, ups) if u > 80 or u < -50][:8],
              "vs_analysts_n": len(vs), "vs_analysts_median_abs_dev": round(statistics.median(dev), 1) if dev else None,
              "vs_analysts_worst": sorted(vs, key=lambda x: -abs(x[4]))[:6],
              "missing": [(r["symbol"], r.get("name"), str(r.get("fair_value_unavailable") or "")[:50]) for r in L if not r.get("fair_value")][:8],
              "archetypes": sorted({a for a, _ in by.get(g, [])})[:6]}
    print(f"@@{g}@@ " + json.dumps(out[g], ensure_ascii=False, default=str)[:2800])
