"""مجلسُ صقر — يقرأ كلَّ شيءٍ ويربط بينه قبل أن يختار (‏D786 · بأمر المالك 2026-11-22).

قال المالك: «عملُنا القديم لا يلغيه الجديد — صقر عنده الرؤيةُ الفنيةُ والرؤيةُ المباشرةُ لسعر السوق، والقدرةُ على الأحداث والأخبار، وأضفنا عليه
قوّةَ التحليل الفنيّ ليكون أنضج… التحليلُ الفنيّ خطوةٌ من بين الخطوات: يقرأ ويحلّل مثل الصفة البشرية — المسارُ صاعدٌ أو هابطٌ أو عرضيّ،
والمستوياتُ التي منها نشتري ومنها نبيع، والشركةُ رابحةٌ أو خاسرة، وهل هذا ثاني ربعِ خسارةٍ متواصلة فتأكيدٌ للبيع أو ثاني ربعِ ربحٍ متتالٍ
ففرصةٌ للشراء، والأخبار (شركةٌ رابحةٌ أُقيل رئيسُها فهبطت رغم نتائجها)، والأحداثُ الاقتصاديةُ والعالمية، وسلوكُ المستثمرين وانطباعُهم،
والصفقاتُ غيرُ الاعتيادية، والحيتانُ أين يتمركزون ومتى يتحرّكون… ويربط بينها — المدرسةُ الحديثة لا القديمة».

فالمجلسُ سبعةُ أعضاء، لكلٍّ حكمُه بسطرٍ واحدٍ وشاهدُه بأرقامه من مصدرها في التطبيق (يوافق · يتحفّظ · يرفض · غيرُ متوفّر):
  ١ المسار — قاعدةُ صقر القديمة نفسُها: صاعدٌ فوق متوسّط 50 وأقوى من تاسي للسعوديّ، ومسارُ العقد للأمريكيّ — والارتدادُ الذي يؤكّده الرسمُ
     من منطقةِ دعمٍ في مسارٍ صاعد تحفّظٌ لا رفض (الربط: المسارُ والمستوى معاً).
  ٢ الرسم — قراءةُ الرسم كما يرسمه التطبيق (‏chart_tech): فرصةٌ بجودتها، أو لا فرصةَ الآن (تحفّظ)، أو رسمٌ يقول العكس (رفض).
  ٣ النتائج — الربعُ الأخير عن مماثله (قاعدةُ صقر القديمة)، والأرباعُ المتتالية (ربحٌ متصاعدٌ أو خسارةٌ متواصلة)، وتجاوزُ التوقّعات أو إخفاقُها.
  ٤ الأخبار — خبرُ الشركة نفسِها وإفصاحاتُها الرسمية، يقرؤها النموذجُ قراءةَ محلّل: يدعم أو يعاكس وبأيّ قوّة.
  ٥ الأحداث — السوقُ العامّ (تاسي · المخاطرُ الجيوسياسية) والأحداثُ الاقتصاديةُ عاليةُ الأثر القريبة، وموعدُ أرباح الشركة.
  ٦ الحيتان — أين المال: سيولةُ الرسم وراصدُ الحيتان فيه، والصفقاتُ الخاصة (السعوديّ)، وتدفّقُ الخيارات (الأمريكيّ): أموالُ الشراء والبيع،
     والعقودُ غيرُ الاعتيادية (حجمٌ فوق الاهتمام المفتوح) مرتّبةً بالمال لا بالعدد، وجدرانُ الاهتمام المفتوح فوق السعر وتحته.
  ٧ المحلّلون — انطباعُ بيوت الخبرة: آخرُ رأيٍ لكلّ بيتٍ في خمسة أشهر وأسعارُهم المستهدفة («أرقام» للسعوديّ، وإجماعُ ياهو للأمريكيّ).
ورفضُ عضوٍ يُسقط الصفقة (كفريق العقود ‏D776)، والتحفّظاتُ تُنقص الدرجة، وما لا مصدرَ له «غيرُ متوفّر» لا يُحسب. ثمّ «الرابط»: نموذجٌ يقرأ
الأعضاءَ معاً كما يقرؤها المحلّل — ما يجتمع وما يتعارض وأيُّه أثقل — محروساً: لا رقمَ إلّا من الشواهد، ولا يوصي بشراءٍ رفضه عضو."""
from __future__ import annotations

import asyncio
import hashlib
import json
import statistics
from datetime import date, datetime, timedelta, timezone

from loguru import logger

ROLES = ("المسار", "الرسم", "الحجم", "النتائج", "الأخبار", "الأحداث", "الحيتان", "المحلّلون")   # ‏D818: «الحجم» — الفوليوم بروفايل
W = {"ok": 9, "na": 0, "warn": -7}
ORD = {2: "الثاني", 3: "الثالث", 4: "الرابع", 5: "الخامس"}
BUY_W = ("شراء", "زيادة", "تجميع", "متفوق", "تفوق")
SELL_W = ("بيع", "تخفيض", "تقليص", "ضعيف", "أقل من")
HOLD_W = ("محايد", "احتفاظ", "حياد", "مماثل")
OUT_TAGS, IN_TAGS = ("انهيار بيعي", "تصريف بيعي"), ("اندفاع شرائي", "تجميع خفي")
OPS_DAYS, DEALS_DAYS, EVENTS_H = 150, 30, 48
UNUSUAL_PREM = 250_000.0       # عقدٌ غيرُ اعتياديٍّ يُحسب مالاً: ربعُ مليون دولارٍ فأكثر (قيس: بيعُ TSLA بسنتٍ واحدٍ 66 ألفاً — يانصيبٌ لا حوت)


def _m(role: str, v: str, say: str) -> dict:
    return {"role": role, "v": v, "say": say}


def days_ar(n: int) -> str:
    return "يوم" if n == 1 else "يومين" if n == 2 else f"{n} أيام" if 3 <= n <= 10 else f"{n} يوماً"


def money(v: float | None, ccy: str = "") -> str:
    if v is None:
        return "غير متوفّر"
    a = abs(v)
    s = f"{v / 1e9:.2f} مليار" if a >= 1e9 else f"{v / 1e6:.1f} مليون" if a >= 1e6 else f"{v:,.0f}"
    return f"{s} {ccy}".strip()


