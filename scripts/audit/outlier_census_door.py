#!/usr/bin/env python3
"""البند الثالث في بوابة القبول — تشخيصُ كلِّ ورقةٍ تبعد قيمتُها عن السعر أكثر من 60٪، وتصنيفُ الجذر آلياً. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/outlier_census_door.py

التوقيعات:
  أسهم     عددُ أسهم المحرّك يخالف «تداول» (الأسهم المصدرة) بأكثر من 30٪
  ربح      مكرّرُنا (القيمةُ السوقية ÷ ربحِنا) يخالف مكرّرَ «تداول» بأكثر من ضعف
  نموّ     نموذجُ التدفّق/الأرباح المستقبلية فوق ضعف السعر بنموٍّ ≥ 15٪
  أقران    نموذجُ مضاعفاتِ الأقران فوق ضعف السعر أو تحت نصفه
  خسارة    ربحُ اثني عشر شهراً سالب
  أخرى     ما لم يطابق شيئاً — يُفحص يدوياً
"""
import asyncio, collections, sys
sys.path.insert(0, "/app")


async def main():
    from app.services import fair_value_models as F
    from app.services.content_engine import fund_store_load
    from app.services.market_screener import get_cached_screener
    from app.services.tadawul_financials import issued_shares, page_pe
    store = fund_store_load()
    rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
    outs = []
    for s, st in store.items():
        fv, px = st.get("fair_value"), (rows.get(s) or {}).get("price")
        if isinstance(fv, (int, float)) and isinstance(px, (int, float)) and px > 0 and abs(fv / px - 1) > 0.6:
            outs.append((s, fv, px))
    print(f"أوراقٌ تبعد > 60٪: {len(outs)}")
    sig = collections.Counter()
    lines = []
    for s, fv, px in sorted(outs, key=lambda t: -abs(t[1] / t[2] - 1)):
        tags = []
        try:
            i = await F.gather(s)
        except Exception as e:                                     # noqa: BLE001
            lines.append(f"  {s} · تعذّر الجمع: {str(e)[:60]}"); sig["تعذّر"] += 1; continue
        if not i:
            lines.append(f"  {s} · لا مدخلات"); sig["لا مدخلات"] += 1; continue
        iss = issued_shares(s)
        if iss and i.shares and not (1 / 1.3 <= i.shares / iss <= 1.3):
            tags.append(f"أسهم({i.shares / iss:.2f}×)")
        ni = (i.ttm or {}).get("net_income")
        pe_t = page_pe(s)
        if ni is not None and ni <= 0:
            tags.append("خسارة")
        elif ni and pe_t and i.shares:
            pe_o = px * i.shares / ni
            if pe_o > 2 * pe_t or pe_o < pe_t / 2:
                tags.append(f"ربح(مكرّرنا {pe_o:.1f} · تداول {pe_t:.1f})")
        r = F.value(i) or {}
        for m in r.get("models") or []:
            k, v = m.get("key", ""), m.get("value") or 0
            if k in ("dcf", "fcfe", "ri", "ddm", "epv") and v > 2 * px and (getattr(i, "growth", None) or 0) >= 0.15:
                tags.append(f"نموّ({k})")
            if k in ("pe", "ev_ebitda", "pb", "ps", "peer_yield") and (v > 2 * px or v < px / 2):
                tags.append(f"أقران({k} {v:.0f})")
        tags = list(dict.fromkeys(tags)) or ["أخرى"]
        for t in tags:
            sig[t.split("(")[0]] += 1
        ms = " ".join(f"{m['key']}={m['value']:.0f}" for m in (r.get("models") or []))
        lines.append(f"  {s} {i.archetype} · قيمة {fv:.1f} سعر {px} ({fv / px - 1:+.0%}) · {' · '.join(tags)} · [{ms}]")
    print("التوقيعات:", dict(sig.most_common()))
    for l in lines:
        print(l)

asyncio.run(main())
