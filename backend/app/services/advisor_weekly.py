"""المراجعةُ الأسبوعية للمحفظة (D571) — كلَّ خميسٍ مساءً، بعد آخر جلسةٍ في الأسبوع.

المرحلةُ الثالثة من مستشار المحفظة: لا ينتظر صقرٌ أن يُسأل. يمرّ على كلّ مركزٍ بملفّ قراره وموقفه
(المرحلة الأولى)، ويحفظ نصيحتَه ويتابعها (الثانية)، ثمّ يرسل للمالك ورقةً واحدة:

  · **لكلّ شركة:** الإجراءُ (أضف · انتظر الشرط · احتفظ · خفّف · استبدل) وسببُه، والدفعةُ التالية بمبلغها
    وأسهمها وشرطها، والموعدُ القادم الذي يهمّها.
  · **ما صار جاهزاً:** دفعاتٌ تحقّق شرطُها ولم تُنفَّذ بعد.
  · **مواعيدُ الأسبوعين القادمين:** نتائجُ متوقّعة، وتوزيعاتُ ريتات، ومؤتمراتُ محلّلين.
  · **المحفظةُ كلُّها:** رأسُ المال، والسيولة، وما يلزم لبلوغ الأهداف، وعددُ الشركات (وتنبيهُ التشتّت).
الأحكامُ كلُّها من الموقف المحسوب؛ والنموذجُ يكتب ثلاثةَ أسطرٍ خلاصةً فقط، وإن تعذّر خرجت الورقةُ بدونها.
لكلّ محفظةٍ ورقتُها (عزلٌ بالسياق كاللقطة اليومية)، وتُحفظ فيستدعيها صقرٌ متى سُئل «مراجعة الأسبوع».
"""
from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta

from loguru import logger

STORE = "advisor:weekly:{}"
SPREAD_N = 12          # فوق هذا العدد يُنبَّه إلى التشتّت
_ORDER = ("استبدل", "خفّف", "أضف على دفعتين", "انتظر الشرط ثمّ أضف على دفعات", "احتفظ", "راقب")


def _next_event(f: dict, today: date) -> str | None:
    ev = []
    if f.get("results_due"):
        ev.append((f["results_due"], f"النتائج حتى {f['results_due']}"))
    nx = (f.get("reit") or {}).get("next_expected")
    if nx:
        ev.append((nx, f"التوزيع القادم نحو {nx}"))
    ev = [e for e in ev if e[0] >= today.isoformat()]
    return sorted(ev)[0][1] if ev else None


def row(f: dict, st: dict, today: date) -> dict:
    nxt = next((t for t in st.get("tranches") or [] if True), None)
    adv = f.get("advice") or {}
    ready = [t for t in adv.get("الدفعات") or [] if "جاهزة" in str(t.get("الحالة"))]
    return {"symbol": f["symbol"], "name": f.get("name"), "action": st.get("action"), "why": st.get("why"),
            "weight": f.get("weight"), "target": f.get("target"), "pnl": f.get("pnl_pct"),
            "next": {k: nxt[k] for k in ("amount", "shares", "when")} if nxt else None,
            "replace": (st.get("replace_with") or {}).get("name"), "swap": st.get("swap"),
            "trim": {"amount": st.get("amount"), "shares": st.get("shares")} if st.get("action") == "خفّف" else None,
            "event": _next_event(f, today), "ready": [t["n"] for t in ready]}


def upcoming(fs: list[dict], today: date, days: int = 14) -> list[str]:
    end = (today + timedelta(days=days)).isoformat()
    t = today.isoformat()
    out = []
    for f in fs:
        if f.get("results_due") and t <= f["results_due"] <= end:
            out.append((f["results_due"], f"{f['name']}: موعدُ النتائج حتى {f['results_due']}"))
        nx = (f.get("reit") or {}).get("next_expected")
        if nx and t <= nx <= end:
            out.append((nx, f"{f['name']}: التوزيعُ القادم نحو {nx}"))
    try:
        from app.services.investor_calls import upcoming as calls
        for c in calls([f["symbol"] for f in fs], today):
            if c.get("date") and c["date"] <= end:
                nm = next((f["name"] for f in fs if f["symbol"] == c.get("symbol")), c.get("symbol"))
                out.append((c["date"], f"{nm}: مؤتمرُ المحلّلين {c['date']}" + (f" الساعة {c['time']}" if c.get("time") else "")))
    except Exception:                                             # noqa: BLE001
        pass
    return [x for _, x in sorted(out)]


