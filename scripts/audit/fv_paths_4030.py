#!/usr/bin/env python3
"""مساراتُ السعر العادل للبحري 4030 — قِيس 58,303 على سعر 35.54. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fv_paths_4030.py
"""
import runpy, sys
sys.argv = ["fv_paths.py", "4030"]
runpy.run_path("/app/scripts/audit/fv_paths.py", run_name="__main__")
