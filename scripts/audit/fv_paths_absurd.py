#!/usr/bin/env python3
"""مساراتُ السعر العادل لأشذّ الأوراق في الإحصاء (250–1400× السعر). قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fv_paths_absurd.py
"""
import runpy, sys
for s in ("1050", "7202", "3002"):
    sys.argv = ["fv_paths.py", s]
    try:
        runpy.run_path("/app/scripts/audit/fv_paths.py", run_name="__main__")
    except SystemExit:
        pass
