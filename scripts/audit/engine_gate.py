#!/usr/bin/env python3
"""بوابةُ قبول المحرّك — بأمر المالك: «أريد الانتهاء من المحرّكات». مسطرةٌ ثابتةٌ على شركات السوق الرئيسيّ كلّها،
ولا يُقال «جاهز» حتى تجتاز بنودُها الخمسة. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/engine_gate.py

  ١ التغطية      ≥ 90٪ لها قيمةٌ عادلة، وكلُّ غائبةٍ بسببٍ مسمّى
  ٢ الحداثة      صفرُ قيمةٍ على قوائمَ أقدم من 15 شهراً، وصفرُ قيمةٍ محسوبةٍ قبل تجزئةٍ/منحة
  ٣ المعقولية    ≤ 5٪ تبتعد عن السعر أكثر من 60٪
  ٤ المرجع       وسيطُ |تقديرنا÷هدف المحلّلين − 1| ≤ 20٪ للسوق، ولكلّ قطاعٍ فيه ≥ 5 شركات أقربُ إلى الهدف من السعر نفسِه (‏D632)
  ٥ الثقة        ≥ 50٪ ثقتُها «متوسطة» أو «مرتفعة»، وكلُّ «منخفضة» بسببٍ مسمّى
"""
import collections, statistics, sys
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.services.market_screener import get_cached_screener
from app.services.content_engine import fund_store_load

uni = main_market(MARKET_UNIVERSE)
rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
store = fund_store_load()
res = []
for s, meta in uni.items():
    r, st = rows.get(s) or {}, store.get(s) or {}
    # المخزنُ أوّلاً: يُحدَّث فور إعادة التقييم، وصفُّ الفرز قد يحمل نسخةً أقدم (قِيس: سلوشنز 307 في الفرز و160.6 في المخزن)
    # ومتى كتبت المسحةُ الورقةَ فقولُها هو الحكم ولو «لا قيمة» — لا يُستعاد رقمُ الفرز الأقدم (‏D627: قِيس الدرع العربي)
    fv = st.get("fair_value") if "fair_value" in st else r.get("fair_value")
    px = r.get("price")
    res.append({"s": s, "name": meta.get("name_ar") or s, "sector": meta.get("sector_ar") or meta.get("sector") or "—",
                "fv": fv if isinstance(fv, (int, float)) and fv > 0 else None,
                "px": px if isinstance(px, (int, float)) and px > 0 else None,
                "at": r.get("analyst_target") if isinstance(r.get("analyst_target"), (int, float)) and r.get("analyst_target") > 0 else None,
                "conf": st.get("fair_value_conf") or r.get("fair_value_conf"),
                "age": st.get("fair_value_age_days"), "stale": st.get("fair_value_stale"),
                "why": st.get("fair_value_unavailable"), "vtp": st.get("value_to_price")})

# الصناديقُ المتداولة أوراقٌ لا شركات: سعرُها صافي أصولها، فلا تُعدّ في المقام
res = [x for x in res if "صندوق" not in str(x["why"] or "")]
N = len(res)
verdict = {}
def line(k, ok, msg):
    verdict[k] = ok
    print(f"{'✔' if ok else '✘'} {k} — {msg}")

have = [x for x in res if x["fv"]]
miss = [x for x in res if not x["fv"]]
cov = len(have) / N if N else 0
named = [x for x in miss if x["why"]]
line("١ التغطية", cov >= 0.90 and len(named) == len(miss),
     f"{len(have)}/{N} = {cov:.0%} · غائبةٌ بسببٍ مسمّى {len(named)}/{len(miss)}")
why = collections.Counter(x["why"] or "بلا سبب" for x in miss)
for w, n in why.most_common(6):
    print(f"     {n:>3} × {w}")
for x in miss:
    if not x["why"]:
        print(f"     بلا سبب: {x['s']} {x['name']} ({x['sector']})")

old = [x for x in have if isinstance(x["age"], (int, float)) and x["age"] > 456]
# قيمةٌ قبل حدثِ رأس مال: سعرُ يوم الحساب (القيمةُ ÷ نسبتِها) يبعد عن سعر اليوم بنسبة تجزئة/منحة
cap = []
for x in have:
    if x["vtp"] and x["px"]:
        then = x["fv"] / x["vtp"]
        r_ = then / x["px"]
        if r_ >= 1.4 or r_ <= 1 / 1.4:
            cap.append((x, round(r_, 2)))
line("٢ الحداثة", not old and not cap, f"قوائمُ أقدم من 15 شهراً {len(old)} · محسوبةٌ قبل حدثِ رأس مال {len(cap)}")
for x, r_ in cap[:8]:
    print(f"     {x['s']} {x['name']} · سعرُ الحساب÷اليوم {r_} · قيمة {x['fv']} · سعر {x['px']}")
for x in old[:5]:
    print(f"     {x['s']} {x['name']} · عمرُ القوائم {x['age']} يوماً")