def render(r: dict) -> str:
    L = [f"مراجعةُ الأسبوع — {r['date']}"]
    if r.get("summary"):
        L += ["", r["summary"]]
    p = r["portfolio"]
    L += ["", f"المحفظة: رأسُ المال {p['capital']:,.0f} ريال · السيولة {p['cash']:,.0f} · "
              f"ما يلزم لبلوغ الأهداف {p['to_targets']:,.0f} · {p['count']} شركة"]
    if p.get("spread"):
        L.append(f"• تنبيه: {p['count']} شركة — فوق {SPREAD_N}؛ اسأل صقر «قلّل عدد الشركات» لخطة تركيز")
    ready = [x for x in r["rows"] if x["ready"]]
    if ready:
        L += ["", "جاهزٌ للتنفيذ (تحقّق شرطُه):"]
        L += [f"• {x['name']}: الدفعة {', '.join(map(str, x['ready']))}" for x in ready]
    for act in _ORDER:
        grp = [x for x in r["rows"] if x["action"] == act]
        if not grp:
            continue
        L += ["", f"{act}:"]
        for x in grp:
            line = f"• {x['name']} — {x.get('why') or ''}".rstrip(" —")
            if x.get("replace"):
                line += f" ⇐ البديل {x['replace']} بنقل {x['swap']['amount']:,.0f} ريال (نحو {x['swap']['shares']} سهماً)"
            elif x.get("trim"):
                line += f" ⇐ خفّف {x['trim']['amount']:,.0f} ريال (نحو {x['trim']['shares']} سهماً)"
            elif x.get("next"):
                n = x["next"]
                line += f" ⇐ التالية {n['amount']:,.0f} ريال (نحو {n['shares']} سهماً) — {n['when']}"
            if x.get("event"):
                line += f" · {x['event']}"
            L.append(line)
    if r.get("upcoming"):
        L += ["", "مواعيدُ الأسبوعين القادمين:"] + [f"• {u}" for u in r["upcoming"]]
    L += ["", "رأيٌ تحليليّ من بيانات التطبيق، والقرارُ لك. اسأل صقر عن أيّ شركةٍ للتفصيل."]
    return "\n".join(L)


