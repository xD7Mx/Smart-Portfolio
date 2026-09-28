#!/usr/bin/env python3
"""جدولُ المالك وحده — سعرُنا العادل مقابل هدف المحللين لكلّ قطاع، بلا إعادة قراءة (D497).

    docker exec sp_backend python /app/scripts/audit/fvm_sanity.py
"""
import asyncio, os, sys
sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xbrl_dep_refresh import sanity  # noqa: E402

asyncio.run(sanity())