# ══ ١ المسار — قاعدةُ صقر القديمة ═══════════════════════════════════════════════════════════════════════
def m_trend(tr: dict | None, side: str, market: str, rs3: float | None = None, chart_buy: bool = False) -> dict:
    if not tr:
        return _m("المسار", "warn", "المسارُ غيرُ متوفّر — لا شموعَ كافية")
    st = tr.get("state")
    if market == "sa":
        bits, v = [], "ok"
        if st != "صاعد":
            # ‏D809 (المالك 2026-11-24): «السعوديُّ لا شراءَ إلا والسهمُ صاعد — حتى لو كان عرضيّاً لكنّه صاعد»: العرضيُّ فوق متوسّط 50 بعائدٍ
            # موجبٍ في ثلاثة أشهر صاعدٌ في جوهره ⇒ تحفّظ؛ والهابطُ والعرضيُّ المائلُ إلى الهبوط لا شراءَ فيهما
            r3 = tr.get("ret3m")
            if st == "عرضي" and tr["close"] >= tr["sma50"] and isinstance(r3, (int, float)) and r3 > 0:
                v = "warn"
                bits.append(f"عرضيٌّ مائلٌ إلى الصعود ({r3:+.1f}٪ في ثلاثة أشهر)")
            else:
                return _m("المسار", "veto", f"المسارُ {st} — لا شراءَ في السعوديّ إلا والسهمُ صاعد")
        if tr["close"] < tr["sma50"]:
            if not chart_buy:
                return _m("المسار", "veto", f"الإغلاقُ {tr['close']:,.2f} دون متوسّط 50 ({tr['sma50']:,.2f}) بلا ارتدادٍ يؤكّده الرسم")
            v = "warn"
            bits.append(f"تصحيحٌ دون متوسّط 50 ({tr['sma50']:,.2f}) يؤكّد الرسمُ ارتدادَه")
        elif st == "صاعد":
            bits.append(f"صاعدٌ فوق متوسّط 50 ({tr['sma50']:,.2f})")
        if rs3 is not None:
            if rs3 <= 0:
                if not chart_buy:
                    return _m("المسار", "veto", f"أضعفُ من تاسي في ثلاثة أشهر بـ{rs3:+.1f} نقطة")
                v = "warn"
            bits.append(f"{'أقوى' if rs3 > 0 else 'أضعف'} من تاسي بـ{rs3:+.1f} نقطة في ثلاثة أشهر")
        return _m("المسار", v, " · ".join(bits))
    want = "صاعد" if side == "long" else "هابط"
    r3 = tr.get("ret3m")
    if st == want:
        good = r3 is not None and ((side == "long" and r3 >= 5) or (side == "short" and r3 <= -5))
        return _m("المسار", "ok" if good else "warn", f"مسارٌ {want} وزخمُه {'معه' if good else 'فاتر'} ({(r3 or 0):+.0f}٪ في ثلاثة أشهر)")
    if st == "عرضي":
        return _m("المسار", "warn", "المسارُ عرضيّ — لا اتجاهَ واضحاً بعد")
    return _m("المسار", "veto", f"المسارُ {st} يعاكس {'الشراء' if side == 'long' else 'البيع'}")


# ══ ٢ الرسم ═══════════════════════════════════════════════════════════════════════════════════════════
def m_chart(cr_side: dict | None, cr_any: dict | None, side: str) -> dict:
    """‏cr_side قراءةُ الرسم لجهة الصفقة، و‏cr_any أفضلُ قراءةٍ للجهتين (ليُرى ما يقول العكس)."""
    anyr = cr_any or cr_side
    if not anyr:
        return _m("الرسم", "warn", "الرسمُ غيرُ مقروء")
    if anyr.get("setup") and anyr.get("side") != side and (anyr.get("quality") or 0) >= 50:
        return _m("الرسم", "veto", f"الرسمُ يقول العكس: {anyr['setup']} (جودة {anyr['quality']}/100) — السعرُ {anyr.get('where')}")
    r = cr_side if cr_side and cr_side.get("setup") else (anyr if anyr.get("setup") and anyr.get("side") == side else None)
    if r:
        q = r.get("quality") or 0
        return _m("الرسم", "ok" if q >= 50 else "warn", f"{r['setup']} — جودة {q}/100 ({r.get('horizon')}) · السعرُ {r.get('where')}")
    return _m("الرسم", "warn", f"لا فرصةَ في الرسم الآن — السعرُ {anyr.get('where') or 'غير متوفّر'}")


# ══ ٣ النتائج ═════════════════════════════════════════════════════════════════════════════════════════
def seq_of(q: list[dict] | None) -> dict | None:
    """الأرباعُ المتتالية من الأقدم إلى الأحدث: آخرُها ربحٌ أم خسارة، وكم ربعاً متتالياً كذلك، وهل نما آخرُها عمّا قبله."""
    ni = [x["ni"] for x in q or [] if isinstance(x.get("ni"), (int, float))]
    if len(ni) < 2:
        return None
    profit = ni[-1] > 0
    n = 0
    for v in reversed(ni):
        if (v > 0) == profit:
            n += 1
        else:
            break
    return {"profit": profit, "n": n, "growing": ni[-1] > ni[-2], "last": ni[-1], "prev": ni[-2], "count": len(ni)}


def m_results(market: str, side: str, stt: str | None, stxt: str | None, yfd: dict | None, ccy: str = "") -> dict:
    long_ = side == "long"
    if market == "sa" and long_ and stt in ("weak", "pending"):
        return _m("النتائج", "veto", stxt or "نتائجُ الربع مخيّبةٌ أو لم تصدر")
    pos = neg = 0
    bits: list[str] = []
    if market == "sa" and stxt and stt in ("strong", "neutral"):
        bits.append(stxt.rstrip("."))
        pos += 2 if stt == "strong" else 0
    sq = seq_of((yfd or {}).get("q"))
    if sq:
        n = sq["n"]
        if not sq["profit"] and n >= 2:
            if long_:
                return _m("النتائج", "veto", f"خسارةٌ للربع {ORD.get(n, n)} على التوالي ({money(sq['last'], ccy)}) — تأكيدُ ضعف")
            pos += 2
            bits.append(f"خسارةٌ للربع {ORD.get(n, n)} على التوالي")
        elif not sq["profit"]:
            neg, pos = (neg + 1, pos) if long_ else (neg, pos + 1)
            bits.append(f"خسارةٌ في آخر ربع ({money(sq['last'], ccy)})")
        elif n >= 2:
            if long_:
                pos += 1 if sq["growing"] else 0
            else:
                neg += 1
            bits.append(f"ربحٌ في {n} أرباعٍ متتالية" + (" ونموٌّ في آخرها" if sq["growing"] else " وتراجعٌ في آخرها"))
        else:
            bits.append("عاد إلى الربح في آخر ربع")
    eps = (yfd or {}).get("eps") or []
    if len(eps) >= 3:
        beats = sum(1 for e in eps if e["act"] > e["est"])
        if beats >= len(eps) - 1:
            pos, neg = (pos + 1, neg) if long_ else (pos, neg + 1)
            bits.append(f"تجاوز توقّعاتِ ربح السهم في {beats} من {len(eps)} أرباع")
        elif beats <= 1:
            pos, neg = (pos, neg + 1) if long_ else (pos + 1, neg)
            bits.append(f"أخفق في توقّعات ربح السهم في {len(eps) - beats} من {len(eps)} أرباع")
    eg = (yfd or {}).get("eg")
    if market == "us" and isinstance(eg, (int, float)):
        if eg >= 0.15:
            pos, neg = (pos + 1, neg) if long_ else (pos, neg + 1)
        elif eg <= -0.2:
            pos, neg = (pos, neg + 1) if long_ else (pos + 1, neg)
        bits.append(f"نموُّ الأرباح عن العام الماضي {eg * 100:+.0f}٪")
    if not bits:
        return _m("النتائج", "na", "النتائجُ الربعيةُ غيرُ متوفّرة")
    return _m("النتائج", "ok" if pos > neg else "warn" if neg > pos else "na", " · ".join(bits))


