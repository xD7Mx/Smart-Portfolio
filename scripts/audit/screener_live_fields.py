#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D226 — الجدولُ لا يخالف صفحةَ السهم لأنه أقدمُ منها.
#
# رأى المالكُ عائدَ التوزيعات ودرجةَ الجودة في فرز السوق يخالفان صفحةَ
# السهم «كأنهما تطبيقان». والسببُ ليس حساباً مختلفاً — فقد وُحِّد المُنتِج
# (‏D223) — بل **زمناً مختلفاً**: صفوفُ الفرز لقطةٌ تُبنى مرّةً في اليوم
# وتُخزَّن، وصفحةُ السهم تحسب لحظتَها.
#
# والفصلُ الصحيح: **ما يكلّف شبكةً يُخزَّن، وما يُقرأ من مخزنٍ يُحسب عند
# الطلب.** السعرُ والمتوسّطاتُ وRSI تبقى لقطةً (نداءُ تاريخٍ لكلّ شركة)،
# وعائدُ التوزيعات ودرجةُ الجودة يُقرآن من المخزن بلا نداءٍ واحد.
#
# والاتّجاه المعاكس هو الخطر: إنعاشٌ يمسح قيمةً كانت في الصفّ فيُفرَّغ
# عمودٌ أمام المالك. فما تعذّر إنعاشُه يبقى كما كان.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

from app.services import market_screener as ms                   # noqa: E402
from app.services import content_engine as ce                    # noqa: E402

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


# مخزنٌ مُصطنَع: رقمُ المزوّد ‎2.56 موجودٌ فيه، والصفُّ المجمَّد يحمل ‎2.44
STORE = {"8210": {"dividend_yield": 2.56, "dps_ttm": 3.84}}
ce.fund_store_load = lambda: STORE
ms.cache.get = lambda k: None                      # لا كاشَ حيّ

FROZEN = [{"symbol": "8210", "price": 157.20, "sector": "التأمين",
           "dividend_yield": 2.44, "finance_score": 81.0}]


async def _no_engine(ysym, sector):
    return None                                    # المحرّكُ يمتنع (لا قوائم)


ms._governance_score = _no_engine
rows = asyncio.run(ms.refresh_derived([dict(r) for r in FROZEN]))

# ── ١ · العائدُ المجمَّدُ يُستبدَل برقم المُنتِج الواحد ────────────────
check(rows[0]["dividend_yield"] == 2.56,
      "١ العائدُ يُنعَش من المُنتِج الواحد لا من اللقطة",
      f"2.44 ⇐ {rows[0]['dividend_yield']}")

# ── ٢ · ومصدرُه يُعلَن ────────────────────────────────────────────────
check(rows[0].get("dividend_yield_source") == "المزوّد",
      "٢ ومصدرُ الرقم معلَن", str(rows[0].get("dividend_yield_source")))

# ── ٣ · الاتّجاه المعاكس: امتناعُ المحرّك لا يُفرّغ عموداً مملوءاً ────
# لو مُسح المخزَّنُ عند تعذّر الحساب لرأى المالكُ عموداً كان مملوءاً وقد فرغ —
# وذلك أسوأ من رقمٍ قديمٍ بيومٍ واحد.
check(rows[0]["finance_score"] == 81.0,
      "٣ درجةٌ تعذّر إنعاشُها تبقى كما كانت", str(rows[0]["finance_score"]))


# ── ٤ · والمحرّكُ حين ينطق يغلب المخزَّن (D198) ──────────────────────
async def _engine(ysym, sector):
    return 88.0


ms._governance_score = _engine
rows2 = asyncio.run(ms.refresh_derived([dict(r) for r in FROZEN]))
check(rows2[0]["finance_score"] == 88.0,
      "٤ وحين ينطق المحرّكُ يغلب المخزَّن", f"81 ⇐ {rows2[0]['finance_score']}")

# ── ٥ · وصفٌّ بلا رمزٍ لا يُسقط الإنعاشَ كلَّه ───────────────────────
rows3 = asyncio.run(ms.refresh_derived([{"price": 10}, dict(FROZEN[0])]))
check(len(rows3) == 2 and rows3[1]["dividend_yield"] == 2.56,
      "٥ صفٌّ ناقصٌ لا يُسقط بقيّةَ الجدول")

# ── ٦ · والنقطةُ تستدعي الإنعاشَ فعلاً ──────────────────────────────
ep = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
# الاسمُ صار `refresh_derived_cached` بعد حفظِ مخرَجه تسعين ثانية
# (‏D243) — والمقصودُ أن النقطةَ تُنعش لا أن تنادي اسماً بعينه.
check("refresh_derived_cached(rows)" in ep or "refresh_derived(rows)" in ep,
      "٦ نقطةُ الفرز تستدعي الإنعاش")

# ── ٧ · صيغتا النداء تُعطيان الرقمَ نفسَه ────────────────────────────
# ══ لماذا هذا الفحصُ بالذات ══
# قال المالك: «الموضوع تكرّر لأكثر من حزمة». وسببُ التكرار أنّي كنتُ أفحص
# طرفاً واحداً في كلّ مرّة. والطرفان ينادِيان الدالّةَ نفسَها بصيغتين:
#   · الفرز يمرّر الكاشَ والمخزنَ **صراحةً** (هما بيده أصلاً)
#   · وصفحةُ السهم تتركها **تقرأ بنفسها**
# فلو اختلف ما تقرؤه الدالّةُ بنفسها عمّا يُمرَّر إليها، عاد الاختلافُ من
# بابٍ آخر — ويمرّ كلُّ فحصٍ يقيس طرفاً واحداً.
import app.services.cache as _cache_mod                          # noqa: E402
from app.services.dividend_yield import resolve as _resolve      # noqa: E402

_FAKE = {"fund:yahoo:8210.SR": {}}
_cache_mod.get = lambda k: _FAKE.get(k)
ce.fund_store_load = lambda: STORE

explicit, src_e = _resolve("8210", 157.20, _FAKE["fund:yahoo:8210.SR"], STORE["8210"])
implicit, src_i = _resolve("8210", 157.20)          # كما تفعل صفحة السهم
check(explicit == implicit and src_e == src_i,
      "٧ صيغتا النداء (صريحةٌ وذاتيةُ القراءة) تُعطيان الرقمَ نفسَه",
      f"{explicit} · {src_e}  ⇐  {implicit} · {src_i}")

# ── ٨ · والرقمُ في صفّ الجدول هو عينُه ما تعرضه الصفحة ───────────────
# القياسُ من طرفٍ إلى طرف: صفٌّ مجمَّدٌ يمرّ بالإنعاش، ورقمُ الصفحة يُحسب،
# ثمّ يُقارَنان — لا يُفحص كلٌّ في معزل.
ms.cache.get = lambda k: _FAKE.get(k)
ms._governance_score = _no_engine
row = asyncio.run(ms.refresh_derived([dict(FROZEN[0])]))[0]
page_value, _ = _resolve("8210", 157.20)
check(row["dividend_yield"] == page_value,
      "٨ رقمُ الجدول = رقمُ صفحة السهم (قياسٌ من طرفٍ إلى طرف)",
      f"جدول {row['dividend_yield']} · صفحة {page_value}")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
