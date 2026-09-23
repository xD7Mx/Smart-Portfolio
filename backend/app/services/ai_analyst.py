"""
المحلّل — الطبقة التي تُحوّل المساعد من رادٍّ على أسئلةٍ عامة إلى محلّلٍ يقرأ
كل ما في التطبيق عن شركةٍ بعينها أو عن السوق، ثم يُصدر رأياً مبنيّاً.

لماذا وُجدت: التطبيق يحتوي تقييماً وحوكمةً وفنيّاً وتوزيعاتٍ ومفكرةَ أحداثٍ
لكل شركة في تداول — وكان المساعد لا يمسّ شيئاً من ذلك. يُسأل عن شركةٍ في
حيازاتك فيردّ بجدول أرقامٍ عام أو بلا شيء.

القواعد التي تحكم كل إجابةٍ هنا:
  • **لا رقم بلا مصدر داخل التطبيق.** ما لا يوجد يُقال «غير متوفّر» صراحةً.
  • **الحكم يُبنى ولا يُلقى.** كل خلاصة تُذكر أسبابها المرقّمة قبلها.
  • **لا تنصّل ولا وعظ.** المالك مستثمرٌ محترف، والجملة الإنشائية إهدارٌ لوقته.
  • **الأرقام لاتينية، والنصّ عربية فصيحة.** بلا رموز تنسيق.
"""
from __future__ import annotations

import datetime as _dt
import json
import os

from loguru import logger

_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MACRO_PATH = os.path.join(_DIR, "data", "macro_calendar.json")


# ── أدوات عرض ────────────────────────────────────────────────────────────
def _f(v, unit: str = "", d: int = 2) -> str:
    if v is None or v == "":
        return "غير متوفّر"
    try:
        x = float(v)
    except (TypeError, ValueError):
        return str(v)
    txt = f"{round(x, d):,.{d}f}".rstrip("0").rstrip(".") if d else f"{int(round(x)):,}"
    return f"{txt}{unit}"


def _pm(v, unit: str = "%") -> str:
    """رقمٌ بإشارته — الإشارة جزءٌ من المعلومة لا زينة."""
    if v is None:
        return "غير متوفّر"
    try:
        x = float(v)
    except (TypeError, ValueError):
        return str(v)
    return f"{'+' if x >= 0 else ''}{_f(x)}{unit}"


def _big(v) -> str:
    """مبلغٌ كبير بصيغةٍ تُقرأ: مليار/مليون."""
    if v is None:
        return "غير متوفّر"
    try:
        x = float(v)
    except (TypeError, ValueError):
        return str(v)
    a = abs(x)
    if a >= 1e9:
        return f"{_f(x / 1e9)} مليار ريال"
    if a >= 1e6:
        return f"{_f(x / 1e6)} مليون ريال"
    return f"{_f(x)} ريال"


def sharia_ar(status) -> str:
    """الحالة الشرعية بالعربية. القيمة المخزَّنة رمزٌ داخلي (COMPLIANT /
    NON_COMPLIANT) وكان المساعد يطبعها كما هي، فتخرج إجابةٌ عربية وفيها
    كلمةٌ إنجليزية. التخزين لا يتغيّر — العرض وحده يُعرَّب، فلا يُمَسّ ما
    تعتمد عليه الحوكمة والتنقية من مطابقةٍ على الرمز."""
    return {
        "COMPLIANT": "متوافق شرعاً",
        "NON_COMPLIANT": "غير متوافق شرعاً",
        "MIXED": "مختلط",
        "UNKNOWN": "غير معروف",
    }.get(str(status or "").strip().upper(), str(status or ""))


def _sec(title: str, lines: list[str]) -> str:
    """قسمٌ لا يُطبع إلا إذا حمل معلومة. سطرٌ كلّه «غير متوفّر» ليس معلومة —
    وقسمٌ عنوانه «التقييم» تحته سطرٌ واحد فارغ يوحي بعجز التطبيق لا بغياب
    بيانات شركةٍ بعينها."""
    body = [ln for ln in lines if ln and "غير متوفّر" not in ln]
    if not body:
        return ""
    return f"{title}\n" + "\n".join(f"  {ln}" for ln in body)


