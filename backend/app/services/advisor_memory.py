"""ذاكرةُ المستشار ومراقبةُ شروطه (D569) — النصيحةُ لا تُقال وتُنسى.

قال المالك: «الدفعاتُ ستتغيّر مع الوقت وبعضُها يكتمل والبعضُ لا — يجب أن يكون متواكباً مع الزمن والمحفظة
والتفاصيل الجديدة، ليكون مستشاري الذكيّ للمستقبل وللأبد».

  · **تُحفظ** كلُّ نصيحةٍ بدفعاتها: سعرُ يومها، وكميةُ المالك يومها، ولكلّ دفعةٍ شرطٌ آليّ.
  · **تُراقَب** يومياً (بعد الإغلاق ومساءً بعد إعلانات النتائج):
      – ما نُفّذ: زيادةُ كمية المالك تملأ الدفعاتِ بالترتيب فتُعلَّم «نُفّذت».
      – ما تحقّق: نتائجُ صدرت وجاءت عند التوقّع أو فوقه، سعرٌ بلغ المستوى، خصمٌ بلغ حدّه.
      – ما يوقفها: نتائجُ دون التوقّع، خفضُ توزيع الريت، هبوطُ صافي أصوله، تأخّرُ توزيعه.
  · **يُبلَّغ** المالكُ بكلّ تحوّلٍ مرّةً واحدة: في إشعارات التطبيق وعلى تلغرام.
  · **يُستدعى** السجلُّ في كلّ سؤالٍ لاحق، فيقول صقر: «نصحتك يومَ كذا بكذا، ونفّذتَ الأولى، والثانيةُ
    تنتظر نتائجَ 30 أكتوبر».
"""
from __future__ import annotations

from datetime import date, timedelta

from loguru import logger

STORE = "advice:{}"
KEEP_DAYS = 200


def _today() -> str:
    return date.today().isoformat()


def recall(sym: str) -> dict | None:
    from app.services import lastgood
    a = lastgood.load(STORE.format(sym)) or None
    return a if a and a.get("status") == "active" else None


def summary(a: dict | None) -> dict | None:
    """ما يُعرض للنموذج وللمالك من النصيحة السابقة."""
    if not a:
        return None
    return {"بتاريخ": a.get("at"), "بسعر": a.get("price"), "الإجراء": a.get("action"),
            "الدفعات": [{"n": t["n"], "أسهم": t["shares"], "متى": t["when"], "الحالة": _AR.get(t.get("status"), t.get("status")),
                         "نُفّذ منها": t.get("done_shares", 0)} for t in a.get("tranches") or []],
            "ملاحظات": (a.get("events") or [])[-4:]}


_AR = {"pending": "تنتظر شرطها", "met": "تحقّق شرطُها — جاهزة", "done": "نُفّذت", "paused": "موقوفة", "failed": "لم يتحقّق"}


def fresh(f: dict, st: dict, pid: int | None) -> dict:
    """نصيحةٌ جديدةٌ من الملفّ والموقف — دفعاتُها بحالاتها الأولى."""
    tr = []
    for t in st.get("tranches") or []:
        now = any(c.get("k") == "now" for c in t.get("cond") or [])
        tr.append({**t, "status": "met" if now else "pending", "done_shares": 0})
    return {"symbol": f["symbol"], "name": f.get("name"), "at": _today(), "price": f.get("price"),
            "qty": f.get("qty") or 0, "pid": pid, "action": st.get("action"), "why": st.get("why"),
            "tranches": tr, "stop_rules": st.get("stop_rules") or [], "status": "active", "events": [],
            "forecast": f.get("next_q"), "reit": {k: (f.get("reit") or {}).get(k) for k in ("nav", "last_amount")} if f.get("is_reit") else None}


def remember(f: dict, st: dict, pid: int | None) -> dict | None:
    """تُحفظ النصيحةُ إن كانت فيها دفعات. ونصيحةٌ قائمةٌ بالإجراء نفسِه لا تُستبدل — تُتابَع (لا تُصفَّر
    حالاتُ دفعاتها بسؤالٍ متكرّر)؛ وإن تغيّر الإجراءُ أو مضى شهرٌ حلّت الجديدةُ محلّها."""
    from app.services import lastgood
    if not st.get("tranches"):
        return None
    old = recall(f["symbol"])
    if old and old.get("action") == st.get("action") and old.get("at", "") >= (date.today() - timedelta(days=30)).isoformat():
        return old
    a = fresh(f, st, pid)
    lastgood.save(STORE.format(f["symbol"]), a)
    return a


