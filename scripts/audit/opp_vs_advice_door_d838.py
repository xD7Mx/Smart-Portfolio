#!/usr/bin/env python3
"""كاشفُ D838 على الخادم — فرصةُ صقر وتحليلُ السلسلة الذكيّ على السهم نفسِه: لماذا يختلفان؟ (قراءةٌ لا تكتب شيئاً)

قال المالك (2026-11-25): «في الفرص وجدتُ فرصةً — ATR مثلاً — رشّحت عقداً بنحو 133 دولاراً، ووضعتُ في التحليل الذكيّ ميزانيةً 200 فقال: لا توجد فرص».

  ١ الفرصة: جهتُها وإعدادُها ومدّتُها وهدفُها وحدُّها وحكمُ صقر.
  ٢ دليلُ الفرصة في السلسلة (كما تحسبه الواجهة): أوّلُ أجلٍ يتّسع لمدّتها، وعقودُ «الأنسب» — بكلفتها وفارقها واهتمامها وحكم التحليل الذكيّ على كلٍّ.
  ٣ التحليلُ الذكيّ كما يطلبه الزرّ الآن (الرمز والميزانية وحدهما): ميلُه وامتناعُه وأنسبُه ومرفوضُه.
  ٤ التحليلُ الذكيّ بجهة الفرصة.

    docker exec -e SP_SYM=ATR -e SP_BUDGET=200 sp_backend python /app/scripts/audit/opp_vs_advice_door_d838.py
"""
import asyncio
import os
import sys

sys.path.insert(0, "/app")
NEED = {1: 45, 2: 75, 3: 110}


def band(side: str, S: float, k: float, px: float | None, delta: float | None, T: float) -> tuple[str | None, float | None, float | None]:
    """نسخةُ ‏bandOf في الواجهة (‏OptionChain.tsx) حرفاً بحرف."""
    if not px or px <= 0 or not S:
        return None, None, None
    long = side == "long"
    be = k + px if long else k - px
    pay = (max(T - k, 0) if long else max(k - T, 0)) - px
    ret = pay / px
    need = S + 0.6 * (T - S) if long else S - 0.6 * (S - T)
    be_ok = be <= need if long else be >= need
    d_ok = True if delta is None else 0.35 <= delta <= 0.8
    if be_ok and d_ok and ret >= 0.5:
        return "core", be, ret
    if ret > 0 and (delta is None or delta >= 0.2):
        return "aux", be, ret
    return None, be, ret


async def main():
    from app.services import chart_scan as CS
    from app.services import option_advisor as OA
    from app.services.options_chain import chain
    sym, budget = os.environ.get("SP_SYM", "ATR").upper(), float(os.environ.get("SP_BUDGET", "200"))
    x = CS.lookup("us", sym)
    if not x:
        print(f"١ {sym} ليس في فرص اليوم الحديثة")
        return
    cn = x.get("council") or {}
    print(f"١ الفرصة {sym}: {x.get('side')} · {x.get('setup')} · مدّة {x.get('horizon')} ({x.get('horizon_n')}) · الإغلاق {x.get('close')} · "
          f"الدخول {x.get('entry')} · الهدف {x.get('target')} · الحدّ {x.get('stop')} · صقر {cn.get('verdict')} {cn.get('score')} · "
          f"قراءتُه {(x.get('link') or {}).get('decision')}")
    base = await chain(sym)
    S = float(base["price"])
    need = NEED.get(x.get("horizon_n"), 45)
    exps = base.get("expirations") or []
    e = next((q for q in exps if q["dte"] >= need), exps[-1] if exps else None)
    print(f"٢ السعر {S} · الآجال {[q['dte'] for q in exps]} · أجلُ الدليل {e and e['date']} ({e and e['dte']} يوماً) لمدّةٍ ≥ {need}")
    ch = await chain(sym, e["t"])
    long = x["side"] == "long"
    rows = [r for r in (ch["calls"] if long else ch["puts"]) if r.get("strike")]
    S1 = float(ch.get("price") or S)
    OA.enrich_rows(rows, S1, e["dte"], long)
    ctx = await OA._context(sym)
    core = []
    for r in rows:
        px = r.get("ask") or r.get("sask") or (r.get("g") or {}).get("px") or r.get("last")
        d = abs((r.get("g") or {}).get("delta")) if (r.get("g") or {}).get("delta") is not None else None
        b, be, ret = band(x["side"], S1, r["strike"], px, d, x["target"])
        if b == "core":
            c = OA.card(r, long, S1, e["dte"], e["date"], ctx)
            core.append((abs((d or 9) - 0.6), r, c, px, ret))
    core.sort(key=lambda t: t[0])
    for _, r, c, px, ret in core[:5]:
        g = c["g"] or {}
        print(f"   الأنسب {r['strike']}: طلب {r.get('ask')} عرض {r.get('bid')} (لقطة {r.get('sask')}/{r.get('sbid')}) · كلفة {c['cost']} · فارق {g.get('spread')}٪ · "
              f"مفتوح {r.get('oi')} · كمية {r.get('volume')} · دلتا {g.get('delta')} · عند الهدف {ret and round(ret * 100)}٪ · حكمُه {c['verdict_ar']}: "
              f"{' | '.join(c['cons'])[:220]}")
    print(f"   سياقُ التحليل: المسار {(ctx.get('trend') or {}).get('state')} · الأخبار {(ctx.get('news') or {}).get('impact')} · التذبذب التاريخيّ {ctx.get('hv')}")
    for lbl, kw in (("٣ كما يطلبه الزرّ الآن", {}), ("٤ بجهة الفرصة", {"side": "call" if long else "put"})):
        res = await OA.analyze(sym, budget=budget, with_summary=False, **kw)
        print(f"{lbl}: الميل {res.get('lean')} ({res.get('lean_note')}) · امتناع {res.get('abstain')} · الآجال {res.get('expiries')} · فُحص {res.get('scanned')}")
        print(f"   الملاءمة: {(res.get('fit') or {}).get('text')}")
        for c in res.get("best") or []:
            print(f"   الأنسب {c['contract']} · {c['cost']} · {c['verdict_ar']} · {c['dte']} يوماً")
        for c in res.get("refused") or []:
            print(f"   مرفوض {c['contract']} · {c['cost']} · {(c['cons'] or [''])[0][:160]}")


asyncio.run(main())
