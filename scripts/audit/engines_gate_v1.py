#!/usr/bin/env python3
"""بوابةُ الإصدار الأوّل لمحرّكات ٢–٥ — بالمعايير المسجَّلة قبل القياس في `docs/ENGINES_V1.md`. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/engines_gate_v1.py

  ٢ الجودة    تغطيةٌ ≥ 95٪ وكلُّ غائبةٍ بسببٍ مسمّى · لا درجةَ على قوائم > 15 شهراً بلا وسمِ قِدَم · لا درجةَ ≥ 65 مع خطٍّ أحمر
  ٣ القرار    لا «شراء»/«شراء قوي» بلا سعرٍ عادل أو بسعرٍ فوقه أو بجودةٍ دون 45 أو بخطٍّ أحمر · ولكلّ قرارٍ سبب
  ٤ الشرعي    لكلّ شركةٍ حالةٌ بمصدرٍ وتاريخ، أو «غير متوفّر» — لا تخمين
  ٥ الفنّي    تغطيةُ من له 200 يومٍ فأكثر · RSI بين 0 و100 · لا قفزةَ يوميةً > 40٪ بلا حدثِ رأس مالٍ مسجَّل
"""
import asyncio, collections, sys
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.services import lastgood
from app.services.content_engine import fund_store_load
from app.services.market_screener import get_cached_screener

BUY = {"شراء", "شراء قوي"}
uni = main_market(MARKET_UNIVERSE)
store = fund_store_load()
deep = lastgood.load("governance:deep") or {}
rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
funds = {s for s, v in store.items() if "صندوق" in str((v or {}).get("fair_value_unavailable") or "")}
syms = [s for s in uni if s not in funds]
verdict = {}


def line(k, ok, msg):
    verdict[k] = ok
    print(f"{'✔' if ok else '✘'} {k} — {msg}")


def show(items, n=8):
    for x in items[:n]:
        print(f"     {x}")


# ══ ٢ الجودة ══
have = [s for s in syms if isinstance((rows.get(s) or {}).get("finance_score"), (int, float))]
miss = [s for s in syms if s not in have]
named = [s for s in miss if (store.get(s) or {}).get("finance_score_unavailable")]
old = [s for s in have if ((store.get(s) or {}).get("stmt_age_days") or 0) > 456 and not (store.get(s) or {}).get("stmt_asof")]
red = [s for s in have if (rows[s].get("red_lines") or 0) and rows[s]["finance_score"] >= 65]
cov = len(have) / len(syms) if syms else 0
line("٢ الجودة", cov >= 0.95 and len(named) == len(miss) and not old and not red,
     f"تغطية {len(have)}/{len(syms)} = {cov:.0%} · غائبةٌ بسببٍ مسمّى {len(named)}/{len(miss)} · قديمةٌ بلا وسم {len(old)} · ≥65 مع خطٍّ أحمر {len(red)}")
show([f"بلا سبب: {s} {uni[s].get('name_ar')}" for s in miss if s not in named])
show([f"خطٌّ أحمر بدرجة {rows[s]['finance_score']}: {s} {uni[s].get('name_ar')}" for s in red])

# ══ ٣ القرار ══
bad, noreason, total = [], [], 0
for s in syms:
    d = (deep.get(s) or {}).get("decision")
    if not d:
        continue
    total += 1
    raw = d.get("raw") if isinstance(d, dict) else d
    reason = d.get("reason") if isinstance(d, dict) else None
    r = rows.get(s) or {}
    fv, px, q = r.get("fair_value"), r.get("price"), r.get("finance_score")
    if raw in BUY:
        why = ("بلا سعرٍ عادل" if not isinstance(fv, (int, float)) else
               "السعرُ فوق القيمة" if isinstance(px, (int, float)) and px > fv else
               "جودةٌ دون 45" if isinstance(q, (int, float)) and q < 45 else
               "خطٌّ أحمر" if (r.get("red_lines") or 0) else None)
        if why:
            bad.append(f"{s} {uni[s].get('name_ar')} · {raw} · {why} · سعر {px} · قيمة {fv} · جودة {q}")
    if not reason:
        noreason.append(f"{s} {uni[s].get('name_ar')} · {raw}")
line("٣ القرار", not bad and not noreason, f"قرارات {total} · شراءٌ يناقض الشروط {len(bad)} · بلا سبب {len(noreason)}")
show(bad)
show(noreason, 4)

