"""أوامرُ المستشار الآليّ — على منهج «سندباد» ومَن سبقه (‏D750 · بأمر المالك 2026-11-16).

قال المالك: «سمعتُ أنهم أطلقوا ميزةً اسمها سندباد — مستشارٌ آليٌّ للمحفظة. خذ المعلومات عنه وحسّن المستشار الآليّ الموجود».
وما يُعلَن عن «الخبير سندباد» (الخبير المالية · سندباد.تك، بتصريحٍ تجريبيٍّ من هيئة السوق المالية): يشتري ويبيع ويوازن المحفظة؛
ولا يشتري إلا بإشارة شراءٍ عاليةِ الثقة **وسيولةٍ كافيةٍ في السهم وحدٍّ أعلى للتخصيص لكلّ سهم**؛ ومديرُ محفظةٍ مرخَّصٌ **يعتمد كلَّ توصيةٍ قبل
تنفيذها** وله إيقافُ أيّ استراتيجية؛ ويُعلن دقّةَ قراراته. ومستشارُنا يملك الأوّلَ منذ D587 (لا «اشترِ» إلا بقناعةٍ مكتملةٍ من خمسة شروط)،
فأُضيف ما نقص منه:
  ١ **الأمرُ بأرقامه**: كلُّ «اشترِ» و«خفّف» و«صفِّ جزئياً» يصير أمراً بعدد أسهمٍ ومبلغٍ وسعر — لا رأياً.
  ٢ **سيولةُ السهم وحجمُ الأمر**: لا شراءَ في سهمٍ متوسّطُ تداوله اليوميّ (عشرون جلسة) دون 3 ملايين ريال، ولا أمرَ فوق 5٪ من تداوله اليوميّ.
  ٣ **الحدُّ الأعلى**: 15٪ للسهم و35٪ للقطاع — والأمرُ يُقصّ ليبقى تحتهما؛ وهدفُ المالك اليدويُّ يتقدّم على الحدّ (الخطُّ الأحمر الأوّل)
     فيُذكر تجاوزُه ولا يُنقض.
  ٤ **اعتمادُ المالك**: الأمرُ «بانتظار اعتمادك» حتى يعتمده المالكُ أو يرفضه، ويُكتشف تنفيذُه من تغيّر المركز، وما زالت شروطُه قبل اعتماده
     ينتهي. و**إيقافٌ** يُسكت الأوامرَ كلَّها حتى يُستأنف.
  ٥ **ثقةُ الأمر** رقماً (من الهامش إلى القيمة العادلة وثقتِها والجودةِ والاتجاه الشهريّ)، و**سجلُّ الدقّة**: بعد شهرٍ من كلّ أمرٍ يُقاس —
     هل تفوّق السهمُ المشترى على تاسي، وتأخّر المبيع؟ — ويُعلن بعدده لا بنسبةٍ مجرّدة.
والتطبيقُ لا ينفّذ صفقة: الأمرُ المعتمد يُنفَّذ في منصّة الوساطة، والتطبيقُ يرى أثره في المحفظة.
"""
from __future__ import annotations

import json
import math
import os
from datetime import date, datetime, timedelta

from loguru import logger

LIMITS = {"stock_max": 15.0, "sector_max": 35.0, "min_adv": 3_000_000.0, "adv_share": 5.0}
BUY_ACTS = ("اشترِ الآن",)
SELL_ACTS = ("خفّف", "صفِّ جزئياً", "خذ الربح")
MEASURE_DAYS = 30


def _f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _path() -> str:
    d = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "robo")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "orders.json")


