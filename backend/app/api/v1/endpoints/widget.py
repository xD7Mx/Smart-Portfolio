"""ويدجت الآيفون (‏D791) — ملخّصُ المحفظة لشاشة الآيفون الرئيسية.

قال المالك (2026-11-24): «أريد على الآيفون ويدجت كبقية التطبيقات لتطبيق المحفظة الذكية».
ويدجت الآيفون الأصيلُ (‏WidgetKit) لا يصنعه إلا تطبيقٌ أصيلٌ يُبنى بـXcode على ماك ويُوقَّع بحساب مطوّر — لا تطبيقُ ويب. فالطريقُ
الذي يعمل اليوم بلا ماكٍ ولا اشتراك: تطبيقُ «Scriptable» المجانيّ يرسم ويدجت من سكربتٍ يقرأ هذه النقطة.

الأمان: النقطةُ العامّة لا تقبل جلسةَ الدخول ولا كلمةَ المرور، بل **رمزَ ويدجتٍ** يُنشئه المالكُ من الإعدادات ويُلغيه متى شاء —
يُعرض مرّةً واحدةً ويُخزَّن **مُجزَّأً** (‏sha256) لا نصّاً، ويُقارَن بزمنٍ ثابت، ويُرسَل في ترويسة لا في الرابط فلا يقع في السجلّات.
والنقطةُ قراءةٌ محضة: أرقامُ «صافي الربح» و«عائد المحفظة» من مصدرها الموحّد نفسِه (‏compute_net_profit) — لا تعريفٌ ثانٍ.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response

router = APIRouter()          # محميّ (جلسةُ المالك): إنشاءُ الرمز وإلغاؤه وحالُه
public_router = APIRouter()   # عامّ برمز الويدجت وحده: الملخّص

KEY = "widget_token"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _row(db: AsyncSession):
    from app.models.market import Settings
    return (await db.execute(select(Settings).where(Settings.key == KEY))).scalar_one_or_none()


def _meta(row) -> dict | None:
    try:
        d = json.loads(row.value) if row and row.value else None
        return d if isinstance(d, dict) and d.get("hash") else None
    except (TypeError, ValueError):
        return None


@router.get("/token")
async def token_status(db: AsyncSession = Depends(get_db)):
    """هل للويدجت رمزٌ نافذ؟ (تلميحُ آخر أربعة أحرف وتاريخُه — لا الرمزُ نفسُه)"""
    m = _meta(await _row(db))
    return success_response(data={"active": bool(m), "hint": (m or {}).get("hint"), "created": (m or {}).get("created"),
                                  "used": (m or {}).get("used")})


@router.post("/token")
async def token_create(db: AsyncSession = Depends(get_db)):
    """رمزٌ جديد — يُعرض **مرّةً واحدة** ويُبطل ما قبله. يُخزَّن مُجزَّأً لا نصّاً."""
    from app.models.market import Settings
    token = "spw_" + secrets.token_urlsafe(32)
    meta = {"hash": _hash(token), "hint": token[-4:], "created": datetime.now(timezone.utc).isoformat(), "used": None}
    row = await _row(db)
    if row is None:
        db.add(Settings(key=KEY, value=json.dumps(meta), category="widget"))
    else:
        row.value = json.dumps(meta)
    await db.commit()
    return success_response(data={"token": token, "hint": meta["hint"], "created": meta["created"]},
                            message="انسخ الرمزَ الآن — لا يُعرض مرّةً ثانية.")


@router.delete("/token")
async def token_revoke(db: AsyncSession = Depends(get_db)):
    """إلغاءُ الرمز — يتوقّف الويدجت فوراً."""
    row = await _row(db)
    if row is not None:
        await db.delete(row)
        await db.commit()
    return success_response(data={"active": False}, message="أُلغي رمزُ الويدجت.")


async def _check(db: AsyncSession, token: str | None) -> None:
    m = _meta(await _row(db))
    if not token or not m or not hmac.compare_digest(_hash(token.strip()), str(m["hash"])):
        raise HTTPException(401, "رمزُ الويدجت غيرُ صالح — أنشئ رمزاً من الإعدادات في التطبيق.")


async def _snapshot(db: AsyncSession, pid: int) -> dict:
    """ملخّصُ محفظةٍ واحدة بمرشِّحها — الأرقامُ من مصادرها في التطبيق."""
    from sqlalchemy.orm import selectinload
    from app.core.portfolio_scope import set_scope
    from app.models.portfolio import Holding
    from app.services.portfolio_return import compute_net_profit
    from app.api.v1.endpoints.holdings import refresh_holdings_prices, _serialize
    set_scope(pid, False)
    hs = [h for h in (await db.execute(select(Holding).options(selectinload(Holding.company)))).scalars().all()
          if h.company and h.company.status != "ARCHIVED" and float(h.quantity or 0) > 0]
    fxs = await refresh_holdings_prices(db, hs)          # الأسعارُ من مخزنها (ربعُ ساعة) — كما يفتح المالكُ الحيازات
    rows = [_serialize(h, fxs.get(h.company_id)) for h in hs]
    net = await compute_net_profit(db)
    return {"net": net, "rows": rows}


@public_router.get("/summary")
async def widget_summary(pf: str | None = None, x_widget_token: str | None = Header(default=None),
                         db: AsyncSession = Depends(get_db)):
    """ملخّصٌ للويدجت: الثروةُ وتغيّرُ اليوم وصافي الربح وعائدُ المحفظة والحيازاتُ الأكثر تحرّكاً وتاسي.

    ‏pf: فارغٌ = المحفظةُ الافتراضية · ‏all = كلُّ المحافظ المضمومة إلى التوحيد (تُجمع أرقامُ كلٍّ من مرشِّحها) · رقمٌ = محفظةٌ بعينها."""
    await _check(db, x_widget_token)
    from app.core.portfolio_scope import reset_scope
    from app.core.portfolio_context import _default_portfolio_id
    from app.models.portfolio import Portfolio
    ps = (await db.execute(select(Portfolio).where(Portfolio.is_archived.is_(False))
                           .execution_options(skip_portfolio_scope=True))).scalars().all()
    if (pf or "").strip().lower() == "all":
        chosen = [p for p in ps if p.include_in_aggregate is not False]
        label = "كلّ المحافظ"
    else:
        want = None
        try:
            want = int(pf) if pf not in (None, "") else None
        except (TypeError, ValueError):
            want = None
        pid = want if any(p.id == want for p in ps) else await _default_portfolio_id(db)
        chosen = [p for p in ps if p.id == pid]
        label = chosen[0].name if chosen else "المحفظة"
    try:
        snaps = [await _snapshot(db, p.id) for p in chosen]
    finally:
        reset_scope()
    rows = [r for s in snaps for r in s["rows"]]
    nets = [s["net"] for s in snaps]
    wealth = round(sum(n.get("wealth") or 0 for n in nets), 2)
    cost = round(sum(n.get("cost_basis") or 0 for n in nets), 2)
    mv = round(sum(float(r.get("market_value") or 0) for r in rows), 2)
    # صافي الربح وعائدُ المحفظة: المقياسُ الموحّد — ومحفظةٌ بلا سجلّ ضخٍّ «غيرُ متوفّر» لا صفر
    nps = [n.get("net_profit") for n in nets]
    net_profit = round(sum(nps), 2) if nps and all(v is not None for v in nps) else None
    ret_pct = round(net_profit / cost * 100, 2) if (net_profit is not None and cost > 0) else None
    # تغيّرُ اليوم بالريال: قيمةُ كلّ سهمٍ × نسبتُه ÷ (100 + نسبتُه) — وما لا نسبةَ له لا يُحسب (لا يُفترض صفراً)
    known = [r for r in rows if isinstance(r.get("change_pct"), (int, float))]
    day = round(sum(float(r["market_value"] or 0) * r["change_pct"] / (100 + r["change_pct"]) for r in known), 2) if known else None
    base = mv - (day or 0)
    day_pct = round(day / base * 100, 2) if (day is not None and base > 0) else None
    tot = sum(float(r.get("market_value") or 0) for r in rows) or 1.0
    items = [{"symbol": (r.get("company") or {}).get("symbol"), "name": (r.get("company") or {}).get("name"),
              "change_pct": r.get("change_pct"), "value": round(float(r.get("market_value") or 0), 2),
              "weight": round(float(r.get("market_value") or 0) / tot * 100, 1), "currency": r.get("currency")} for r in rows]
    top = sorted(items, key=lambda x: -x["value"])[:6]
    movers = sorted([x for x in items if isinstance(x["change_pct"], (int, float))], key=lambda x: -abs(x["change_pct"]))[:3]
    tasi = None
    try:
        from app.services.market_data import market_service
        q = await market_service.get_price("^TASI.SR")
        if q and q.get("price"):
            tasi = {"price": round(float(q["price"]), 2), "change_pct": q.get("change_pct")}
    except Exception:                                                  # noqa: BLE001 — المؤشّرُ «غيرُ متوفّر» لا يُسقط الملخّص
        tasi = None
    # آخرُ استعمالٍ للرمز — يراه المالكُ في الإعدادات (يعرف أنّ الويدجت يعمل)
    try:
        row = await _row(db)
        m = _meta(row)
        if m is not None:
            m["used"] = datetime.now(timezone.utc).isoformat()
            row.value = json.dumps(m)
            await db.commit()
    except Exception:                                                  # noqa: BLE001
        await db.rollback()
    return success_response(data={
        "at": datetime.now(timezone.utc).isoformat(), "portfolio": label, "currency": "SAR",
        "wealth": wealth, "market_value": mv, "cash": round(wealth - mv, 2), "net_profit": net_profit, "return_pct": ret_pct,
        "day_change": day, "day_change_pct": day_pct, "unrealized": round(mv - cost, 2),
        "holdings": top, "movers": movers, "count": len(rows), "tasi": tasi,
    })
