#!/usr/bin/env python3
"""تشخيصٌ: هل يعمل في الحاوية كودُ D623–D626؟ وما يُخرجه التحليلُ لورقةٍ قديمة القوائم وأخرى بعيدة. قارئٌ فقط."""
import asyncio, pathlib, sys
sys.path.insert(0, "/app")
src = pathlib.Path("/app/app/services/analysis.py").read_text()
print("D624 في الحاوية:", "_fv[\"age_days\"] > 456" in src, "· D625:", "def confidence_of" in src)
from app.services import analysis as A
print("إصدارُ المحرّك:", A._ENGINE_V)
from app.services.content_engine import fund_store_load
st = fund_store_load()

async def main():
    for s in ("8070", "2140", "4011", "8250"):
        a = await A.analyze_company(f"{s}.SR", allow_supplement=False) or {}
        print(s, "تحليل:", a.get("fair_value"), a.get("fair_value_conf"), a.get("fair_value_age_days"),
              (a.get("fair_value_detail") or {}).get("engine"), "| مخزن:",
              {k: (st.get(s) or {}).get(k) for k in ("fair_value", "fair_value_conf", "fair_value_age_days", "score_asof")})
asyncio.run(main())
