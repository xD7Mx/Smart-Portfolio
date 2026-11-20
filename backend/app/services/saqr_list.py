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
# ‏D775 — المالك (2026-11-20): «الأفضلُ أن تكون الميزانيةُ كستمايز: أخلّيها 300، أخلّيها 150، أخلّيها 100 — كلَّ يومٍ يجي خيرٌ معه».
# فلا تُبنى القائمةُ لميزانيةٍ واحدة: يُحفظ لكلّ سهمٍ أفضلُ عقدٍ عند كلّ كلفة (الحدُّ الكفء — كلُّ عقدٍ فيه أعلى درجةً من كلّ أرخصَ منه)،
# ويُختار عند العرض أفضلُها ضمن ميزانية المالك الآن — فتبديلُها فوريٌّ بلا بحثٍ جديد، في الجلسة وخارجها.
LEVELS = (100, 150, 200, 300, 500)
V = 3
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


def frontier(cards: list[dict]) -> list[dict]:
    """الحدُّ الكفء: العقودُ بكلفتها صعوداً، ولا يبقى إلا ما درجتُه أعلى من كلّ أرخصَ منه — فأفضلُ عقدٍ ضمن أيّ ميزانيةٍ آخرُ ما لا يتجاوزها منه."""
    out: list[dict] = []
    for k in sorted(cards, key=lambda k: (k["cost"], -k["score"])):
        if not out or k["score"] > out[-1]["score"]:
            out.append(k)
    return out


async def build(cfg: dict, held: set[str] | None = None, final: bool = False) -> dict:
    """تُبنى القائمة دفعةً: المجالُ ⇐ العقودُ الطويلةُ الصالحة ⇐ الخبر ⇐ الإيجابياتُ والسلبياتُ لكلّ عقد ⇐ الحدُّ الكفءُ لكلّ سهم — وتُضمّ إلى
    ما بُني قبلها فتنمو (‏D774)، ولكلّ سهمٍ فُحص سببُ امتناعه؛ والميزانيةُ تُطبَّق عند العرض (‏view — ‏D775)."""
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
            U = await SU.universe()
            tr_all, fund, names = U["tr"], U["fund"], U.get("names") or {}
            held = held or set()
            ranked = order([(s, t) for s, t in tr_all.items() if t["state"] in ("صاعد", "هابط") and s not in held], budget)
            old = load()
            same = bool(old and old.get("v") == V)
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
                        _, cards = await asyncio.wait_for(OP.valid_contracts(s, call, tr, diag=dg), 60)
                    except asyncio.TimeoutError:
                        cards, dg = [], {"why": "تعذّرت قراءةُ عقوده في دقيقة"}
                    except Exception:                             # noqa: BLE001
                        cards, dg = [], {"why": "تعذّرت قراءةُ عقوده"}
                if not cards:
                    done[s] = {"at": stamp, "why": dg.get("why") or (OP.STAGES[dg["stage"]] if "stage" in dg else "لا عقدَ طويلَ يستوفي الشروط")}
                return s, tr, cards
            got = [x for x in await asyncio.gather(*(one(s, t) for s, t in plan)) if x[2]]
            _JOB["msg"] = "قراءةُ الأخبار"
            try:
                news = await OP.read_news({s: tr for s, tr, _ in got})
            except Exception:                                     # noqa: BLE001
                news = {}
            entries: dict[str, dict] = {}
            for s, tr, cards in got:
                n = news.get(s)
                side, note = OP.direction(tr, n)
                if side != cards[0]["type"]:
                    done[s] = {"at": stamp, "why": "خبرٌ قويٌّ يعاكس المسار"}
                    continue
                ok = []
                for k in cards:
                    pros, cons = assess(k, tr, fund.get(s), n)
                    if len(cons) > len(pros):
                        continue
                    margin = len(pros) - len(cons)
                    ok.append({**{x: k[x] for x in ("contract", "type", "strike", "expiry", "t", "dte", "ask", "bid", "mid", "cost", "px_src", "quote_at",
                                                     "spread_pct", "spread_usd", "breakeven", "need_pct", "target", "target_label", "rr", "pop", "p_touch",
                                                     "delta", "iv", "oi", "score") if x in k},
                               "gain_target": round(k["rr"] * 100), "tp30": tp30(k), "pros": pros, "cons": cons, "margin": margin,
                               "grade": "قويّة" if margin >= 4 else "جيّدة"})
                if not ok:
                    done[s] = {"at": stamp, "why": "سلبياتُه أكثر من إيجابياته"}
                    continue
                done[s] = {"at": stamp, "why": None}
                entries[s] = {"symbol": s, "name": names.get(s) or cards[0].get("name"), "price": cards[0].get("price"), "fund": fund.get(s, (None, None))[0],
                              "trend": {"state": tr["state"], "strength": tr["strength"], "ret3m": tr.get("ret3m")},
                              "news": {"impact": n.get("impact"), "event": n.get("event")} if n else None, "seen": stamp, "cards": frontier(ok)}
            scanned_now = {s for s, _ in plan}
            fresh_n = len(entries)
            for s, e in ((old or {}).get("entries") or {}).items():
                if same and s not in scanned_now and s not in held and s not in entries and _age_h(e.get("seen"), now) < KEEP_H:
                    entries[s] = e
            try:
                us = (await sessions())["us"]
            except Exception:                                     # noqa: BLE001
                us = {}
            ny = now.astimezone(NY).date()
            fs, lab = for_session(us.get("state"), ny, final)
            # ‏D771 — قيس على الخادم (2026-11-20 قبل الافتتاح): المصدرُ يُصفّر العرضَ والطلبَ خارج الجلسة فخرجت القائمةُ فارغةً (0 من 70) —
            # فبناءٌ فارغٌ خارج الجلسة لا يمحو قائمةً صالحة: تبقى ويُكتب أنّ التحديثَ ينتظر الجلسة
            if not entries and old and old.get("entries") and us.get("state") != "open":
                old["retry"] = {"at": now.isoformat(timespec="seconds"), "why": "خارج الجلسة لا عرضَ ولا طلبَ حيّين — تُحدَّث في الجلسة"}
                _save(old)
                return old
            res = {"v": V, "at": now.isoformat(timespec="seconds"), "for": fs, "label": lab, "entries": entries, "done": done,
                   "scanned": len(done), "universe": len(tr_all), "batch": len(plan), "fresh": fresh_n, "more": any(s not in done for s, _ in ranked)}
            _save(res)
            v = view(res, budget, cfg.get("sides") == "calls")
            logger.info("قائمةُ صقر: {} سهماً بعقود ({} جديداً من دفعة {}) · فُحص {} من {} ({}) · بميزانية {}: {} عقداً · امتناع {}", len(entries), fresh_n,
                        len(plan), len(done), len(ranked), lab, budget, len(v["items"]), v["excluded"])
            return res
        finally:
            _JOB.update(on=False, msg="")


