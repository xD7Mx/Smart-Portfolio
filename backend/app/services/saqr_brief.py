"""صقرُ تلغرام يعرف عملَه — فرصُه ونظرتُه وعقودُه وتقريرُه (‏D819 · بأمر المالك 2026-11-24).

قال المالك: «سؤالُ صقر لا يعطيني نتيجةً ملموسة». قِيس على الخادم (‏saqr_ask_door_d819.py) والأسئلةُ أسئلتُه:
  · «ما أفضلُ فرصةٍ اليوم في السوق الأمريكي؟» ⇐ «هذا خارج نطاق عملي؛ يقتصر على السوق السعودي» — وصقرٌ يمسح السوقَ الأمريكيَّ كلَّ يوم.
  · «وش رأيك في NVDA؟» و«أعطني عقدَ خياراتٍ بميزانية 500 دولار» ⇐ «خارج نطاق التطبيق» — والتطبيقُ فيه دفترُ عقودٍ لكلّ ميزانية.
  · «ما نظرتُك لتاسي هذا الأسبوع؟» ⇐ «بياناتُ تاسي غير متوفّرة» — ونظرةُ صقر لتاسي في التقرير اليوميّ.
والسببُ الجذريّ: سياقُ المحادثة بيانُ المحفظة وحده (14 كتلة · 107 آلاف حرف، يُقصّ منها «نبضُ السوق») بلا كتلةٍ واحدةٍ من عمل صقر، وتعليماتُه
القديمةُ تحصره في السوق السعوديّ. فهنا ما يعرفه صقر من عمله نفسِه — من ملفّاته المحفوظة لا من رأس النموذج: فرصُ آخر مسحٍ للسوقين بدخولها
وهدفها ووقفها وحكمه، وعقودُ الخيارات في دفتر كلّ ميزانية، ونظرتُه لتاسي، وعنوانُ التقرير اليوميّ وأخبارُه — يُجاب منه مباشرةً حين يُسأل
عنه (جوابٌ ثابتُ الأرقام فوراً)، ويُعطى للنموذج في رأس سياقه لما سوى ذلك.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

RY = timezone(timedelta(hours=3))
SIDE = {"long": "شراء", "short": "بيع"}
US_WORDS = ("امريكي", "أمريكي", "الأمريكي", "الامريكي", "امريكا", "أمريكا", "us", "usa", "ناسداك", "وول ستريت")
SA_WORDS = ("سعودي", "السعودي", "تاسي", "تداول", "المحلي")
OPP_WORDS = ("فرصه", "فرصة", "فرص", "صفقه", "صفقة", "صفقات", "اشتري ايش", "وش اشتري", "ماذا اشتري", "ايش اشتري", "أدخل", "ادخل")
OPT_WORDS = ("عقد", "عقود", "خيارات", "اوبشن", "أوبشن", "كول", "بوت", "call", "put", "option")
TASI_WORDS = ("تاسي", "المؤشر", "السوق السعودي")
VIEW_WORDS = ("نظرتك", "نظرة", "رأيك", "توقعك", "توقّعك", "اتجاه")


def _n(t: str) -> str:
    return re.sub(r"[إأآٱ]", "ا", str(t or "")).replace("ة", "ه").replace("ى", "ي").lower()


def _has(t: str, words) -> bool:
    n = _n(t)
    return any(_n(w) in n for w in words)


def _f(v, d: int = 2) -> str:
    try:
        return f"{float(v):,.{d}f}"
    except Exception:                                             # noqa: BLE001
        return "—"


def _when(iso: str | None) -> str:
    try:
        t = datetime.fromisoformat(str(iso)).astimezone(RY)
        return t.strftime("%d/%m %H:%M")
    except Exception:                                             # noqa: BLE001
        return "—"


# ── ١ الفرص ──────────────────────────────────────────────────────────────────────────────────────────
def opps(market: str, n: int = 5) -> dict:
    """فرصُ آخر مسحٍ لسوقٍ بأرقامها ⇐ ‏{at, items:[…], found, fresh}."""
    from app.services import chart_scan as CS
    d = CS.load(market) or {}
    fresh = CS.fresh(market) is not None
    items = []
    for x in (d.get("items") or [])[:n]:
        c = x.get("council") or {}
        lk = x.get("link") or {}
        e = x.get("entry") or [None, None]
        items.append({"symbol": x["symbol"], "name": x.get("name") or x["symbol"], "side": SIDE.get(x.get("side"), x.get("side")), "setup": x.get("setup"),
                      "quality": x.get("quality"), "entry": e, "target": x.get("target"), "stop": x.get("stop"), "horizon": x.get("horizon"),
                      "verdict": c.get("verdict"), "score": c.get("score"), "decision": lk.get("decision"), "link": lk.get("link"), "close": x.get("close")})
    return {"at": d.get("at"), "found": d.get("found"), "items": items, "fresh": fresh, "market": market}


def opps_text(market: str, n: int = 5) -> str:
    o = opps(market, n)
    flag, name, ccy = ("🇸🇦", "السعودي", "ريال") if market == "sa" else ("🇺🇸", "الأمريكي", "$")
    if not o["items"]:
        return f"{flag} لا فرصَ في آخر مسحٍ للسوق {name}" + (f" ({_when(o['at'])})" if o["at"] else " — لم يُمسح بعد") + "."
    head = f"{flag} فرصُ صقر — السوق {name} · مسح {_when(o['at'])}" + ("" if o["fresh"] else " (قديم)")
    rows = [head]
    for i, x in enumerate(o["items"], 1):
        e = x["entry"] or [None, None]
        v = f"صقر {x['verdict']} ({x['score']}/100)" if x.get("verdict") else ""
        dec = f" · القرار: {x['decision']}" if x.get("decision") else ""
        rows.append(f"{i}. {x['name']} ({x['symbol']}) — {x['side']} · {x['setup']} · جودة {x['quality']}\n"
                    f"   الدخول {_f(e[0])}–{_f(e[1])} · الهدف {_f(x['target'])} · الوقف {_f(x['stop'])} {ccy} · {x.get('horizon') or ''}\n"
                    f"   {v}{dec}" + (f"\n   {x['link']}" if x.get("link") else ""))
    return "\n".join(rows)


# ── ٢ عقودُ الخيارات ─────────────────────────────────────────────────────────────────────────────────
def options(budget: float | None = None, n: int = 5) -> dict:
    """عقودُ دفتر أقرب ميزانيةٍ (≥ المطلوبة إن وُجدت) ⇐ ‏{budget, picks:[…]}."""
    from app.services import option_picks as OP
    bs = OP.book_budgets()
    if not bs:
        return {"budget": None, "picks": []}
    b = min((x for x in bs if budget is None or x >= budget), default=max(bs)) if budget else bs[0]
    book = OP.book_load(b)
    picks = []
    for e in (book.get("open") or [])[:n]:
        c = e.get("card") or {}
        last = e.get("last") or {}
        picks.append({"contract": e.get("contract"), "symbol": e.get("symbol"), "name": e.get("name"), "type": "شراء (كول)" if e.get("type") == "call" else "بيع (بوت)",
                      "strike": e.get("strike"), "expiry": e.get("expiry"), "cost": c.get("cost"), "target": e.get("target"), "breakeven": c.get("breakeven"),
                      "pop": c.get("pop"), "dte": last.get("dte", c.get("dte")), "pl": last.get("pl_pct"), "status": last.get("why")})
    return {"budget": b, "picks": picks}


def options_text(budget: float | None = None) -> str:
    o = options(budget)
    if not o["picks"]:
        return "📑 لا عقودَ مفتوحةً في دفتر صقر الآن" + (f" لميزانية {o['budget']:,}$" if o["budget"] else "") + "."
    rows = [f"📑 عقودُ صقر — ميزانية {o['budget']:,}$" + (f" (أقربُ دفترٍ لـ{int(budget):,}$)" if budget and budget != o["budget"] else "")]
    for i, p in enumerate(o["picks"], 1):
        rows.append(f"{i}. {p['name'] or p['symbol']} — {p['type']} · تنفيذ {_f(p['strike'])} · انتهاء {p['expiry']} ({p['dte']} يوماً)\n"
                    f"   الكلفة {_f(p['cost'], 0)}$ · التعادل {_f(p['breakeven'])} · الهدف {_f(p['target'])} · احتمالُ الربح {_f(p['pop'], 0)}٪"
                    + (f" · الآن {p['pl']:+.1f}٪" if isinstance(p.get("pl"), (int, float)) else "")
                    + f"\n   الرمز: {p['contract']}")
    return "\n".join(rows)


# ── ٣ نظرةُ صقر لتاسي والتقريرُ اليوميّ ─────────────────────────────────────────────────────────────────
def _main_report() -> dict | None:
    from app.services import research_desk as RD
    for pid in (1, "all"):
        r = RD.load_report(pid)
        if r:
            return r
    return None


def tasi() -> dict:
    r = _main_report() or {}
    m = r.get("market") or {}
    t, tech, sq = m.get("tasi") or {}, m.get("tech") or {}, m.get("saqr") or {}
    return {"date": r.get("date"), "close": t.get("close"), "pct": t.get("pct"), "view": tech.get("view"), "why": sq.get("why") or [],
            "themes": sq.get("themes") or [], "headline": r.get("headline")}


def tasi_text() -> str:
    t = tasi()
    if not t["date"]:
        return "🇸🇦 لا تقريرَ يوميَّ بعد — نظرةُ صقر لتاسي تُكتب بعد إغلاق السوق."
    rows = [f"🇸🇦 نظرةُ صقر لتاسي — {t['view'] or '—'}", f"تاسي {_f(t['close'])} ({t['pct']:+.2f}٪) · جلسة {t['date']}" if isinstance(t.get("pct"), (int, float))
            else f"تاسي {_f(t['close'])} · جلسة {t['date']}"]
    for w in t["why"][:4]:
        rows.append(f"• {w if isinstance(w, str) else w.get('text') or w.get('say') or ''}")
    if t.get("headline"):
        rows.append(f"العنوان: {t['headline']}")
    return "\n".join(rows)


def daily() -> dict:
    r = _main_report() or {}
    return {"date": r.get("date"), "headline": r.get("headline"), "local": [x.get("text") for x in (r.get("local") or [])[:3]],
            "global": [x.get("text") for x in (r.get("global") or [])[:3]]}


# ── ٤ ما يعرفه صقر — للنموذج في رأس السياق ──────────────────────────────────────────────────────────────
def knowledge() -> dict:
    out = {}
    try:
        out["فرص صقر — السوق السعودي"] = opps("sa", 6)
        out["فرص صقر — السوق الأمريكي"] = opps("us", 6)
    except Exception:                                             # noqa: BLE001
        pass
    try:
        out["عقود الخيارات في دفتر صقر"] = options(None, 6)
    except Exception:                                             # noqa: BLE001
        pass
    try:
        out["نظرة صقر لتاسي"] = tasi()
        out["التقرير اليومي"] = daily()
    except Exception:                                             # noqa: BLE001
        pass
    return out


RULES = """
— ما تعرفه من عملك (‏«صقر — عمله») —
التطبيقُ يغطّي السوقين: السعوديَّ (تداول) والأمريكيَّ وعقودَ خياراته. فلا تقل «خارج نطاقي» عن سهمٍ أمريكيٍّ أو عقد خيارات.
فرصُ صقر وعقودُه ونظرتُه لتاسي وتقريرُه اليوميّ في كتلة «صقر — عمله»: أجب منها بأرقامها (الدخول · الهدف · الوقف · التنفيذ · الانتهاء
· الكلفة) وتاريخِ مسحها؛ وما ليس فيها فقل إنّه غيرُ متوفّر. ولا تخترع فرصةً ولا عقداً ليس فيها."""


def _budget(q: str) -> float | None:
    m = re.search(r"(\d[\d,]{1,7})", q.replace("٬", ","))
    if not m:
        return None
    try:
        v = float(m.group(1).replace(",", ""))
        return v if 50 <= v <= 1_000_000 else None
    except ValueError:
        return None


def ticker_text(sym: str) -> str | None:
    """سهمٌ أمريكيٌّ بعينه: ما قرأه صقرٌ في رسمه في آخر مسح — فرصةٌ بأرقامها، أو قراءةٌ بلا فرصةٍ مكتملة؛ و‏None إن لم يُقرأ."""
    from app.services import chart_scan as CS
    kind, x = CS.chart_of("us", sym)
    if kind == "opp" and x:
        c = x.get("council") or {}
        e = x.get("entry") or [None, None]
        return (f"🇺🇸 {x.get('name') or sym} ({sym}) — فرصةٌ في آخر مسح: {SIDE.get(x.get('side'), x.get('side'))} · {x.get('setup')} · جودة {x.get('quality')}\n"
                f"الدخول {_f(e[0])}–{_f(e[1])} · الهدف {_f(x.get('target'))} · الوقف {_f(x.get('stop'))}$ · {x.get('horizon') or ''}"
                + (f"\nصقر {c.get('verdict')} ({c.get('score')}/100)" if c.get("verdict") else "")
                + (f"\n{(x.get('link') or {}).get('link')}" if (x.get("link") or {}).get("link") else ""))
    if kind in ("weak", "flat") and x:
        return (f"🇺🇸 {sym} — قرأ صقرٌ رسمَه في آخر مسح: " + ("إعدادٌ دون الجودة المطلوبة" if kind == "weak" else "لا فرصةَ في الرسم الآن")
                + (f" ({x.get('setup')} · جودة {x.get('quality')})" if x.get("setup") else "") + ".")
    return None


def answer(question: str) -> str | None:
    """جوابٌ ثابتُ الأرقام من عمل صقر — للفرص والعقود ونظرة تاسي؛ و‏None لما سوى ذلك (فيُسأل النموذجُ بسياقٍ فيه عملُ صقر)."""
    q = question or ""
    if _has(q, OPT_WORDS):
        return options_text(_budget(q))
    if _has(q, OPP_WORDS):
        us, sa = _has(q, US_WORDS), _has(q, SA_WORDS)
        if us and not sa:
            return opps_text("us")
        if sa and not us:
            return opps_text("sa")
        return opps_text("sa", 3) + "\n\n" + opps_text("us", 3)
    if _has(q, TASI_WORDS) and _has(q, VIEW_WORDS):
        return tasi_text()
    for sym in re.findall(r"\b([A-Z]{2,5})\b", q):                  # «وش رأيك في NVDA؟»
        got = ticker_text(sym)
        if got:
            return got
    return None
