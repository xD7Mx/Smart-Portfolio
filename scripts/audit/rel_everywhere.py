#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D230 — التقييمُ المتاحُ يظهر في كلّ شاشةٍ تعرض تقييماً.
#
# قال المالك: «في تحليل الذكاء لا زالت الشركات تعرض غير متاح بالرغم من
# التقييم النسبي متوفر لها». وكان محقّاً من وجهين:
#   ١· «رؤية الذكاء لشركات محفظتك» تقرأ `analyze_company` — وهو يحسب
#      القيمةَ النسبية — ثم تُسقطها من مخرَجها، فتُعلن غياباً وهو حاضرٌ
#      في يدها.
#   ٢· صفوفُ الفرز تُخزَّن يومياً، فكلُّ صفٍّ بُني قبل وجود المحرّك يبقى
#      بلا قيمةٍ إلى الأبد — عطبُ اللقطة المجمّدة (‏D226) من وجهٍ أشدّ.
#
# فيُقاس السلوكُ لا النصّ: تُشغَّل الدالّتان على مدخلاتٍ محكومة.
# وبالاتّجاه المعاكس: حيث يوجد هدفُ محلّلين لا تزحف النسبيةُ عليه، وحيث
# لا تقييمَ أصلاً يبقى «غير متاح» — فالصدقُ في الغياب شرطٌ لا استثناء.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


# ── مخزنٌ محكوم: قطاعٌ من عشرِ شركاتٍ مضاعفاتُه معلومة ───────────────────
SECTOR = "الطاقة"
STORE = {f"1{i:03d}": {"pe_ratio": 10 + i * 0.3, "price_to_book": 1 + i * 0.03,
                       "book_value": 40.0}
         for i in range(10)}
STORE["9999"] = {"pe_ratio": 11.0, "price_to_book": 1.1, "book_value": 40.0}

from app.services import content_engine as _ce  # noqa: E402
from app.data import company_sectors as _cs  # noqa: E402
import app.services.market_screener as ms  # noqa: E402

_ce.fund_store_load = lambda: dict(STORE)                        # type: ignore[assignment]
_cs.SYMBOL_TO_SECTOR_AR = {k: SECTOR for k in STORE}             # type: ignore[assignment]
ms.cache.get = lambda *_a, **_k: None                            # type: ignore[assignment]


async def _no_score(*_a, **_k):
    return None


ms._governance_score = _no_score                                 # type: ignore[assignment]


def _refresh(rows):
    return asyncio.run(ms.refresh_derived(rows))


# ── ١ · صفٌّ قديمٌ بلا قيمةٍ نسبيةٍ يُنعَش عند التقديم ────────────────────
stale = {"symbol": "9999", "sector": SECTOR, "price": 50.0, "fair_value": None}
out = _refresh([dict(stale)])[0]
check(out.get("rel_value") is not None,
      "١ صفُّ الفرز المجمَّدُ تُحسب له القيمةُ النسبيةُ عند التقديم",
      f"rel_value={out.get('rel_value')} · ثقة {out.get('rel_conf')}")
check(bool(out.get("rel_basis")) and out.get("rel_low") is not None,
      "٢ ومعها أساسُها ونطاقُها ودرجةُ ثقتها — لا رقمَ عارياً",
      f"«{out.get('rel_basis')}» {out.get('rel_low')}–{out.get('rel_high')}")

# ── ٣ · الاتّجاه المعاكس: حيث وُجد الهدفُ لا تُحسب ───────────────────────
withfv = _refresh([{"symbol": "9999", "sector": SECTOR, "price": 50.0,
                    "fair_value": 55.0}])[0]
check(withfv.get("rel_value") is None,
      "٣ وحيث وُجد هدفُ المحلّلين لا تزحف عليه",
      f"fair_value={withfv.get('fair_value')} · rel_value={withfv.get('rel_value')}")

# ── ٤ · «رؤية الذكاء» تُمرّر ما في يدها ──────────────────────────────────
import app.services.analysis as _an  # noqa: E402
from app.api.v1.endpoints import ai as _ai  # noqa: E402


class _Co:
    def __init__(self):
        self.symbol, self.company_name, self.status = "9999", "شركةُ فحص", "ACTIVE"


class _H:
    def __init__(self):
        self.company = _Co()


class _Scalars:
    def all(self):
        return [_H()]


class _Res:
    def scalars(self):
        return _Scalars()


class _DB:
    async def execute(self, *_a, **_k):
        return _Res()


def _insight(analysis: dict) -> dict:
    async def _fake(*_a, **_k):
        return analysis
    _an.analyze_company = _fake                                  # type: ignore[assignment]
    r = asyncio.run(_ai.get_portfolio_insight(db=_DB()))         # type: ignore[arg-type]
    body = r.body if hasattr(r, "body") else r
    if isinstance(body, (bytes, bytearray)):
        import json
        body = json.loads(body)
    data = body.get("data") if isinstance(body, dict) else None
    return (data or {}).get("companies", [{}])[0]

_REL = {"price": 50.0, "fair_value": None, "fair_value_upside_pct": None,
        "rel_value": 54.0, "rel_low": 50.0, "rel_high": 58.0,
        "rel_conf": "متوسطة", "rel_basis": "مكرّر الربحية",
        "rel_upside_pct": 8.0,
        "financial": {"score": 70}}

c = _insight(dict(_REL))
check(c.get("rel_value") is not None and c.get("rel_upside_pct") is not None,
      "٤ رؤيةُ الذكاء تُمرّر القيمةَ النسبيةَ التي حسبها المحرّك",
      f"rel_value={c.get('rel_value')} · فرصة {c.get('rel_upside_pct')}%")
check(c.get("valuation") != "غير متاح",
      "٥ فلا تُعلن «غير متاح» على شركةٍ تقييمُها في يدها",
      str(c.get("valuation")))
check(c.get("fair_value") is None and c.get("valuation_basis") == "مكرّر الربحية",
      "٦ ولا تُدسّ في خانة هدف المحلّلين — أساسُها مُعلَن",
      f"fair_value={c.get('fair_value')} · أساس «{c.get('valuation_basis')}»")

# ── ٧ · والصدقُ في الغياب: بلا هدفٍ وبلا نسبيةٍ يبقى «غير متاح» ──────────
bare = _insight({"price": 50.0, "fair_value": None, "fair_value_upside_pct": None,
                 "financial": {"score": None}})
check(bare.get("valuation") == "غير متاح",
      "٧ وحيث لا تقييمَ أصلاً يبقى «غير متاح» — لا رقمَ يُختلق",
      str(bare.get("valuation")))

# ── ٨ · وبطاقةُ الجوال ليست أفقرَ من الجدول ─────────────────────────────
ai_page = (ROOT / "frontend/src/pages/AIPage.tsx").read_text(encoding="utf-8")
mobile = ai_page[ai_page.find("md:hidden"):]
check("rel_upside_pct" in mobile and "c.rel_value" in mobile,
      "٨ بطاقةُ الجوال تعرض ما يعرضه الجدول — لا شاشتان بحظّين")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
