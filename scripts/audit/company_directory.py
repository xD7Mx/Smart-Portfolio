#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D256 — دليلُ الشركات: هويّةٌ من مصدرها، ورابطٌ لا يُختلق.
#
# بأمر المالك: «أضف ميزة دليل الشركات كزرٍّ بجانب علامة البحث في نبض
# السوق — دليلُ الشركات تجده في أرقام».
#
# وخطرُه صنفان وقعنا فيهما قبلاً: حقلٌ يُقرأ من حيث لا وجودَ له فيخرج
# «غير متوفّر» للسوق كلِّه (وهو اختلاقُ حقلٍ لا نقصُ بيانات)، ورابطٌ
# يُصنَع لمن لا معرِّفَ له فيفتح صفحةَ خطأ. فيُقاس السلوك:
#   ٠· الدليلُ يحمل السوقَ كلَّه لا عيّنةً
#   ١· ولكلّ صفٍّ رمزٌ واسمٌ وقطاع
#   ٢· ورابطُ «أرقام» لمن له معرِّفٌ وحدَه — ولا يُختلق لغيره
#   ٣· ولا حقلَ حكمٍ شرعيٍّ هنا (مصدرُه آخر، وحقلٌ فارغٌ للجميع عطب)
#   ٤· ووسمُ الإيقاف يُنقل كما هو من طبقة المزامنة
#   ٥· ولا سعرَ في الدليل — هويّةٌ لا شاشةُ تداول
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
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


from app.api.v1.endpoints.market import company_directory  # noqa: E402
from app.data.saudi_directory import SAUDI_DIRECTORY  # noqa: E402
import app.services.argaam_ids as ai  # noqa: E402

# خريطةُ معرِّفاتٍ ناقصةٌ عمداً: شركتان لهما معرِّفٌ والباقي بلا.
_syms = sorted(SAUDI_DIRECTORY)
ai._load = lambda: {"ids": {_syms[0]: "47", _syms[1]: "81"},   # type: ignore[assignment]
                    "built_at": 9e12}

res = asyncio.run(company_directory())
data = (res or {}).get("data") or {}
rows = data.get("companies") or []

check(len(rows) == len(SAUDI_DIRECTORY) and data.get("count") == len(rows),
      "٠ الدليلُ يحمل السوقَ كلَّه لا عيّنةً",
      f"{len(rows)} من {len(SAUDI_DIRECTORY)}")
check(all(r.get("symbol") and r.get("name") for r in rows),
      "١ ولكلّ صفٍّ رمزٌ واسم")
check(sum(1 for r in rows if r.get("sector")) >= len(rows) - 5,
      "١ب ولقطاعِه", f"{sum(1 for r in rows if r.get('sector'))} بقطاع")

with_url = [r for r in rows if r.get("argaam_url")]
check(len(with_url) == 2 and all("companyid/" in r["argaam_url"] for r in with_url),
      "٢ رابطُ «أرقام» لمن له معرِّفٌ وحدَه — ولا يُختلق لغيره",
      f"{len(with_url)} رابطاً من {len(rows)}")
check(all(r.get("argaam_url") is None for r in rows if r["symbol"] not in _syms[:2]),
      "٢ب ومن لا معرِّفَ له يعود بلا رابطٍ لا برابطِ بحث")

check(all("sharia" not in r for r in rows),
      "٣ ولا حقلَ حكمٍ شرعيٍّ هنا — مصدرُه آخر، وفراغُه للجميع عطب")
check(all("price" not in r and "change_pct" not in r for r in rows),
      "٥ ولا سعرَ في الدليل — هويّةٌ لا شاشةُ تداول")
check(all(isinstance(r.get("suspended"), bool) for r in rows),
      "٤ ووسمُ الإيقاف منقولٌ لكلّ صفٍّ بقيمةٍ صريحة")

# ── الزرُّ في موضعه: بجانب البحث في «نبض السوق» ─────────────────────────
page = (ROOT / "frontend" / "src" / "pages" / "MarketPage.tsx").read_text(encoding="utf-8")
m = re.search(r"InlineStockSearch onPick=\{onSearch\} />", page)
tail = page[m.end(): m.end() + 400] if m else ""
check(bool(m) and "CompanyDirectory" in tail,
      "٦ الزرُّ في ترويسة «نبض السوق» بجانب البحث مباشرةً")
comp = (ROOT / "frontend" / "src" / "components" / "market"
        / "CompanyDirectory.tsx").read_text(encoding="utf-8")
check('aria-label="دليل الشركات"' in comp,
      "٦ب وله اسمٌ مسموعٌ — لا زرَّ صامتاً في التطبيق")

print(("FAIL" if fail else "PASS") + " D256 — دليلُ الشركات")
raise SystemExit(fail)