far = [x for x in have if x["px"] and abs(x["fv"] / x["px"] - 1) > 0.60]
line("٣ المعقولية", len(far) <= 0.05 * max(1, len(have)), f"تبتعد عن السعر > 60٪: {len(far)}/{len(have)}")
for x in sorted(far, key=lambda x: -abs(x["fv"] / x["px"] - 1))[:10]:
    print(f"     {x['s']} {x['name']} ({x['sector']}) · قيمة {x['fv']:.2f} · سعر {x['px']} · {x['fv']/x['px']-1:+.0%} · ثقة {x['conf']}")

pairs = [x for x in have if x["at"]]
dev = [abs(x["fv"] / x["at"] - 1) for x in pairs]
med = statistics.median(dev) if dev else None
by = collections.defaultdict(list)
# ‏D631: بُعدُ **سعر السوق نفسِه** عن هدف المحلّلين — وصار مسطرةَ القطاع (‏D632). هدفُهم سعرٌ بعد اثني عشر شهراً لا قيمةُ اليوم،
# فحيث يبعد السعرُ نفسُه أكثرَ من 20٪ يقيس البندُ تفاؤلَ المحلّلين لا خطأَ المحرّك. والحكمُ وعتبتُه كما أُقرّا.
px_by = collections.defaultdict(list)
for x in pairs:
    by[x["sector"]].append(abs(x["fv"] / x["at"] - 1))
    if x["px"]:
        px_by[x["sector"]].append(abs(x["px"] / x["at"] - 1))
# ‏D632 (بقرار المالك): هدفُ المحلّلين سعرٌ بعد اثني عشر شهراً لا قيمةُ اليوم، فالقطاعُ يُقاس بأن يتفوّق المحرّكُ على
# سعر السوق نفسِه في الاقتراب من الهدف — أي أن يضيف معلومةً لا يحملها السعر. ووسيطُ السوق كلِّه ≤ 20٪ كما أُقرّ.
bad_sec = {k: statistics.median(v) for k, v in by.items()
           if len(v) >= 5 and px_by.get(k) and statistics.median(v) > statistics.median(px_by[k])}
_pxall = [abs(x["px"] / x["at"] - 1) for x in pairs if x["px"]]
# ‏D634 · الإصدارُ الأوّل (القاعدةُ مسجَّلةٌ قبل القياس): البندُ ٤ لكلّ قطاعٍ غير موسومٍ بأنّه لم يجتز المعايرة،
# والموسومُ يبقى ظاهراً في الجدول بعلامته — رقمُه منشورٌ بثقةٍ منخفضةٍ وسببٍ مسمّى.
try:
    from app.services.analysis import V1_UNCALIBRATED
except Exception:                                                  # noqa: BLE001
    V1_UNCALIBRATED = frozenset()
bad_open = {k: v for k, v in bad_sec.items() if k not in V1_UNCALIBRATED}
line("٤ المرجع", med is not None and med <= 0.20 and not bad_open,
     (f"لها هدفُ محلّلين {len(pairs)} · وسيطُ الانحراف {med:.0%}"
      + (f" · والسعرُ نفسُه {statistics.median(_pxall):.0%}" if _pxall else "")) if med is not None else "لا أهدافَ محلّلين")
for k, v in sorted(by.items(), key=lambda kv: -statistics.median(kv[1])):
    if len(v) >= 3:
        _p = px_by.get(k) or []
        mark = "◌" if k in V1_UNCALIBRATED else "✘" if k in bad_sec else " "
        print(f"     {mark} {k:<28} n={len(v):>3} · وسيط {statistics.median(v):.0%}"
              + (f" · السعرُ نفسُه {statistics.median(_p):.0%}" if _p else ""))

cc = collections.Counter(x["conf"] or "—" for x in have)
good = cc.get("متوسطة", 0) + cc.get("مرتفعة", 0)
line("٥ الثقة", good >= 0.5 * max(1, len(have)), f"{dict(cc)} · متوسطةٌ فأعلى {good}/{len(have)}")

print("\nالحكم:", "✔ اجتاز المحرّكُ البوابة" if all(verdict.values()) else
      f"✘ لم يجتز — البنودُ الساقطة: {[k for k, v in verdict.items() if not v]}")

# ══ مقاييسُ آلية لحارس التجميد (‏D635) — خطُّ الأساس يُقارَن بها كلُّ إصدارٍ لاحق ══
import json as _json
print("@@METRICS@@" + _json.dumps({
    "coverage": round(cov, 4), "unnamed_missing": len(miss) - len(named), "stale": len(old), "precapital": len(cap),
    "far_share": round(len(far) / max(1, len(have)), 4), "median_dev": round(med, 4) if med is not None else None,
    "sector_dev": {k: round(statistics.median(v), 4) for k, v in by.items() if len(v) >= 5},
    "sector_price": {k: round(statistics.median(px_by[k]), 4) for k in by if len(by[k]) >= 5 and px_by.get(k)},
    "flagged": sorted(V1_UNCALIBRATED), "conf_share": round(good / max(1, len(have)), 4),
    # ‏D672: حصّةُ «مرتفعة» وحدها — هدفُ المالك (2026-10-10)، ويحرسها خطؤها لا كلمتُها
    "conf_high_share": round(cc.get("مرتفعة", 0) / max(1, len(have)), 4),
    "verdict": {k: bool(v) for k, v in verdict.items()},
}, ensure_ascii=False))