# ══ ٤ الأخبار ═════════════════════════════════════════════════════════════════════════════════════════
def m_news(news: dict | None, side: str) -> dict:
    if news is None:
        return _m("الأخبار", "warn", "قراءةُ الأخبار غيرُ متوفّرة الآن")
    imp, st, ev = str(news.get("impact") or ""), int(news.get("strength") or 0), str(news.get("event") or "")
    if imp in ("إيجابي", "سلبي") and st >= 1:
        good = (imp == "إيجابي") == (side == "long")
        if not good and st >= 2:
            return _m("الأخبار", "veto", f"خبرٌ يعاكس: {ev or imp}")
        return _m("الأخبار", "ok" if good else "warn", f"{'يدعمها' if good else 'يعاكسها بخفّة'}: {ev or imp}")
    return _m("الأخبار", "ok", "لا خبرَ مؤثّراً للشركة في الأيام الأخيرة")


# ══ ٥ الأحداث ═════════════════════════════════════════════════════════════════════════════════════════
def m_events(market: str, side: str, reg: dict | None, geo: dict | None, evs: list[dict] | None, earn_days: int | None,
             world: list[dict] | None = None, tone: str | None = None) -> dict:
    """‏D788: ومعها قراءةُ العالم الواحدة (‏saqr_mind) — محاورُه التي تخصّ قطاعَ الشركة: المعاكسُ القويُّ تحفّظ، والداعمُ يُذكر."""
    bits, v = [], "ok"
    if market == "sa":
        if reg:
            # ‏D809 (المالك 2026-11-24: «السوقُ هابط فاستبعد ستّاً اليوم — ما أحبّ هذه الشكلية؛ الفرصُ دائماً موجودة»): هبوطُ تاسي تحفّظٌ يُنقص
            # الدرجةَ ويصغّر الحجم — لا رفضٌ لكلّ سهمٍ صاعدٍ في سوقٍ هابط
            if reg.get("verdict") == "هابط" and side == "long":
                v = "warn"
                bits.append(f"تاسي هابط ({reg.get('close', 0):,.0f}) — الشراءُ في الصاعد وحده وبحجمٍ أصغر")
            else:
                bits.append(f"تاسي {reg.get('verdict')}")
            if reg.get("verdict") == "عرضي":
                v = "warn"
        if geo:
            if geo.get("level") == "مرتفع":
                v = "warn"                                      # ‏D809: خطرٌ عامٌّ يُنقص الدرجة — لا يُسقط كلَّ فرصة
                bits.append(f"خطرٌ جيوسياسيّ مرتفع: {geo.get('why') or ''}".strip())
            if geo.get("level") == "متوسط":
                v = "warn"
                bits.append(f"خطرٌ جيوسياسيّ متوسّط: {geo.get('why') or ''}".strip())
    long_ = side == "long"
    for t in (world or [])[:2]:
        against = (t["dir"] == "سلبي") == long_
        if against and t["strength"] >= 2:
            v = "warn"
        bits.append(("العالم يعاكسها — " if against else "العالم يدعمها — ") + f"{t['name']}: {t['why']}")
    if not world and tone in ("إيجابي", "سلبي"):
        bits.append(f"نبرةُ العالم لسوقها {tone}")
    hi = [e for e in evs or [] if e.get("impact") == "High"]
    if hi:
        v = "warn"
        bits.append("حدثٌ عالي الأثر خلال يومين: " + "، ".join(str(e.get("ar") or e.get("title")) for e in hi[:2]))
    if earn_days is not None and 0 <= earn_days <= 14:
        v = "warn"
        bits.append("إعلانُ أرباح الشركة " + ("اليوم" if earn_days == 0 else f"بعد {days_ar(earn_days)}"))
    if not bits:
        bits.append("لا حدثَ عاليَ الأثر قريباً")
    return _m("الأحداث", v, " · ".join(bits))


# ══ ٦ الحيتان ═════════════════════════════════════════════════════════════════════════════════════════
def m_whales(side: str, liq: dict | None, deals: dict | None = None, flow: dict | None = None, ccy: str = "") -> dict:
    long_ = side == "long"
    bits: list[str] = []
    pos = neg = 0
    if liq and liq.get("side") not in (None, "na"):
        tag = liq.get("tag")
        against = ((liq.get("side") == ("down" if long_ else "up")) and (liq.get("strength") or 0) >= 65) or tag in (OUT_TAGS if long_ else IN_TAGS)
        if against:
            return _m("الحيتان", "veto", f"المالُ {'يخرج' if long_ else 'يدخل'}: السيولةُ {liq.get('word')} {liq.get('level') or ''}".strip()
                      + (f" ({tag})" if tag else ""))
        bits.append(f"السيولةُ {liq.get('word')} {liq.get('level') or ''}".strip() + (f" — {tag}" if tag else ""))
        if liq.get("side") == ("up" if long_ else "down"):
            pos += 1
        elif liq.get("side") == ("down" if long_ else "up"):
            neg += 1
        if tag in (IN_TAGS if long_ else OUT_TAGS):
            pos += 1
    if deals and deals.get("n"):
        prem = deals.get("prem")
        bits.append(f"الصفقاتُ الخاصة في {DEALS_DAYS} يوماً: {deals['n']} بـ{money(deals.get('value'), ccy)}"
                    + (f" بسعرٍ {'أعلى' if prem >= 0 else 'أدنى'} من السوق {abs(prem):.1f}٪" if isinstance(prem, (int, float)) else ""))
        if isinstance(prem, (int, float)):
            if prem >= 1:
                pos += 1 if long_ else 0
            elif prem <= -3:
                neg += 1 if long_ else 0
    if flow:
        cp, pp = flow.get("cprem") or 0, flow.get("pprem") or 0
        bull = cp >= 1.5 * max(pp, 1)
        bear = pp >= 1.5 * max(cp, 1)
        bits.append(f"أموالُ الخيارات اليوم: شراءٌ {money(cp, '$')} مقابل بيعٍ {money(pp, '$')}")
        if bull:
            pos, neg = (pos + 1, neg) if long_ else (pos, neg + 1)
        elif bear:
            pos, neg = (pos, neg + 1) if long_ else (pos + 1, neg)
        u = (flow.get("unusual") or [])[:1]
        if u:
            bits.append(f"أكبرُ رهانٍ غيرِ اعتياديّ {u[0]['label']} بـ{money(u[0]['prem'], '$')}")
        wc, wp = flow.get("wall_c"), flow.get("wall_p")
        if wc or wp:
            bits.append("جدرانُ الاهتمام المفتوح: " + " · ".join(x for x in (f"شراءٌ عند {wc[0]:g}" if wc else "", f"بيعٌ عند {wp[0]:g}" if wp else "") if x))
    if not bits:
        return _m("الحيتان", "na", "حركةُ الحيتان غيرُ متوفّرة")
    return _m("الحيتان", "ok" if pos > neg else "warn" if neg > pos else "na", " · ".join(bits))


# ══ ٧ المحلّلون ═══════════════════════════════════════════════════════════════════════════════════════
def classify(rating: str | None) -> str | None:
    t = str(rating or "")
    if any(w in t for w in SELL_W):
        return "sell"
    if any(w in t for w in BUY_W):
        return "buy"
    if any(w in t for w in HOLD_W):
        return "hold"
    return None


