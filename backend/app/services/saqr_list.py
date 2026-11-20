"""قائمةُ صقر — سكرتيرُ المالك لعقود الخيارات الطويلة (‏D771 بأمر المالك 2026-11-20).

قال المالك: «أنا ما أبغى يتعلّم الآن — أنت المتعلّم، وهو فقط المنفّذ… عقودُ الخيارات عندنا تحدّد الميزانيةَ فتُخرج قائمةً كاملة… أبغى صقر
أقلَّ الإيمان يشتغل مثل السكرتير: يطلع لي مثلاً 50 عقداً وأنا أختار بينها… لا نختار إلا طويلَ المدى… والاختيارُ نابعٌ عن مؤشراتٍ تدعمه،
بذكاء، مع فهم سلبياته — إذا كثرت السلبياتُ على الإيجابيات نمتنع… عقودٌ تطلع 30٪ أقلَّ شيء… أشتغل اليوم حتى أدخل اليومَ التالي».

فالقائمةُ تُبنى بعد إغلاق السوق الأمريكيّ للجلسة القادمة، وتُحدَّث في الجلسة، وبأمر المالك:
  ١ المجال: كلُّ ورقةٍ لها عقودُ خيارات واجتازت الفرزَ الأساسيّ (saqr_universe — الأساسُ قبل الفنّ)، ومسارُها صاعدٌ أو هابطٌ واضح.
  ٢ العقد: محرّكُ «عقود الخيارات» نفسُه (option_picks) — آجالٌ 150–430 يوماً، وكلفتُه ضمن ميزانية العقد عند المالك، وعرضٌ وطلبٌ حقيقيّان
     بفارقٍ ≤ 10٪، واهتمامٌ مفتوح، ودلتا 0.30–0.85، ونقطةُ تعادلٍ دون الهدف الفنيّ، والربحُ عند الهدف ≥ 75٪ من الكلفة.
  ٣ الأخبار: يقرؤها النموذجُ لكلّ ما بقي — والخبرُ القويُّ المعاكسُ يُسقط العقد.
  ٤ الإيجابياتُ والسلبيات من أرقام العقد ومساره وأساسه وخبره — وما زادت سلبياتُه على إيجابياته يُمتنع عنه.
  ٥ عتبةُ الثلاثين: سعرُ السهم الذي يربح عنده العقدُ 30٪ عند انتهائه، وما يحتاجه السهمُ ليبلغه.
والأرقامُ كلُّها من السوق (لا اختلاق)، والاحتمالُ تقديرٌ من التذبذب الضمنيّ لا وعد، وأقصى الخسارة كلفةُ العقد."""
from __future__ import annotations

import asyncio
import json
import os
from datetime import date, datetime, timedelta, timezone

from loguru import logger

from app.services import option_picks as OP

MAX_LIST = 50
CANDIDATES = 70          # أقوى المسارات (والميسورُ عقدُها أوّلاً) — كلٌّ منها خمسةُ نداءاتٍ للسلسلة
LT_X = 8                 # العقدُ الطويلُ بدلتا 0.3–0.85 يكلّف نحو 8–20 ضعفَ سعر السهم بالدولار (قيس: F ‏VALE ‏NIO)
TP_REF = 0.30            # المالك: «عقودٌ تطلع 30٪ أقلَّ شيء»
DEFAULT_BUDGET = 150.0   # المالك: «بالميزانية اللي نحدّدها 150»
_JOB = {"on": False, "msg": "", "at": None}
_LOCK = asyncio.Lock()


def _path() -> str:
    d = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "saqr")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "list.json")


def load() -> dict | None:
    try:
        with open(_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _save(res: dict) -> None:
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False)
    os.replace(tmp, _path())


def budget_of(cfg: dict) -> float:
    return float(cfg.get("per_trade") or DEFAULT_BUDGET)


DAYS_AR = ("الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد")


def for_session(state: str | None, ny_today: date) -> tuple[str, str]:
    """(تاريخُ الجلسة التي أُعدّت لها القائمة، وصفُها): في الجلسة أو قبلها ⇐ اليوم، وبعدها أو في العطلة ⇐ يومُ العمل التالي."""
    d = ny_today
    if state not in ("open", "pre"):
        d = d + timedelta(days=1)
    while d.weekday() >= 5:
        d = d + timedelta(days=1)
    lab = "جلسة اليوم" if d == ny_today else f"جلسة {DAYS_AR[d.weekday()]} {d.day:02d}/{d.month:02d}"
    return d.isoformat(), lab


