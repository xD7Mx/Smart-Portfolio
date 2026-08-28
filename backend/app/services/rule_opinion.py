"""
"ذكاء بدون ذكاء" — a deterministic, rule-based رأي الذكاء generator.

Produces EXACTLY the same JSON structure the Gemini-backed stock_opinion
returns (sentiment + technical + valuation + fundamentals + dividends +
summary), computed 100% locally from the real analysis numbers we already
have — no API key, no quota, no network beyond the market data itself.

This is the permanent reliability floor for the feature: Gemini (when its
free quota allows) may phrase things more fluidly, but if it is missing,
exhausted, or slow, THIS engine answers instead — the button never fails
as long as the stock has data. Every sentence traces to a real number.
"""


def _sentiment(analysis: dict) -> tuple[str, list[str]]:
    """Weighted read of the same signals a human analyst would check first.
    Score starts neutral (0) and moves with each real signal; the label is
    a banded verdict, and each contributing signal becomes a bullet."""
    t = analysis.get("technical") or {}
    f = analysis.get("fundamentals") or {}
    fin = analysis.get("financial") or {}
    bullets: list[str] = []
    score = 0

    fin_score = fin.get("score")
    if fin_score is not None:
        if fin_score >= 70:
            score += 2
            bullets.append(f"صحة مالية قوية ({fin_score}/100) تدعم الثقة بالمركز المالي للشركة.")
        elif fin_score >= 50:
            score += 1
            bullets.append(f"صحة مالية مقبولة ({fin_score}/100).")
        else:
            score -= 2
            bullets.append(f"الصحة المالية ضعيفة ({fin_score}/100) — عامل حذر أساسي.")

    pct_avg = t.get("pct_from_avg")
    if pct_avg is not None:
        if pct_avg <= -15:
            score += 2
            bullets.append(f"السعر أقل من متوسطه العادل بـ{abs(pct_avg):.0f}% — فرصة تعافٍ إحصائية نحو المتوسط.")
        elif pct_avg >= 15:
            score -= 2
            bullets.append(f"السعر أعلى من متوسطه العادل بـ{pct_avg:.0f}% — احتمال تصحيح نحو المتوسط.")

    rsi = t.get("rsi")
    if rsi is not None:
        if rsi <= 30:
            score += 1
            bullets.append(f"مؤشر RSI عند {rsi} (تشبع بيعي — ارتداد محتمل).")
        elif rsi >= 70:
            score -= 1
            bullets.append(f"مؤشر RSI عند {rsi} (تشبع شرائي — ضغط جني أرباح محتمل).")

    trend = t.get("trend")
    if trend == "صاعد":
        score += 1
        bullets.append("الاتجاه العام صاعد فوق متوسط 50 يوماً.")
    elif trend == "هابط":
        score -= 1
        bullets.append("الاتجاه العام هابط تحت متوسط 50 يوماً.")

    dy = f.get("dividend_yield")
    if dy is not None and dy >= 4:
        score += 1
        bullets.append(f"عائد توزيعات مجزٍ {dy:.1f}% يوفر دخلاً حقيقياً بغض النظر عن حركة السعر.")

    growth = f.get("earnings_growth")
    if growth is not None:
        if growth > 5:
            score += 1
            bullets.append(f"نمو ربحية السهم +{growth:.1f}%.")
        elif growth < -5:
            score -= 1
            bullets.append(f"تراجع ربحية السهم {growth:.1f}%.")

    label = ("متفائل" if score >= 4 else "متفائل بحذر" if score >= 2
             else "محايد" if score >= -1 else "متشائم بحذر" if score >= -3 else "متشائم")
    if not bullets:
        bullets.append("لا تتوفر إشارات كافية للحسم — البيانات المتاحة محدودة حالياً.")
    return label, bullets[:4]