def m_analysts(side: str, ops: dict | None, yfd: dict | None, price: float | None, ccy: str = "") -> dict:
    """‏ops من «أرقام» (السعوديّ): ‏{buy, hold, sell, target, n} — وإلّا إجماعُ ياهو."""
    long_ = side == "long"
    b = h = s = 0
    target, src = None, ""
    if ops and ops.get("n"):
        b, h, s, target, src = ops["buy"], ops["hold"], ops["sell"], ops.get("target"), f"بيوتُ الخبرة في خمسة أشهر ({ops['n']})"
    elif yfd and (yfd.get("votes") or yfd.get("rec")):
        vt = yfd.get("votes") or {}
        b, h, s = (vt.get("strongBuy") or 0) + (vt.get("buy") or 0), vt.get("hold") or 0, (vt.get("sell") or 0) + (vt.get("strongSell") or 0)
        target, src = yfd.get("target"), f"المحلّلون ({(b + h + s) or yfd.get('n') or 0})"
    n = b + h + s
    if not n and target is None:
        return _m("المحلّلون", "na", "آراءُ المحلّلين غيرُ متوفّرة")
    up = (target / price - 1) * 100 if target and price else None
    say = f"{src}: شراءٌ {b} · حيادٌ {h} · بيعٌ {s}" + (f" — المستهدفُ {target:,.2f} ({up:+.0f}٪)" if up is not None else "")
    bs, ss = (b / n if n else 0), (s / n if n else 0)
    if long_:
        v = "ok" if bs >= 0.5 and (up is None or up >= 8) else "warn" if ss >= 0.4 or (up is not None and up <= -5) else "na"
    else:
        v = "ok" if ss >= 0.4 or (up is not None and up <= -5) else "warn" if bs >= 0.6 and (up is not None and up >= 15) else "na"
    return _m("المحلّلون", v, say)


# ══ الحكم ═════════════════════════════════════════════════════════════════════════════════════════════
def judge(ev: dict) -> dict:
    """حكمُ المجلس على صفقةٍ واحدة من شواهدها — ‏{members, veto, oks, warns, score, verdict}."""
    side, market, ccy = ev.get("side", "long"), ev.get("market", "us"), ev.get("ccy", "")
    cr_side, cr_any = ev.get("cr_side"), ev.get("cr_any")
    chart_buy = bool(cr_side and cr_side.get("setup") and cr_side.get("side") == side and (cr_side.get("quality") or 0) >= 50)
    from app.services import volume_profile as VP
    mem = [m_trend(ev.get("tr"), side, market, ev.get("rs3"), chart_buy),
           m_chart(cr_side, cr_any, side),
           VP.member(ev.get("vp_rd"), side),                      # ‏D818: الطريقُ مفتوحٌ من قاعدة حجم؟ أم جدارٌ أمامه أو مطاردة؟
           m_results(market, side, ev.get("stt"), ev.get("stxt"), ev.get("yf"), ccy),
           m_news(ev.get("news"), side),
           m_events(market, side, ev.get("reg"), ev.get("geo"), ev.get("events"), ev.get("earn_days"), ev.get("world"), ev.get("tone")),
           m_whales(side, ev.get("liq"), ev.get("deals"), ev.get("flow"), ccy),
           m_analysts(side, ev.get("ops"), ev.get("yf"), ev.get("price"), ccy)]
    veto = [m for m in mem if m["v"] == "veto"]
    oks, warns = sum(1 for m in mem if m["v"] == "ok"), sum(1 for m in mem if m["v"] == "warn")
    score = 50 + sum(W.get(m["v"], 0) for m in mem)
    if mem[1]["v"] == "ok" and cr_side:
        score += ((cr_side.get("quality") or 50) - 50) / 5
    score = int(max(0, min(100, round(score))))
    verdict = "يرفض" if veto else "يوافق" if score >= 70 and warns <= 1 else "يوافق بتحفّظ"
    return {"members": mem, "veto": bool(veto), "veto_why": [f"{m['role']}: {m['say']}" for m in veto], "oks": oks, "warns": warns,
            "score": score, "verdict": verdict}


def lines(bd: dict) -> list[str]:
    """أسطرُ المجلس في أسباب الشراء — كلُّ عضوٍ بحكمه."""
    word = {"ok": "يوافق", "warn": "يتحفّظ", "veto": "يرفض", "na": "غير متوفّر"}
    return [f"{m['role']} ({word[m['v']]}): {m['say']}" for m in bd["members"]]


# ══ الرابط — النموذجُ يقرأ الأعضاءَ معاً ═══════════════════════════════════════════════════════════════
LINK_PROMPT = """أنت صقر — محلّلٌ استثماريٌّ واحدٌ محترف — تقرأ شواهدَك الثمانيةَ عن سهمٍ واحد قبل قرار {what}: المسار · الرسم · الحجم (الفوليوم بروفايل) · النتائج · الأخبار ·
الأحداث · الحيتان · المحلّلون — لكلٍّ حكمُه (يوافق · يتحفّظ · يرفض · غير متوفّر) وشاهدُه بأرقامه.
اربط بينها كما يربط المحلّلُ البشريّ لا كما يجمعها الحاسوب: ما الذي يجتمع؟ وما الذي يتعارض (نتائجُ قويةٌ وخبرٌ جوهريٌّ سلبيّ، أو رسمٌ يدعو للشراء
وحيتانٌ تخرج، أو مسارٌ صاعدٌ وحدثٌ عالي الأثر غداً)؟ وأيُّها أثقلُ الآن ولماذا؟
القواعدُ الصارمة:
١) لا تذكر رقماً ليس في الشواهد، ولا حدثاً ليس فيها.
٢) إن رفض شاهدٌ فلا يكون القرارُ «{buy}» — قل لماذا.
٣) شرطُ التغيير مشروطٌ بمستوىً أو حدثٍ من الشواهد، لا وعدٌ ولا يقين.
٤) عربيةٌ فصحى موجزة — وصقرٌ واحدٌ يتكلّم: لا «مجلس» ولا «عضو» ولا «أعضاء» في كلامك.
أعد JSON فقط: {{"decision": "{buy}" أو "انتظار" أو "تجنّب", "confidence": "مرتفعة" أو "متوسطة" أو "منخفضة",
 "link": "جملتان أو ثلاث تربط الشواهد", "conflict": "أهمُّ تعارضٍ أو ''", "watch": "ما الذي يغيّر الحكم"}}
الشواهد:
"""


def one_voice(t: str) -> str:
    """‏D807 (المالك 2026-11-24): «لا أريد الإشارةَ إلى صقر بأنّه مجلس — "استبعدها مجلسُ صقر ورفضها عضو": إيش الكلام الفاضي هذا؟ صقرٌ واحد»."""
    import re as _re
    for a, b in (("مجلسُ صقر", "صقر"), ("مجلسَ صقر", "صقر"), ("مجلسِ صقر", "صقر"), ("مجلس صقر", "صقر"), ("المجلسُ", "صقر"), ("المجلسَ", "صقر"),
                 ("المجلسِ", "صقر"), ("المجلس", "صقر"), ("الأعضاءُ", "الشواهدُ"), ("الأعضاءَ", "الشواهدَ"), ("الأعضاءِ", "الشواهدِ"), ("الأعضاء", "الشواهد"),
                 ("أعضاءُ", "شواهدُ"), ("أعضاء", "شواهد"), ("عضوٌ", "شاهدٌ"), ("عضواً", "شاهداً"), ("عضوٍ", "شاهدٍ")):
        t = t.replace(a, b)
    return _re.sub(r"\bعضو\b", "شاهد", t)



