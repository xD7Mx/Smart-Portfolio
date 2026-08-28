"""
Rule-based portfolio analytics — computed entirely from the real holdings,
so the evaluation / risk / report screens are NEVER empty (they don't depend
on Gemini). Gemini is layered on top as an optional narrative when available.

Inputs: holdings = [{name, symbol, qty, avg, mv, pnl, pnl_pct, sector,
                     safety, valuation, upside}], cash.
"""

from typing import Optional


def _concentration(holdings: list[dict]):
    total = sum(h["mv"] for h in holdings) or 1
    weights = [(h, h["mv"] / total * 100) for h in holdings]
    weights.sort(key=lambda x: x[1], reverse=True)
    hhi = sum((w / 100) ** 2 for _, w in weights)  # 0..1
    top = weights[0] if weights else (None, 0)
    return weights, hhi, top, total


def _sector_weights(holdings: list[dict], total: float):
    sec: dict[str, float] = {}
    for h in holdings:
        s = h.get("sector") or "غير مصنّف"
        sec[s] = sec.get(s, 0) + h["mv"]
    return sorted(((s, v / (total or 1) * 100) for s, v in sec.items()), key=lambda x: x[1], reverse=True)


MAX_PERFORMANCE_BOOST = 30


def _improvement_steps(*, basis: str, div: int, risk_score: int, top, losers: list,
                        unplanned: list, unplanned_pct: float, boost: int,
                        total_ret: float | None) -> list[str]:
    """Concrete, ranked actions to close the gap to 100/100 — never left as
    an unexplained number. Ordered roughly by how much each would actually
    move the score, given the same weights evaluate() itself uses."""
    steps: list[str] = []

    if basis == "plan" and div < 100:
        steps.append(f"قرّب توزيعك الفعلي من نسبك المستهدفة (درجة الالتزام حالياً {div}/100) — أي اقتراب يرفع 70% من وزن الدرجة البنيوية.")
    if basis == "structure" and div < 100:
        steps.append("حدّد خطة توزيع نسبي (تبويب التوزيع النسبي) ليُقاس التزامك الفعلي بدل قراءة عامة للتنويع.")
    # unplanned_pct is only a meaningful share-of-portfolio figure in "plan"
    # mode — in "structure" mode EVERY holding is unplanned by construction
    # (unplanned_pct is forced to 0 there), so showing this step there would
    # misleadingly claim "0% of the portfolio" and duplicate the step above.
    if basis == "plan" and unplanned:
        steps.append(f"حدّد نسبة مستهدفة لـ{len(unplanned)} شركة ({unplanned_pct:.0f}% من المحفظة) ما زالت بلا خطة.")
    if top and top[1] > 25:
        steps.append(f"قلّص وزن أكبر مركز ({top[0]['name']} بنسبة {top[1]:.0f}%) نحو 25% أو أقل لتقليل مخاطر التركّز.")
    if losers:
        steps.append(f"راجع {len(losers)} مركزاً متراجعاً بأكثر من 8% — قد يستدعي تعزيزاً أو إعادة تقييم لأطروحته.")
    if total_ret is None:
        steps.append("لا تتوفر بيانات أداء كافية لاحتساب مكافأة التميّز ضد السوق بعد.")
    elif boost < MAX_PERFORMANCE_BOOST:
        steps.append(f"استمر في رفع العائد الحقيقي الكلي (توزيعات + منح + أرباح) — كل ~1.7% إضافية ترفع مكافأة الأداء نقطة واحدة حتى الحد الأقصى +{MAX_PERFORMANCE_BOOST}.")
    if not steps:
        steps.append("المحفظة في أفضل حالاتها الممكنة وفق البيانات الحالية — استمر بنفس الأسلوب.")
    return steps


