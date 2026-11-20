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
CANDIDATES = 45          # أقوى المسارات (والميسورُ عقدُها أوّلاً) — كلٌّ منها خمسةُ نداءاتٍ للسلسلة (والذاكرةُ على الخادم محدودة)
REFRESH_MIN = 120        # تُحدَّث في الجلسة كلَّ ساعتين
FINAL_MIN = 45           # وآخرُ بناءٍ قبل الإغلاق بخمسٍ وأربعين دقيقة: قائمةُ الجلسة القادمة
# ‏D774 — قيس على الخادم (2026-11-20، الجلسةُ مفتوحة): 0 عقداً من 45 سهماً — بدأ صقر بالأرخص من مجالٍ عامّ فكان أكثرُها رقيقَ العقود الطويلة.
# فيبدأ بما عقودُه سائلة (الأسيلُ في «عقود الخيارات» أو تداولٌ يوميٌّ ≥ مئة مليون دولار)، ويُكمل الفحصَ دفعةً كلَّ نصف ساعةٍ في الجلسة
# فتنمو القائمةُ حتى الخمسين، ويُحفظ لكلّ سهمٍ فُحص سببُ امتناعه بعينه.
LIQ_MIN = 100.0          # مليونُ دولارٍ تداولاً يومياً
EXTEND_MIN = 30          # دفعةُ فحصٍ جديدةٌ كلَّ نصف ساعةٍ ما بقي ما لم يُفحص والقائمةُ دون الخمسين
RESCAN_H = 6             # لا يُعاد فحصُ سهمٍ قبل ست ساعاتٍ إلا إن لم يبقَ غيرُه
KEEP_H = 20              # عقدٌ دخل القائمةَ يبقى فيها عشرين ساعةً ما لم يُعَد فحصُ سهمه — فتحمل قائمةُ الغد عملَ اليوم كلِّه
V = 2
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


def for_session(state: str | None, ny_today: date, final: bool = False) -> tuple[str, str]:
    """(تاريخُ الجلسة التي أُعدّت لها القائمة، وصفُها): في الجلسة أو قبلها ⇐ اليوم، وبعدها أو في العطلة أو آخرَ الجلسة (final) ⇐ يومُ العمل التالي."""
    d = ny_today
    if final or state not in ("open", "pre"):
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


def order(ranked: list, budget: float) -> list:
    """ترتيبُ الفحص (‏D774): الميسورُ السائلُ أوّلاً، ثمّ الميسور، ثمّ السائل، ثمّ الباقي — وفي كلٍّ الأقوى مساراً."""
    liquid = set(OP.UNIVERSE)

    def tier(s, t):
        afford = t["close"] * LT_X <= budget * 2
        liq = s in liquid or (t.get("traded") or 0) >= LIQ_MIN
        return 0 if afford and liq else 1 if afford else 2 if liq else 3
    return sorted(ranked, key=lambda kv: (tier(*kv), -kv[1]["strength"]))


def _age_h(at: str | None, now: datetime) -> float:
    try:
        return (now - datetime.fromisoformat(at)).total_seconds() / 3600 if at else 1e9
    except ValueError:
        return 1e9


