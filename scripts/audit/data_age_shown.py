#!/usr/bin/env python3
"""عمرُ الرقم معروضٌ معه — لا يُقرأ قديمٌ حديثاً (D380 · D381).

    python3 scripts/audit/data_age_shown.py

قِيس على خادم المالك: ‎8010 خرجت بقيمةٍ عادلةٍ ومدخلاتُها فتراتُ
‎2020–2022، والسطرُ يقول «شائخ=False» لأن العمرَ كان يُحسَب من تاريخ
**الجلب**. و‎54 ورقةً في السوق الرئيسيّ قوائمُها أقدمُ من ‎200 يوم —
‎25 شركةَ تأمينٍ أرقامُها ‎2022، وستُّ ريتاتٍ بعمر سبعِ سنوات — ودرجةُ
جودتها تُعرَض رقماً مجرَّداً كدرجةِ شركةٍ أودعت هذا الربع.

فالقاعدةُ: **عمرُ الرقم جزءٌ منه لا حاشيةٌ عنه.** ويُحرَس طرفاها:

  · الخادمُ يحسب العمرَ من **أحدثِ فترةٍ ماليةٍ مستعملة** لا من الجلب،
    ويُرسل تاريخَ الأرقام وعمرَها مع أصل الأساسيات.
  · والشاشةُ تعرض ذلك التاريخَ **في سطر الدرجة نفسِه**، وبلونِ التحذير
    متى تجاوز العمرُ عتبةَ الشيخوخة — فيُقرأ مع الدرجة لا بعدها، ولا
    يُكتب حاشيةً أسفل الشاشة (منهيٌّ عنه في الميثاق).

وفحصُ الشاشةِ هنا ساكنٌ عن قصد: كواشفُ المتصفّح تحتاج `node` وتطبيقاً
حيّاً ولا تتوفّر في كلّ بيئة (‏D375)، وهذا الحارسُ يجب أن يعمل في
كلّ بيئةٍ لأنه يحرس صدقاً لا هيئة.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


# ── ١ · الخادمُ: العمرُ من أحدثِ فترةٍ لا من الجلب ──────────────────────
_OLD = [{"as_of": f"{y}-12-31", "year": y, "revenue": 7e9, "net_income": 3.9e8,
         "eps": 3.1, "equity": 3.3e9, "total_assets": 1.9e10,
         "total_liabilities": 1.55e10, "shares_outstanding": 1.25e8,
         "operating_cash_flow": 1.6e8, "capex": 4.6e7, "ending_cash": 1.6e9,
         "pretax_income": 4.8e8} for y in (2020, 2021, 2022)]
try:
    from app.services.fair_value import compute as _fv
    _r = _fv({"pe_ratio": 20.0, "price_to_book": 3.4, "book_value": 26.8,
              "return_on_equity": 11.7, "dividend_per_share": 1.0,
              "beta": 0.47, "sector": "التأمين", "eps": 3.13},
             92.05, sector_avg_pe=18.0, sector_avg_pb=2.5,
             asof="2026-09-16", periods=_OLD, archetype="insurance",
             symbol="8010", peer_count=9)
except Exception as e:                                            # noqa: BLE001
    _r = {"خطأ": type(e).__name__}
check((_r.get("age_days") or 0) > 1000 and _r.get("stale") is True,
      "١ عمرُ التقدير من أحدثِ فترةٍ ماليةٍ — لا من تاريخ الجلب",
      f"{_r.get('age_days')} يوماً · شائخ={_r.get('stale')}")
check(str(_r.get("data_asof") or "").startswith("2022")
      and _r.get("fetched_at") == "2026-09-16",
      "١ب وتاريخُ الجلب يبقى باسمه لا مكانَ العمر",
      f"بيانات={_r.get('data_asof')} · جلب={_r.get('fetched_at')}")

# ── ٢ · والأصلُ يحمل تاريخَ الأرقام وعمرَها ─────────────────────────────
AN = (ROOT / "backend" / "app" / "services" / "analysis.py").read_text("utf-8")
check('"تاريخ الأرقام": _stmt_asof' in AN
      and '"عمر الأرقام أياماً": _stmt_age' in AN,
      "٢ أصلُ الأساسيات يحمل تاريخَ الأرقام وعمرَها إلى الشاشة")
check(re.search(r"_stmt_asof\s*=\s*max\(_ds\)", AN) is not None,
      "٢ب والتاريخُ أحدثُ فترةٍ فعلاً — لا أوّلُ ما وُجد")

# ── ٣ · والشاشةُ تعرضه في سطر الدرجة ───────────────────────────────────
PANEL = (ROOT / "frontend" / "src" / "components" / "analysis"
         / "AnalysisPanel.tsx")
if not PANEL.exists():
    # بيئةٌ بلا واجهةٍ تُعلَن ولا تُحسَب نجاحاً (‏D375)
    print("⚠ لا مجلَّدَ واجهةٍ في هذه البيئة — فحصُ الشاشة لم يُقَس")
    fail = 1
else:
    TSX = PANEL.read_text("utf-8")
    check('data.governance_provenance' in TSX
          and 'prov["تاريخ الأرقام"]' in TSX,
          "٣ الشاشةُ تقرأ تاريخَ الأرقام من الأصل الواصل")
    # وفي **سطر الدرجة** نفسِه: يُقاس أن العرضَ داخل الكتلة التي تحمل
    # `scoreTier` — لا في حاشيةٍ أسفل الشاشة.
    _i = TSX.find("scoreTier(fin.score)")
    _seg = TSX[max(0, _i - 400): _i + 500] if _i > 0 else ""
    check('prov["تاريخ الأرقام"]' in _seg,
          "٣ب وفي سطر الدرجة نفسِه — لا حاشيةً أسفل الشاشة")
    check("var(--warn-ink)" in _seg and "> 200" in _seg,
          "٣ج ولونُ التحذير متى تجاوز العمرُ عتبةَ الشيخوخة",
          "رمزٌ من الأنماط لا قيمةٌ ثابتة")

print(("FAIL" if fail else "PASS")
      + " D380 · D381 — عمرُ الرقم جزءٌ منه لا حاشيةٌ عنه")
sys.exit(fail)