def _performance_boost(total_return_pct: float) -> int:
    """A fairness "boost" that credits REAL portfolio performance as an
    achievement, without letting market volatility unfairly sink the score.
    Strongly asymmetric on purpose: beating the market is a major achievement
    that deserves a major reward, so a strong real total return (which already
    includes market-independent production — dividends + bonus shares — not
    just price) lifts the score up to +30 (reached around a ~50% cumulative
    total return). A negative return only nudges it down a little (down to
    −4), because a temporary market-driven drawdown is not a failure of the
    investor's method. Still bounded — and the final score is clamped to 100."""
    if total_return_pct >= 0:
        return round(min(30, total_return_pct * 0.6))
    return round(max(-4, total_return_pct * 0.15))


MAX_RECOVERY_BOOST = 10


def _capital_recovery_boost(capital_recovered_pct: float) -> int:
    """Small extra credit (up to +10) for how much of the ORIGINAL paid
    capital has already been recovered through production (dividends + bonus
    + reinvestment value) — a risk-reduction achievement distinct from the
    performance boost above: money no longer at risk is money that can't be
    lost to a market drop."""
    return round(max(0, min(MAX_RECOVERY_BOOST, capital_recovered_pct * 0.1)))


def evaluate(holdings: list[dict], cash: float, targets: dict | None = None,
             performance: dict | None = None, capital_recovery: dict | None = None) -> dict:
    """توازن المحفظة — structural core (breadth+concentration, or adherence to
    the user's own التوزيع النسبي plan) PLUS an optional performance boost.

    The structural core stays price-independent, so a lucky/unlucky DAY never
    moves it. On top of it, when `performance` = {total_return_pct,
    price_return_pct} is supplied, a bounded, asymmetric boost rewards the
    investor's actual achieved performance vs. mere price volatility — the
    gap between the total real return (incl. dividends + bonus production)
    and the raw price return is the method's cushion against the market.
    Omit `performance` and the score is exactly the old structural one.
    """
    holdings = [h for h in holdings if h.get("mv", 0) > 0]
    if not holdings:
        return {
            "diversification_score": 0, "risk_score": 0,
            "overall_score": 0,
            "summary": "المحفظة فارغة — أضف شركات لتبدأ رؤية التقييم.",
            "source": "rule",
        }
    weights, hhi, top, total = _concentration(holdings)
    sectors = _sector_weights(holdings, total)
    n = len(holdings)
    targets = targets or {}

    planned = [h for h in holdings if targets.get(h.get("company_id")) is not None]
    unplanned = [h for h in holdings if targets.get(h.get("company_id")) is None]
    # A single stray target (e.g. one holding out of ten) shouldn't flip the
    # WHOLE score onto "plan adherence" (70% weight) while the rest of the
    # portfolio is unplanned and silently excluded from the deviation math —
    # that let one assigned target swing the structural score on almost no
    # real signal. Require targets to actually cover the majority of the
    # portfolio's value before trusting them as the basis.
    planned_value_pct = (sum(h["mv"] for h in planned) / total * 100) if (planned and total) else 0

    div_reasons: list[str] = []
    risk_reasons: list[str] = []

    if planned and planned_value_pct >= 50:
        # Plan adherence: how close current weights sit to your own declared
        # targets — a heavy, intentional position that matches its target
        # scores well; only the *drift* away from your plan is penalised.
        # Companies you haven't assigned a target to yet (still building the
        # portfolio) are reported separately, never treated as "0% target"
        # drift.
        deviations = []
        for h in planned:
            current_w = h["mv"] / total * 100 if total else 0
            deviations.append(abs(current_w - targets[h["company_id"]]))
        avg_dev = sum(deviations) / len(deviations)
        div = max(0, min(100, round(100 - avg_dev * 2)))
        unplanned_pct = sum(h["mv"] for h in unplanned) / total * 100 if total else 0
        basis = "plan"
        div_reasons.append(f"متوسط الانحراف عن نسبك المستهدفة {avg_dev:.1f} نقطة مئوية → كل نقطة انحراف تخصم نقطتين من 100.")
        if unplanned:
            div_reasons.append(f"{len(unplanned)} شركة ({unplanned_pct:.0f}% من المحفظة) بلا نسبة مستهدفة — لا تُحتسب ضمن الانحراف حالياً، لكنها تبقى فجوة في اكتمال الخطة.")
        if div < 100:
            div_reasons.append("للوصول إلى 100: صفّر الانحراف بين وزن كل شركة ونسبتها المستهدفة" + (" وحدّد نسبة لكل شركة متبقية." if unplanned else "."))
    else:
        # No declared plan at all — fall back to a generic structural read:
        # more names + more sectors + lower concentration.
        breadth_pts = round((min(n, 12) / 12) * 55)
        conc_pts = round((1 - hhi) * 30)
        sector_pts = round((min(len(sectors), 6) / 6) * 15)
        div = min(100, breadth_pts + conc_pts + sector_pts)
        unplanned_pct = 0
        basis = "structure"
        div_reasons.append(f"عدد الشركات: {n}/12 → {breadth_pts}/55 نقطة.")
        div_reasons.append(f"تشتت التركّز (عكس مؤشر HHI): {conc_pts}/30 نقطة — أكبر مركز يمثل {top[1]:.0f}%.")
        div_reasons.append(f"عدد القطاعات: {len(sectors)}/6 → {sector_pts}/15 نقطة.")
        if div < 100:
            missing = []
            if breadth_pts < 55: missing.append(f"أضف شركات حتى تصل إلى 12 (حالياً {n})")
            if conc_pts < 30: missing.append("قلّص تركّز أكبر مركز")
            if sector_pts < 15: missing.append(f"وسّع القطاعات حتى تصل إلى 6 (حالياً {len(sectors)})")
            div_reasons.append("للوصول إلى 100: " + "، ".join(missing) + ". أو حدّد خطة توزيع نسبي ليُقاس التزامك الفعلي بدلاً من هذه القراءة العامة.")

    # Risk score (higher = safer): its own job — concentration + drawdowns —
    # kept separate from the structural/plan score above, not blended in.
    losers = [h for h in holdings if h.get("pnl_pct", 0) <= -8]
    conc_penalty = round(top[1] * 0.4)
    losers_penalty = len(losers) * 6
    hhi_penalty = round(hhi * 40)
    risk_score = max(0, min(100, round(80 - top[1] * 0.4 - len(losers) * 6 - (hhi * 40))))
    risk_reasons.append(f"القاعدة 80 نقطة، ناقص {conc_penalty} لتركّز أكبر مركز ({top[1]:.0f}%)، ناقص {losers_penalty} لعدد {len(losers)} مركزاً متراجعاً بأكثر من 8%، ناقص {hhi_penalty} لمؤشر تركّز المحفظة (HHI).")
    if conc_penalty == 0 and losers_penalty == 0 and hhi_penalty == 0:
        risk_reasons.append("لا توجد عوامل مخاطرة ظاهرة حالياً — سقف هذا المقياس عند صفر مخاطر هو 80/100 وفق منهجيته (لا يبلغ 100 إلا ضمن التقييم الإجمالي بعد إضافة مكافأة الأداء).")
    elif risk_score < 100:
        needs = []
        if conc_penalty > 0: needs.append("قلّص وزن أكبر مركز")
        if losers_penalty > 0: needs.append("عالج المراكز المتراجعة")
        if hhi_penalty > 0: needs.append("وزّع رأس المال على مراكز أكثر تقارباً في الحجم")
        risk_reasons.append("للوصول إلى الحد الأقصى (80): " + "، ".join(needs) + ".")
    # Plan adherence is a more informed signal than raw structure, so it
    # earns more weight — but risk_score still guards against genuine
    # danger (heavy concentration, real drawdowns) that a plan doesn't
    # excuse away.
    div_w, risk_w = (0.7, 0.3) if basis == "plan" else (0.5, 0.5)
    structural = round(div * div_w + risk_score * risk_w)

    # Performance boost — rewards real achievement, fair against volatility.
    # An implausible magnitude (data glitch — e.g. an incomplete cash-deposit
    # ledger shrinking the capital base toward zero) shouldn't get to swing
    # the score off a bogus number, so a total return outside a sane range
    # is treated as unreliable and simply excluded from the boost.
    perf = performance or {}
    total_ret = perf.get("total_return_pct")
    price_ret = perf.get("price_return_pct")
    perf_reliable = total_ret is not None and abs(total_ret) <= 300
    boost = _performance_boost(total_ret) if perf_reliable else 0
    cushion = (total_ret - price_ret) if (perf_reliable and price_ret is not None) else None

    # Capital-recovery boost — how much of the paid-in capital has already
    # been extracted via production (dividends + bonus + reinvestment value).
    cap_rec = capital_recovery or {}
    capital_recovered_pct = cap_rec.get("capital_recovered_pct")
    recovery_boost = _capital_recovery_boost(capital_recovered_pct) if capital_recovered_pct is not None else 0

    overall = max(0, min(100, structural + boost + recovery_boost))

    if basis == "plan":
        parts = [
            f"تضم المحفظة {n} شركة عبر {len(sectors)} قطاع.",
            f"التوزيع الحالي قريب من خطتك المستهدفة بنسبة {div}%." if div >= 70 else f"هناك انحراف ملحوظ عن خطتك المستهدفة (تطابق {div}%).",
            (f"{len(unplanned)} شركة ({unplanned_pct:.0f}% من المحفظة) لم تُحدَّد لها نسبة مستهدفة بعد." if unplanned else ""),
        ]
    else:
        parts = [
            f"تضم المحفظة {n} شركة عبر {len(sectors)} قطاع.",
            f"أكبر مركز هو {top[0]['name']} بوزن {top[1]:.0f}% من المحفظة" + (" — تركيز مرتفع يستدعي الانتباه." if top[1] > 35 else "."),
        ]
    parts.append("يوجد " + str(len(losers)) + " مركز متراجع بأكثر من 8%." if losers else "لا توجد مراكز متراجعة بشكل حاد.")

    # Performance narrative — frames real return as achievement against
    # market volatility (the production cushion), and states the boost.
    if total_ret is not None and perf_reliable:
        parts.append(f"العائد الحقيقي الكلي للمحفظة {total_ret:+.1f}% (متضمناً التوزيعات والمنح).")
        if cushion is not None and cushion >= 1 and price_ret is not None:
            parts.append(
                f"رغم أن الأداء السعري المجرّد {price_ret:+.1f}%، أنتج أسلوبك (توزيعات ومنح) "
                f"{cushion:+.1f}% إضافية كحاجز ضد تقلّب السوق — تميّز حقيقي في الأداء."
            )
        if boost > 0:
            parts.append(f"أُضيفت {boost}+ نقطة للتقييم تقديراً لهذا الأداء الفعلي مقابل ظروف السوق.")
        elif boost < 0:
            parts.append(f"خُصمت {abs(boost)} نقطة بأثر محدود فقط، لأن التراجع السعري قد يكون ظرفاً سوقياً مؤقتاً لا خللاً في الأسلوب.")
    elif total_ret is not None and not perf_reliable:
        parts.append("بيانات عائد المحفظة الحقيقي الحالية غير منطقية (على الأرجح سجل إيداعات ناقص) فاستُبعدت من التقييم مؤقتاً.")
    if capital_recovered_pct is not None:
        if recovery_boost > 0:
            parts.append(f"استرددت {capital_recovered_pct:.0f}% من رأس مالك المدفوع عبر التوزيعات والمنح وإعادة الاستثمار — أُضيفت {recovery_boost}+ نقطة تقديراً لتقليل رأس المال المعرّض للخطر.")

    improvement_steps = _improvement_steps(
        basis=basis, div=div, risk_score=risk_score, top=top, losers=losers,
        unplanned=unplanned, unplanned_pct=unplanned_pct, boost=boost, total_ret=total_ret if perf_reliable else None,
    ) if overall < 100 else ["المحفظة في أفضل حالاتها الممكنة وفق البيانات الحالية — استمر بنفس الأسلوب."]
    if capital_recovered_pct is not None and recovery_boost < MAX_RECOVERY_BOOST and overall < 100:
        improvement_steps.append(f"استمر باسترداد رأس المال المدفوع عبر التوزيعات والمنح — كل 10% إضافية ترفع مكافأة الاسترداد نقطة واحدة حتى الحد الأقصى +{MAX_RECOVERY_BOOST}.")

    weight_label = "70% التزام بالخطة + 30% مخاطر" if basis == "plan" else "50% توازن بنيوي + 50% مخاطر"
    overall_reasons = [f"الدرجة البنيوية {structural}/100 ({weight_label}: {div}×{div_w:.0%} + {risk_score}×{risk_w:.0%})."]
    if perf_reliable:
        overall_reasons.append(f"مكافأة/خصم الأداء الفعلي مقابل السوق: {boost:+d} نقطة (العائد الحقيقي الكلي {total_ret:+.1f}%).")
    else:
        overall_reasons.append("لا توجد مكافأة أداء بعد — تفتقر لبيانات عائد المحفظة الحقيقي الموثوقة.")
    if capital_recovered_pct is not None:
        overall_reasons.append(f"مكافأة استرداد رأس المال: {recovery_boost:+d} نقطة (استُرد {capital_recovered_pct:.0f}% من رأس المال المدفوع).")
    overall_reasons.append(f"الإجمالي = {structural} {'+' if boost >= 0 else '−'} {abs(boost)} {'+' if recovery_boost >= 0 else '−'} {abs(recovery_boost)} = {overall}/100.")

    return {
        "diversification_score": div,
        "diversification_basis": basis,
        "diversification_reasons": div_reasons,
        "unplanned_pct": round(unplanned_pct, 1) if basis == "plan" else None,
        "risk_score": risk_score,
        "risk_reasons": risk_reasons,
        "overall_reasons": overall_reasons,
        "structural_score": structural,
        "performance_boost": boost,
        "capital_recovered_pct": round(capital_recovered_pct, 1) if capital_recovered_pct is not None else None,
        "recovery_boost": recovery_boost,
        "total_return_pct": round(total_ret, 1) if total_ret is not None else None,
        "price_return_pct": round(price_ret, 1) if price_ret is not None else None,
        "production_cushion_pct": round(cushion, 1) if cushion is not None else None,
        "overall_score": overall,
        "improvement_steps": improvement_steps,
        "executive_summary": " ".join(p for p in parts if p),
        "summary": " ".join(p for p in parts if p),
        "source": "rule",
    }