async def build(cfg: dict, held: set[str] | None = None, final: bool = False) -> dict:
    """تُبنى القائمة دفعةً: المجالُ ⇐ العقدُ الطويل ⇐ الخبر ⇐ الإيجابياتُ والسلبيات — وتُضمّ إلى ما بُني قبلها بالميزانية نفسِها (‏D774)
    فتنمو حتى الخمسين، ولكلّ سهمٍ فُحص سببُ امتناعه؛ وتُحفظ لتُقرأ حتى البناء التالي."""
    from app.services import saqr_universe as SU
    from app.services.live_quote import sessions
    from app.services.market_session import NY
    if _LOCK.locked():
        return load() or {}
    async with _LOCK:
        _JOB.update(on=True, msg="قراءةُ المجال", at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        try:
            now = datetime.now(timezone.utc)
            budget = budget_of(cfg)
            calls_only = cfg.get("sides") == "calls"
            U = await SU.universe()
            tr_all, fund, names = U["tr"], U["fund"], U.get("names") or {}
            held = held or set()
            ranked = order([(s, t) for s, t in tr_all.items() if t["state"] in ("صاعد", "هابط") and s not in held
                            and not (calls_only and t["state"] == "هابط")], budget)
            old = load()
            same = bool(old and old.get("v") == V and old.get("budget") == budget and bool(old.get("calls_only")) == calls_only)
            done = {s: d for s, d in ((old or {}).get("done") or {}).items() if same and _age_h(d.get("at"), now) < RESCAN_H}
            # ما لم يُفحص أوّلاً بترتيبه، ثمّ الأقدمُ فحصاً (حين يُفحص المجالُ كلُّه)
            plan = sorted(ranked, key=lambda kv: (kv[0] in done, (done.get(kv[0]) or {}).get("at") or ""))[:CANDIDATES]
            _JOB["msg"] = f"البحثُ في عقود {len(plan)} ورقة"
            sem = asyncio.Semaphore(4)
            stamp = now.isoformat(timespec="seconds")

            async def one(s, tr):
                call = tr["state"] == "صاعد"
                dg: dict = {}
                async with sem:
                    try:
                        k, low = await asyncio.wait_for(OP.contracts_for(s, call, budget, tr, diag=dg), 60)
                    except asyncio.TimeoutError:
                        k, low, dg = None, None, {"why": "تعذّرت قراءةُ عقوده في دقيقة"}
                    except Exception:                             # noqa: BLE001
                        k, low, dg = None, None, {"why": "تعذّرت قراءةُ عقوده"}
                if not k:
                    why = "فوق الميزانية" if low else dg.get("why") or (OP.STAGES[dg["stage"]] if "stage" in dg else "لا عقدَ طويلَ يستوفي الشروط")
                    done[s] = {"at": stamp, "why": why, "low": low}
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
                    done[s] = {"at": stamp, "why": "خبرٌ قويٌّ يعاكس المسار"}
                    continue
                pros, cons = assess(k, tr, fund.get(s), n)
                if len(cons) > len(pros):
                    done[s] = {"at": stamp, "why": "سلبياتُه أكثر من إيجابياته"}
                    continue
                done[s] = {"at": stamp, "why": None}
                margin = len(pros) - len(cons)
                items.append({**{x: k[x] for x in ("contract", "type", "strike", "expiry", "t", "dte", "ask", "bid", "mid", "cost", "px_src", "quote_at",
                                                    "spread_pct", "spread_usd", "breakeven", "need_pct", "target", "target_label", "rr", "pop", "p_touch",
                                                    "delta", "iv", "oi", "score") if x in k},
                              "symbol": s, "name": names.get(s) or k.get("name"), "price": k.get("price"), "gain_target": round(k["rr"] * 100),
                              "tp30": tp30(k), "pros": pros, "cons": cons, "margin": margin, "grade": "قويّة" if margin >= 4 else "جيّدة",
                              "fund": fund.get(s, (None, None))[0], "trend": {"state": tr["state"], "strength": tr["strength"], "ret3m": tr.get("ret3m")},
                              "news": {"impact": n.get("impact"), "event": n.get("event")} if n else None, "seen": stamp})
            scanned_now = {s for s, _ in plan}
            kept = [i for i in ((old or {}).get("items") or []) if same and i["symbol"] not in scanned_now and i["symbol"] not in held
                    and _age_h(i.get("seen") or old.get("at"), now) < KEEP_H]
            fresh_n = len(items)
            items = sorted(items + kept, key=lambda x: (-x["margin"], -x["score"]))[:MAX_LIST]
            try:
                us = (await sessions())["us"]
            except Exception:                                     # noqa: BLE001
                us = {}
            ny = now.astimezone(NY).date()
            fs, lab = for_session(us.get("state"), ny, final)
            # ‏D771 — قيس على الخادم (2026-11-20 قبل الافتتاح): المصدرُ يُصفّر العرضَ والطلبَ خارج الجلسة فخرجت القائمةُ فارغةً (0 من 70) —
            # فبناءٌ فارغٌ خارج الجلسة لا يمحو قائمةً صالحة: تبقى ويُكتب أنّ التحديثَ ينتظر الجلسة
            if not items and old and old.get("items") and us.get("state") != "open":
                old["retry"] = {"at": now.isoformat(timespec="seconds"), "why": "خارج الجلسة لا عرضَ ولا طلبَ حيّين — تُحدَّث في الجلسة"}
                _save(old)
                return old
            excl: dict[str, int] = {}
            for d in done.values():
                if d.get("why"):
                    excl[d["why"]] = excl.get(d["why"], 0) + 1
            lows = [d["low"] for d in done.values() if d.get("low")]
            res = {"v": V, "at": now.isoformat(timespec="seconds"), "for": fs, "label": lab, "budget": budget, "items": items,
                   "scanned": len(done), "universe": len(tr_all), "batch": len(plan), "fresh": fresh_n,
                   "excluded": dict(sorted(excl.items(), key=lambda kv: -kv[1])), "cheapest": min(lows) if lows else None,
                   "more": any(s not in done for s, _ in ranked), "done": done,
                   "snap": any(i.get("px_src") == "snap" for i in items), "calls_only": calls_only}
            _save(res)
            logger.info("قائمةُ صقر: {} عقداً ({} جديداً من دفعة {}) · فُحص {} من {} ({}) بميزانية {} · امتناع {}", len(items), fresh_n, len(plan),
                        len(done), len(ranked), lab, budget, res["excluded"])
            return res
        finally:
            _JOB.update(on=False, msg="")


def job() -> dict:
    return dict(_JOB)


def due(now: datetime, clock: tuple[datetime, datetime] | None, lst: dict | None) -> tuple[bool, bool]:
    """(أتُبنى الآن؟ أهي الأخيرةُ للجلسة القادمة؟) — في الجلسة وحدها: لا قائمة (أو بصيغةٍ أقدم)، أو مضى نصفُ ساعةٍ والقائمةُ دون الخمسين وبقي
    ما لم يُفحص (‏D774)، أو مضت ساعتان، أو حان آخرُ بناءٍ قبل الإغلاق ولم يُبنَ."""
    if not clock or not (clock[0] <= now <= clock[1]):
        return False, False
    final_at = clock[1] - timedelta(minutes=FINAL_MIN)
    at = None
    try:
        at = datetime.fromisoformat(lst["at"]) if lst and lst.get("at") else None
    except ValueError:
        at = None
    if now >= final_at:
        return (at is None or at < final_at), True
    if not lst or lst.get("v") != V:
        return True, False
    gap = EXTEND_MIN if lst.get("more") and len(lst.get("items") or []) < MAX_LIST else REFRESH_MIN
    return (at is None or (now - at).total_seconds() >= gap * 60), False


def kick(cfg: dict, held: set[str], now: datetime, clock) -> bool:
    """من دورة صقر: يُطلق البناءَ في الخلفية إن حان — فلا تحبس الدورةُ دقائقَه."""
    go, final = due(now, clock, load())
    if not go or _LOCK.locked():
        return False
    asyncio.get_running_loop().create_task(build(cfg, held, final))
    return True