# ══ ٤ الشرعي ══
src = collections.Counter()
nosrc = []
for s in syms:
    r = rows.get(s) or {}
    if r.get("sharia"):
        if r.get("sharia_source"):
            src[r["sharia_source"]] += 1
        else:
            nosrc.append(f"{s} {uni[s].get('name_ar')} · {r['sharia']}")
    else:
        src["غير متوفّر"] += 1
try:
    from app.services.maqasid import meta as _mmeta
    m = _mmeta()
except Exception:                                                  # noqa: BLE001
    m = {}
dated = bool((m.get("maqasid") or {}) or (m.get("argaam") or {}))
line("٤ الشرعي", not nosrc and dated, f"{dict(src)} · حالةٌ بلا مصدر {len(nosrc)} · تاريخُ المصادر {'موجود' if dated else 'غائب'}")
show(nosrc)
print(f"     تاريخُ المصدرين: {m}")

# ══ ٥ الفنّي ══
from app.services.market_data import market_service
from app.services.split_watch import factor_after


async def series(s):
    try:
        return await asyncio.wait_for(market_service._yahoo()._fetch_chart_points(f"{s}.SR", "1y", "1d"), 25)
    except Exception:                                              # noqa: BLE001
        return None


async def tech():
    sem = asyncio.Semaphore(4)
    out = {}

    async def one(s):
        async with sem:
            out[s] = await series(s)
    await asyncio.gather(*(one(s) for s in syms))
    return out

pts = asyncio.run(tech())
fetched = {s: p for s, p in pts.items() if p}
long_ = [s for s, p in fetched.items() if len([x for x in p if x.get("close")]) >= 200]
no_tech = [s for s in long_ if not isinstance((rows.get(s) or {}).get("rsi"), (int, float))]
bad_rsi = [s for s in syms if isinstance((rows.get(s) or {}).get("rsi"), (int, float)) and not 0 <= rows[s]["rsi"] <= 100]
from app.services.technical import clean_series
jumps, recorded = [], 0
for s, p in fetched.items():
    # الحدثُ «مسجَّلٌ» إن سجّله دفترُ التجزئة، أو سجّله المحرّكُ الفنّيّ نفسُه حين عدّل السلسلةَ له (‏D636)
    tech_dates = {d for e in clean_series(p)[1] for d in (e.get("date"), e.get("until")) if d}
    cl = [(str(x.get("date"))[:10], x["close"]) for x in p if x.get("close")]
    for (d0, a), (d1, b) in zip(cl, cl[1:]):
        if a > 0 and abs(b / a - 1) > 0.40:
            try:
                f = factor_after(s, d0) / (factor_after(s, d1) or 1)   # حدثٌ بين يومَي القفزة وحدهما
            except Exception:                                      # noqa: BLE001
                f = 1
            if d1 in tech_dates or d0 in tech_dates:
                recorded += 1
                continue
            if not f or abs(f - 1) < 1e-9:
                jumps.append(f"{s} {uni[s].get('name_ar')} · {d0}→{d1} · {a}→{b} ({b/a-1:+.0%})")
line("٥ الفنّي", not no_tech and not bad_rsi and not jumps,
     f"سلاسلُ وصلت {len(fetched)}/{len(syms)} · لها 200 يومٍ فأكثر {len(long_)} · بلا مؤشّرات {len(no_tech)} · RSI خارج مداه {len(bad_rsi)} · قفزاتٌ بلا حدث {len(jumps)} · قفزاتٌ سجّلها المحرّكُ وعدّل لها {recorded}")
show([f"بلا مؤشّرات: {s} {uni[s].get('name_ar')}" for s in no_tech])
show(jumps)

# ══ مقاييسُ آلية لحارس التجميد (‏D639) — تُضمّ إلى مقاييس بوابة السعر العادل ══
import json as _json
print("@@METRICS@@" + _json.dumps({
    "q_coverage": round(cov, 4), "q_unnamed": len(miss) - len(named), "q_stale_unlabeled": len(old),
    "q_redline_high": len(red), "d_bad": len(bad), "d_noreason": len(noreason), "s_nosrc": len(nosrc),
    "t_unrecorded_jumps": len(jumps), "t_no_tech": len(no_tech), "t_bad_rsi": len(bad_rsi),
    "verdict": {k: bool(v) for k, v in verdict.items()},
}, ensure_ascii=False))
print("\nالحكم:", "✔ اجتازت المحرّكاتُ ٢–٥" if all(verdict.values()) else
      f"✘ البنودُ الساقطة: {[k for k, v in verdict.items() if not v]}")