def tp30(k: dict) -> dict:
    """سعرُ السهم الذي يربح عنده العقدُ 30٪ عند الانتهاء، وبعدُه عن السعر الآن."""
    call = k["type"] == "call"
    lv = k["strike"] + (1 + TP_REF) * k["ask"] if call else k["strike"] - (1 + TP_REF) * k["ask"]
    S = k.get("price") or 0
    return {"price": round(lv, 2), "pct": round(((lv / S - 1) if call else (1 - lv / S)) * 100, 1) if S else None}


def assess(k: dict, tr: dict, fund: tuple | None, news: dict | None) -> tuple[list[str], list[str]]:
    """الإيجابياتُ والسلبيات من أرقام العقد ومساره وأساسه وخبره — كلٌّ بسببه ورقمه."""
    call = k["type"] == "call"
    pros, cons = [], []
    up = tr["close"] > tr["sma50"] > tr["sma200"]
    dn = tr["close"] < tr["sma50"] < tr["sma200"]
    if (call and up) or (not call and dn):
        pros.append(f"المسارُ {tr['state']} مكتمل: الإغلاق {tr['close']:,.2f} {'فوق' if call else 'دون'} متوسّطي 50 ({tr['sma50']:,.2f}) و200 ({tr['sma200']:,.2f})")
    else:
        cons.append(f"المسارُ {tr['state']} غيرُ مكتمل: الإغلاق {tr['close']:,.2f} بين المتوسّطين")
    r3 = tr.get("ret3m") or 0
    if (call and r3 >= 5) or (not call and r3 <= -5):
        pros.append(f"زخمٌ مع الصفقة: {r3:+.0f}٪ في ثلاثة أشهر")
    elif (call and r3 < 0) or (not call and r3 > 0):
        cons.append(f"زخمُ ثلاثة أشهر يعاكس الصفقة ({r3:+.0f}٪)")
    if fund:
        sc, why = fund
        if call and sc >= 80:
            pros.append(f"أساسٌ ماليٌّ متين ({sc:.0f}/100): {why}")
        elif call and sc < 70:
            cons.append(f"الأساسُ مقبولٌ لا ممتاز ({sc:.0f}/100)")
    imp = str((news or {}).get("impact") or "")
    if news and imp in ("إيجابي", "سلبي") and int(news.get("strength") or 0) >= 1:
        if (imp == "إيجابي") == call:
            pros.append(f"الخبرُ يدعمها: {news.get('event') or imp}")
        else:
            cons.append(f"خبرٌ معاكس: {news.get('event') or imp}")
    gain = k["rr"] * 100                 # المحرّكُ يشترط 75٪ فأكثر عند الهدف
    if gain >= 100:
        pros.append(f"الربحُ عند الهدف الفنيّ {k['target']:,.2f}: {gain:+.0f}٪ من الكلفة")
    elif gain < 90:
        cons.append(f"الربحُ عند الهدف {k['target']:,.2f} {gain:+.0f}٪ فقط")
    if k["pop"] >= 35:
        pros.append(f"احتمالُ الربح عند الانتهاء نحو {k['pop']:.0f}٪")
    elif k["pop"] < 28:
        cons.append(f"احتمالُ الربح عند الانتهاء نحو {k['pop']:.0f}٪ فقط")
    if k["p_touch"] >= 50:
        pros.append(f"احتمالُ لمس الهدف قبل الانتهاء نحو {k['p_touch']:.0f}٪")
    if k["spread_pct"] <= 5:
        pros.append(f"فارقٌ ضيّق {k['spread_pct']:.1f}٪ (نحو {k['spread_usd']:,.0f}$ للعقد)")
    elif k["spread_pct"] > 7:
        cons.append(f"فارقٌ واسعٌ نسبياً {k['spread_pct']:.1f}٪ (نحو {k['spread_usd']:,.0f}$ للعقد)")
    if (k.get("oi") or 0) >= 1000:
        pros.append(f"سيولةٌ عالية: {k['oi']:,} عقداً مفتوحاً")
    elif (k.get("oi") or 0) < 300:
        cons.append(f"سيولةٌ محدودة: {k.get('oi') or 0:,} عقداً مفتوحاً")
    if k["dte"] >= 240:
        pros.append(f"أجلٌ طويل {k['dte']} يوماً — تآكلٌ بطيءٌ ووقتٌ كافٍ")
    elif k["dte"] < 180:
        cons.append(f"أجلٌ أقصر في الطويل ({k['dte']} يوماً)")
    if k["need_pct"] > 15:
        cons.append(f"يحتاج السهم {k['need_pct']:.1f}٪ ليبلغ التعادل")
    if k["iv"] > 80:
        cons.append(f"تذبذبٌ ضمنيٌّ مرتفع {k['iv']:.0f}٪ — العقدُ غالٍ")
    if abs(k["delta"]) < 0.35:
        cons.append(f"دلتا منخفضة {k['delta']:+.2f} — يحتاج حركةً كبيرة")
    return pros, cons


