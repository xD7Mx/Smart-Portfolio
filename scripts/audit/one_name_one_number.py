#!/usr/bin/env python3
"""الاسمُ لصاحبه: سعرُنا العادل ≠ هدفُ المحللين ≠ نسبيُّ القطاع (D386).

    python3 scripts/audit/one_name_one_number.py

قال المالك: «هدفُ المحللين شيءٌ من ياهو، والسعرُ العادل شيءٌ آخرُ من
صنعنا». وقِيس على ‎1120 قبل الإصلاح أن ثلاثةَ أرقامٍ تتزاحم على اسمٍ
واحد، وأنّ الاسمَ الأثمنَ كان معلَّقاً على **أضعفها**:

  · **‎32.13** مقارنةٌ بمضاعفات نظائره في القطاع — وهو الذي كان يحمل
    وسمَ «السعر العادل» في الشاشة (‏يقول: مبالغٌ فيه ‎-51%).
  · **‎74.95** متوسّطُ أهداف بيوت الخبرة من ياهو (‏يقول: ‎+13.6%).
  · **‎104.72** تقديرُ محرّكنا من قوائم الشركة — **كان محجوباً**.

فثلاثةُ أحكامٍ متعارضةٍ باسمٍ واحد، والميثاقُ يقول: رقمٌ واحدٌ باسمٍ
واحد. والترتيبُ المعلَن الآن: سعرُنا العادلُ أوّلاً باسمه ومعه مداه
وثقتُه وتاريخُ أرقامه، فإن امتنع محرّكُنا فهدفُ المحللين **باسمه
ومصدرِه**، فإن غاب فالنسبيُّ إلى القطاع باسمه — ولا يلبس أحدُهما ثوبَ
الآخر، ولا يُستعار رقمٌ من مصدرٍ ليملأ اسمَ غيره.
"""
from __future__ import annotations

import pathlib
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


def _find(*rel: str) -> pathlib.Path | None:
    for base in (ROOT, pathlib.Path("/app"), pathlib.Path.cwd()):
        for r in rel:
            c = base / r
            if c.exists():
                return c
    return None


# ── ١ · الخادمُ لا يكتب سعرَنا العادل من مصدرٍ خارجيّ ──────────────────
_an = _find("backend/app/services/analysis.py", "app/services/analysis.py")
if _an is None:
    print("⚠ لا شفرةَ تحليلٍ في مسارٍ معروفٍ — لم يُقَس")
else:
    AN = _an.read_text("utf-8")
    check('"fair_value": _fv.get("value")' in AN,
          "١ «السعر العادل» = قيمةُ محرّكنا لا رقمٌ مستعار")
    check('"analyst_target": _shown_fv' in AN
          and '"analyst_target_source"' in AN,
          "١ب وهدفُ المحللين حقلٌ مستقلٌّ باسمه ومصدرِه")
    check('"fair_value_conf"' in AN and '"fair_value_asof"' in AN,
          "١ج ومعه ثقتُه وتاريخُ أرقامه — لا رقمٌ عارٍ")

_vf = _find("backend/app/services/valuation_fields.py",
            "app/services/valuation_fields.py")
if _vf is None:
    print("⚠ لا سلسلةَ عرضٍ في مسارٍ معروفٍ — لم يُقَس")
else:
    VF = _vf.read_text("utf-8")
    check('("analyst_target", "target_mean_price")' in VF
          and '("fair_value", "target_mean_price")' not in VF,
          "١د والسلسلةُ الواحدة لا تُسمّي هدفَ ياهو سعراً عادلاً")

_sc = _find("backend/app/services/market_screener.py",
            "app/services/market_screener.py")
if _sc is None:
    print("⚠ لا شفرةَ فرزٍ في مسارٍ معروفٍ — لم يُقَس")
else:
    SC = _sc.read_text("utf-8")
    check('r["analyst_target"] = pick("target_mean_price")' in SC
          and 'r["fair_value"] = pick("target_mean_price")' not in SC,
          "١ه والفرزُ كذلك: كلُّ رقمٍ باسمه")

# ── ٢ · والشاشاتُ تُسمّي كلَّ رقمٍ باسمه ───────────────────────────────
for _rel, _nm in (("frontend/src/components/analysis/AnalysisPanel.tsx",
                   "صفحةُ التحليل"),
                  ("frontend/src/pages/AIPage.tsx", "صفحةُ الذكاء"),
                  ("frontend/src/components/market/StockView.tsx",
                   "صفحةُ السهم")):
    _f = _find(_rel)
    if _f is None:
        print(f"⚠ لا {_nm} في هذه البيئة — لم يُقَس")
        continue
    T = _f.read_text("utf-8")
    # الوسمُ القديمُ المعطوب: «هدف المحللين» على حقلِ سعرِنا العادل
    _bad = ('data.fair_value == null && data.rel_value != null ? "السعر العادل"'
            in T) or ('c.fair_value == null && c.rel_value != null ? "السعر العادل"'
                      in T)
    check(not _bad, f"٢ {_nm}: لا وسمَ ملتبساً بين الحقلَين")
    check("analyst_target" in T,
          f"٢ب {_nm}: تعرف هدفَ المحللين حقلاً مستقلّاً")

print(("FAIL" if fail else "PASS")
      + " D386 — رقمٌ واحدٌ باسمٍ واحد، والاسمُ لصاحبه")
sys.exit(fail)