# ── التقويم الاقتصادي ────────────────────────────────────────────────────
def load_macro_calendar() -> dict:
    """تقويمٌ **مخزَّن** لا مُستنبَط: مواعيد لجنة السوق المفتوحة الأمريكية
    وما يشبهها. سبب أهميته للسوق السعودي أن الريال مربوطٌ بالدولار، فقرار
    الفائدة الأمريكي يمرّ إلى «ساما» في اليوم نفسه غالباً ويصيب البنوك
    والعقار والتمويل مباشرةً.

    يُقرأ من ملفٍ قابلٍ للتحديث لا من ذاكرة النموذج، ويُعرض دائماً موسوماً
    بأنه تقويم مخزَّن مع تاريخ آخر تحديثٍ له — فإن قدُم، ظهر قِدَمه للمالك
    بدل أن يُقدَّم كحقيقةٍ راهنة."""
    try:
        with open(_MACRO_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def next_macro_events(limit: int = 3) -> list[dict]:
    cal = load_macro_calendar()
    today = _dt.date.today().isoformat()
    out = []
    for ev in cal.get("events") or []:
        d = str(ev.get("date") or "")
        if d >= today:
            out.append(ev)
    out.sort(key=lambda e: e.get("date") or "")
    return out[:limit]


def _ev_date(e: dict) -> str:
    """تاريخ الحدث. المفكرة تُعيد أيضاً صفّاً نصّياً يقول «لا توجد إجراءات» —
    وهو ليس حدثاً؛ بلا تاريخٍ يُستبعَد، وإلا ظهر في القائمة سطرٌ بلا تاريخ
    يقول «لا يوجد» وكأنه موعدٌ قادم."""
    # مفكرة التطبيق تُسمّي الحقل `published` لا `date`. إغفاله كان يُفرغ كل
    # حدثٍ من تاريخه فيسقط في الترشيح — فتبدو المفكرة فارغة وهي مليئة.
    for k in ("date", "published", "event_date", "ex_date", "when"):
        v = e.get(k)
        if v:
            return str(v)[:10]
    return ""


def _ev_title(e: dict) -> str:
    # الصفّ النائب («لا توجد إجراءات…») ليس حدثاً — يُستبعَد بنوعه صراحةً
    # لا بالاعتماد على خلوّه من التاريخ وحده.
    if (e.get("kind") or "") == "معلومة":
        return ""
    for k in ("title", "headline", "type", "event"):
        v = e.get(k)
        if v:
            return str(v).strip()
    return ""


def _days_until(iso: str) -> int | None:
    try:
        return (_dt.date.fromisoformat(iso[:10]) - _dt.date.today()).days
    except Exception:
        return None


def macro_section(days: int | None = None, label: str = "") -> str:
    """التقويم الاقتصادي، مقصوراً على النافذة المسؤول عنها إن وُجدت.

    خارج النافذة لا يُعرض كأنه جواب: يُقال صراحةً إنه لا شيء فيها، ويُذكر
    الموعد التالي موسوماً بأنه بعدها."""
    cal = load_macro_calendar()
    evs = next_macro_events(3)
    if not evs:
        return ""
    if days:
        horizon = (_dt.date.today() + _dt.timedelta(days=days)).isoformat()
        inside = [e for e in evs if str(e.get("date") or "") <= horizon]
        if not inside:
            nxt = evs[0]
            n = _days_until(nxt.get("date") or "")
            return (f"التقويم الاقتصادي: لا مواعيد مؤثّرة {label}. "
                    f"التالي بعد النافذة: {nxt.get('date')} — {nxt.get('title')}"
                    + (f" (بعد {n} يوماً)." if n else "."))
        evs = inside
    lines = []
    for e in evs:
        n = _days_until(e.get("date") or "")
        when = f"بعد {n} يوماً" if (n and n > 0) else ("اليوم" if n == 0 else "")
        lines.append(f"• {e.get('date')} — {e.get('title')}"
                     + (f" ({when})" if when else "")
                     + (f"\n    الأثر على تداول: {e['impact']}" if e.get("impact") else ""))
    stamp = cal.get("updated") or "غير مؤرّخ"
    lines.append(f"• المصدر: تقويم مخزَّن في التطبيق، آخر تحديث {stamp}. "
                 "حدِّثه إن تغيّرت المواعيد.")
    return _sec("التقويم الاقتصادي المؤثّر:", lines)


# ── تحديد الشركة المقصودة ────────────────────────────────────────────────
def resolve_company(question: str, ctx: dict) -> dict | None:
    """يستخرج الشركة المذكورة في السؤال من حيازاتك أوّلاً ثم من دليل السوق.

    الحيازات تتقدّم عمداً: حين تقول «الراجحي» وأنت تملكه، فسؤالك عن **مركزك**
    فيه لا عن السهم مجرّداً."""
    from app.services.ai_chat_rules import _n
    q = _n(question)
    if not q:
        return None
    best = None

    # كلماتٌ عامة ترد في أسماء كثيرة، فمطابقتها وحدها تُحيل السؤال إلى شركةٍ
    # لم تُذكر: «شركة الاتصالات» ليست «الاتصالات السعودية» بالضرورة.
    _STOP = {"شركه", "مصرف", "بنك", "مجموعه", "السعوديه", "القابضه", "العربيه",
             "للتسويق", "للاستثمار", "الوطنيه", "التعاونيه", "الخليج"}

    def consider(name, symbol, source, row):
        nonlocal best
        if not name:
            return
        key = _n(str(name))
        if len(key) < 3:
            return
        # المطابقة على الاسم كاملاً أوّلاً (أقوى)، ثم على كلمةٍ مميّزة منه:
        # «حلّل جرير» لا تحوي «جرير للتسويق»، وكان السؤال يسقط بلا إجابة.
        score = 0
        if key in q:
            score = len(key) + 100
        else:
            for tok in key.split():
                if len(tok) >= 4 and tok not in _STOP and tok in q:
                    score = max(score, len(tok))
        if not score:
            return
        cand = {"name": name, "symbol": symbol, "source": source, "row": row,
                "score": score}
        if best is None or cand["score"] > best["score"]:
            best = cand

    for h in ((ctx.get("المحفظة") or {}).get("المراكز") or []):
        consider(h.get("الشركة"), h.get("الرمز"), "حيازة", h)
    for r in (ctx.get("بيانات الفرز") or []):
        consider(r.get("الشركة"), r.get("الرمز"), "سوق", r)

    # الرمز الرقمي (٤ خانات) يُطابَق مستقلاً — أدقّ من الاسم حين يُذكر.
    import re
    for tok in re.findall(r"\b\d{4}\b", question or ""):
        for h in ((ctx.get("المحفظة") or {}).get("المراكز") or []):
            if str(h.get("الرمز")) == tok:
                return {"name": h.get("الشركة"), "symbol": tok, "source": "حيازة",
                        "row": h, "score": 99}
        for r in (ctx.get("بيانات الفرز") or []):
            if str(r.get("الرمز")) == tok:
                return {"name": r.get("الشركة"), "symbol": tok, "source": "سوق",
                        "row": r, "score": 99}
        return {"name": None, "symbol": tok, "source": "رمز", "row": {}, "score": 50}
    return best


# ── تحليل شركة ───────────────────────────────────────────────────────────
async def company_analysis(db, ent: dict, ctx: dict) -> str:
    """تقرير شركةٍ واحد يجمع كل ما يعرفه التطبيق عنها: مركزك · التقييم ·
    المتانة · الفنّي · التوزيعات · الأحداث القادمة · ثم الخلاصة المُعلَّلة."""
    symbol = str(ent.get("symbol") or "")
    name = ent.get("name") or symbol
    held = ent.get("source") == "حيازة"
    row = ent.get("row") or {}

    detail: dict = {}
    try:
        from app.services.analysis import analyze_company
        detail = await analyze_company(symbol, db=db) or {}
    except Exception as e:                                        # noqa: BLE001
        logger.debug(f"analyst: analyze_company({symbol}) skipped: {e}")

    fund = (detail.get("fundamentals") or {}) if detail else {}

    def g(*keys):
        for src in (detail, fund, row):
            for k in keys:
                if isinstance(src, dict) and src.get(k) not in (None, ""):
                    return src[k]
        return None

    head = f"{name} ({symbol})" if symbol else str(name)
    parts: list[str] = [f"تحليل {head} — "
                        + ("من حيازاتك." if held else "سهم في السوق لا تملكه حالياً.")]

    # ١) مركزك
    if held:
        parts.append(_sec("مركزك:", [
            f"• الكمية {_f(row.get('الكمية'), d=0)} سهماً بمتوسط تكلفة "
            f"{_f(row.get('متوسط التكلفة'))} ريال، والسعر الآن {_f(row.get('السعر الحالي'))} ريال.",
            f"• القيمة السوقية {_f(row.get('القيمة السوقية'))} ريال"
            # الوزن يُذكر فقط إن كان محسوباً؛ «وزنه 0%» لمركزٍ بثمانية عشر ألفاً
            # رقمٌ خاطئ ظاهرياً يُفقد الثقة بالتقرير كلّه.
            + (f"، ووزنه {_f(row.get('الوزن٪'))}% من مراكزك." if row.get("الوزن٪") else "."),
            f"• الربح غير المحقّق {_pm(row.get('الربح/الخسارة'), ' ريال')} "
            f"({_pm(row.get('العائد٪'))}).",
        ]))

    # ٢) التقييم
    pe, target = g("pe_ratio"), g("target_mean_price")
    price = g("price", "السعر", "current_price")

    # ── سعرٌ حيّ أوّلاً، وإلّا فسعرٌ موصوفٌ بعمره ──────────────────────────
    # مصدر السعر لسهمٍ لا تملكه هو صفُّ «الفرز»، ومخزّنه يعيش ٣٦ ساعة ثم
    # يسقط إلى آخر لقطةٍ سليمة بلا حدٍّ لعمرها. فكان يُقال «السعر الآن ١٧»
    # وهو اليوم ٥ — ومعه «اتجاه صاعد» مبنيٌّ على المتوسّطات القديمة نفسها.
    # لا يُقال «الآن» إلّا لسعرٍ من اليوم؛ وما عداه يُذكر عمره صراحةً.
    price_note = ""
    if symbol and not held:
        try:
            # ══ السعرُ من لقطة «تداول» الرسمية أوّلاً ══ (D437)
            # كان من ياهو وحدَه — محكوماً بالحصّة ومتأخّراً — والتطبيقُ يملك
            # لقطةَ «تداول» الحيّة بلا حصّة، وهي ما تعرضه شاشاتُه. فصقرُ يقرأ
            # ما تقرؤه الشاشة، وياهو احتياطٌ بعدها.
            lp = None
            try:
                from app.services.tadawul_market import row_for
                lp = (row_for(symbol) or {}).get("price")
            except Exception:                                     # noqa: BLE001
                lp = None
            if not lp:
                from app.services.market_data import market_service
                live = await market_service.get_price(f"{symbol}.SR")
                lp = getattr(live, "price", None) if live else None
            if lp:
                price = float(lp)
                price_note = ""
            else:
                raise ValueError("no live price")
        except Exception:
            try:
                from app.services.market_screener import screener_age_hours
                age = screener_age_hours()
            except Exception:
                age = None
            if age is None:
                price_note = " (آخر سعرٍ مسجَّل — تاريخه غير معروف، وقد لا يكون سعر اليوم)"
            elif age >= 24:
                price_note = f" (آخر سعرٍ مسجَّل قبل {int(age // 24)} يوم تقريباً — ليس سعر اليوم)"
            elif age >= 6:
                price_note = f" (آخر سعرٍ مسجَّل قبل {int(age)} ساعة تقريباً)"
    upside = None
    if target and price:
        try:
            upside = (float(target) - float(price)) / float(price) * 100
        except Exception:
            upside = None
    # ══ السعرُ العادل من المحرّك باسمه في التطبيق ══ (D437)
    _fv = g("السعر العادل", "fair_value")
    _fv_up = g("الفجوة عن السعر العادل٪", "fair_value_upside_pct")
    _fv_cf = g("ثقة السعر العادل", "fair_value_conf")
    parts.append(_sec("التقييم:", [
        (f"• السعر العادل {_f(_fv)} ريال"
         + (f"، أي {_pm(_fv_up)} عن السعر" if _fv_up is not None else "")
         + (f" · ثقة {_fv_cf}" if _fv_cf else "")) if _fv else None,
        f"• مكرّر الربحية {_f(pe)}" + (f" · العائد على حقوق الملكية {_f(g('roe'))}%" if g("roe") else ""),
        f"• القيمة السوقية {_big(g('market_cap'))}" if g("market_cap") else None,
        (f"• متوسط هدف المحللين {_f(target)} ريال، أي {_pm(upside)} عن السعر الحالي."
         if target else None),
        f"• عائد التوزيعات {_f(g('dividend_yield', 'عائد التوزيعات٪'))}%"
        if g("dividend_yield", "عائد التوزيعات٪") else None,
    ]))

    # ٣) المتانة المالية — من محرّك الحوكمة نفسه لا من رأيٍ ثانٍ
    gov = detail.get("governance") or {}
    gov_lines = []
    if gov.get("evaluable") is False:
        gov_lines.append("• بيانات القوائم غير كافية لإصدار درجة — التطبيق يمتنع "
                         "عن الدرجة بدل اختلاقها.")
    else:
        # الاسمُ كما في التطبيق (‏D437): كانت «درجة المتانة» هنا و«درجة
        # الحوكمة» في السياق و«درجة الجودة المالية» في الشاشة — ثلاثةُ أسماء.
        sc = gov.get("score") or g("درجة الجودة المالية", "درجة الحوكمة", "finance_score")
        if sc is not None:
            gov_lines.append(f"• درجة الجودة المالية {_f(sc, d=0)}/100"
                             + (f" · القرار المحسوب: {gov.get('decision')}" if gov.get("decision") else ""))
        if gov.get("narrative"):
            gov_lines.append(f"• {str(gov['narrative']).strip()}")
    sharia = detail.get("sharia_status") or row.get("شرعي")
    if sharia:
        gov_lines.append(f"• التوافق الشرعي: {sharia_ar(sharia)}"
                         + (f" (المصدر {detail.get('sharia_source')})" if detail.get("sharia_source") else ""))
    parts.append(_sec("المتانة والالتزام:", gov_lines))

    # ٤) الفنّي
    rsi = g("rsi", "RSI")
    tech_lines = []
    if rsi is not None:
        state = ("منطقة تشبّع شرائي" if float(rsi) >= 70 else
                 "منطقة تشبّع بيعي" if float(rsi) <= 30 else "نطاق محايد")
        tech_lines.append(f"• مؤشر القوّة النسبية {_f(rsi, d=0)} — {state}.")
    d50, d200 = g("dist_sma50", "عن م50٪"), g("dist_sma200", "عن م200٪")
    if d50 is not None or d200 is not None:
        tech_lines.append(f"• الموقع من المتوسطات: {_pm(d50)} عن متوسط 50 يوماً، "
                          f"{_pm(d200)} عن متوسط 200 يوم.")
    # بنية الاتجاه: موقع السعر من المتوسطين معاً يقول ما لا يقوله أيٌّ منهما
    # وحده — فوقهما اتجاهٌ صاعد، دونهما هابط، وبينهما مرحلة تحوّل.
    if d50 is not None and d200 is not None:
        a, b = float(d50), float(d200)
        trend = ("صاعدة — السعر فوق المتوسطين" if a > 0 and b > 0 else
                 "هابطة — السعر دون المتوسطين" if a < 0 and b < 0 else
                 "مرحلة تحوّل — فوق أحد المتوسطين ودون الآخر")
        tech_lines.append(f"• بنية الاتجاه: {trend}.")
    lo, hi = g("week52_low"), g("week52_high")
    if lo and hi and price:
        try:
            lo_f, hi_f, p = float(lo), float(hi), float(price)
            off = (p - hi_f) / hi_f * 100
            up = (p - lo_f) / lo_f * 100
            # الموقع داخل النطاق (0٪ عند القاع، 100٪ عند القمّة) — رقمٌ واحد
            # يختصر «أين نحن من سنةٍ كاملة من التداول».
            pos = (p - lo_f) / (hi_f - lo_f) * 100 if hi_f > lo_f else None
            tech_lines.append(f"• نطاق 52 أسبوعاً {_f(lo_f)}–{_f(hi_f)} ريال: السعر "
                              f"{_pm(off)} عن القمّة و{_pm(up)} عن القاع"
                              + (f"، أي عند {_f(pos)}% من النطاق." if pos is not None else "."))
        except Exception:
            pass
    vol = g("avg_volume")
    if vol:
        tech_lines.append(f"• متوسط أحجام التداول: {_f(vol, d=0)} سهماً يومياً.")
    parts.append(_sec("القراءة الفنّية:", tech_lines))

    # ٥) التحليل الأساسي — من القوائم المالية نفسها لا من نِسَبٍ سطحية
    fund_sec, fund_signals = await _fundamental_section(symbol)
    parts.append(fund_sec)

    # ٦) الأحداث القادمة
    try:
        from app.services.content_engine import company_calendar
        evs = await company_calendar(symbol, name) or []
        dated, undated = [], []
        for e in evs:
            t = _ev_title(e)
            if not t:
                continue
            d, kind = _ev_date(e), (e.get("date_kind") or "event")
            if kind == "undated" or not d:
                undated.append(f"• {t}")
            elif kind == "announced":
                undated.append(f"• {t} (أُعلن في {d})")
            else:
                dated.append(f"• {d} — {t}")
        if dated:
            parts.append(_sec("أقرب الأحداث المؤرَّخة:", dated[:4]))
        if undated:
            parts.append(_sec("معلنة بلا تاريخ محدَّد:", undated[:3]))
        if not dated and not undated:
            parts.append("أقرب الأحداث: لا إجراءات شركات معلنة لهذه الشركة حتى الآن.")
    except Exception as e:                                        # noqa: BLE001
        logger.debug(f"analyst: calendar({symbol}) skipped: {e}")

    # ══ شواهدُ «أرقام» — المصدرُ نفسُه الذي يستشهد به رأيُ الذكاء ══ (D218)
    # بأمر المالك: يستقي صقرٌ ورأيُ الذكاء من مَعينٍ واحد، فيتطابق مخرَجُهما
    # ولا يختلف تقريرُ التلغرام عن بطاقة الشاشة في واقعةٍ منشورة. وهي
    # **بيّنةٌ لا حكم**: الخلاصةُ أدناه تبقى من إشارات التطبيق نفسِها،
    # وتوصيةُ بيت خبرةٍ لا تُصيَّر قراراً ثانياً.
    try:
        from app.services.argaam_evidence import argaam_evidence, evidence_lines
        _ev = evidence_lines(await argaam_evidence(symbol))
        if _ev:
            parts.append(_sec("شواهد من «أرقام» (بيانات منشورة، لا أحكام):",
                              [f"• {l}" for l in _ev[:3]]))
    except Exception as e:                                        # noqa: BLE001
        logger.debug(f"analyst: argaam evidence({symbol}) skipped: {e}")

    # ٦) الخلاصة — تُبنى من الإشارات المتاحة، وتُعلن عددها بصراحة
    verdict = _verdict(held, row, pe, upside, gov, rsi, d200, fund_signals)
    parts.append(verdict)
    out = "\n\n".join(p for p in parts if p)
    return out


async def _fundamental_section(symbol: str) -> tuple[str, list[tuple[bool, str]]]:
    """التحليل الأساسي: نموّ الإيرادات وصافي الدخل، الهوامش، التدفّق النقدي
    التشغيلي والحرّ، المديونية وتغطية الفوائد — كلّها من **القوائم المالية**
    متعدّدة السنوات التي تقرأها صفحة الحوكمة، لا من نسبةٍ واحدة سطحية.

    قياسٌ لا وصف: كل بندٍ يُذكر بقيمته وتغيّره السنوي، لأن الاتجاه أهمّ من
    اللقطة — شركةٌ بهامش 12٪ هابطٍ من 20٪ ليست كشركةٍ بهامش 12٪ صاعد من 6٪."""
    try:
        from app.services.market_data import market_service
        ysym = f"{symbol}.SR" if str(symbol).isdigit() else symbol
        data = await market_service.get_financials(ysym)
    except Exception as e:                                        # noqa: BLE001
        logger.debug(f"analyst: financials({symbol}) skipped: {e}")
        return "", []
    periods = (data or {}).get("periods") or []
    if not periods:
        return "", []
    latest = periods[-1]
    prev = periods[-2] if len(periods) >= 2 else None

    def yoy(field):
        if not prev:
            return None
        a, b = latest.get(field), prev.get(field)
        if a is None or not b:
            return None
        return (a - b) / abs(b) * 100

    def line(label, field, fmt=_big, unit=""):
        v = latest.get(field)
        if v is None:
            return None
        ch = yoy(field)
        txt = fmt(v) if fmt is _big else f"{_f(v)}{unit}"
        return f"• {label}: {txt}" + (f" ({_pm(ch)} عن العام السابق)" if ch is not None else "")

    lines = [
        f"• آخر سنة مالية مُدرَجة: {latest.get('year')}"
        + (f" (مقارنةً بـ{prev.get('year')})" if prev else ""),
        line("الإيرادات", "revenue"),
        line("صافي الدخل", "net_income"),
        line("ربحية السهم", "eps", fmt=None, unit=" ريال"),
        line("التدفّق النقدي التشغيلي", "operating_cash_flow"),
        line("التدفّق النقدي الحرّ", "free_cash_flow"),
    ]
    # الهامش الصافي يُحسب هنا لا يُنقل: نسبةٌ محسوبة من رقمين موجودين أصدق
    # من نسبةٍ مخزّنة قد تكون من سنةٍ أخرى.
    rev, ni = latest.get("revenue"), latest.get("net_income")
    if rev and ni is not None:
        margin = ni / rev * 100
        prev_margin = None
        if prev and prev.get("revenue") and prev.get("net_income") is not None:
            prev_margin = prev["net_income"] / prev["revenue"] * 100
        lines.append(f"• الهامش الصافي: {_f(margin)}%"
                     + (f" مقابل {_f(prev_margin)}% في السنة السابقة" if prev_margin is not None else ""))
    if latest.get("debt_ratio") is not None:
        lines.append(f"• نسبة المديونية: {_f(latest['debt_ratio'])}%"
                     + (f" ({_pm(yoy('debt_ratio'))} عن العام السابق)" if yoy("debt_ratio") is not None else ""))
    if latest.get("interest_coverage") is not None:
        cov = float(latest["interest_coverage"])
        read = ("تغطية مريحة" if cov >= 5 else "تغطية ضيّقة" if cov >= 2 else "تغطية حرجة")
        lines.append(f"• تغطية الفوائد: {_f(cov)} مرّة — {read}.")
    if (data or {}).get("verdict"):
        lines.append(f"• قراءة القوائم: {str(data['verdict']).strip()}")
    if (data or {}).get("investment_phase"):
        lines.append("• الشركة في طور استثماري: التدفّق الحرّ السالب هنا إنفاقٌ "
                     "رأسمالي لا خللٌ تشغيلي.")

    # إشارات تدخل الميزان النهائي — الخلاصة كانت تُبنى من السعر والمحللين
    # وحدهم، فتتجاهل أهمّ ما في الشركة: أرباحها ونقدها.
    sig: list[tuple[bool, str]] = []
    g_rev, g_ni = yoy("revenue"), yoy("net_income")
    if g_ni is not None:
        sig.append((g_ni > 0, f"صافي الدخل {'نامٍ' if g_ni > 0 else 'متراجع'} {_f(abs(g_ni))}% سنوياً"))
    if g_rev is not None:
        sig.append((g_rev > 0, f"الإيرادات {'نامية' if g_rev > 0 else 'متراجعة'} {_f(abs(g_rev))}%"))
    fcf = latest.get("free_cash_flow")
    if fcf is not None and not (data or {}).get("investment_phase"):
        sig.append((float(fcf) > 0, f"التدفّق النقدي الحرّ {'موجب' if float(fcf) > 0 else 'سالب'}"))
    cov = latest.get("interest_coverage")
    if cov is not None:
        sig.append((float(cov) >= 5, f"تغطية الفوائد {_f(cov)} مرّة"))
    return _sec("التحليل الأساسي (من القوائم المالية):", lines), sig


def _verdict(held, row, pe, upside, gov, rsi, d200, fundamentals=None) -> str:
    """خلاصةٌ مُعلَّلة: نجمع الإشارات الإيجابية والسلبية ونُظهر الميزان.

    لا نُصدر «اشترِ/بِع» — التطبيق أداة قياسٍ لا وسيط. لكنّ الامتناع عن
    الخلاصة رأساً تهرّبٌ أيضاً؛ فالمخرَج: ميزانٌ ظاهر يقرأه المالك بنفسه."""
    pos, neg = [], []
    for ok, txt in (fundamentals or []):
        (pos if ok else neg).append(txt)
    if upside is not None:
        (pos if upside > 10 else neg if upside < -5 else pos).append(
            f"هدف المحللين {'أعلى' if upside > 0 else 'أدنى'} من السعر بـ{_f(abs(upside))}%")
    sc = gov.get("score")
    if sc is not None:
        (pos if float(sc) >= 60 else neg).append(f"درجة الجودة المالية {_f(sc, d=0)}/100")
    if rsi is not None:
        if float(rsi) >= 70:
            neg.append("المؤشر الفنّي في تشبّع شرائي")
        elif float(rsi) <= 30:
            pos.append("المؤشر الفنّي في تشبّع بيعي (فرصة فنّية محتملة)")
    if d200 is not None:
        (pos if float(d200) > 0 else neg).append(
            f"السعر {'فوق' if float(d200) > 0 else 'دون'} متوسط 200 يوم")
    if held and row.get("العائد٪") is not None:
        (pos if float(row["العائد٪"]) > 0 else neg).append(
            f"مركزك عليه {_pm(row['العائد٪'])}")
    if not pos and not neg:
        return ("الخلاصة: البيانات المتاحة عن هذه الشركة لا تكفي لبناء رأي. "
                "لن أخمّن.")
    lines = ["الخلاصة:"]
    if pos:
        lines.append("  يدعمها: " + "؛ ".join(pos) + ".")
    if neg:
        lines.append("  يضغط عليها: " + "؛ ".join(neg) + ".")
    # بلا ذيل «وهي إشاراتٌ قياسية لا توصية» — تحفّظٌ يعتذر عمّا لم يُطلب،
    # والسجلّ الرسميّ يذكر الميزان ولا يشرح نفسه (بأمر المالك).
    lines.append(f"  الميزان: {_signals(len(pos), 'داعمة', nom=True)}"
                 f" مقابل {_signals(len(neg), 'ضاغطة', nom=False)}.")
    return "\n".join(lines)


def _signals(n: int, adj: str, nom: bool) -> str:
    """«إشارتان داعمتان مقابل إشارتين ضاغطتين» — المثنّى يُرفع في موضع الفاعل
    ويُجرّ بعد «مقابل». الرقم المجرّد قبل التمييز ركاكةٌ تُفسد نبرة التقرير."""
    dual_n, dual_g = ("إشارتان", "إشارتين")
    adj_dual = adj[:-1] + ("تان" if nom else "تين")     # داعمة → داعمتان/داعمتين
    if n == 0:
        return f"لا إشارة {adj}"
    if n == 1:
        return f"إشارة {adj} واحدة"
    if n == 2:
        return f"{dual_n if nom else dual_g} {adj_dual}"
    return f"{n} إشارات {adj}"


# ── تحليل السوق ──────────────────────────────────────────────────────────
def market_analysis(ctx: dict) -> str:
    """قراءة تاسي من نفس معطيات صفحة السوق: المؤشر · الاتساع · القطاعات ·
    قراءة الذكاء المخزّنة — ثم استنتاجٌ مبنيّ عليها."""
    from app.services import cache
    ov = cache.get("market:overview") or {}
    mv = cache.get("market:movers") or {}
    brief = (ctx.get("نبض السوق") or cache.get("market:brief:latest") or {})
    tasi = ov.get("tasi") or {}
    if not (tasi or mv):
        return ("معطيات السوق لم تُحدَّث بعد في تطبيقك — تُبنى مع أول مسحة سوق. "
                "لا أملك قراءةً صادقة الآن.")
    parts = ["قراءة السوق (تاسي):"]
    if tasi:
        parts.append(f"  • المؤشر عند {_f(tasi.get('price'))} نقطة "
                     f"({_pm(tasi.get('change_pct'))} اليوم).")
    adv, dec = mv.get("advancers"), mv.get("decliners")
    if adv is not None and dec is not None:
        tone = ("اتساع إيجابي واسع" if adv > dec * 1.5 else
                "اتساع سلبي واسع" if dec > adv * 1.5 else "اتساع متوازن")
        parts.append(f"  • {adv} صاعدة مقابل {dec} هابطة — {tone}.")
    sectors = mv.get("sectors") or []
    if sectors:
        s = sorted([x for x in sectors if x.get("avg_change_pct") is not None],
                   key=lambda x: -x["avg_change_pct"])
        if s:
            parts.append(f"  • الأقوى: {s[0]['sector']} ({_pm(s[0]['avg_change_pct'])})"
                         f" · الأضعف: {s[-1]['sector']} ({_pm(s[-1]['avg_change_pct'])}).")
    if brief.get("summary"):
        parts.append(f"  • قراءة التطبيق: {brief['summary']}")
    mac = macro_section()
    if mac:
        parts.append("")
        parts.append(mac)
    return "\n".join(parts)


# ── الأحداث القادمة على مستوى المحفظة ────────────────────────────────────
def parse_window(question: str) -> tuple[int | None, str]:
    """يقرأ النافذة الزمنية من السؤال ويُعيد (عدد الأيام, وصفها).

    سببه: «أحداث هذا الأسبوع والقادم» سؤالٌ عن **مدّة**، وتجاهلها يُنتج إجابةً
    صحيحة الأرقام خاطئة الموضوع — تعرض موعداً بعد أربعين يوماً على أنه حدث
    الأسبوع. النافذة جزءٌ من السؤال لا زينةٌ فيه."""
    from app.services.ai_chat_rules import _has
    q = question or ""
    week = _has(q, "اسبوع", "الاسبوع", "هذا الاسبوع")
    nxt = _has(q, "القادم", "القادمه", "المقبل", "المقبله", "الجاي")
    if _has(q, "اليوم"):
        return 1, "اليوم"
    if week:
        return (14, "هذا الأسبوع والقادم") if nxt else (7, "هذا الأسبوع")
    if _has(q, "شهر"):
        return (60, "هذا الشهر والقادم") if nxt else (30, "خلال شهر")
    if _has(q, "سنه", "العام"):
        return 365, "خلال سنة"
    return None, ""


async def portfolio_events(db, question: str = "", limit: int = 6) -> str:
    """أقرب الأحداث المؤثّرة على **شركاتك أنت** — من نفس مفكرة التطبيق،
    مقصورةً على النافذة التي سألتَ عنها إن ذكرتَها."""
    # مفكرة الشركات تُبنى بنداءٍ لكل شركة؛ عشر شركات = عشرة مسارات. القياس
    # في المختبر 1.25 ثانية، وعلى خادمٍ حقيقي أضعافها لأن كل نداءٍ يمرّ
    # بالشبكة. النتيجة نفسها لا تتغيّر خلال دقائق، فنُخزّنها خمس دقائق:
    # السؤال الثاني عن الأحداث يصير فوريّاً.
    from app.services import cache as _cache
    _ck = "analyst:events:" + (question or "")[:60]
    _hit = _cache.get(_ck)
    if _hit is not None:
        return _hit

    days, label = parse_window(question)
    horizon = (_dt.date.today() + _dt.timedelta(days=days)).isoformat() if days else None
    today = _dt.date.today().isoformat()
    rows: list[str] = []
    beyond: list[str] = []
    announced: list[tuple[str, str]] = []
    undated: list[str] = []
    try:
        from sqlalchemy import select
        from app.models.portfolio import Company, Holding
        from app.services.content_engine import company_calendar
        import asyncio
        pairs = (await db.execute(
            select(Company.symbol, Company.company_name)
            .join(Holding, Holding.company_id == Company.id)
            .where(Company.status != "ARCHIVED").distinct()
        )).all()
        pairs = [(s, n) for s, n in pairs if s]
        if pairs:
            res = await asyncio.gather(*(company_calendar(s, n or s) for s, n in pairs),
                                       return_exceptions=True)
            items = []
            for (sym, nm), got in zip(pairs, res):
                if isinstance(got, Exception):
                    continue
                for e in (got or []):
                    t = _ev_title(e)
                    if not t:
                        continue
                    d, kind = _ev_date(e), (e.get("date_kind") or "event")
                    # **الشرط الحاسم**: لا يدخل النافذةَ الزمنية إلا حدثٌ
                    # تاريخُه تاريخُ وقوعه. المُعلَن بلا موعد لا يُؤرَّخ ولا
                    # يُرشَّح — يُعرض في سلّته الموسومة.
                    if kind == "event" and d and d >= today:
                        items.append((d, f"• {d} — {nm}: {t}"))
                    elif kind == "announced" and d:
                        announced.append((d, f"• أُعلن في {d} — {nm}: {t}"))
                    elif kind == "undated":
                        undated.append(f"• {nm}: {t}")
            items.sort(key=lambda x: x[0])
            if horizon:
                rows = [t for d, t in items if d <= horizon][:limit]
                # ما بعد النافذة يُذكر **موسوماً** بأنه خارجها، لا مدسوساً
                # داخلها: من سأل عن الأسبوع لا يُعطى موعداً بعد أربعين يوماً
                # كأنه جوابه.
                beyond = [t for d, t in items if d > horizon][:2]
            else:
                rows = [t for _, t in items[:limit]]
    except Exception as e:                                        # noqa: BLE001
        logger.debug(f"analyst: portfolio events skipped: {e}")

    out = []
    head = f"أحداث شركاتك {label}:" if label else "أقرب أحداث شركاتك:"
    if rows:
        out.append(_sec(head, rows))
    elif label:
        out.append(f"لا أحداث مسجّلة لشركاتك {label} في مفكرة التطبيق.")
    else:
        out.append("لا أحداث مسجّلة لشركاتك في المفكرة حالياً.")
    if beyond:
        out.append(_sec("وبعد هذه النافذة:", beyond))
    # إعلاناتٌ نعرف متى صدرت لا متى تقع — تُعرض بوصفها ماضياً معلوماً.
    announced.sort(key=lambda x: x[0], reverse=True)
    if announced:
        out.append(_sec("إعلانات صدرت مؤخّراً (تاريخ الإعلان لا تاريخ الحدث):",
                        [t for _, t in announced[:4]]))
    # إجراءاتٌ حقيقية بلا موعد معلن. سلّةٌ مستقلّة عمداً: عرضها داخل نافذةٍ
    # زمنية يجعلها تبدو موقوتة وهي ليست كذلك — وهذا أسوأ من إخفائها.
    if undated:
        out.append(_sec("معلنة بلا تاريخ محدَّد (لا تدخل أي نافذة زمنية):",
                        undated[:4]))

    mac = macro_section(days=days, label=label)
    if mac:
        out.append(mac)
    result = "\n\n".join(out)
    _cache.set(_ck, result, 300)
    return result
