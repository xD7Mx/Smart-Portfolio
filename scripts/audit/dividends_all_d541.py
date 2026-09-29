"""D541 — التوزيعاتُ كلُّ السنوات: لا range=10y ولا قصَّ في السنويّ أو القائمة.

    python3 scripts/audit/dividends_all_d541.py
"""
import pathlib
import sys

B = pathlib.Path(__file__).resolve().parents[2] / "backend" / "app"
md = (B / "services" / "market_data.py").read_text(encoding="utf-8")
ep = (B / "api" / "v1" / "endpoints" / "market.py").read_text(encoding="utf-8")
ok = ("range=10y&interval=1mo&events=div" not in md and "range=max&interval=1mo&events=div" in md
      and "sorted(by_year.keys())[-10:]" not in ep and '.get("history", [])[-8:]' not in ep)
print(("PASS" if ok else "FAIL") + " D541 — التوزيعاتُ كلُّ السنوات الموزَّعة")
sys.exit(0 if ok else 1)