async def link(sym: str, name: str | None, market: str, side: str, bd: dict, chart: dict | None = None, price: float | None = None) -> dict | None:
    """«الرابط»: قراءةُ النموذج للمجلس كلِّه — محروسةً بأرقام الشواهد؛ وتعذّرُه None (لا قراءةَ بديلة)."""
    from app.services import cache
    from app.services import research_desk as RD
    from app.services.chart_read import clean_text
    buy = "شراء" if side == "long" else "بيع"
    ctx = {"symbol": sym, "name": name or "", "market": "السعوديّ" if market == "sa" else "الأمريكيّ", "side": buy, "price": price,
           "evidence": [{"role": m["role"], "verdict": {"ok": "يوافق", "warn": "يتحفّظ", "veto": "يرفض", "na": "غير متوفّر"}[m["v"]], "say": m["say"]}
                        for m in bd["members"]],
           "saqr": {"verdict": bd["verdict"], "score": bd["score"]}}
    if chart:
        ctx["chart"] = {k: chart.get(k) for k in ("setup", "where", "entry", "target", "stop", "rr", "horizon") if chart.get(k) is not None}
        ctx["zones"] = [{"name": z.get("name"), "lo": z.get("lo"), "hi": z.get("hi")} for z in chart.get("zones") or []]
    # ‏D833 (المالك: «خلِّ صقر يتعلّم من المكتبة… داخليةً لا تخرج عندي»): علمُه من كتب المالك يزن به الشواهد — خارجَ الشواهد وأرقامِها (فلا يُقتبس
    # منه رقمٌ يمرّ على حارس الأرقام)، وبصمتُه في مفتاح الذاكرة فيتجدّد الحكمُ متى تعلّم جديداً
    try:
        from app.services import library_wisdom as LW
        lib, lib_v = LW.saqr_block()
    except Exception:                                             # noqa: BLE001
        LW, lib, lib_v = None, "", ""
    key = "council:link:" + hashlib.md5((json.dumps(ctx, ensure_ascii=False, sort_keys=True, default=str) + lib_v).encode()).hexdigest()[:16]
    hit = cache.get(key)
    if hit is not None:
        return hit or None
    head = LINK_PROMPT.format(what="الشراء" if side == "long" else "البيع", buy=buy)
    if lib:
        head = head.replace("الشواهد:\n", lib + "الشواهد:\n")
    try:
        obj = await RD._gemini([{"text": head + json.dumps(ctx, ensure_ascii=False, default=str)}], max_tokens=900, temperature=0.2, deadline=75.0)
    except Exception as e:                                        # noqa: BLE001
        logger.debug("مجلسُ صقر/الرابط {}: {}", sym, type(e).__name__)
        obj = None
    if not isinstance(obj, dict):
        return None
    pool = _numbers(ctx)
    out = {"decision": obj.get("decision") if obj.get("decision") in (buy, "انتظار", "تجنّب") else "انتظار",
           "confidence": obj.get("confidence") if obj.get("confidence") in ("مرتفعة", "متوسطة", "منخفضة") else "منخفضة", "dropped": 0}
    if bd["veto"] and out["decision"] == buy:
        out["decision"] = "تجنّب"
    titles = LW.saqr_titles() if (LW and lib) else []
    for f in ("link", "conflict", "watch"):
        t = clean_text(obj.get(f), pool) if obj.get(f) else ""
        if obj.get(f) and t is None:
            out["dropped"] += 1
        t = LW.scrub(t or "", titles) if (LW and lib) else (t or "")     # ‏D833: العلمُ داخليّ — لا كتابَ ولا مكتبةَ في كلامه
        out[f] = one_voice(t)
    if not out["link"]:
        return None
    cache.set(key, out, 6 * 3600)
    return out


