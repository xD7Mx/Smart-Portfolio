"""كاشف D619 حيّاً: يُبطل تقييماتِ «سلوشنز» المحفوظةَ قبل تجزئتها (حساباتٌ مشتقّة لا أرقامُ المالك) ويُعيد حسابها،
ويطبع القيمةَ العادلة قبل وبعد مقابل السعر."""
import asyncio, sys
sys.path.insert(0, "/app")


async def main():
    from app.services.content_engine import fund_store_load
    from app.services.split_watch import invalidate_valuations
    from app.services.analysis import analyze_company
    sym = "7202"
    before = (fund_store_load().get(sym) or {}).get("fair_value")
    print("قبل:", before)
    from app.services.split_watch import backfill_ledger, factor_after
    print("سجلُّ التجزئات من عمليات المالك:", await backfill_ledger(), "· معاملُ 7202 بعد 2026-06-30 =", factor_after(sym, "2026-06-30"))
    print("الإبطال:", invalidate_valuations(sym))
    from app.services.market_valuation_sweep import sweep
    print("المسحة:", {k: v for k, v in (await sweep([sym])).items() if not isinstance(v, (list, dict))})
    print("المخزن بعد:", {k: v for k, v in (fund_store_load().get(sym) or {}).items() if k.startswith("fair_value")})
    r = await analyze_company(sym + ".SR")
    fv, px = (r or {}).get("fair_value"), (r or {}).get("price")
    v = (r or {}).get("valuation") or {}
    print(f"بعد: القيمةُ العادلة {fv} · السعر {px} · الصعود {round((fv / px - 1) * 100, 1) if fv and px else None}٪ · الثقة {v.get('confidence') or v.get('conf')}")
    for n in (v.get("notes") or [])[:8]:
        print("  ملاحظة:", n)

asyncio.run(main())