def build_stock_opinion(symbol: str, name: str, analysis: dict) -> dict:
    """Same output contract as ai_content.stock_opinion, built from rules."""
    t = analysis.get("technical") or {}
    f = analysis.get("fundamentals") or {}
    price = analysis.get("price")

    # The headline verdict is the ONE app-wide decision (from the governance
    # Decision Engine, carried on analysis["decision"]) — NOT a separate
    # sentiment scale that could contradict what الحوكمة/تقييم الأداء show.
    # The bulleted reasoning below still comes from _sentiment.
    sent_label, sentiment_bullets = _sentiment(analysis)
    label = (analysis.get("decision") or {}).get("label") or sent_label

    technical_bullets: list[str] = []
    if t.get("rsi") is not None:
        technical_bullets.append(f"RSI عند {t['rsi']} — " + ("تشبع بيعي" if t["rsi"] <= 30 else "تشبع شرائي" if t["rsi"] >= 70 else "منطقة متوازنة") + ".")
    if t.get("support") and t.get("resistance"):
        technical_bullets.append(f"الدعم عند {t['support']} والمقاومة عند {t['resistance']} (آخر 60 جلسة).")
    if t.get("trend"):
        technical_bullets.append(f"الاتجاه الفني {t['trend']}" + (f" بتقييم {t.get('verdict')}" if t.get("verdict") else "") + ".")

    valuation_bullets: list[str] = []
    if t.get("mean_basis") and price:
        valuation_bullets.append(f"السعر الحالي {price} مقابل متوسطه المتحرّك {t['mean_basis']}.")
    if t.get("mean_note"):
        valuation_bullets.append(t["mean_note"])

    fundamentals_bullets: list[str] = []
    if f.get("pe_ratio"):
        pe = f["pe_ratio"]
        fundamentals_bullets.append(f"مكرر الربحية {pe:.1f}" + (" — تقييم منخفض جذاب" if pe < 15 else " — تقييم مرتفع يتطلب نمواً يبرره" if pe > 25 else " — ضمن النطاق المعتاد") + ".")
    if f.get("roe") is not None:
        fundamentals_bullets.append(f"العائد على حقوق المساهمين {f['roe']:.1f}%" + (" — كفاءة ممتازة" if f["roe"] >= 15 else "") + ".")
    if f.get("profit_margin") is not None:
        fundamentals_bullets.append(f"هامش الربح الصافي {f['profit_margin']:.1f}%.")
    if f.get("earnings_growth") is not None:
        fundamentals_bullets.append(f"نمو الأرباح {f['earnings_growth']:+.1f}%.")

    dividends_headline = None
    dividends_bullets: list[str] = []
    if f.get("dividend_yield"):
        dividends_headline = "التوزيعات"
        dividends_bullets.append(f"عائد التوزيعات الحالي {f['dividend_yield']:.2f}%.")
        if f.get("dividend_per_share"):
            dividends_bullets.append(f"التوزيع السنوي {f['dividend_per_share']:.2f} ريال للسهم.")

    # ══ الحكم يواجه شواهده ══ (بأمر المالك)
    # كان الحكم يُكتب من الدرجات، والشواهد تُكتب من الأرقام، ولا يلتقيان:
    # فيظهر «شراء» وتحته نقاطٌ سلبية صريحة. والمالك محقّ في أن هذا تناقض،
    # ومحقٌّ أيضاً في أن العلاج **ليس** إخفاء السلبيّ — فهو يستثمر بهذه
    # المعلومة، وتطبيقٌ يُجمّل ديكورٌ لا أداة.
    #
    # فالعلاج أن يعترف الحكم بما يعارضه بدل أن يتجاهله: تُوزن الشواهد
    # بالمعايير نفسها التي كُتبت بها (لا بتقديرٍ جديد)، فإن خالف ميزانُها
    # اتّجاهَ الحكم قيل ذلك صراحةً وسُمّي أبرزُ ما يعارضه. لا رقمٌ يُحذف
    # ولا حكمٌ يُقلب — يُضاف **سببُ بقائه رغم المعارض**.
    def _sign(txt: str) -> int:
        neg = ("تشبع شرائي", "هابط", "يتطلب نمواً يبرره", "أعلى من متوسطه",
               "احتمال تصحيح", "سلبي", "تراجع", "-")
        pos = ("تشبع بيعي", "صاعد", "جذاب", "ممتازة", "أقل من متوسطه",
               "احتمال تعافٍ", "إيجابي")
        if any(w in txt for w in pos):
            return 1
        if any(w in txt for w in neg):
            return -1
        return 0

    evidence = (technical_bullets + valuation_bullets + fundamentals_bullets)
    signed = [(b, _sign(b)) for b in evidence]
    pos_n = sum(1 for _, g in signed if g > 0)
    neg_n = sum(1 for _, g in signed if g < 0)
    buy_side = any(w in (label or "") for w in ("شراء", "إيجابي", "تجميع"))
    sell_side = any(w in (label or "") for w in ("بيع", "سلبي", "تخفيف"))

    summary_parts = [f"القراءة العامة لسهم {name}: {label}."]
    if t.get("verdict"):
        summary_parts.append(f"الوضع الفني {t['verdict']}.")
    if analysis.get("financial", {}).get("score") is not None:
        summary_parts.append(f"الصحة المالية {analysis['financial']['score']}/100.")

    # الميزان يُقال دائماً — لا حين يخالف فقط: قارئٌ يرى «٤ مقابل ١» يعرف
    # وزن الحكم، وقارئٌ لا يرى شيئاً يظنّ الإجماع.
    tension = None
    if pos_n or neg_n:
        summary_parts.append(f"ميزان الشواهد: {pos_n} مؤيّدة مقابل {neg_n} معارضة.")
        against = [b for b, g in signed if (g < 0 and buy_side) or (g > 0 and sell_side)]
        if against and (buy_side or sell_side):
            tension = {
                "label": label,
                "supports": pos_n, "opposes": neg_n,
                "against": against[:3],
                "note": ("الحكم مبنيٌّ على الدرجات المالية والحوكمية، "
                         "وهذه الشواهد تعارضه ولم تُسقطه — تُقرأ معه لا بدلاً منه."),
            }
    summary_parts.append("القرار النهائي يبقى بيد المستثمر.")

    return {
        "sentiment_label": label,
        "sentiment_bullets": sentiment_bullets,
        "technical_headline": "القراءة الفنية" if technical_bullets else None,
        "technical_bullets": technical_bullets or None,
        "valuation_headline": "التقييم السعري" if valuation_bullets else None,
        "valuation_bullets": valuation_bullets or None,
        "fundamentals_headline": "الأساسيات المالية" if fundamentals_bullets else None,
        "fundamentals_bullets": fundamentals_bullets or None,
        "dividends_headline": dividends_headline,
        "dividends_bullets": dividends_bullets or None,
        "summary": " ".join(summary_parts),
        # ما يعارض الحكم — يُعرض تحته صراحةً، ولا يُخفى ولا يقلب الحكم.
        "tension": tension,
        "source": "rule",
    }
