"""
Verification probe — run this on the EC2 server (real internet access) to
confirm, with REAL data, how many years the new financial-statements source
actually returns for your real portfolio holdings. Makes no changes to the
running site.

Usage (inside the backend container, which already has httpx/deps):
    docker compose cp verify_financials.py backend:/tmp/verify_financials.py
    docker compose exec backend python3 /tmp/verify_financials.py
"""
import asyncio
import sys
sys.path.insert(0, "/app")

SYMBOLS = ["2222.SR", "1150.SR", "1120.SR", "7010.SR", "4190.SR"]  # real portfolio holdings


async def main():
    from app.services.market_data import market_service

    for sym in SYMBOLS:
        print("=" * 80)
        print("SYMBOL:", sym)
        data = await market_service.get_financials(sym)
        if not data or not data.get("periods"):
            print("  -> NO DATA RETURNED for this symbol.")
            continue
        periods = data["periods"]
        print(f"  -> {len(periods)} year(s) returned, source(s): {set(p.get('source') for p in periods)}")
        for p in periods:
            print(f"     {p['year']}: revenue={p.get('revenue')}, net_income={p.get('net_income')}, "
                  f"eps={p.get('eps')}, equity={p.get('equity')}, debt_ratio={p.get('debt_ratio')}, "
                  f"ocf={p.get('operating_cash_flow')}, fcf={p.get('free_cash_flow')}, "
                  f"ending_cash={p.get('ending_cash')}, interest_coverage={p.get('interest_coverage')}")

asyncio.run(main())
