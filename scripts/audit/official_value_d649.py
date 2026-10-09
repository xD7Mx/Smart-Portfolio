#!/usr/bin/env python3
"""حارسُ D649 · رقمُ اليوم واحد: صفحةُ الشركة وتفاصيلُ نماذجها والفرزُ والمختبر وسجلُّ التحقّق يعرضون الرقمَ نفسَه.

العطب: الصفحةُ تمزج تقديرَ النماذج بالسعر **اللحظيّ** (0.4 من حركته) وتحفظه 24 ساعة، والفرزُ يعرض رقمَ المسحة؛
فرقمان لمعنًى واحد طوالَ الجلسة. والمسحةُ تشارك الصفحةَ مفتاحَ الكاش فتكتب رقماً حُسب بسعر لحظة فتح الصفحة لا بالإقفال."""
import asyncio, datetime as dt, os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

an_src = (ROOT / "backend/app/services/analysis.py").read_text(encoding="utf-8")
sw_src = (ROOT / "backend/app/services/market_valuation_sweep.py").read_text(encoding="utf-8")
mk_src = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")

from app.services import content_engine as CE, analysis as AN   # noqa: E402
today = dt.date.today()
rows = {"1010": {"fair_value": 50.0, "fair_value_conf": "متوسطة", "score_asof": today.isoformat()},
        "2020": {"fair_value": 40.0, "score_asof": (today - dt.timedelta(days=AN.OFFICIAL_MAX_AGE + 1)).isoformat()},
        "3030": {"fair_value": None, "fair_value_unavailable": "قوائمُ قديمة", "score_asof": today.isoformat()},
        "4040": {"pe_ratio": 12.0}}
CE.fund_store_load = lambda: rows
check((AN.official_row("1010.SR") or {}).get("fair_value") == 50.0, "١ صفُّ المسحة الحديث هو رقمُ اليوم")
check(AN.official_row("2020") is None, f"٢ ومسحةٌ أقدمُ من {AN.OFFICIAL_MAX_AGE} أيّام لا تُعرض — المسحةُ معطوبةٌ والحيُّ أصدق")
check((AN.official_row("3030") or {}).get("fair_value_unavailable") == "قوائمُ قديمة",
      "٣ وامتناعُ المسحة رقمُ اليوم أيضاً — لا تُظهر الصفحةُ رقماً امتنع عنه الفرز")
check(AN.official_row("4040") is None, "٤ ولا رقمَ يومٍ لشركةٍ لم تمسحها المسحة — تُحسب حيّةً")

i_ovl = an_src.find("D649 · رقمُ اليوم واحد")
i_gate = an_src.find('_gate_fv = _fv.get("value")')
check(0 < i_ovl < i_gate, "٥ رقمُ اليوم يُطبَّق قبل بوّابة القرار — القرارُ يُحكم بالرقم المعروض (D454)")
check(':fresh:' in an_src and ':official:' in an_src,
      "٦ للمسحة مفتاحُ كاشٍ بيومها وللصفحة مفتاحٌ بتاريخ المسحة — لا تقرأ إحداهما ما حسبته الأخرى")
check('analyze_company(f"{sym}.SR", allow_supplement=False, official=False)' in sw_src,
      "٧ المسحةُ تقيس الآن بسعر الإقفال ولا تقرأ رقمَها السابق")
cg = (ROOT / "scripts/audit/candidate_gate.py").read_text(encoding="utf-8")
check("from app.services.market_valuation_sweep import _one" in cg, "٨ وقياسُ المرشَّح يمرّ بالمسحة نفسِها — يقيس شيفرته لا المخزن")

# تفاصيلُ النماذج: «القيمة العادلة اليوم» = رقمُ المسحة، والنماذجُ تبقى كما حُسبت، والهدفُ يُبنى على المعروض
import types                                                         # noqa: E402
fake = types.ModuleType("fvm_fake")
async def _fs(sym):
    return {"value": 52.0, "low": 45.0, "high": 60.0, "price": 40.0, "upside": 30.0, "target_12m": 57.2,
            "models": [{"key": "pe", "value": 70.0, "family": "equity"}]}
try:
    from app.api.v1.endpoints import market as MK                    # noqa: E402
    import app.services.fair_value_models as FM                      # noqa: E402
    FM.for_symbol = _fs
    r = asyncio.run(MK.get_fair_value_models("1010"))
    body = getattr(r, "body", None)
    import json                                                      # noqa: E402
    d = (json.loads(body) if body else r).get("data") if not isinstance(r, dict) else r.get("data")
    check(d.get("value") == 50.0 and d.get("live_value") == 52.0 and d.get("upside") == 25.0,
          "٩ تفاصيلُ النماذج تعرض رقمَ المسحة وبعدَه عن السعر الحيّ، وتقديرُ اللحظة باسمه", str({k: d.get(k) for k in ("value", "live_value", "upside")}))
    check(d.get("target_12m") == 55.0 and d.get("models"), "١٠ والهدفُ لاثني عشر شهراً على الرقم المعروض، والنماذجُ باقية",
          str(d.get("target_12m")))
except Exception as e:                                               # noqa: BLE001
    check("official_row(sym4)" in mk_src and '"live_value": res.get("value")' in mk_src,
          "٩ تفاصيلُ النماذج تعرض رقمَ المسحة (فحصُ نصّ — تعذّر الاستيراد)", f"{type(e).__name__}: {str(e)[:80]}")
check("_rf649" in mk_src and '"fair_value_upside_pct": round((data["fair_value"] - _lp) / _lp * 100, 1)' in mk_src,
      "١١ وصفحةُ الشركة تحسب البعدَ عن السعر بسعر اللحظة كالفرز")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
