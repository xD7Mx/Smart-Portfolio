#!/usr/bin/env python3
"""حارسُ D600: ربحُ التأمين لا يُطبَّع صعوداً إلى وسيطه — و«عند الشكّ يُخفَّض لا يُرفَع».

    python3 scripts/audit/insurance_norm_d600.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services.fair_value_models import base_of, Inputs
# ملاذ كما قِيس: هوامشُ 4.1٪ ثمّ 2.7٪ ثمّ 1.5٪
ann = [{"as_of": "2023-12-31", "revenue": 934.7e6, "net_income": 38.2e6, "equity": 390e6},
       {"as_of": "2024-12-31", "revenue": 1010.7e6, "net_income": 26.9e6, "equity": 433e6},
       {"as_of": "2025-12-31", "revenue": 1445.4e6, "net_income": 21.7e6, "equity": 462e6}]
mk = lambda arch: Inputs(symbol="8020", price=8.8, shares=50e6, annual=ann, ttm=dict(ann[-1]), balance=ann[-1],
                         ttm_source="t", archetype=arch)
ins, oth = base_of(mk("insurance")), base_of(mk("consumer_defensive"))
check(ins and abs(ins.ni_n - 21.7e6) < 1, "١ التأمين: الربحُ الأخيرُ الأدنى هو المعتمد (21.7 مليون لا 39)", str(ins and ins.ni_n))
check(oth and oth.ni_n > 30e6, "٢ وغيرُ التأمين يبقى على وسيط هامشه كما كان", str(oth and round(oth.ni_n)))
up = [dict(p, net_income=p["net_income"] * (0.5 if j < 2 else 2)) for j, p in enumerate(ann)]
ins_up = base_of(Inputs(symbol="8020", price=8.8, shares=50e6, annual=up, ttm=dict(up[-1]), balance=up[-1],
                        ttm_source="t", archetype="insurance"))
check(ins_up and ins_up.ni_n < up[-1]["net_income"], "٣ وسنةٌ استثنائيةٌ مرتفعةٌ تُطبَّع نزولاً كما كانت — التحفّظُ في الاتجاهين")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