def view(lst: dict | None, budget: float, calls_only: bool = False, held: set[str] | None = None) -> dict | None:
    """القائمةُ كما يراها المالكُ بميزانيته الآن (‏D775): لكلّ سهمٍ أفضلُ عقدٍ لا تتجاوز كلفتُه الميزانية، الأعلى إيجابياتٍ أوّلاً حتى الخمسين —
    وما زادت كلفةُ أرخصِ عقوده عليها يُعدّ «فوق الميزانية» بأرخصه، ومعه كم عقداً عند كلّ ميزانيةٍ جاهزة."""
    if not lst:
        return None
    held = held or set()
    entries = {s: e for s, e in (lst.get("entries") or {}).items() if s not in held}

    def pick(e: dict, b: float) -> dict | None:
        ok = [k for k in e.get("cards") or [] if k["cost"] <= b and not (calls_only and k["type"] == "put")]
        return ok[-1] if ok else None             # الحدُّ مرتّبٌ بالكلفة والدرجةُ فيه صاعدة ⇐ الأخيرُ أفضلُها
    items, over = [], []
    excl: dict[str, int] = {}
    for d in (lst.get("done") or {}).values():
        if d.get("why"):
            excl[d["why"]] = excl.get(d["why"], 0) + 1
    for s, e in entries.items():
        k = pick(e, budget)
        if k:
            items.append({**k, **{x: e.get(x) for x in ("symbol", "name", "price", "fund", "trend", "news", "seen")}})
        elif calls_only and all(c["type"] == "put" for c in e.get("cards") or []):
            excl["بيعٌ وأنت على الشراء وحده"] = excl.get("بيعٌ وأنت على الشراء وحده", 0) + 1
        else:
            over.append(min(c["cost"] for c in e["cards"]))
    if over:
        excl["فوق الميزانية"] = len(over)
    items.sort(key=lambda x: (-x["margin"], -x["score"]))
    levels = {str(b): sum(1 for e in entries.values() if pick(e, b)) for b in sorted({*LEVELS, int(budget)})}
    return {"v": lst.get("v"), "at": lst.get("at"), "for": lst.get("for"), "label": lst.get("label"), "budget": budget, "items": items[:MAX_LIST],
            "scanned": lst.get("scanned"), "universe": lst.get("universe"), "excluded": dict(sorted(excl.items(), key=lambda kv: -kv[1])),
            "cheapest": min(over) if over else None, "more": lst.get("more"), "levels": levels, "retry": lst.get("retry"),
            "snap": any(i.get("px_src") == "snap" for i in items), "calls_only": calls_only}


def job() -> dict:
    return dict(_JOB)


def due(now: datetime, clock: tuple[datetime, datetime] | None, lst: dict | None) -> tuple[bool, bool]:
    """(أتُبنى الآن؟ أهي الأخيرةُ للجلسة القادمة؟) — في الجلسة وحدها: لا قائمة (أو بصيغةٍ أقدم)، أو مضى نصفُ ساعةٍ وبقي ما لم يُفحص (‏D774)،
    أو مضت ساعتان، أو حان آخرُ بناءٍ قبل الإغلاق ولم يُبنَ."""
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
    gap = EXTEND_MIN if lst.get("more") else REFRESH_MIN     # ‏D775: يُكمل حتى يُفحص المجالُ كلُّه — فلكلّ ميزانيةٍ يختارها المالكُ عقودُها
    return (at is None or (now - at).total_seconds() >= gap * 60), False


def kick(cfg: dict, held: set[str], now: datetime, clock) -> bool:
    """من دورة صقر: يُطلق البناءَ في الخلفية إن حان — فلا تحبس الدورةُ دقائقَه."""
    go, final = due(now, clock, load())
    if not go or _LOCK.locked():
        return False
    asyncio.get_running_loop().create_task(build(cfg, held, final))
    return True
