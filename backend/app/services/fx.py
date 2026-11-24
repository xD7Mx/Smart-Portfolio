"""سعرُ الصرف إلى الريال (‏D789) — المحفظةُ كلُّها بعملةٍ واحدة هي الريال، والسهمُ الأمريكيُّ يُسعَّر بالدولار.

قال المالك (2026-11-23): «هل المعاملاتُ ستكون صحيحة؟ … أبغاها تدعم السوقين كاملَين، والمحفظةُ نفسُها تدعم الكيانَين».
والقاعدة: كلُّ مالٍ يُخزَّن في المحفظة بالريال — التكلفةُ والنقدُ والقيمةُ والتوزيعات — فتبقى عشراتُ مواضع الجمع والقيدُ
المزدوجُ ومطابقةُ النقد كما هي؛ والدولارُ يبقى في **السعر** وحده (سعرُ العملية والسعرُ الحيّ وتوزيعُ السهم).
  • العمليةُ تحمل سعرَ صرفها يومَ تنفيذها (‏Transaction.fx_rate) — فتكلفتُها بالريال ثابتةٌ لا تتحرّك بسعر اليوم.
  • والقيمةُ السوقيةُ بسعر اليوم — ففرقُ الصرف يظهر ربحاً أو خسارةً كما يظهر عند الوسيط.
  • وعمليةٌ بلا سعر صرف (كلُّ ما سُجّل قبل ‏D789، والسعوديُّ كلُّه) سعرُها واحد: تبقى أرقامُها كما سُجّلت حرفاً.

المصدر: ياهو ‏SAR=X (ريالٌ لكلّ دولار) بمسار السعر نفسِه (‏market_service.get_price — مخبّأٌ ربعَ ساعة)، ويُقبل في نطاق ربط
الريال وحده (3.70–3.80)؛ وتعذّرُه يعيد آخرَ سعرٍ مقروءٍ بتاريخه، ثمّ السعرَ الرسميَّ المثبَّت 3.75 (ربطُ البنك المركزيّ السعوديّ
منذ 1986). ويُسمّى المصدرُ في كلّ حالة («حيّ» · «آخرُ سعرٍ مقروء» · «السعرُ الرسميّ») فلا يُقرأ تقديرٌ كأنه سعرٌ حيّ.
"""
from __future__ import annotations

from datetime import datetime, timezone

BASE = "SAR"
PEG = 3.75                      # ربطُ الريال بالدولار — رسميٌّ منذ 1986
BAND = (3.70, 3.80)             # ما خرج عنه ليس سعرَ الريال (خطأُ مصدرٍ أو رمزٍ) فلا يُقبل
SUPPORTED = ("SAR", "USD")
LG_KEY = "fx:usd_sar"
SOURCE_AR = {"live": "حيّ", "lastgood": "آخرُ سعرٍ مقروء", "peg": "السعرُ الرسميّ المثبَّت"}

_last: dict = {"rate": None, "source": None, "at": None}


def norm(currency: str | None) -> str:
    c = (currency or BASE).strip().upper()
    return c if c in SUPPORTED else BASE


def is_us_symbol(symbol: str | None) -> bool:
    """رمزٌ أمريكيّ: حروفٌ لا أرقامٌ سعودية (‏AAPL · BRK-B · BRK.B)."""
    s = (symbol or "").strip().upper()
    base = s[:-3] if s.endswith(".SR") else s
    return bool(base) and not base.isdigit() and not s.endswith(".SR") and not s.startswith("^")


def last_rate() -> float:
    """آخرُ سعرٍ قُرئ في هذه العملية — للمسارات المتزامنة؛ وقبل أوّل قراءةٍ السعرُ الرسميّ."""
    return float(_last["rate"] or PEG)


def _ok(r) -> bool:
    try:
        return BAND[0] <= float(r) <= BAND[1]
    except (TypeError, ValueError):
        return False


