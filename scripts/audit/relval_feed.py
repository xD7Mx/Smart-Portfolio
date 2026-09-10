#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D233 — محرّكٌ رئيسيٌّ يُغذّى مُدخَلُه، ولا يُترك للحظّ.
#
# بأمر المالك: «لنجعل التقييم النسبي محرّكاً رئيسياً… يجب تغذيته ليغطّي
# كامل السوق». ومُدخَلُه مضاعفانِ لكلّ شركة، والمسحةُ الليلية كانت تنادي
# `get_company_info` للكون كلِّه — لكنّ نداءً يعود **من الكاش** لا يمرّ
# بحافظ التقييم، فيبقى بيانٌ في اليد ولا يصل المخزن. وميزةٌ رئيسيةٌ
# مُدخَلُها متروكٌ للحظّ ليست رئيسية.
#
# فيُقاس السلوكُ على مزوّدٍ مموَّه:
#   ١· التغطيةُ تُحصي الصالحَ لا الموجود (مكرّرٌ ٩٩٩ ليس مضاعفاً)
#   ٢· التغذيةُ تنادي **الناقصين وحدَهم** — لا الكونَ كلَّه
#   ٣· وتحفظ ممّا يعود ولو كان من الكاش (هو العطبُ بعينه)
#   ٤· وتتوقّف عند احتياطي حصّةِ نهار العمل ولا تسرقه
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


from app.services import content_engine as ce  # noqa: E402
from app.services import market_data as md  # noqa: E402

UNIVERSE = [("1001", "أ"), ("1002", "ب"), ("1003", "ج"), ("1004", "د")]
# ‏1001 مغطّاةٌ · 1002 مكرّرُها خارج المدى (‏999) فليست مغطّاة ·
# ‏1003 و1004 لا صفَّ لهما أصلاً.
STORE = {"1001": {"pe_ratio": 14.0}, "1002": {"pe_ratio": 999.0}}
called: list[str] = []
saved: dict[str, dict] = {}

ce._universe_pairs = lambda: list(UNIVERSE)                      # type: ignore[assignment]
ce.fund_store_load = lambda: {k: dict(v) for k, v in STORE.items()}  # type: ignore[assignment]


class _Svc:
    async def get_company_info(self, ysym):
        called.append(ysym)
        # يعود من الكاش: مخرَجٌ صحيحٌ بلا مرورٍ بحافظ التقييم داخل الجالب.
        return {"pe_ratio": 12.5, "price_to_box": None, "price_to_book": 1.4}


def _persist(ysym, data):
    sym = str(ysym).split(".")[0]
    saved[sym] = {"pe_ratio": data.get("pe_ratio"),
                  "price_to_book": data.get("price_to_book")}
    STORE[sym] = dict(saved[sym])


md.market_service = _Svc()                                       # type: ignore[assignment]
md._persist_valuation = _persist                                 # type: ignore[assignment]

_headroom = {"used": 0, "limit": 10000}
import app.services.usage_tracker as ut  # noqa: E402
ut.usage = lambda p: {"daily_used": _headroom["used"],            # type: ignore[assignment]
                      "daily_limit": _headroom["limit"]}

# ── ١ · التغطيةُ تُحصي الصالح ─────────────────────────────────────────────
cov = ce.relative_inputs_coverage()
check(cov["universe"] == 4 and cov["covered"] == 1
      and set(cov["missing"]) == {"1002", "1003", "1004"},
      "١ التغطيةُ تُحصي المضاعفَ الصالحَ لا الموجود",
      f"{cov['covered']}/{cov['universe']} · ناقص {sorted(cov['missing'])}")

# ── ٢ · التغذيةُ للناقصين وحدَهم ─────────────────────────────────────────
filled = asyncio.run(ce.top_up_relative_inputs())
check(sorted(called) == ["1002.SR", "1003.SR", "1004.SR"],
      "٢ نُوديَ الناقصون وحدَهم — لا الكونُ كلُّه",
      f"{len(called)} نداءً: {sorted(called)}")

# ── ٣ · والحفظُ ممّا يعود ولو من الكاش — وهو العطبُ بعينه ────────────────
check(filled == 3 and set(saved) == {"1002", "1003", "1004"}
      and saved["1003"]["pe_ratio"] == 12.5,
      "٣ حُفظ المضاعفُ صراحةً ممّا عاد به الجالب",
      f"مُلئ {filled} · محفوظ {sorted(saved)}")
after = ce.relative_inputs_coverage()
check(after["covered"] == 4 and not after["missing"],
      "٤ فصارت التغطيةُ كاملةً للسوق المموَّه",
      f"{after['covered']}/{after['universe']}")

# ── ٥ · ولا تُسرَق حصّةُ نهار العمل ──────────────────────────────────────
STORE.clear()
STORE.update({"1001": {"pe_ratio": 14.0}})
called.clear(); saved.clear()
_headroom["used"] = _headroom["limit"] - 10        # دون الاحتياطي (‏120)
filled2 = asyncio.run(ce.top_up_relative_inputs())
check(filled2 == 0 and not called,
      "٥ عند اقتراب الاحتياطي تتوقّف بهدوء ولا تنادي",
      f"مُلئ {filled2} · نداءات {len(called)}")

# ── ٦ · ولا نداءَ حين لا نقص ─────────────────────────────────────────────
_headroom["used"] = 0
STORE.update({s: {"pe_ratio": 13.0} for s, _ in UNIVERSE})
called.clear()
filled3 = asyncio.run(ce.top_up_relative_inputs())
check(filled3 == 0 and not called,
      "٦ وحين تكتمل التغطيةُ لا نداءَ ولا كتابة")

# ── ٧ · والمسحةُ الليلية تستدعيها فعلاً ─────────────────────────────────
src = (ROOT / "backend/app/services/content_engine.py").read_text(encoding="utf-8")
i_sweep = src.index("async def build_fundamentals_full")
i_end = src.index("def relative_inputs_coverage", i_sweep)
check("top_up_relative_inputs(" in src[i_sweep:i_end],
      "٧ المسحةُ الليلية تستدعي التغذية — لا دالّةٌ لا ينادِيها أحد")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
