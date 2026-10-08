#!/usr/bin/env python3
"""حارسُ D645: الكونُ شركاتُ الرئيسيّ المدرجةُ اليوم — المشطوبُ يخرج، واللقطةُ الناقصةُ لا تُسقط أحداً؛
والتاريخُ القصيرُ يمنع الفنّيَّ وحده لا ظهورَ الشركة في الفرز."""
import os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
from app.data import universe as U                       # noqa: E402
from app.services import tadawul_market as TM            # noqa: E402

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.data.market_universe import MARKET_UNIVERSE as uni      # noqa: E402 — الكونُ الحقيقيّ (≈ 273 رئيسيّ)
main = [s for s in uni if U.is_main(s)]
orig = TM.usable_rows
TM.usable_rows = lambda: ({s: {} for s in main if s not in ("2002", "8270", "4010")}, False, "t")
gone = U.delisted(uni)
check(gone == {"2002", "8270", "4010"} and not ({"2002", "8270", "4010"} & set(U.main_market(uni))),
      "١ المشطوبُ من لقطة «تداول» الكاملة يخرج من الكون (بتروكيم · بروج · دور)", str(sorted(gone)))
TM.usable_rows = lambda: ({s: {} for s in main[: len(main) // 2]}, False, "t")
check(U.delisted(uni) == set() and len(U.main_market(uni)) == len(main),
      "٢ واللقطةُ الناقصةُ (أقلُّ من 90٪) لا تُسقط أحداً — الغيابُ فيها عطبُ جلبٍ لا شطب")
TM.usable_rows = lambda: ({}, False, None)
check(U.delisted(uni) == set(), "٣ وبلا لقطةٍ لا شطب")
TM.usable_rows = orig
sc = (ROOT / "backend/app/services/market_screener.py").read_text()
check('"technical_unavailable": f"تاريخُ تداولٍ قصير' in sc and '"price": closes[-1]' in sc,
      "٤ والشركةُ بتاريخٍ قصيرٍ تظهر في الفرز بسعرها (أرماح · 31 جلسة) والفنّيُّ فارغٌ بسببه")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
