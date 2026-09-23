#!/usr/bin/env python3
"""خريطةُ القطاعات تعرض درجةَ كلِّ شركةٍ حسبها المحرّك — لا ما فُتح منها (D432).

    python3 scripts/audit/sector_map_all_scores.py

قال المالك: «عدمُ ظهور جميع درجات الحوكمة لكامل الشركات لكامل القطاعات،
وإنّما جزئياتٌ على مزاجه — هذا قصورٌ يحتاج حلّاً». ورأى «المرافق العامة —
7 شركات»: درجةٌ لواحدةٍ (‏2080 = 80) و«لا ينطبق» للستّ الباقية.

وقِيس السبب: `get_sector_map` تجمع الدرجاتِ من ثلاثة مصادرَ فقط — مسحُ
حوكمة السوق (يستثني ما يملكه المالك، ويُبطَل مع كلّ تعديلٍ للقواعد)،
وعمودُ `Company.finance_score` (شركاتُ المحفظة وحدَها)، ومخزنُ
`governance:deep` (يُملأ **عند فتح صفحة الشركة**). ولا تقرأ مخزنَ مسحة
التقييم — المصدرَ الوحيدَ الشاملَ، وفيه درجةٌ لـ270 شركةً من 273. فتظهر
الدرجةُ لشركةٍ فتحها المالكُ أو يملكها، وتغيب عن غيرها: «على مزاجه».

والفحصُ سلوكيّ: تُنادى الدالّةُ الحقيقيةُ بقاعدةٍ فارغةٍ ومسحٍ فارغ،
ومخزنُ المسحة وحدَه يحمل درجاتِ ثلاثِ شركاتِ مرافق — فيُشترط أن تظهر
الثلاثُ في قطاعها.
"""
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")

import asyncio
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


try:
    from app.services import governance as G
    from app.services.content_engine import _fund_store_put_many
    from app.data.saudi_directory import SAUDI_DIRECTORY
    from app.data.universe import is_nomu as _is_nomu
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)


class _Res:
    def all(self):
        return []


class _DB:
    async def execute(self, *_a, **_k):
        return _Res()


async def _no_scan(*_a, **_k):
    return {"opportunities": []}

G.get_market_governance = _no_scan

WANT = {"2081": 71.0, "2082": 64.0, "2083": 58.0}
_fund_store_put_many({s: {"finance_score": v} for s, v in WANT.items()})
from app.services import lastgood as _lg                           # noqa: E402
_lg.flush()

sec = (SAUDI_DIRECTORY.get("2081") or {}).get("sector")
out = asyncio.run(G.get_sector_map(_DB()))
row = next((s for s in (out or {}).get("sectors", []) if s["sector"] == sec), None)
check(row is not None, "٠ قطاعُ الشركات الثلاث في الخريطة", str(sec))
if row:
    got = {c["symbol"]: c["finance_score"] for c in row["companies"]}
    for s, v in WANT.items():
        check(got.get(s) == v,
              f"١ {s} تظهر درجتُها من مسحة التقييم وإن لم تُفتح صفحتُها",
              f"المعروض {got.get(s)} · المحسوب {v}")
    check(row.get("avg_score") is not None,
          "٢ ومتوسطُ القطاع يُحسب منها", str(row.get("avg_score")))

# ── ٣ · والخريطةُ للسوق الرئيسيّ وحدَه ──────────────────── (D387)
# في الصورة نفسِها «غاز 9516» بين المرافق — ورقةُ «نمو»، والمالكُ أخرج
# «نمو» من عرض السوق. والخريطةُ كانت تجمع الدليلَ كلَّه بلا تصفية.
_nomu = [c["symbol"] for s_ in (out or {}).get("sectors", [])
         for c in s_["companies"] if _is_nomu(c["symbol"])]
check(not _nomu, "٣ لا ورقةَ «نمو» في خريطة القطاعات",
      f"{len(_nomu)}: {_nomu[:6]}" if _nomu else "")

print(("FAIL" if fail else "PASS")
      + " D432 — كلُّ درجةٍ حسبها المحرّك تظهر في خريطة القطاعات")
sys.exit(fail)
