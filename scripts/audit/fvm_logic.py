#!/usr/bin/env python3
"""المحرّكُ متعدّدُ النماذج (D468) — أحكامُه على مدخلاتٍ معلومة.

    python3 scripts/audit/fvm_logic.py

بأمر المالك: «طوِّر المحرّكَين ليكونا أقوى نسخةٍ في السوق». وكلُّ حكمٍ هنا
درسٌ قِيس: عددُ أسهمٍ بالآلاف في السنويّ (العثيم 900,000)، وربعٌ استثنائيّ
(خسارةُ تطبيق ERP)، وشاذٌّ داخلَ عائلته لا خارجَها، والمصرفُ بلا خصمِ تدفّق.
"""
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    from app.services import fair_value_models as F
except ModuleNotFoundError as e:
    if e.name and e.name.startswith("app.services.fair_value_models"):
        print("FAIL D468 — لا محرّكَ متعدّدَ النماذج"); sys.exit(1)
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)
except ImportError:
    print("FAIL D468 — لا محرّكَ متعدّدَ النماذج"); sys.exit(1)

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

A = [{"year": 2023, "revenue": 10.23e9, "net_income": 488.6e6, "ebit": 618.6e6, "operating_cash_flow": 681.1e6, "capex": 385e6, "equity": 1.41e9, "eps": 0.5356, "shares_outstanding": 900000.0, "as_of": "2023-12-31"},
     {"year": 2024, "revenue": 10.76e9, "net_income": 516.3e6, "ebit": 676.0e6, "operating_cash_flow": 909.3e6, "capex": 590.8e6, "equity": 1.37e9, "eps": 0.5678, "shares_outstanding": 900000.0, "as_of": "2024-12-31"},
     {"year": 2025, "revenue": 11.09e9, "net_income": 262.7e6, "ebit": 455.7e6, "operating_cash_flow": 740.8e6, "capex": 306e6, "equity": 1.23e9, "eps": 0.2779, "shares_outstanding": 900000.0, "as_of": "2025-12-31"}]
Q = [{"as_of": d, "revenue": r, "net_income": n, "ebit": e, "operating_cash_flow": o, "capex": c, "eps": n / 9e8,
      "shares_outstanding": s, "equity": 1.1e9, "total_debt": 3.0e9, "ending_cash": 1.0e8}
     for d, r, n, e, o, c, s in (("2025-09-30", 2.71e9, 19.9e6, 69e6, 581e6, 205e6, 900000.0),
                                 ("2025-12-31", 2.89e9, 30e6, 90e6, 300e6, 100e6, 9e8),
                                 ("2026-03-31", 2.97e9, 57.6e6, 106e6, 480e6, 37e6, 9e8),
                                 ("2026-06-30", 2.52e9, -102.9e6, -58.5e6, 273e6, 66e6, 8.65e8))]
sh = F._shares_of(A, Q)
check(sh and 8.5e8 <= sh <= 9.1e8, "١ عددُ الأسهم لا يؤخذ بالآلاف من السنويّ (900,000) — يُشتقّ من الربح ÷ الربحية", f"{sh:,.0f}")
ttm, src = F._ttm_of(Q, A)
check(abs(ttm["revenue"] - sum(q["revenue"] for q in Q)) < 1 and "أربعةُ أرباع" in src, "٢ الاثنا عشر شهراً من أربعة أرباعٍ متتالية")
peers = {"pe": [22, 28, 35, 19, 40], "pb": [3.5, 5, 8, 2.8, 6], "ps": [0.5, 0.9, 1.4, 0.7, 2.1],
         "pocf": [9, 12, 15, 8, 20], "ev_ebit": [18, 24, 30, 16, 35], "ev_sales": [0.7, 1.0, 1.6, 0.8, 2.3]}
i = F.Inputs(symbol="4001", price=4.38, shares=sh, annual=A, ttm=ttm, balance=Q[-1], ttm_source=src,
             archetype="consumer_defensive", sector="Consumer Staples Distribution & Retail", dps_ttm=0.1, peers=peers)
r = F.value(i)
check(any("طُبِّع" in n for n in r["notes"]), "٣ الربعُ الاستثنائيّ يُطبَّع على هامش السنوات ويُذكر", (r["notes"] or [""])[0][:60])
fams = {f["family"] for f in r["families"]}
# ‏D487: مجموعةُ InvestingPro للتجزئة الاستهلاكية (العثيم 4001: 15 نموذجاً، المتوفّرُ عندنا 12)
check({"cashflow", "multiples"} <= fams and r["count"] >= 9, "٤ عائلتا التدفّق والمضاعفات وتسعةُ نماذج فأكثر من مجموعة InvestingPro", f"{sorted(fams)} · {r['count']}")
check(r["low"] <= r["value"] <= r["high"] and all(m["low"] <= m["value"] <= m["high"] for m in r["models"]),
      "٥ لكلّ نموذجٍ نطاقٌ ولها نطاقٌ يحيط بالقيمة")
agg = F.aggregate([{"key": "a", "family": "cashflow", "value": 5, "low": 4, "high": 6},
                   {"key": "b", "family": "cashflow", "value": 5.5, "low": 4, "high": 6},
                   {"key": "c", "family": "cashflow", "value": 60, "low": 50, "high": 70},
                   {"key": "d", "family": "equity", "value": 1.6, "low": 1.4, "high": 1.8},
                   {"key": "e", "family": "multiples", "value": 12, "low": 9, "high": 16}], 4.38, "consumer_defensive")
ex = [e["key"] for e in agg["excluded"]]
check(ex == ["c"] and {f["family"] for f in agg["families"]} == {"cashflow", "equity", "multiples"},
      "٦ الشاذُّ يُستبعَد داخلَ عائلته ولا تُسقَط عائلةٌ لأنها تخالف غيرَها", str(ex))
b = F.value(F.Inputs(symbol="1120", price=100, shares=4e9, annual=A, ttm=ttm, balance=Q[-1], ttm_source=src,
                     archetype="bank", peers=peers))
check(not any(m["family"] == "cashflow" for m in b["models"]), "٧ المصرفُ لا يُقيَّم بخصم تدفّقٍ حرّ")
check(all(isinstance(a, tuple) and len(a) == 3 for m in r["models"] for a in m["assumptions"]),
      "٨ ولكلّ نموذجٍ افتراضاتُه بمداها ومصدرها")
bl = F.blend({"value": 8.0, "low": 6.0, "high": 10.0, "price": 5.0, "families": [{"family": "cashflow", "weight": 1.0, "value": 8}],
              "rates": {"ke": 0.10}}, {"value": 4.0, "low": 3.0, "high": 5.0}, "bank", 0.05)
_a = F.BLEND_ALPHA["bank"]
check(0 <= _a <= 1 and abs(bl["value"] - (_a * 8 + (1 - _a) * 4)) < 1e-6
      and ((_a == 1 and bl["families"][-1]["family"] != "calibrated") or
           (bl["families"][-1]["family"] == "calibrated" and abs(bl["families"][-1]["weight"] - (1 - _a)) < 1e-9)),
      "٩ المزيجُ مع المحرّك المُعايَر بالحصّة المقيسة للنمط (BLEND_ALPHA)", f"α={_a} · {bl['value']}")
check(abs(bl["target_12m"] - bl["value"] * 1.05) < 0.01, "١٠ والهدفُ لاثني عشر شهراً = القيمة × (1 + كلفةِ الحقوق − عائدِ التوزيع)", str(bl["target_12m"]))
print(f"{'FAIL' if fail else 'PASS'} D468 — المحرّكُ متعدّدُ النماذج")
sys.exit(fail)
