#!/usr/bin/env python3
"""تشخيص: هل ما زالت الشركاتُ مدرجةً في «تداول» اليوم؟ (بتروكيم · بروج · دور · أرماح) — من لقطة «تداول» الحيّة. قارئٌ فقط."""
import sys
sys.path.insert(0, "/app")
from app.services import tadawul_market as tm
rows, live, at = tm.usable_rows()
meta = {"live": live, "at": at}
print("لقطةُ تداول:", len(rows or {}), "رمزاً ·", meta)
for s in ("2002", "8270", "4010", "6022", "2310", "4290"):
    r = tm.row_for(s)
    print(s, "←", {k: (r or {}).get(k) for k in ("name_ar", "name", "sector_en", "price", "last", "close", "listing_date")} if r else "ليس في اللقطة")
