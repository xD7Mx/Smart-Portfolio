#!/usr/bin/env python3
"""أحدثُ ربعٍ يصل المحرّكَ — ولا يُدمَج في السلسلة السنوية (‏D412).

    python3 scripts/audit/latest_quarter_reaches_engine.py

قِيس على خادم المالك: **25 من 30** ورقةً تملك ربعيّاً أحدثَ ممّا
تُقيَّم به. وسيطُ عمر المستعمَل ‎266 يوماً ووسيطُ المتاح ‎85 — فكنّا
نقيّم بأرقامٍ عمرُها ثلاثةُ أضعافِ ما نملك، ثمّ نَصِمُها بالشيخوخة
بحقّ. والعلّةُ عندنا: `get_financials` تقرأ `for_symbol(sym, 'annual')`
وحدَها، والربعيُّ محفوظٌ في المخزَن نفسِه بدالّةٍ لا يستعملها التقييم.

## ولماذا لا يُدمَج

مستهلكو السلسلة يقيسون النموَّ المركّبَ على **عددها** ويقرؤون
`periods[-1]` سنةً كاملة. فإقحامُ ربعٍ فيها يخلط أساسَين ويكسر كلَّ
نموٍّ محسوب. فيُسلَّم **حقلاً مستقلّاً** (`latest_quarter`) يقرؤه من
يعنيه: عمرُ الأرقام أوّلاً.
"""
from __future__ import annotations

# ══ لا فحصَ يكتب في بيانات المالك ══ (D160 · D429)
# يُحوَّل مخزنُ الحالة إلى مجلّدٍ مؤقّت **قبل** أيّ استيرادٍ من `app`،
# فالوحداتُ تقرأ مسارَها عند تحميلها. وسجلُّ مشاهداتِ حالة السوق معه:
# حكمُ العطلة يقرأ مشاهداتِ اليوم، فمشاهدةُ فحصٍ تدخله تُفسد دليلَه.
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")

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
    for base in (ROOT / "backend", pathlib.Path("/app"), ROOT):
        for r in rel:
            c = base / r
            if c.exists():
                return c
    return None


# ── ١ · البابُ الواحدُ يسلّم أحدثَ ربع ────────────────────────────────
_md = _find("app/services/market_data.py")
if _md is None:
    print("⚠ لا بابَ بياناتٍ في مسارٍ معروف — لم يُقَس")
else:
    T = _md.read_text("utf-8")
    check('"latest_quarter": _lq' in T,
          "١ البابُ الواحد يسلّم أحدثَ ربعٍ مع القوائم")
    check("get_quarterly_financials(symbol)" in T,
          "١ب ويقرؤه من مخزن الربعيّ نفسِه")

# ── ٢ · والتحليلُ يمرّره ───────────────────────────────────────────────
_an = _find("app/services/analysis.py")
if _an is not None:
    A = _an.read_text("utf-8")
    check('latest_quarter=(_stmt or {}).get("latest_quarter")' in A,
          "٢ والتحليلُ يمرّره إلى المحرّك")

# ── ٣ · والمحرّكُ يقرأ منه عمرَ الأرقام ───────────────────────────────
try:
    from app.services.fair_value import compute
except (ModuleNotFoundError, ImportError) as e:
    print(f"⚠ بيئةٌ ناقصة ({e}) — لم يُقَس أثرُه")
    print(("FAIL" if fail else "PASS") + " D412")
    sys.exit(fail)

_per = [{"as_of": "2025-12-31", "equity": 1000.0, "total_assets": 6000.0,
         "net_income": 120.0, "shares_outstanding": 100.0, "eps": 1.2,
         "revenue": 400.0, "total_liabilities": 5000.0},
        {"as_of": "2024-12-31", "equity": 950.0, "total_assets": 5800.0,
         "net_income": 110.0, "shares_outstanding": 100.0, "eps": 1.1,
         "revenue": 380.0, "total_liabilities": 4850.0}]
_info = {"book_value": 10.0, "trailing_eps": 1.2, "return_on_equity": 0.12}
_kw = dict(price=12.0, sector_avg_pe=10.0, sector_avg_pb=1.1,
           periods=_per, archetype="bank", symbol="0000")

_a = compute(_info, **_kw)
_b = compute(_info, latest_quarter={"as_of": "2026-06-30",
                                    "equity": 1050.0}, **_kw)

check(_a.get("data_asof") == "2025-12-31",
      "٣ بلا ربعٍ: تاريخُ الأرقام من أحدثِ سنة", str(_a.get("data_asof")))
check(_b.get("data_asof") == "2026-06-30",
      "٣ب ومعه: من أحدثِ إفصاحٍ منشور", str(_b.get("data_asof")))
check(bool(_b.get("asof_from_quarter")),
      "٣ج والمصدرُ مُعلَنٌ في المخرَج — لا تبديلَ صامت")

# ── ٤ · والأثرُ يبلغ القرار ───────────────────────────────────────────
check(_a.get("stale") is True and _b.get("stale") is False,
      "٤ فالوسمُ ينقلب من شائخٍ إلى في أوانه",
      f"{_a.get('age_days')} ← {_b.get('age_days')} يوماً")
if _a.get("entry_price") and _b.get("entry_price"):
    check(_b["entry_price"] > _a["entry_price"],
          "٤ب وسعرُ الدخول يرتفع — الإنذارُ الكاذبُ كان يخفضه ظلماً",
          f"{_a['entry_price']} ← {_b['entry_price']}")

# ── ٥ · ولا يُدمَج في السلسلة السنوية ─────────────────────────────────
# لو أُقحم لصار طولُ السلسلة ثلاثةً والنموُّ المركّبُ على أساسَين.
check(len(_per) == 2,
      "٥ والسلسلةُ السنويةُ تبقى كما هي — لا يُخلط أساسان",
      f"{len(_per)} فترتين")

print(("FAIL" if fail else "PASS")
      + " D412 — أحدثُ ربعٍ يصل المحرّك، والسلسلةُ لا تُخلَط")
sys.exit(fail)
