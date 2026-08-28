"""
Main API Router — registers all v1 endpoints.
"""

from fastapi import APIRouter, Depends
from app.api.v1.endpoints import (
    liquidity,
    health, portfolio, portfolios, companies, holdings, transactions, notes,
    installments, cash, dividends, bonus, goals, allocation,
    market, ai, notifications, reports, scheduler, settings, backup, auth, library
)
from app.core.auth import require_auth
from app.core.portfolio_context import scope_portfolio

api_router = APIRouter()

# Public: health check (container orchestration) and login itself.
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
# قراءة الملف الشخصي والصورة عامّة (لشاشة القفل قبل الدخول)
api_router.include_router(settings.public_router, prefix="/settings", tags=["Settings"])

# Everything else requires a valid session token — this app has no
# per-user accounts, just one shared owner password gating the whole API
# (previously every endpoint, including deposit/withdraw/delete, had zero
# authentication and was reachable by anyone who found the server's IP).
protected = APIRouter(dependencies=[Depends(require_auth), Depends(scope_portfolio)])
protected.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
protected.include_router(portfolios.router, prefix="/portfolios", tags=["Portfolios"])
protected.include_router(companies.router, prefix="/companies", tags=["Companies"])
protected.include_router(holdings.router, prefix="/holdings", tags=["Holdings"])
protected.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
protected.include_router(installments.router, prefix="/installments", tags=["Installments"])
protected.include_router(cash.router, prefix="/cash", tags=["Cash"])
protected.include_router(dividends.router, prefix="/dividends", tags=["Dividends"])
protected.include_router(bonus.router, prefix="/bonus", tags=["Bonus Shares"])
protected.include_router(goals.router, prefix="/goals", tags=["Goals"])
protected.include_router(notes.router, prefix="/notes", tags=["Notes"])
protected.include_router(allocation.router, prefix="/allocation", tags=["Allocation"])
protected.include_router(liquidity.router, prefix="/liquidity", tags=["Liquidity"])
protected.include_router(market.router, prefix="/market", tags=["Market"])
protected.include_router(ai.router, prefix="/ai", tags=["AI"])
protected.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
protected.include_router(reports.router, prefix="/reports", tags=["Reports"])
protected.include_router(library.router, prefix="/library", tags=["Library"])
protected.include_router(scheduler.router, prefix="/scheduler", tags=["Scheduler"])
protected.include_router(settings.router, prefix="/settings", tags=["Settings"])
protected.include_router(backup.router, prefix="/backups", tags=["Backup"])
api_router.include_router(protected)