def evaluate(a: dict, live: dict, today: str | None = None) -> tuple[dict, list[str]]:
    """دالّةٌ نقيّة: النصيحةُ + الحالةُ الحيّة ⇒ النصيحةُ محدَّثةً + أحداثٌ جديدةٌ تُبلَّغ.

    live: price · qty · results (قائمةُ نهايات الفترات المنشورة) · ni_latest ·
          reit {last_amount, prev_amount, nav, overdue}."""
    today = today or _today()
    ev: list[str] = []
    name = a.get("name") or a["symbol"]
    if a.get("at", "") < (date.fromisoformat(today) - timedelta(days=KEEP_DAYS)).isoformat():
        a["status"] = "expired"
        return a, [f"انتهت مدّةُ نصيحة {name} ({a.get('at')}) — اسأل صقر من جديد لتُبنى على أرقام اليوم"]
    px = live.get("price")

    # ما نُفّذ — زيادةُ الكمية تملأ الدفعاتِ بالترتيب
    gained = max(0.0, float(live.get("qty") or 0) - float(a.get("qty") or 0))
    used = sum(float(t.get("done_shares") or 0) for t in a["tranches"])
    extra = gained - used
    for t in a["tranches"]:
        if extra <= 0:
            break
        need = t["shares"] - float(t.get("done_shares") or 0)
        if need <= 0:
            continue
        fill = min(need, extra)
        t["done_shares"] = round(float(t.get("done_shares") or 0) + fill, 2)
        extra -= fill
        if t["done_shares"] >= t["shares"] * 0.9 and t.get("status") != "done":
            t["status"] = "done"
            ev.append(f"{name}: نُفّذت الدفعة {t['n']} ({t['done_shares']:g} سهماً)")

    # ما يوقفها
    stop = None
    fc = a.get("forecast") or {}
    pub = [d for d in live.get("results") or [] if fc.get("as_of") and d >= fc["as_of"]]
    if pub and fc.get("net_income") and live.get("ni_latest") is not None:
        floor = fc["net_income"] * (1 - (fc.get("mape") or 0) / 100)
        if live["ni_latest"] < floor and not a.get("_res_bad"):
            a["_res_bad"] = True
            stop = (f"{name}: صدرت نتائجُ {pub[-1]} بصافي ربح {live['ni_latest'] / 1e6:,.1f} مليون — دون توقّع التطبيق "
                    f"({fc['net_income'] / 1e6:,.1f} مليون بهامش خطئه) — توقّفت الدفعاتُ المعلّقة، اسأل صقر قبل أيّ إضافة")
    r = live.get("reit") or {}
    if r.get("last_amount") is not None and r.get("prev_amount") is not None and r["last_amount"] < r["prev_amount"] \
            and not a.get("_cut"):
        a["_cut"] = True
        stop = f"{name}: خفّض التوزيعَ من {r['prev_amount']} إلى {r['last_amount']} — توقّفت الدفعاتُ المعلّقة"
    base_nav = (a.get("reit") or {}).get("nav")
    if r.get("nav") and base_nav and r["nav"] < base_nav * 0.97 and not a.get("_nav"):
        a["_nav"] = True
        stop = f"{name}: هبط صافي أصوله إلى {r['nav']} من {base_nav} — توقّفت الدفعاتُ المعلّقة"
    if r.get("overdue") and not a.get("_late"):
        a["_late"] = True
        ev.append(f"{name}: تأخّر التوزيعُ عن إيقاعه المعتاد — راجع إعلان الصندوق")
    if stop:
        ev.append(stop)
        for t in a["tranches"]:
            if t.get("status") in ("pending", "met"):
                t["status"] = "paused"

    # ما تحقّق
    for t in a["tranches"]:
        if t.get("status") != "pending":
            continue
        hit = None
        for c in t.get("cond") or []:
            k = c.get("k")
            if k == "results" and len(pub) >= c.get("nth", 1) and not a.get("_res_bad"):
                hit = f"صدرت النتائجُ ({pub[c.get('nth', 1) - 1]}) وجاء الربحُ عند توقّع التطبيق أو فوقه" \
                    if fc.get("net_income") and live.get("ni_latest") is not None else f"صدرت النتائج ({pub[-1]}) — راجعها"
            elif k == "reclaim" and px and c.get("level") and px >= c["level"]:
                hit = f"ثبت السعرُ {px} فوق متوسط 200 يوم ({c['level']})"
            elif k == "below" and px and c.get("level") and px <= c["level"]:
                hit = f"بلغ السعرُ {px} مستوى الشراء ({c['level']})"
            if hit:
                break
        if hit:
            t["status"] = "met"
            import math
            sh = int(math.floor(t["amount"] / px)) if px else t["shares"]
            ev.append(f"{name}: تحقّق شرطُ الدفعة {t['n']} — {hit}. الدفعة: {t['amount']:,.0f} ريال (نحو {sh} سهماً بسعر اليوم)")
    if all(t.get("status") in ("done", "paused", "failed") for t in a["tranches"]):
        a["status"] = "closed"
    a.setdefault("events", []).extend(f"{today}: {e}" for e in ev)
    return a, ev