async def _summary(r: dict) -> str | None:
    """ثلاثةُ أسطرٍ بصوت المستشار — من الورقة وحدها، ولا تغيّر حكماً فيها."""
    import httpx
    from app.core.config import settings
    from app.services.usage_tracker import can_call, record
    if not settings.AI_API_KEY or not can_call("gemini"):
        return None
    slim = {"المحفظة": r["portfolio"], "الشركات": [{k: x.get(k) for k in ("name", "action", "why", "event", "ready")} for x in r["rows"]],
            "المواعيد": r.get("upcoming")}
    prompt = ("أنت «صقر»، المستشارُ الماليّ لمالك المحفظة. اكتب **ثلاثة أسطرٍ فقط** خلاصةً لهذا الأسبوع: أهمُّ ما يفعله، "
              "وأهمُّ ما ينتظره، وأهمُّ خطرٍ يراقبه — من الورقة وحدها، ولا تغيّر أيَّ إجراءٍ أو رقمٍ فيها، ولا تذكر رقماً ليس فيها. "
              "بلا تحيّةٍ ولا رموز تنسيق، وكلُّ سطرٍ يبدأ بـ«•».\n\n" + json.dumps(slim, ensure_ascii=False, default=str))
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=40) as c:
            res = await c.post(f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent"
                               f"?key={settings.AI_API_KEY}",
                               json={"contents": [{"parts": [{"text": prompt}]}],
                                     "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400}})
        if res.status_code != 200:
            return None
        from app.services.ai_chat import _strip_markup
        return _strip_markup(res.json()["candidates"][0]["content"]["parts"][0]["text"].strip())
    except Exception:                                             # noqa: BLE001
        return None


async def review(db) -> dict:
    """ورقةُ المحفظة النشطة في السياق: ملفٌّ وموقفٌ لكلّ مركز، والنصيحةُ تُحفظ وتُتابَع."""
    from app.api.v1.endpoints.allocation import get_allocation
    from app.core.portfolio_scope import active_pid
    from app.services import advisor as A
    from app.services.advisor_memory import remember
    today = date.today()
    res = await get_allocation(db)
    d = (json.loads(res.body) if hasattr(res, "body") else res)["data"]
    items = [it for it in d.get("items") or [] if float(it.get("market_value") or 0) > 0]
    fs, rows = [], []
    for it in items:
        try:
            f = await asyncio.wait_for(A.dossier(db, str(it["symbol"]), it.get("name") or ""), timeout=40)
        except Exception as e:                                    # noqa: BLE001
            logger.warning("المراجعة الأسبوعية {}: {}", it.get("symbol"), type(e).__name__)
            continue
        st = A.stance(f)
        try:
            remember(f, st, active_pid())
        except Exception:                                         # noqa: BLE001
            pass
        fs.append(f)
        rows.append(row(f, st, today))
    rows.sort(key=lambda x: (_ORDER.index(x["action"]) if x["action"] in _ORDER else 9, -(x.get("weight") or 0)))
    to_t = sum(float(it.get("total_amount") or 0) for it in items if (it.get("total_amount") or 0) > 0)
    r = {"date": today.isoformat(), "rows": rows, "upcoming": upcoming(fs, today),
         "portfolio": {"capital": d.get("investable") or 0, "cash": d.get("available_cash") or 0,
                       "to_targets": round(to_t, 2), "count": len(items), "spread": len(items) > SPREAD_N}}
    r["summary"] = await _summary(r)
    r["text"] = render(r)
    return r


async def weekly() -> dict:
    """كلَّ خميس: ورقةٌ لكلّ محفظةٍ غيرِ مؤرشفة — تُحفظ وتُرسَل في التطبيق وتلغرام."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.portfolio_scope import reset_scope, set_scope
    from app.models.portfolio import Portfolio
    from app.services import lastgood
    from app.services.advisor_memory import notify
    rep = {}
    async with AsyncSessionLocal() as db:
        ps = (await db.execute(select(Portfolio.id, Portfolio.name).where(Portfolio.is_archived.is_(False))
                               .order_by(Portfolio.id))).all()
        try:
            for pid, pname in ps:
                set_scope(pid, False)
                r = await review(db)
                if not r["rows"]:
                    continue
                lastgood.save(STORE.format(pid), {**r, "at": datetime.now().isoformat(timespec="minutes"), "portfolio_name": pname})
                await notify(f"صقر — مراجعةُ الأسبوع ({pname})", r["text"].split("\n")[1:], raw=True)
                rep[pid] = len(r["rows"])
        finally:
            reset_scope()
    logger.info("المراجعة الأسبوعية: {}", rep)
    return rep


def asks_weekly(question: str) -> bool:
    q = (question or "").replace("ـ", "")
    return ("مراجع" in q and ("اسبوع" in q or "أسبوع" in q)) or "ورقة الاسبوع" in q or "ورقة الأسبوع" in q


async def answer(db) -> dict:
    """«مراجعة الأسبوع» — آخرُ ورقةٍ إن كانت حديثة (أقلُّ من أسبوع)، وإلا تُبنى الآن."""
    from app.core.portfolio_scope import active_pid
    from app.services import lastgood
    pid = active_pid()
    old = lastgood.load(STORE.format(pid)) or {}
    if old.get("date") and old["date"] >= (date.today() - timedelta(days=6)).isoformat():
        return {"reply": old["text"], "grounded": True, "source": "advisor-weekly"}
    r = await review(db)
    lastgood.save(STORE.format(pid), {**r, "at": datetime.now().isoformat(timespec="minutes")})
    return {"reply": r["text"], "grounded": True, "source": "advisor-weekly"}