def load(pid: int | None = None) -> dict:
    try:
        all_ = json.load(open(_path(), encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        all_ = {}
    st = all_.get(str(pid or 0)) or {}
    st.setdefault("paused", False)
    st.setdefault("orders", [])
    return st


def save(st: dict, pid: int | None = None) -> None:
    try:
        all_ = json.load(open(_path(), encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        all_ = {}
    all_[str(pid or 0)] = st
    tmp = _path() + ".tmp"
    json.dump(all_, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, _path())


def confidence(pos: dict) -> int:
    """ثقةُ أمر الشراء (0–100): الهامشُ إلى القيمة العادلة (40) وثقتُها (20) والجودةُ المالية (20) والاتجاهُ الشهريّ (20)."""
    p, fv = _f(pos.get("price")), _f(pos.get("fair_value"))
    up = (fv / p - 1) * 100 if p and fv else 0
    conf = {"مرتفعة": 1.0, "متوسطة": 0.6}.get(str(pos.get("fair_value_conf") or ""), 0.3)
    q = (_f(pos.get("quality")) or 50) / 100
    m = {"صاعد": 1.0, "عرضي": 0.5}.get(str((pos.get("monthly") or {}).get("state") or ""), 0.0)
    return int(round(40 * max(0.0, min(up, 30)) / 30 + 20 * conf + 20 * max(0.0, min(q, 1.0)) + 20 * m))


def plan(positions: list[dict], capital: float, cash: float, adv: dict, limits: dict | None = None) -> tuple[list[dict], list[dict]]:
    """الأوامرُ من قرار الطيار لكلّ مركز — بعد بوّابات السيولة وحجم الأمر والحدّ الأعلى للسهم والقطاع. ويعود معها ما أُجّل وسببُه."""
    L = {**LIMITS, **(limits or {})}
    orders, held = [], []
    sec_w: dict[str, float] = {}
    for p in positions:
        sec_w[str(p.get("sector") or "—")] = sec_w.get(str(p.get("sector") or "—"), 0.0) + (_f(p.get("current_weight")) or 0)
    budget = max(0.0, cash)
    for p in sorted(positions, key=lambda x: -confidence(x)):
        sym, name, px = str(p.get("symbol")).replace(".SR", ""), p.get("name") or p.get("symbol"), _f(p.get("price"))
        ap = p.get("autopilot") or {}
        act = str(ap.get("action") or "")
        qty = _f(p.get("quantity")) or 0
        cw, tw = _f(p.get("current_weight")) or 0, _f(p.get("target_weight")) or 0
        sector = str(p.get("sector") or "—")
        if not px or capital <= 0:
            continue
        if act in BUY_ACTS:
            a = adv.get(sym)
            want = _f(p.get("need")) or 0
            stock_cap = max(L["stock_max"], tw)                    # هدفُ المالك يتقدّم على الحدّ
            room_stock = max(0.0, (stock_cap - cw) / 100 * capital)
            room_sector = max(0.0, (L["sector_max"] - sec_w.get(sector, 0)) / 100 * capital)
            room_adv = (a * L["adv_share"] / 100) if a else 0.0
            amount = min(want, room_stock, room_sector, room_adv, budget)
            shares = int(math.floor(amount / px)) if amount > 0 else 0
            checks = [{"k": "القناعة مكتملة", "ok": True, "d": " · ".join(ap.get("conviction") or [])},
                      {"k": "سيولة السهم كافية", "ok": bool(a and a >= L["min_adv"]),
                       "d": f"متوسّط التداول اليوميّ {a / 1e6:,.1f} مليون ريال" if a else "متوسّط التداول غير متوفّر"},
                      {"k": "حجم الأمر ≤ 5٪ من تداول السهم", "ok": bool(a) and amount <= room_adv + 0.01,
                       "d": f"الحدّ {room_adv:,.0f} ريال" if a else "—"},
                      {"k": f"ضمن حدّ السهم {stock_cap:.0f}٪", "ok": cw + amount / capital * 100 <= stock_cap + 0.01,
                       "d": f"وزنه {cw:.1f}٪ ← {cw + amount / capital * 100:.1f}٪" + (" (هدفُك يتجاوز الحدّ — قرارُك)" if tw > L["stock_max"] else "")},
                      {"k": f"ضمن حدّ القطاع {L['sector_max']:.0f}٪", "ok": sec_w.get(sector, 0) + amount / capital * 100 <= L["sector_max"] + 0.01,
                       "d": f"{sector} {sec_w.get(sector, 0):.1f}٪"}]
            why = None
            if not (a and a >= L["min_adv"]):
                why = "سيولةُ السهم دون الحدّ — لا شراء"
            elif budget <= 0:
                why = "لا سيولةَ نقدية متاحة للشراء"
            elif room_sector <= 0:
                why = f"قطاعُه بلغ حدَّه {L['sector_max']:.0f}٪"
            elif room_stock <= 0:
                why = f"بلغ حدَّه {stock_cap:.0f}٪"
            elif shares < 1:
                why = "المبلغُ المتاح دون سهمٍ واحد"
            if why:
                held.append({"symbol": sym, "name": name, "action": act, "why": why})
                continue
            amount = shares * px
            budget -= amount
            sec_w[sector] = sec_w.get(sector, 0) + amount / capital * 100
            orders.append({"symbol": sym, "name": name, "side": "شراء", "shares": shares, "price": px, "amount": round(amount, 2),
                           "confidence": confidence(p), "why": "؛ ".join(ap.get("why") or [])[:240], "checks": checks,
                           "level": ap.get("level"), "qty_at": qty, "sector": sector})
        elif act in SELL_ACTS or (cw > L["stock_max"] and (tw <= 0 or tw <= L["stock_max"])):
            if not qty:
                continue
            if act == "خفّف" and tw > 0 and cw > tw:
                amount = (cw - tw) / 100 * capital
            elif act in SELL_ACTS:
                amount = qty * px / 3
            else:
                amount = (cw - L["stock_max"]) / 100 * capital
                act = f"فوق حدّ السهم {L['stock_max']:.0f}٪"
            shares = min(int(qty), int(math.ceil(amount / px)))
            if shares < 1:
                continue
            orders.append({"symbol": sym, "name": name, "side": "بيع", "shares": shares, "price": px, "amount": round(shares * px, 2),
                           "confidence": None, "why": ("؛ ".join(ap.get("why") or []) or act)[:240],
                           "checks": [{"k": act, "ok": True, "d": f"وزنه {cw:.1f}٪" + (f" وهدفُه {tw:.1f}٪" if tw else "")}],
                           "level": ap.get("level"), "qty_at": qty, "sector": sector})
    return orders, held


def merge(st: dict, built: list[dict], today: str, qty_now: dict, px_now: dict, tasi_now: float | None) -> tuple[dict, list[dict]]:
    """يدمج أوامرَ اليوم في السجلّ: الأمرُ القائمُ لنفس السهم والاتجاه يُحدَّث ولا يتكرّر، والمعلّقُ الذي زالت شروطُه ينتهي، والمعتمدُ يُكتشف
    تنفيذُه من تغيّر الكمية. ويعود معه ما استجدّ (لإشعار المالك به وحدَه)."""
    orders = st.get("orders") or []
    now = datetime.now().isoformat(timespec="minutes")
    live = {(o["symbol"], o["side"]): o for o in orders if o["status"] in ("pending", "approved")}
    fresh = []
    keep = set()
    for b in built:
        k = (b["symbol"], b["side"])
        o = live.get(k)
        if o and o["status"] == "pending":
            o.update({x: b[x] for x in ("shares", "price", "amount", "confidence", "why", "checks", "level")}, updated=now)
            keep.add(k)
        elif o:
            keep.add(k)
        else:
            n = {**b, "id": f"{today}-{b['symbol']}-{'b' if b['side'] == 'شراء' else 's'}", "status": "pending", "created": now,
                 "day": today, "price_at": b["price"], "tasi_at": tasi_now}
            orders.append(n)
            fresh.append(n)
            keep.add(k)
    for o in orders:
        k = (o["symbol"], o["side"])
        if o["status"] == "pending" and k not in keep:
            o.update(status="expired", closed=now, why_closed="زالت شروطُه قبل اعتماده")
        if o["status"] == "approved":
            q = qty_now.get(o["symbol"], 0)
            done = (q >= o["qty_at"] + 0.5 * o["shares"]) if o["side"] == "شراء" else (q <= o["qty_at"] - 0.5 * o["shares"])
            if done:
                o.update(status="executed", executed=now, exec_price=px_now.get(o["symbol"]))
            elif o.get("decided") and o["decided"][:10] < (date.fromisoformat(today) - timedelta(days=14)).isoformat():
                o.update(status="expired", closed=now, why_closed="لم يُنفَّذ خلال أسبوعين من اعتماده")
    st["orders"] = orders[-400:]
    return st, fresh


def decide(st: dict, oid: str, approve: bool) -> dict | None:
    for o in st.get("orders") or []:
        if o["id"] == oid and o["status"] == "pending":
            o.update(status="approved" if approve else "rejected", decided=datetime.now().isoformat(timespec="minutes"))
            return o
    return None


def record(orders: list[dict], px_now: dict, tasi_now: float | None, today: str) -> dict:
    """سجلُّ الدقّة: كلُّ أمرٍ مضى عليه شهرٌ يُقاس بعائده منذ صدوره مقابل تاسي — الشراءُ صائبٌ إن تفوّق، والبيعُ صائبٌ إن تأخّر.
    يُقاس الأمرُ لا التنفيذ: الحكمُ على المستشار لا على ما فعله المالك."""
    floor = (date.fromisoformat(today) - timedelta(days=MEASURE_DAYS)).isoformat()
    rows = []
    for o in orders:
        p0, t0, p1 = _f(o.get("price_at")), _f(o.get("tasi_at")), _f(px_now.get(o["symbol"]))
        if o.get("day", "9") > floor or not (p0 and t0 and p1 and tasi_now):
            continue
        ex = (p1 / p0 - 1) * 100 - (tasi_now / t0 - 1) * 100
        rows.append({"symbol": o["symbol"], "side": o["side"], "excess": round(ex, 2), "hit": ex > 0 if o["side"] == "شراء" else ex < 0})
    n, hits = len(rows), sum(1 for r in rows if r["hit"])
    return {"n": n, "hits": hits, "rate": round(hits / n * 100) if n else None, "measure_days": MEASURE_DAYS,
            "avg_excess": round(sum(r["excess"] if r["side"] == "شراء" else -r["excess"] for r in rows) / n, 2) if n else None}


async def _adv(symbols: list[str]) -> dict:
    """متوسّطُ قيمة التداول اليوميّ لعشرين جلسة (الإغلاقُ × الكمية) لكلّ سهم."""
    import asyncio
    from app.services.market_data import market_service as M

    async def one(s):
        try:
            pts = (await asyncio.wait_for(M.get_bars(f"{s}.SR", "1d"), 25) or [])[-20:]
        except Exception:                                         # noqa: BLE001
            return s, None
        vals = [(_f(p.get("close")) or 0) * (_f(p.get("volume")) or 0) for p in pts]
        vals = [v for v in vals if v > 0]
        return s, (sum(vals) / len(vals)) if len(vals) >= 10 else None
    return dict(await asyncio.gather(*(one(s) for s in symbols)))


async def refresh(db, notify: bool = False) -> dict:
    """يبني أوامرَ اليوم من رأي الطيار الآليّ ويدمجها في السجلّ — ويُشعر المالكَ بما استجدّ (إن لم يكن موقوفاً)."""
    from app.core.portfolio_scope import active_pid
    from app.services import autopilot
    pid = active_pid()
    st = load(pid)
    pk = await autopilot.pack(db)
    pos = pk["positions"]
    capital, cash = float(pk.get("wealth") or 0), float(pk.get("cash") or 0)
    adv = await _adv([str(p["symbol"]).replace(".SR", "") for p in pos if (p.get("autopilot") or {}).get("action") in BUY_ACTS])
    built, held = ([], []) if st["paused"] else plan(pos, capital, cash, adv)
    tasi = None
    try:
        from app.services.tadawul_market import index_quote
        tasi = _f((await index_quote() or {}).get("price"))
    except Exception:                                             # noqa: BLE001
        pass
    today = date.today().isoformat()
    qty_now = {str(p["symbol"]).replace(".SR", ""): _f(p.get("quantity")) or 0 for p in pos}
    px_now = {str(p["symbol"]).replace(".SR", ""): _f(p.get("price")) for p in pos}
    st, fresh = merge(st, built, today, qty_now, px_now, tasi)
    st.update(held=held, asof=datetime.now().isoformat(timespec="minutes"), capital=capital, cash=cash,
              record=record(st["orders"], px_now, tasi, today))
    save(st, pid)
    if notify and fresh and not st["paused"]:
        try:
            from app.services.advisor_memory import notify as _n
            lines = [f"• {o['side']} {o['shares']:,} سهم {o['name']} بنحو {o['amount']:,.0f} ريال"
                     + (f" — ثقة {o['confidence']}٪" if o.get("confidence") is not None else "") for o in fresh]
            await _n(f"🧭 أوامرُ بانتظار اعتمادك — {len(fresh)}", lines + ["", "اعتمدها أو ارفضها من «المستشار الآلي»."], raw=True)
        except Exception as e:                                    # noqa: BLE001
            logger.warning("أوامر المستشار: الإشعار {}", type(e).__name__)
    return view(st)


def view(st: dict) -> dict:
    rank = {"pending": 0, "approved": 1, "executed": 2, "rejected": 3, "expired": 4}
    orders = sorted(st.get("orders") or [], key=lambda o: (rank.get(o["status"], 9), o.get("created") or ""), reverse=False)
    act = [o for o in orders if o["status"] in ("pending", "approved")]
    past = sorted([o for o in orders if o["status"] not in ("pending", "approved")], key=lambda o: o.get("created") or "", reverse=True)[:12]
    return {"paused": st.get("paused", False), "limits": LIMITS, "orders": act, "history": past, "held": st.get("held") or [],
            "record": st.get("record") or {"n": 0}, "asof": st.get("asof")}