async def _live(db, a: dict) -> dict:
    sym = a["symbol"]
    out: dict = {}
    try:
        from app.services.tadawul_market import row_for
        out["price"] = (row_for(sym) or {}).get("price")
    except Exception:                                             # noqa: BLE001
        pass
    try:
        from sqlalchemy import func, select
        from app.models.portfolio import Company, Holding
        q = select(func.sum(Holding.quantity)).join(Company, Holding.company_id == Company.id).where(Company.symbol == sym)
        if a.get("pid"):
            q = q.where(Holding.portfolio_id == a["pid"])
        out["qty"] = float((await db.execute(q.execution_options(skip_portfolio_scope=True))).scalar() or 0)
    except Exception as e:                                        # noqa: BLE001
        logger.debug("advisor watch qty {}: {}", sym, e)
    try:
        from app.services import tadawul_xbrl as X
        qs = X.for_symbol(sym, "quarterly") or []
        out["results"] = sorted(p["as_of"] for p in qs if p.get("as_of"))
        if qs:
            last = qs[-1]
            out["ni_latest"] = last.get("net_income_parent") if last.get("net_income_parent") is not None else last.get("net_income")
    except Exception:                                             # noqa: BLE001
        pass
    if a.get("reit") is not None:
        try:
            from app.services.reit_advisor import cached, summarize
            raw = cached(sym)
            if raw:
                ds = sorted([d for d in raw["dists"] if d.get("eligibility")], key=lambda d: d["eligibility"])
                r = summarize(raw["dists"], raw.get("vals") or [], out.get("price"))
                out["reit"] = {"last_amount": ds[-1]["amount"] if ds else None,
                               "prev_amount": ds[-2]["amount"] if len(ds) >= 2 else None,
                               "nav": r.get("nav"), "overdue": r.get("overdue")}
        except Exception:                                         # noqa: BLE001
            pass
    return out


async def notify(title: str, lines: list[str]) -> None:
    """إشعارٌ في التطبيق ورسالةٌ على تلغرام — مرّةً لكلّ تحوّل."""
    msg = "\n".join(f"• {l}" for l in lines)
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.market import Notification, NotificationPriority
        async with AsyncSessionLocal() as db:
            db.add(Notification(category="advisor", priority=NotificationPriority.HIGH, title=title, message=msg,
                                extra_data={"source": "advisor"}))
            await db.commit()
    except Exception as e:                                        # noqa: BLE001
        logger.warning("المستشار: الإشعار {}", e)
    try:
        import html
        from app.services.saqr_bot import bot
        if bot.enabled:
            await bot.send(f"<b>{html.escape(title)}</b>\n{html.escape(msg)}", keyboard=False)
    except Exception as e:                                        # noqa: BLE001
        logger.warning("المستشار: تلغرام {}", e)


async def watch() -> dict:
    """المهمّةُ اليومية: كلُّ نصيحةٍ قائمة تُقيَّم على الحالة الحيّة، ويُبلَّغ الجديدُ وحده."""
    from app.core.database import AsyncSessionLocal
    from app.services import lastgood
    rep = {"advices": 0, "events": 0}
    all_ev: list[str] = []
    async with AsyncSessionLocal() as db:
        for k in lastgood.keys_with_prefix("advice:"):
            a = lastgood.load(k) or {}
            if a.get("status") != "active":
                continue
            rep["advices"] += 1
            a, ev = evaluate(a, await _live(db, a))
            lastgood.save(k, a)
            all_ev += ev
    rep["events"] = len(all_ev)
    if all_ev:
        await notify("صقر — متابعةُ نصائحك", all_ev)
    logger.info("المستشار: {}", rep)
    return rep
