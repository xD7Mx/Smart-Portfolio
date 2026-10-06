#!/usr/bin/env python3
"""حارسُ D602: سنةُ الشركة حديثةِ الإدراج لا تُبنى بجمع أرباعٍ تراكمية.

    python3 scripts/audit/new_listing_d602.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services.fair_value_models import quarters_to_year
# تمكين: 3 · 6 · 9 أشهر تراكمية (ربحُ السنة نحو 97 مليوناً)
cum = [{"as_of": "2025-03-31", "revenue": 650e6, "net_income": 24e6},
       {"as_of": "2025-06-30", "revenue": 1310e6, "net_income": 49e6},
       {"as_of": "2025-09-30", "revenue": 1990e6, "net_income": 73e6}]
y = quarters_to_year(cum)
check(abs(y["net_income"] - 73e6 * 12 / 9) < 1, "١ التراكميُّ يُسنوَن آخرُه: 73 × 12 ÷ 9 = 97 مليوناً لا 293", str(round(y["net_income"] / 1e6, 1)))
per = [{"as_of": "2025-03-31", "revenue": 650e6, "net_income": 24e6},
       {"as_of": "2025-06-30", "revenue": 660e6, "net_income": 25e6},
       {"as_of": "2025-09-30", "revenue": 680e6, "net_income": 24e6}]
y2 = quarters_to_year(per)
check(abs(y2["net_income"] - 73e6 * 4 / 3) < 1, "٢ والأرباعُ المنفصلةُ تُجمع كما كانت", str(round(y2["net_income"] / 1e6, 1)))
mixed = [{"as_of": "2024-12-31", "revenue": 700e6, "net_income": 20e6}, {"as_of": "2025-03-31", "revenue": 650e6, "net_income": 24e6}]
check("مجموعُ" in quarters_to_year(mixed)["_basis"], "٣ وأرباعٌ من سنتين ليست تراكماً واحداً")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
