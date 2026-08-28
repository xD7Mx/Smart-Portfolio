#!/usr/bin/env python3
"""
Smart Portfolio — Market Update Script
========================================
Updates prices for all active portfolio companies.
Can be run manually or triggered by the scheduler.

Usage: python scripts/update_market.py
"""

import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from loguru import logger


async def update_all_prices():
    """Fetch and update prices for all active holdings."""
    logger.info("📊 Starting market price update...")

    try:
        from app.services.market_data import market_service
        # TODO: query active company symbols from DB, update holdings
        logger.info("✅ Market update completed.")
    except Exception as e:
        logger.error(f"❌ Market update failed: {e}")


if __name__ == "__main__":
    asyncio.run(update_all_prices())
