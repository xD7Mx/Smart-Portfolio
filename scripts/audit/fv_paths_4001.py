#!/usr/bin/env python3
"""مساراتُ السعر العادل للبحري 4001 — مقابل InvestingPro (6.06). قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fv_paths_4001.py
"""
import runpy, sys
sys.argv = ["fv_paths.py", "4001"]
runpy.run_path("/app/scripts/audit/fv_paths.py", run_name="__main__")
