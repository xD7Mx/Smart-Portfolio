#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D226 (طرفٌ إلى طرف) — ما يخرج من النقطة، لا ما تعيده الدالّة.
#
# قال المالك: «الموضوع تكرّر لأكثر من حزمة». وسببُ التكرار في فحصي لا في
# الشيفرة: كنتُ أقيس **دالّةً في معزل** وأقول «طوبق». والدالّةُ قد تصحّ
# والنقطةُ لا تستدعيها، أو تستدعيها بصيغةٍ أخرى، أو يسبقها كاشٌ فيُقدَّم
# الصفُّ المجمَّد كما هو.
#
# فيُشغَّل هنا **خادمٌ حقيقيّ** (بلا شبكة): يُركَّب موجِّهُ السوق، ويُسأل
# `/market/screener` عبر HTTP، ويُقارَن ما في الصفّ بما تحسبه صفحةُ السهم
# من المُنتِج الواحد. صفٌّ مجمَّدٌ على رقمٍ قديم يجب أن يخرج بالرقم الحيّ.
#
# وإن غاب `fastapi.testclient` قيل ذلك ومُرّ — فحصٌ لا يستطيع القياس لا يحكم.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import pathlib
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except Exception as e:                                            # noqa: BLE001
    print(f"… تعذّر الفحص: fastapi/testclient غيرُ متاح ({type(e).__name__}).")
    raise SystemExit(0)

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


PROVIDER_DY = 2.56
STORE = {"8210": {"dividend_yield": PROVIDER_DY, "dps_ttm": 3.84}}
# الصفُّ كما تركته لقطةُ الأمس: عائدٌ قديمٌ ودرجةٌ مخزَّنة.
FROZEN = [{"symbol": "8210", "name": "بوبا العربية", "price": 157.20,
           "sector": "التأمين", "dividend_yield": 2.44, "finance_score": 81.0}]

import app.services.content_engine as ce                          # noqa: E402
ce.fund_store_load = lambda: STORE
import app.services.market_screener as ms                         # noqa: E402
ms.get_cached_screener = lambda: [dict(r) for r in FROZEN]


async def _abstain(ysym, sector):
    return None


async def _speaks(ysym, sector):
    return 88.0


from app.api.v1.endpoints import market as mkt                    # noqa: E402
from app.services.dividend_yield import resolve                   # noqa: E402

app = FastAPI()
app.include_router(mkt.router, prefix="/api/v1/market")
try:
    from app.core.auth import require_owner
    app.dependency_overrides[require_owner] = lambda: None
except Exception:                                                 # noqa: BLE001
    pass
client = TestClient(app)


def served_row(verdict=None):
    # ══ كلُّ قياسٍ يبدأ من صفر ══ (بعد D243)
    # مخرَجُ الإنعاش محفوظٌ تسعين ثانيةً ودرجةُ كلّ رمزٍ ساعةً — وهو مقصود.
    # وموضوعُ هذا الفحص سلسلةُ الإنتاج، فيُبطَل المحفوظُ قبل كلّ طلبٍ كي
    # يُقاس ما تحسبه النقطةُ الآن لا جوابُ طلبٍ سابق. ولا `delete` في
    # وحدة الكاش، فيُكتب المفتاحُ بعمرٍ صفريّ بأدواتها نفسِها.
    from app.services import cache as _c2
    _c2.set(ms.REFRESHED_KEY, None, 0)
    _c2.set("screener:gov:8210.SR", None, 0)
    # ‏D434: حكمُ المحرّك يصل التقديمَ محفوظاً — يُكتب عند بناء الجدول
    # (‏`_enrich_fundamentals`) لا بتشغيل المحرّك لكلّ صفٍّ في كلّ فتحة.
    if verdict is not None:
        _c2.set("screener:gov:8210.SR", verdict, 60)
    r = client.get("/api/v1/market/screener")
    if r.status_code != 200:
        return None, r.status_code
    rows = (r.json().get("data") or {}).get("rows") or []
    return next((x for x in rows if str(x.get("symbol")) == "8210"), None), 200


# ── ١ · النقطةُ تردّ، والصفُّ موجود ──────────────────────────────────
ms._governance_score = _abstain
row, code = served_row()
check(row is not None, "١ نقطةُ الفرز تردّ بصفّ الشركة", f"HTTP {code}")
if row is None:
    print()
    print("النتيجة: فيه ملاحظات ✘")
    raise SystemExit(1)

# ── ٢ · العائدُ الخارجُ من النقطة = ما تحسبه صفحةُ السهم ─────────────
page, page_src = resolve("8210", 157.20)
check(row.get("dividend_yield") == page,
      "٢ عائدُ الجدول من النقطة = عائدُ صفحة السهم",
      f"جدول {row.get('dividend_yield')} · صفحة {page}")

# ── ٣ · ولم يخرج الرقمُ المجمَّد ─────────────────────────────────────
# الاتّجاه المعاكس للعطب: لو لم يُستدعَ الإنعاشُ لخرج ‎2.44 وسكت كلُّ فحص.
check(row.get("dividend_yield") != 2.44,
      "٣ ولم يخرج الرقمُ المجمَّد من اللقطة", str(row.get("dividend_yield")))

# ── ٤ · ومصدرُه معلَنٌ في الصفّ ──────────────────────────────────────
check(row.get("dividend_yield_source") == page_src,
      "٤ ومصدرُ الرقم معلَنٌ ومطابق", f"{row.get('dividend_yield_source')} · {page_src}")

# ── ٥ · وحين ينطق المحرّكُ تخرج درجتُه لا المخزَّنة ──────────────────
# ══ يُبطَل المحفوظُ قبل القياس ══ (بعد D243)
# صار مخرَجُ الإنعاش محفوظاً تسعين ثانية ودرجةُ كلّ رمزٍ ساعةً — وهو
# مقصودٌ (الفتحةُ الثانية بلا حساب). وموضوعُ هذا الفحص سلسلةُ الإنتاج لا
# دلالةُ الحفظ، فيُبطَل المحفوظُ صراحةً ثمّ يُقاس. ولو تُرك، لقاس الفحصُ
# جوابَ الطلب السابق وسمّاه عطباً — وهو خطأُ قياسٍ لا عطبُ تطبيق.
row2, _ = served_row(verdict=88.0)
check(row2 is not None and row2.get("finance_score") == 88.0,
      "٥ درجةُ المحرّك تخرج من النقطة لا المخزَّنة",
      f"مخزَّن 81 ⇐ {None if row2 is None else row2.get('finance_score')}")

# ── ٦ · وامتناعُ المحرّك يُبقي المخزَّنة ولا يُفرّغ العمود ───────────
row3, _ = served_row()                   # لا حكمَ محفوظ: جهلٌ يُبقي
check(row3 is not None and row3.get("finance_score") == 81.0,
      "٦ وامتناعُه يُبقي المخزَّنة — لا عمودَ يُفرَّغ",
      str(None if row3 is None else row3.get("finance_score")))

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