async def usd_sar() -> dict:
    """{rate, source, at} — ‏source: live · lastgood · peg."""
    from app.services import lastgood
    try:
        from app.services.market_data import market_service
        p = await market_service.get_price("SAR=X")
        d = p.to_dict() if hasattr(p, "to_dict") else (p or {})
        r = d.get("price")
        if _ok(r):
            out = {"rate": round(float(r), 6), "source": "live", "at": datetime.now(timezone.utc).isoformat()}
            _last.update(out)
            lastgood.save(LG_KEY, out)
            return out
    except Exception:                                                # noqa: BLE001 — المصدرُ يتعذّر فيُنزل إلى ما بعده
        pass
    lg = lastgood.load(LG_KEY)
    if isinstance(lg, dict) and _ok(lg.get("rate")):
        out = {"rate": float(lg["rate"]), "source": "lastgood", "at": lg.get("at") or lg.get("_stale_since")}
        _last.update(out)
        return out
    out = {"rate": PEG, "source": "peg", "at": None}
    _last.update(out)
    return out


async def rate_now(currency: str | None) -> float:
    """ريالٌ لكلّ وحدةٍ من العملة اليوم — الريالُ واحد."""
    return 1.0 if norm(currency) == BASE else float((await usd_sar())["rate"])


async def company_fx(db, company_id: int) -> tuple[str, float, bool]:
    """(العملة، سعرُ اليوم للقيمة السوقية، أهي «قديمةٌ بلا سعر صرف»).

    الشركةُ بغير الريال وفي سجلّها عمليةٌ ماليةٌ بلا سعر صرف (سُجّلت قبل ‏D789 بأرقامٍ عُدّت ريالاً) تبقى قيمتُها بسعرٍ واحد —
    فلا تقفز أرقامُ المالك بضربها في سعر اليوم بلا طلبه؛ وتُعلَّم ليُكمل سعرَ صرفها بنفسه."""
    from sqlalchemy import func, select
    from app.models.portfolio import Company
    from app.models.transaction import Transaction
    cur = norm((await db.execute(select(Company.currency).where(Company.id == company_id))).scalar())
    if cur == BASE:
        return cur, 1.0, False
    legacy = (await db.execute(
        select(func.count(Transaction.id)).where(
            Transaction.company_id == company_id,
            Transaction.transaction_type.in_(["BUY", "SELL", "DIVIDEND"]),
            Transaction.fx_rate.is_(None),
        )
    )).scalar() or 0
    if legacy:
        return cur, 1.0, True
    return cur, await rate_now(cur), False


async def rates_for(db, company_ids) -> dict:
    """سعرُ صرف اليوم لكلّ شركة — واحدٌ للريال وللقديمة بلا سعر صرف — بنداءين للقاعدة مهما كثرت الشركات.

    لكلّ حسابٍ يحوّل سعرَ السهم إلى مالٍ أو المالَ إلى أسهم (الأهداف · التوازن · التصفية · المنحة · خطط السيولة)."""
    from sqlalchemy import select
    from app.models.portfolio import Company
    from app.models.transaction import Transaction
    ids = sorted({int(i) for i in company_ids if i is not None})
    out = {i: 1.0 for i in ids}
    if not ids:
        return out
    curs = dict((await db.execute(select(Company.id, Company.currency).where(Company.id.in_(ids)))).all())
    foreign = [i for i in ids if norm(curs.get(i)) != BASE]
    if not foreign:
        return out
    legacy = set((await db.execute(
        select(Transaction.company_id).where(
            Transaction.company_id.in_(foreign),
            Transaction.transaction_type.in_(["BUY", "SELL", "DIVIDEND"]),
            Transaction.fx_rate.is_(None),
        ).distinct()
    )).scalars().all())
    r = float((await usd_sar())["rate"])
    for i in foreign:
        out[i] = 1.0 if i in legacy else r
    return out


def tx_fx(t) -> float:
    """سعرُ صرف العملية المسجَّل — وبلا سعرٍ واحد (السعوديُّ وما قبل ‏D789 كما سُجّل)."""
    v = getattr(t, "fx_rate", None)
    try:
        return float(v) if v is not None and float(v) > 0 else 1.0
    except (TypeError, ValueError):
        return 1.0