async def build(cfg: dict, held: set[str] | None = None) -> dict:
    """تُبنى القائمة: المجالُ ⇐ العقدُ الطويل ⇐ الخبر ⇐ الإيجابياتُ والسلبيات — وتُحفظ لتُقرأ حتى البناء التالي."""
    from app.services import saqr_universe as SU
    from app.services.live_quote import sessions
    from app.services.market_session import NY
    if _LOCK.locked():
        return load() or {}
    async with _LOCK:
        _JOB.update(on=True, msg="قراءةُ المجال", at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        try:
            budget = budget_of(cfg)
            calls_only = cfg.get("sides") == "calls"
            U = await SU.universe()
            tr_all, fund, names = U["tr"], U["fund"], U.get("names") or {}
            held = held or set()
            ranked = sorted(((s, t) for s, t in tr_all.items() if t["state"] in ("صاعد", "هابط") and s not in held
                             and not (calls_only and t["state"] == "هابط")), key=lambda kv: -kv[1]["strength"])
            cheap = [x for x in ranked if x[1]["close"] * LT_X <= budget * 1.5]
            plan = (cheap + [x for x in ranked if x not in cheap])[:CANDIDATES]
            _JOB["msg"] = f"البحثُ في عقود {len(plan)} ورقة"
            sem = asyncio.Semaphore(4)
            excl: dict[str, int] = {}
            lows: list[float] = []

            async def one(s, tr):
                call = tr["state"] == "صاعد"
                async with sem:
                    try:
                        k, low = await asyncio.wait_for(OP.contracts_for(s, call, budget, tr), 60)
                    except Exception:                             # noqa: BLE001
                        k, low = None, None
                if not k:
                    if low:
                        lows.append(low)
                    key = "فوق الميزانية" if low else "لا عقدَ طويلَ يستوفي الشروط"
                    excl[key] = excl.get(key, 0) + 1
                return s, tr, k
            got = [x for x in await asyncio.gather(*(one(s, t) for s, t in plan)) if x[2]]
            _JOB["msg"] = "قراءةُ الأخبار"
            try:
                news = await OP.read_news({s: tr for s, tr, _ in got})
            except Exception:                                     # noqa: BLE001
                news = {}
            items = []
            for s, tr, k in got:
                n = news.get(s)
                side, note = OP.direction(tr, n)
                if side != k["type"]:
                    excl["خبرٌ قويٌّ يعاكس المسار"] = excl.get("خبرٌ قويٌّ يعاكس المسار", 0) + 1
                    continue
                pros, cons = assess(k, tr, fund.get(s), n)
                if len(cons) > len(pros):
                    excl["سلبياتُه أكثر من إيجابياته"] = excl.get("سلبياتُه أكثر من إيجابياته", 0) + 1
                    continue
                margin = len(pros) - len(cons)
                items.append({**{x: k[x] for x in ("contract", "type", "strike", "expiry", "t", "dte", "ask", "bid", "mid", "cost", "px_src", "quote_at",
                                                    "spread_pct", "spread_usd", "breakeven", "need_pct", "target", "target_label", "rr", "pop", "p_touch",
                                                    "delta", "iv", "oi", "score") if x in k},
                              "symbol": s, "name": names.get(s) or k.get("name"), "price": k.get("price"), "gain_target": round(k["rr"] * 100),
                              "tp30": tp30(k), "pros": pros, "cons": cons, "margin": margin, "grade": "قويّة" if margin >= 4 else "جيّدة",
                              "fund": fund.get(s, (None, None))[0], "trend": {"state": tr["state"], "strength": tr["strength"], "ret3m": tr.get("ret3m")},
                              "news": {"impact": n.get("impact"), "event": n.get("event")} if n else None})
            items.sort(key=lambda x: (-x["margin"], -x["score"]))
            items = items[:MAX_LIST]
            try:
                us = (await sessions())["us"]
            except Exception:                                     # noqa: BLE001
                us = {}
            ny = datetime.now(timezone.utc).astimezone(NY).date()
            fs, lab = for_session(us.get("state"), ny)
            res = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "for": fs, "label": lab, "budget": budget, "items": items,
                   "scanned": len(plan), "universe": len(tr_all), "excluded": excl, "cheapest": min(lows) if lows else None,
                   "snap": any(i.get("px_src") == "snap" for i in items), "calls_only": calls_only}
            _save(res)
            logger.info("قائمةُ صقر: {} عقداً من {} ورقة ({}) بميزانية {}", len(items), len(plan), lab, budget)
            return res
        finally:
            _JOB.update(on=False, msg="")


def job() -> dict:
    return dict(_JOB)
