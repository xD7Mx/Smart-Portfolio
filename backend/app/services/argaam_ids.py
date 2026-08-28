"""خريطة رمز تداول ← معرّف الشركة في «أرقام» — تُبنى تلقائياً وتدوم.

## لماذا لا تُجمع الروابط يدوياً

عرض المالك أن نجمع الروابط يدوياً. وهو حلٌّ يعمل اليوم ويموت غداً: كل
إدراجٍ جديد في السوق يحتاج تدخّلاً بشرياً، وكل تغييرٍ في ترقيم «أرقام»
يترك روابطَ ميتة لا يكتشفها أحد حتى يضغطها المالك.

والبديل موجودٌ ومقيس: **صفحة مفكرة أرقام تحمل قائمة الشركات كاملةً**
(٤٠٨ شركة) في ترميزها، كلٌّ برمز تداول واسمها ومعرّفها:

    <span relf-Stocksymbol="2222" relf-companyName="أرامكو السعودية"
          value="3509">

فالخريطة تُقرأ من المصدر نفسه، وتتجدّد مع كل تحديثٍ مجدوَل. الإدراج
الجديد يدخل وحده يوم يظهر في الصفحة، بلا صيانة.

## الدوام حين ينقطع المصدر

تُحفظ الخريطة على القرص بعد كل بناءٍ ناجح. فإن تعذّر الوصول لاحقاً —
حجبٌ أو تغيير بنية — تُقرأ آخر خريطةٍ سليمة بدل أن تختفي الأزرار كلّها.
وتُحفظ معها لحظةُ بنائها: المصدر المخزَّن يُعرض بتاريخ تخزينه، لا كأنه
لحظيّ.
"""

import json
import time
from pathlib import Path
from loguru import logger

STORE = Path(__file__).resolve().parents[3] / "data" / "argaam_ids.json"
MAX_AGE = 7 * 24 * 3600          # يُعاد البناء أسبوعياً
BASE = "https://www.argaam.com"


def _load() -> dict:
    try:
        if STORE.exists():
            return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"argaam_ids: تعذّرت قراءة المخزَّن: {e}")
    return {}


def _save(ids: dict, built_at: float) -> None:
    try:
        STORE.parent.mkdir(parents=True, exist_ok=True)
        STORE.write_text(json.dumps({"built_at": built_at, "ids": ids},
                                    ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"argaam_ids: تعذّر الحفظ: {e}")


async def build(force: bool = False) -> dict:
    """يبني الخريطة من صفحة المفكرة. لا يرفع استثناءً أبداً.

    عند الفشل يُعاد المخزَّن كما هو — **ولا يُمسح**. خريطةٌ عمرها أسبوع
    خيرٌ من لا خريطة: أرقامُ الشركات لا تتغيّر، والناقص وحده هو المُدرَج
    حديثاً.
    """
    cached = _load()
    ids = cached.get("ids") or {}
    age = time.time() - float(cached.get("built_at") or 0)
    if ids and not force and age < MAX_AGE:
        return ids

    try:
        from app.services.argaam_calendar import CAL_URL, UA, _company_index
        import httpx
        async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                     headers={"User-Agent": UA,
                                              "Accept-Language": "ar,en;q=0.8"}) as c:
            r = await c.get(CAL_URL)
            r.raise_for_status()
            idx = _company_index(r.text)          # الاسم ← (رمز، معرّف)
        fresh = {sym: cid for (sym, cid) in idx.values()}
        if len(fresh) < 200:
            # عددٌ أقلّ من هذا يعني بنيةً تغيّرت لا سوقاً انكمش — لا يُعتمد.
            logger.warning(f"argaam_ids: {len(fresh)} فقط — تُرفض ويبقى المخزَّن.")
            return ids
        _save(fresh, time.time())
        logger.info(f"🔗 argaam_ids: {len(fresh)} شركة.")
        return fresh
    except Exception as e:
        logger.warning(f"argaam_ids: تعذّر البناء ({e}) — يُخدَم المخزَّن ({len(ids)}).")
        return ids


def url_for(symbol: str, ids: dict | None = None) -> str | None:
    """رابط صفحة الشركة في أرقام — أو None إن لم يُعرف معرّفها.

    ولا يُختلق رابطٌ بالبحث: زرٌّ يفتح صفحة بحثٍ ليس «افتح في أرقام»،
    والوعد الذي لا يُوفى أسوأ من زرٍّ غائب.
    """
    ids = ids if ids is not None else (_load().get("ids") or {})
    cid = ids.get(str(symbol or "").replace(".SR", "").strip())
    return f"{BASE}/ar/company/companyoverview/marketid/3/companyid/{cid}" if cid else None


def snapshot() -> dict:
    """الخريطة وعمرها — للواجهة، فتعرف متى بُنيت."""
    c = _load()
    return {"ids": c.get("ids") or {}, "built_at": c.get("built_at")}