def _numbers(x) -> list[float]:
    """أرقامُ الشواهد المسموحُ ذكرُها في «الرابط»."""
    import re
    out: list[float] = []

    def walk(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            out.append(float(v))
        elif isinstance(v, str):
            for m in re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?", v):
                try:
                    out.append(float(m.replace(",", "")))
                except ValueError:
                    pass
        elif isinstance(v, dict):
            for w in v.values():
                walk(w)
        elif isinstance(v, (list, tuple)):
            for w in v:
                walk(w)
    walk(x)
    return out


# ══ الشواهد — من مصادرها في التطبيق (قِيست على الخادم: ‏saqr_council_door.py) ═══════════════════════════════════
def _raw(v):
    if isinstance(v, dict):
        v = v.get("raw")
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def parse_yf(r: dict | None) -> dict | None:
    """ياهو ‏quoteSummary: الإيرادُ والربحُ ربعياً، ومفاجآتُ ربح السهم، ورأيُ المحللين — قيس للسوقين (‏2222.SR · NVDA)."""
    if not isinstance(r, dict):
        return None
    fq = (((r.get("earnings") or {}).get("financialsChart") or {}).get("quarterly")) or []
    q = [{"label": x.get("date"), "rev": _raw(x.get("revenue")), "ni": _raw(x.get("earnings"))} for x in fq if _raw(x.get("earnings")) is not None]
    eps = []
    for x in ((r.get("earningsHistory") or {}).get("history")) or []:
        a, e = _raw(x.get("epsActual")), _raw(x.get("epsEstimate"))
        if a is not None and e is not None:
            qd = x.get("quarter")
            eps.append({"date": qd.get("fmt") if isinstance(qd, dict) else None, "act": a, "est": e, "sur": _raw(x.get("surprisePercent"))})
    fd = r.get("financialData") or {}
    t0 = ((((r.get("recommendationTrend") or {}).get("trend")) or [{}])[0]) or {}
    return {"q": q[-4:], "eps": eps[-4:], "rec": fd.get("recommendationKey"), "target": _raw(fd.get("targetMeanPrice")),
            "n": _raw(fd.get("numberOfAnalystOpinions")), "px": _raw(fd.get("currentPrice")), "eg": _raw(fd.get("earningsGrowth")),
            "rg": _raw(fd.get("revenueGrowth")), "votes": {k: t0.get(k) for k in ("strongBuy", "buy", "hold", "sell", "strongSell") if isinstance(t0.get(k), int)}}


async def yf(ysym: str) -> dict | None:
    from app.services import cache
    from app.services.market_data import market_service as M
    from app.services.usage_tracker import can_call, record
    ck = f"council:yf:{ysym}"
    hit = cache.get(ck)
    if hit is not None:
        return hit or None
    if not can_call("yahoo"):
        return None
    record("yahoo")
    try:
        r = await asyncio.wait_for(M._yahoo()._quote_summary(ysym, "earnings,earningsHistory,financialData,recommendationTrend"), 20)
    except Exception:                                             # noqa: BLE001
        r = None
    out = parse_yf(r)
    cache.set(ck, out or {}, 24 * 3600 if out else 1800)
    return out


def deals_of(rows: list[dict], price: float | None, today: date | None = None, days: int = DEALS_DAYS) -> dict | None:
    """الصفقاتُ الخاصة للشركة في ‏`days` يوماً: عددُها وقيمتُها وعلاوتُها على السعر (سعرُها الموزون بالكمّية إلى سعر السوق الآن)."""
    today = today or datetime.now(timezone.utc).date()
    keep = []
    for d in rows or []:
        at = str(d.get("at") or "")
        try:
            dd = datetime.strptime(at, "%d-%m-%Y").date() if "-" in at and len(at.split("-")[0]) == 2 else date.fromisoformat(at[:10])
        except ValueError:
            continue
        if (today - dd).days <= days:
            keep.append(d)
    if not keep:
        return None
    q = sum(d.get("quantity") or 0 for d in keep)
    vwap = sum((d.get("price") or 0) * (d.get("quantity") or 0) for d in keep) / q if q else None
    return {"n": len(keep), "value": sum(d.get("value") or 0 for d in keep), "vwap": vwap,
            "prem": (vwap / price - 1) * 100 if vwap and price else None}


def ops_of(rows: list[dict], today: date | None = None, days: int = OPS_DAYS) -> dict | None:
    """آراءُ بيوت الخبرة: آخرُ رأيٍ لكلّ بيتٍ في ‏`days` يوماً — مصنّفاً (شراء · حياد · بيع) ووسيطُ المستهدف."""
    today = today or datetime.now(timezone.utc).date()
    latest: dict[str, dict] = {}
    for r in rows or []:
        try:
            dd = date.fromisoformat(str(r.get("date"))[:10])
        except ValueError:
            continue
        if (today - dd).days > days:
            continue
        h = str(r.get("house") or "")
        if h and (h not in latest or str(r["date"]) > str(latest[h]["date"])):
            latest[h] = r
    if not latest:
        return None
    cls = [classify(r.get("rating")) for r in latest.values()]
    tg = [r["target"] for r in latest.values() if isinstance(r.get("target"), (int, float)) and r["target"] > 0]
    return {"n": len(latest), "buy": cls.count("buy"), "hold": cls.count("hold"), "sell": cls.count("sell"),
            "target": statistics.median(tg) if tg else None}


def flow_of(chains: list[dict], S: float | None) -> dict | None:
    """تدفّقُ الخيارات من سلاسل الآجال القريبة: أموالُ الشراء والبيع اليوم (الحجمُ × آخرُ سعر × 100)، والعقودُ غيرُ الاعتيادية (حجمٌ فوق
    1.5× الاهتمام المفتوح) مرتّبةً بالمال، وأكبرُ اهتمامٍ مفتوحٍ للشراء فوق السعر وللبيع تحته."""
    if not chains or not S:
        return None
    cprem = pprem = 0.0
    unusual, wc, wp = [], {}, {}
    for ch in chains:
        for side, rows in (("C", ch.get("calls") or []), ("P", ch.get("puts") or [])):
            for o in rows:
                v, oi, last, k = o.get("volume") or 0, o.get("oi") or 0, o.get("last") or 0, o.get("strike")
                prem = v * last * 100
                if side == "C":
                    cprem += prem
                    if k and k >= S:
                        wc[k] = wc.get(k, 0) + oi
                else:
                    pprem += prem
                    if k and k <= S:
                        wp[k] = wp.get(k, 0) + oi
                if v >= 500 and v > 1.5 * max(oi, 1) and prem >= UNUSUAL_PREM:
                    unusual.append({"contract": o.get("contract"), "side": side, "vol": v, "oi": oi, "prem": prem,
                                    "label": f"{'شراء' if side == 'C' else 'بيع'} {k:g}"})
    if not cprem and not pprem:
        return None
    unusual.sort(key=lambda x: -x["prem"])
    top = lambda d: max(d.items(), key=lambda kv: kv[1]) if d else None   # noqa: E731
    return {"cprem": cprem, "pprem": pprem, "unusual": unusual[:4], "wall_c": top(wc), "wall_p": top(wp)}


async def flow(sym: str) -> dict | None:
    from app.services import cache
    from app.services.options_chain import chain
    ck = f"council:flow:{sym}"
    hit = cache.get(ck)
    if hit is not None:
        return hit or None
    try:
        base = await asyncio.wait_for(chain(sym), 20)
    except Exception:                                             # noqa: BLE001
        base = None
    if not base:
        cache.set(ck, {}, 1800)
        return None
    chs = [base]
    for e in (base.get("expirations") or [])[:3]:
        if e["t"] != base.get("expiry"):
            try:
                ch = await asyncio.wait_for(chain(sym, e["t"]), 20)
            except Exception:                                     # noqa: BLE001
                ch = None
            if ch:
                chs.append(ch)
        if len(chs) >= 3:
            break
    out = flow_of(chs, base.get("price"))
    cache.set(ck, out or {}, 1800)
    return out


async def events(market: str, hours: int = EVENTS_H) -> list[dict]:
    """الأحداثُ الاقتصاديةُ عاليةُ الأثر القادمة خلال ‏`hours` ساعة لسوقها — ‏[] عند التعذّر."""
    from app.services import cache
    from app.services import econ_calendar as EC
    ck = f"council:events:{market}"
    hit = cache.get(ck)
    if hit is not None:
        return hit
    try:
        w = await asyncio.wait_for(EC.week(with_reading=False, market=market), 25)
    except Exception:                                             # noqa: BLE001
        return []
    lim = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    out = [{"ar": e.get("ar"), "title": e.get("title"), "at": e.get("at"), "impact": e.get("impact")} for e in w.get("events") or []
           if not e.get("past") and e.get("impact") == "High" and str(e.get("at") or "") <= lim]
    cache.set(ck, out, 1800)
    return out


async def heads_sa(sym: str, name: str | None) -> list[dict]:
    """أخبارُ الشركة السعودية: إفصاحاتُها الرسميةُ في ثلاثين يوماً («أرقام») وعناوينُها في عشرة أيام («جوجل نيوز») — مخبّأةٌ ساعتين."""
    from app.services import cache
    ck = f"council:heads:sa:{sym}"
    hit = cache.get(ck)
    if hit is not None:
        return hit
    out: list[dict] = []
    floor = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    try:
        from app.services.argaam_calendar import fetch_company_page
        pg = await asyncio.wait_for(fetch_company_page(sym), 25)
        for d in (pg or {}).get("disclosures") or []:
            if d.get("title") and str(d.get("date") or "") >= floor:
                out.append({"at": d.get("date"), "title": d["title"], "src": "إفصاح — أرقام"})
    except Exception as e:                                        # noqa: BLE001
        logger.debug("مجلسُ صقر/إفصاحات {}: {}", sym, type(e).__name__)
    if name:
        try:
            from app.services.news_fetcher import _collect
            for it in await asyncio.wait_for(_collect([f'"{name}" سهم'], "أسواق", max_age_days=10, tags=[sym], count=10), 25):
                out.append({"at": str(it.get("published") or "")[:10], "title": it.get("headline"), "src": it.get("source") or ""})
        except Exception as e:                                    # noqa: BLE001
            logger.debug("مجلسُ صقر/عناوين {}: {}", sym, type(e).__name__)
    out = sorted((x for x in out if x.get("title")), key=lambda x: str(x["at"]), reverse=True)[:10]
    cache.set(ck, out, 2 * 3600)
    return out


async def heads_us(sym: str) -> list[dict]:
    from app.services import option_picks as OP
    try:
        return [{"at": h["at"], "title": h["title"], "src": h.get("publisher") or ""} for h in await asyncio.wait_for(OP.headlines(sym), 20)]
    except Exception:                                             # noqa: BLE001
        return []


NEWS_PROMPT = """أنت محلّلُ أسهمٍ {mk}. لكلّ شركةٍ أدناه عناوينُ أخبارها وإفصاحاتُها الأخيرة. اقرأها وحدها — لا تُضف معلومةً من خارجها — وقدّر أثرَها
على سهم الشركة في الأسابيع القادمة:
- impact: "إيجابي" أو "سلبي" أو "محايد"
- strength: 0 (لا حدث) · 1 (أثرٌ طفيف) · 2 (حدثٌ مهمّ: نتائجُ مفاجئة، ترقيةٌ أو تخفيضٌ مؤثّر، عقدٌ أو صفقةٌ كبيرة، غرامة) · 3 (حدثٌ جوهريّ: إقالةُ
  رئيسٍ تنفيذيّ أو استقالتُه، تحقيقٌ أو دعوى كبرى، خسارةُ عميلٍ رئيسيّ، استحواذ، إيقافُ التداول)
- event: جملةٌ عربيةٌ قصيرةٌ تذكر الحدثَ كما في العنوان وتاريخَه (أو "" إن لا حدث)
وعناوينُ تعليقات الأسعار اليومية («سهمُ كذا اليوم عند…») ليست أحداثاً.
JSON فقط: {{"SYM": {{"impact": "...", "strength": 0, "event": "..."}}}} — اذكر الرموزَ ذاتَ الحدث وحدها؛ ومن لم تذكره فلا حدثَ له.

"""


async def read_news(market: str, heads: dict[str, list[dict]], names: dict[str, str] | None = None) -> dict[str, dict | None]:
    """قراءةُ النموذج لأخبار الشركات دفعاتٍ من عشرين — مخبّأةٌ ساعتين لكلّ رمز؛ ودفعةٌ تعذّرت فرموزُها «غير متوفّرة» (None)،
    ورمزٌ بلا عناوين لا حدثَ له."""
    from app.services import cache
    from app.services import research_desk as RD
    out: dict[str, dict | None] = {}
    todo = {}
    for s, h in heads.items():
        hit = cache.get(f"council:news:{market}:{s}")
        if hit is not None:
            out[s] = hit
        elif not h:
            out[s] = {"impact": "محايد", "strength": 0, "event": ""}
        else:
            todo[s] = h
    keys = list(todo)
    for i in range(0, len(keys), 20):
        chunk = keys[i:i + 20]
        body = "\n\n".join(f"{s}{' — ' + names[s] if names and names.get(s) else ''}:\n" + "\n".join(f"  [{x.get('at')}] {x.get('title')} ({x.get('src')})" for x in todo[s][:8])
                           for s in chunk)
        try:
            got = await RD._gemini([{"text": NEWS_PROMPT.format(mk="سعوديٌّ محترف" if market == "sa" else "أمريكيٌّ محترف") + body}],
                                   max_tokens=2500, temperature=0.1)
        except Exception as e:                                    # noqa: BLE001
            logger.warning("مجلسُ صقر/الأخبار: {}", type(e).__name__)
            got = None
        for s in chunk:
            if not isinstance(got, dict):
                out[s] = None
                continue
            r = got.get(s) if isinstance(got.get(s), dict) else {}
            stv = r.get("strength")
            rec = {"impact": r.get("impact") if r.get("impact") in ("إيجابي", "سلبي", "محايد") else "محايد",
                   "strength": max(0, min(3, int(stv))) if isinstance(stv, (int, float)) or str(stv or "").isdigit() else 0,
                   "event": str(r.get("event") or "")[:220]}
            out[s] = rec
            cache.set(f"council:news:{market}:{s}", rec, 2 * 3600)
    return out


async def context(market: str) -> dict:
    """سياقُ السوق مرّةً للمجلس كلِّه: تاسي والمخاطرُ الجيوسياسية (السعوديّ)، والأحداثُ عاليةُ الأثر القادمة."""
    ctx: dict = {"events": await events(market)}
    try:                                                          # ‏D788: قراءةُ العالم الواحدة للسوقين
        from app.services import saqr_mind as SM
        ctx["world"] = await SM.world()
    except Exception:                                             # noqa: BLE001
        ctx["world"] = None
    if market == "sa":
        from app.services import saqr_sa as SA
        try:
            ctx["reg"] = await SA.regime()
        except Exception:                                         # noqa: BLE001
            ctx["reg"] = None
        try:
            ctx["geo"] = await SA.geo()
        except Exception:                                         # noqa: BLE001
            ctx["geo"] = None
    return ctx


async def collect(market: str, cands: list[dict], ctx: dict, conc: int = 4, flow_max: int = 20) -> dict[str, dict]:
    """شواهدُ المجلس لكلّ مرشّح — ‏cands: ‏[{symbol, name, side, price, tr, rs3, cr_side, cr_any, liq, stt, stxt, earn_days}] — يُكمَل لكلٍّ:
    النتائجُ والمحلّلون (ياهو · «أرقام»)، والأخبار (تُقرأ دفعةً)، والصفقاتُ الخاصة (السعوديّ)، وتدفّقُ الخيارات (الأمريكيّ لأوّل ‏flow_max)."""
    from app.services import analyst_opinions as AO
    from app.services import special_deals as SD
    sem = asyncio.Semaphore(conc)
    evs: dict[str, dict] = {}
    heads: dict[str, list[dict]] = {}
    names = {c["symbol"]: c.get("name") or "" for c in cands}
    order = {c["symbol"]: i for i, c in enumerate(cands)}

    async def one(c):
        s = c["symbol"]
        async with sem:
            yfd = await yf(f"{s}.SR" if market == "sa" else s)
            h = await (heads_sa(s, c.get("name")) if market == "sa" else heads_us(s))
            fl = await flow(s) if market == "us" and order[s] < flow_max else None
            try:                                                  # ‏D818: بروفايلُ الحجم بنافذة أفق السهم (شموعُ الساعة لنحو ثلاثة أشهر)
                from app.services import volume_profile as VP
                vp = await VP.for_symbol(s, None, market == "sa")
                vp_rd = VP.read(vp, c.get("price"), c.get("side", "long"))
            except Exception:                                     # noqa: BLE001
                vp, vp_rd = None, None
        heads[s] = h
        ev = {**c, "market": market, "ccy": "ريال" if market == "sa" else "$", "yf": yfd, "flow": fl, "events": ctx.get("events"), "vp": vp, "vp_rd": vp_rd,
              "reg": ctx.get("reg"), "geo": ctx.get("geo")}
        try:                                                      # ‏D788: محاورُ العالم التي تخصّ قطاعَ الشركة
            from app.services import saqr_mind as SM
            w = ctx.get("world")
            ev["world"] = SM.hits(w, market, SM.sector_of(s, market, c.get("sector")))
            ev["tone"] = (w or {}).get("tone_sa" if market == "sa" else "tone_us")
        except Exception:                                         # noqa: BLE001
            ev["world"], ev["tone"] = [], None
        if market == "sa":
            ev["deals"] = deals_of(SD.for_symbol(s), c.get("price"))
            ev["ops"] = ops_of(AO.for_symbol(s))
        evs[s] = ev
    await asyncio.gather(*(one(c) for c in cands))
    news = await read_news(market, heads, names)
    for s, ev in evs.items():
        ev["news"] = news.get(s)
        ev["heads"] = (heads.get(s) or [])[:5]
    return evs


async def chart_sa(sym: str) -> tuple[dict | None, dict | None, dict | None]:
    """رسمُ الشركة السعودية كما يرسمه التطبيق (شموعُ الرسم المخبّأة) ⇐ (قراءةُ الشراء، أفضلُ قراءةٍ للجهتين، مسارُ صقر) — مخبّأةٌ نصفَ ساعة."""
    from app.services import cache
    from app.services import chart_tech as T
    from app.services import option_picks as OP
    from app.services.market_data import market_service as M
    ck = f"council:chart:sa:{sym}"
    hit = cache.get(ck)
    if hit is not None:
        return tuple(hit) if hit else (None, None, None)
    try:
        bars = T.clean(await asyncio.wait_for(M.get_bars(f"{sym}.SR", "1d"), 25))[-520:]
    except Exception:                                             # noqa: BLE001
        bars = []
    if len(bars) < 60:
        return None, None, None
    out = (T.read(bars, saudi=True, longs_only=True), T.read(bars, saudi=True, longs_only=False), OP.trend_of(bars))
    cache.set(ck, list(out), 1800)
    return out


def earn_days(sym: str, today: date | None = None) -> int | None:
    """أيامٌ إلى إعلان أرباح الشركة الأمريكية — من مجال صقر (‏saqr_universe: ‏earnings_release_next_date) إن كان مخبّأً."""
    from app.services import cache
    tr = cache.get(f"saqr:tr:{sym}") or {}
    try:
        return (date.fromisoformat(str(tr.get("earn"))[:10]) - (today or datetime.now(timezone.utc).date())).days if tr.get("earn") else None
    except ValueError:
        return None


def compact(bd: dict) -> dict:
    """ما يُحفظ ويُعرض من حكم المجلس."""
    return {"verdict": bd["verdict"], "score": bd["score"], "veto": bd["veto"], "oks": bd["oks"], "warns": bd["warns"],
            "members": [{"role": m["role"], "v": m["v"], "say": m["say"]} for m in bd["members"]], "veto_why": bd["veto_why"]}


# ══ ‏D832 — بابُ صقر الواحد للدخول الآليّ في السوقين ══
# المالك (2026-11-25): «أريد صقر سواء الأمريكيّ أو السعوديّ مستوى النجاح والاختيار في ليفل موحّد — صقرٌ واحد… لا أريد إلا اللونَ الأخضر».
# قيس على الخادم قبله: الأمريكيُّ الآليُّ اشترى أعلى توصيات «عقود الخيارات» درجةً (49 من 100) بلا حكم صقر ولا حدِّ النجاح الذي ضبطه المالك (90٪)؛
# والسعوديُّ يقبل «يوافق بتحفّظ» ويشتري إن تعذّرت القراءةُ الأخيرة. فالبابُ واحدٌ للسوقين لحظةَ الشراء الآليّ:
#   ١ المنبع: فرصُ اليوم من مسح السوق كلِّه — الشواهدُ الثمانيةُ نفسُها ومنها الحجم — بموافقةٍ كاملةٍ واتّجاهِ الصفقة نفسِه.
#   ٢ حكمٌ جديدٌ لحظةَ الشراء: «يوافق» كاملةً (لا «بتحفّظ»)، وقراءتُه الأخيرةُ «شراء» (أو «بيع» للهبوط) — وتعذّرُها يمنع: لا دخولَ بشاهدٍ ناقص.
#   ٣ نسبةُ النجاح لا تقلّ عن حدّ المالك الواحد للسوقين (‏saqr_trader.win_floor).
AUTO_VERDICT = "يوافق"


def gate_why(bd: dict, lk: dict | None, side: str, need_link: bool = True) -> str | None:
    """سببُ امتناع الدخول الآليّ — أو None إن اجتاز الباب."""
    buy = "شراء" if side == "long" else "بيع"
    if bd.get("veto"):
        return "صقر لا يشتريه الآن — " + " · ".join(bd.get("veto_why") or [])
    if bd.get("verdict") != AUTO_VERDICT:
        return f"حكمُ صقر «{bd.get('verdict')}» ({bd.get('score')}/100 · {bd.get('warns')} تحفّظ) — الدخولُ الآليُّ بموافقته الكاملة وحدها"
    if not need_link:
        return None
    if not lk:
        return "قراءةُ صقر الأخيرة غيرُ متوفّرة الآن — لا دخولَ آليّاً بشاهدٍ ناقص"
    if lk.get("decision") != buy:
        return f"قراءةُ صقر الأخيرة: {lk.get('decision')} — {lk.get('link') or ''}".rstrip(" —")
    return None


def opportunities(market: str) -> dict[str, dict]:
    """فرصُ اليوم التي وافق عليها صقرٌ موافقةً كاملة — منبعُ الدخول الآليّ في السوقين؛ وما قالت قراءتُه الأخيرةُ فيه غيرَ الشراء لا يدخل.
    ‏{رمز: الفرصة} — ولا مسحَ حديث ⇒ لا شيء (فلا دخولَ آليّ)."""
    from app.services import chart_scan as CS
    d = CS.fresh(market) or {}
    out = {}
    for x in d.get("items") or []:
        cn, lk = x.get("council") or {}, x.get("link") or {}
        buy = "شراء" if x.get("side") == "long" else "بيع"
        if cn.get("verdict") == AUTO_VERDICT and not cn.get("veto") and (not lk or lk.get("decision") == buy):
            out[x["symbol"]] = x
    return out


async def confirm(market: str, cands: list[dict], ctx: dict | None = None) -> dict[str, dict]:
    """حكمُ صقر الجديد لحظةَ الشراء على مرشّحين من الفرص — ‏{رمز: {bd, lk, why}}: why=None ⇐ اجتاز الباب."""
    if not cands:
        return {}
    ctx = ctx if ctx is not None else await context(market)
    evs = await collect(market, cands, ctx)
    out = {}
    for c in cands:
        s = c["symbol"]
        bd = judge(evs[s])
        why = gate_why(bd, None, c.get("side", "long"), need_link=False)
        lk = None
        if not why:
            lk = await link(s, c.get("name"), market, c.get("side", "long"), bd, chart=c.get("cr_side"), price=c.get("price"))
            why = gate_why(bd, lk, c.get("side", "long"))
        out[s] = {"bd": bd, "lk": lk, "why": why, "ev": evs[s]}
    return out
