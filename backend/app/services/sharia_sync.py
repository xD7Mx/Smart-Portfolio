"""
Sharia-compliance sync — resolves each portfolio company's compliance
status exactly once and stores it on the company row permanently.
The AI (Gemini) is the primary source, answering strictly from known
public Sharia-screening standards and refusing to guess when unsure;
Sahmak is tried as a secondary source if the AI comes back unsure.
Once a company has a known status (COMPLIANT/NON_COMPLIANT) it is never
looked up again, protecting both quotas.
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Company, Holding
from app.services.market_data import SahmakAdapter
from app.services.ai_sharia import ai_lookup_sharia_status

logger = logging.getLogger(__name__)


async def sync_portfolio_sharia_status(db: AsyncSession) -> dict:
    """Looks up Sharia status only for companies currently held in the
    portfolio, and only those not already resolved (UNKNOWN/None)."""
    result = await db.execute(
        select(Company)
        .join(Holding, Holding.company_id == Company.id)
        .where((Company.sharia_status == None) | (Company.sharia_status == "UNKNOWN"))  # noqa: E711
        .distinct()
    )
    companies = result.scalars().all()

    from app.services import maqasid
    sahmak = SahmakAdapter()
    checked, updated = 0, 0
    for company in companies:
        base_symbol = company.symbol.replace(".SR", "")
        if not base_symbol.isdigit():
            continue  # Saudi tickers only
        checked += 1

        # Maqasid is authoritative & served live from _serialize, so we only
        # need to persist a status for symbols it does NOT cover (financials).
        if maqasid.rating(base_symbol):
            continue
        status = await ai_lookup_sharia_status(base_symbol, company.company_name)
        if not status:
            status = await sahmak.get_sharia_status(base_symbol)
        if status:
            company.sharia_status = status
            updated += 1
    if updated:
        await db.commit()
    return {"checked": checked, "updated": updated, "total_holdings": len(companies)}