def risk(holdings: list[dict], cash: float) -> dict:
    holdings = [h for h in holdings if h.get("mv", 0) > 0]
    if not holdings:
        return {"overall_risk_level": "UNKNOWN", "summary": "المحفظة فارغة.", "risks": [], "source": "rule"}
    weights, hhi, top, total = _concentration(holdings)
    sectors = _sector_weights(holdings, total)
    risks: list[dict] = []

    if top[1] >= 40:
        risks.append({"description": f"تركّز مرتفع جداً في {top[0]['name']} ({top[1]:.0f}% من المحفظة) — أي هبوط فيه يؤثر بقوة على المحفظة."})
    elif top[1] >= 25:
        risks.append({"description": f"تركّز ملحوظ في {top[0]['name']} ({top[1]:.0f}%) — فكّر في توزيع أوسع."})
    if sectors and sectors[0][1] >= 50:
        risks.append({"description": f"تركّز قطاعي: {sectors[0][1]:.0f}% من المحفظة في قطاع {sectors[0][0]} — مخاطرة قطاعية."})
    for h in holdings:
        if h.get("pnl_pct", 0) <= -12:
            risks.append({"description": f"{h['name']} متراجع {h['pnl_pct']:.0f}% — راجع أطروحتك الاستثمارية فيه."})
    for h in holdings:
        if h.get("safety") is not None and h["safety"] < 45:
            risks.append({"description": f"{h['name']}: درجة سلامة مالية ضعيفة — يتطلب مراقبة أوثق."})
    for h in holdings:
        if h.get("valuation") and "أعلى" in h["valuation"]:
            risks.append({"description": f"{h['name']}: مقيّم أعلى من قيمته العادلة حسب تقدير المحللين."})
    if len(holdings) < 4:
        risks.append({"description": f"عدد الشركات قليل ({len(holdings)}) — التنويع محدود ويزيد التقلب."})
    if (cash or 0) <= 0:
        risks.append({"description": "لا توجد سيولة نقدية — يقيّد اقتناص الفرص أو الشراء عند التصحيح."})

    # de-dupe & cap
    seen = set(); uniq = []
    for rr in risks:
        if rr["description"] not in seen:
            seen.add(rr["description"]); uniq.append(rr)
    uniq = uniq[:8] or [{"description": "لا توجد مخاطر بنيوية ظاهرة من البيانات الحالية — المحفظة متوازنة نسبياً."}]

    hi = sum(1 for r in uniq if any(k in r["description"] for k in ("مرتفع جداً", "متراجع", "ضعيفة")))
    level = "HIGH" if (top[1] >= 40 or hi >= 3) else "MEDIUM" if (top[1] >= 25 or hi >= 1) else "LOW"
    label = {"HIGH": "عالٍ", "MEDIUM": "متوسط", "LOW": "منخفض"}[level]
    summary = f"مستوى المخاطر العام: {label}. أبرز عامل هو {'التركّز' if top[1] >= 25 else 'تقلب المراكز' if hi else 'محدودية التنويع' if len(holdings) < 4 else 'مخاطر السوق العامة'}."
    return {"overall_risk_level": level, "summary": summary, "risks": uniq, "source": "rule"}


def report(holdings: list[dict], cash: float, metrics: dict, targets: dict | None = None,
           performance: dict | None = None, capital_recovery: dict | None = None) -> dict:
    holdings = [h for h in holdings if h.get("mv", 0) > 0]
    if not holdings:
        return {"content": "المحفظة فارغة حالياً — أضف شركات ليُبنى التقرير تلقائياً.", "source": "rule"}
    ev = evaluate(holdings, cash, targets, performance, capital_recovery)
    rk = risk(holdings, cash)
    weights, hhi, top, total = _concentration(holdings)
    sectors = _sector_weights(holdings, total)
    mv = metrics.get("market_value", total)
    roi = metrics.get("roi_pct", 0)

    # نثر رزين للمتلقّي البسيط — أرقام مرساة قليلة، ووصف نوعي لما عداها.
    # مبدأ المرآة: إن كانت النتائج إيجابية والمحفظة قوية كان التقرير إيجاباً
    # خالصاً بلا استدراكات؛ وإن ضعُفت النتائج قيل ذلك بصدق هادئ. لا اختلاق.
    total_ret = ev.get("total_return_pct")
    anchor_ret = total_ret if total_ret is not None else roi
    # مبدأ المرآة كما اعتمده المالك: النتائج الإيجابية = تقرير إيجابي خالص.
    strong = anchor_ret >= 0
    cash_pct = (cash / (total + cash) * 100) if (total + cash) > 0 else 0

    top_sector = sectors[0][0] if sectors else None
    div_word = ("تنويع واسع" if len(sectors) >= 5 else "تنويع متوازن" if len(sectors) >= 3 else "تركيز مدروس")
    cash_word = ("سيولة وفيرة تمنحها جاهزية عالية لاقتناص الفرص" if cash_pct >= 25
                 else "سيولة مريحة تمنحها مرونة في الحركة" if cash_pct >= 8
                 else "توظيف شبه كامل لرأس المال في مراكزها")

    paras = []
    if strong:
        paras.append(
            f"تقف المحفظة اليوم على أرض صلبة؛ فقد بُنيت على مدى الفترة الماضية بنهجٍ منضبط "
            f"يجمع بين انتقاء شركات قيادية راسخة والصبر على ثمارها، وتعكس نتائجها الحالية "
            f"سلامة هذا النهج ووضوح بوصلته."
        )
        paras.append(
            f"يتوزّع رأس المال على {len(holdings)} شركة عبر {div_word} بين القطاعات، "
            + (f"يتصدّرها حضورٌ معتبر في قطاع {top_sector}، " if top_sector else "")
            + f"مع {cash_word}. هذا البناء يمنح المحفظة ثباتاً أمام تقلبات السوق اليومية، "
            f"ويجعل نموّها محصّلة جودة شركاتها لا رهاناً على موجة عابرة."
        )
        # الوصف يطابق ما يقيسه الرقم فعلاً: إنتاجٌ محقّق (توزيعات · أرباح بيع ·
        # منحة) على رأس المال المدفوع. القول إنه «نموّ قيمة المراكز» وصفٌ لشيء
        # آخر لا يدخل هذا الرقم — والقارئ يبني قراره على الجملة لا على الكود.
        perf = f"أمّا الثمرة، فيلخّصها عائدٌ محقّق بلغ {anchor_ret:+.1f}% من رأس المال المدفوع منذ التأسيس، تراكم عبر التوزيعات النقدية وحصيلة البيع وأسهم المنحة"
        if ev.get("capital_recovered_pct") and ev["capital_recovered_pct"] >= 20:
            perf += f"، فيما استُرد نحو {ev['capital_recovered_pct']:.0f}% من رأس المال المدفوع عبر ما أنتجته المحفظة بنفسها"
        perf += ". وهو مسارٌ يتقدّم بخطى ثابتة، ويؤكد أن قيمة المحفظة تُبنى من الداخل قبل أن يمنحها السوق سعرها."
        paras.append(perf)
        paras.append(
            "وفي المحصّلة، تسير المحفظة على الطريق الذي رُسم لها: أساسٌ متين، وإدارة صبورة، "
            "ونتائج تتحدث عن نفسها. ويبقى القرار الاستثماري، كما هو دوماً، بيد صاحب المحفظة وحده."
        )
    else:
        paras.append(
            "تمرّ المحفظة بمرحلة تستدعي القراءة الهادئة؛ فالنتائج الحالية دون المأمول، "
            "وهو أمر تمرّ به المحافظ الجادّة دون أن ينتقص من سلامة نهجها طويل الأمد."
        )
        paras.append(
            f"يتوزّع رأس المال على {len(holdings)} شركة عبر {div_word} بين القطاعات، مع {cash_word} — "
            f"بنيةٌ تحفظ للمحفظة توازنها وتحدّ من أثر أي مركز منفرد."
        )
        paras.append(
            f"يقف العائد المحقّق عند {anchor_ret:+.1f}% من رأس المال المدفوع منذ التأسيس. "
            + (rk["risks"][0]["description"] + "." if rk.get("risks") else "")
        )
        paras.append(
            "الصورة العامة قابلة للتحسّن مع الوقت والانضباط، والمراجعة الدورية للمراكز هي الأداة الصحيحة لذلك. "
            "ويبقى القرار الاستثماري بيد صاحب المحفظة وحده."
        )

    return {"content": "\n\n".join(paras), "overall_score": ev["overall_score"],
            "improvement_steps": ev.get("improvement_steps"), "source": "rule"}
