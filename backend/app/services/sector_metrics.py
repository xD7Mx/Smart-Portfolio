"""مقاييسُ الإطار القطاعيّ — ما يقيسه الإطار نفسه لا ما يقيسه العامّ.

## لماذا وُجد هذا الملفّ

الدرجة تُقاس اليوم بإطارٍ معترف به لكل نمط نشاط (‏CAMELS للبنوك · NAREIT
للصناديق العقارية · …)، لكنّ **أركان الإطار نفسها** كانت تُعلَن «خارج
النطاق» جملةً واحدة. وقد صحّ ذلك حين قيل عن البنود **الرقابية**: كفاية
رأس المال تحتاج الأصول المرجّحة بالمخاطر، ولا تُبلَّغ في القوائم العامّة.

لكنّ بعض أركان الإطار **ليست رقابية**، بل بنودٌ عاديّة في قائمة الدخل
والتدفّق النقديّ، امتنعنا عنها لأننا لم نطلبها من المصدر لا لأنها غير
موجودة. وفرقٌ كبيرٌ بين «لا يوفّره المصدر» و«لم نسأله» — والأول وحده
عذر.

فطُلبت البنود، ويُشتقّ منها هنا:

  **البنوك (‏CAMELS)**
    • هامش صافي العمولة (‏NIM) = صافي دخل العمولات ÷ متوسّط الأصول.
      ركنُ الربحية (‏E) في الإطار، ومقياسُ جودة التسعير لا حجمه.
    • تكلفة المخاطر (‏Cost of Risk) = مخصّص خسائر الائتمان ÷ متوسّط
      الأصول. ركنُ جودة الأصول (‏A). وهي **ليست** نسبة التعثّر: التعثّر
      رصيدٌ في الميزانية لا يُبلَّغ عامّاً، وتكلفة المخاطر تدفّقٌ سنويّ
      يُبلَّغ — فتُسمّى باسمها ولا تُقدَّم بديلاً عمّا ليست هو.
    • نسبة التكلفة إلى الدخل (‏CIR) — ركنُ الكفاءة، كان مشتقّاً سلفاً.

  **الصناديق العقارية (‏NAREIT)**
    • الأموال من العمليات (‏FFO) = صافي الربح + الإهلاك − مكاسب بيع
      العقار. وهو **التعريف الرسميّ** لا تقريبٌ له، متى وصل البندان.
      وإن لم تصل المكاسب حُذف الحدّ وقيل إن الحساب دونه.
    • ‏AFFO ≈ FFO − الإنفاق الرأسمالي. تقريبٌ معلَنٌ أنه تقريب: التعريف
      يطرح الإنفاق **الصيانيّ** وحده، ولا يفصله المصدر عن التوسّعيّ.
    • السعر إلى ‏FFO ونسبة توزيع ‏FFO — بهما يُقاس الريت لا بمكرر الربحية،
      لأن الإهلاك المحاسبيّ يُخفّض ربحه دون أن يمسّ نقده.

## القاعدة

١. لا يُشتقّ مقياسٌ إلا إذا وصلت **كلّ** بنوده — ولا يُسدّ ناقصٌ بتخمين.
٢. ما اشتُقّ يُنقل من «خارج النطاق» إلى «مُطبَّق» **لهذه الشركة**، وما لم
   يُشتقّ يبقى معلَناً خارجه.
٣. كلُّ مقياس يحمل نطاقه المرجعيّ المعترف به، ليُقرأ الرقم لا ليُعرض.
٤. التقريب يُسمّى تقريباً، والبديل لا يلبس اسم الأصل.
"""

from __future__ import annotations


def _n(d: dict, k: str) -> float | None:
    v = (d or {}).get(k)
    return float(v) if isinstance(v, (int, float)) else None


def _avg(a: float | None, b: float | None) -> float | None:
    """متوسّط الرصيد بين فترتين — البسط تدفّقُ سنةٍ والمقام رصيدُ لحظة،
    فقسمةُ التدفّق على رصيد الإقفال وحده تُحيّز النتيجة في سنة النموّ."""
    if a is None and b is None:
        return None
    vals = [v for v in (a, b) if v is not None]
    return sum(vals) / len(vals)


def _m(key, label, value, unit, band, better, note=None):
    return {"key": key, "label": label, "value": round(value, 2),
            "unit": unit, "band": band, "better": better, "note": note}


def _ebitda_of(p: dict) -> float | None:
    """الأرباحُ التشغيلية قبل الإهلاك — باشتقاقٍ متدرّج.

    ══ الإهلاكُ لا يصل فتسقط أربعةُ مؤشّرات ══ (كشفه المسبار على السوق)
    كان الاشتقاقُ يشترط الربحَ التشغيليَّ **والإهلاكَ معاً**، ومصدرُنا لا
    يُدرج الإهلاك في قائمة الدخل لكثيرٍ من الشركات (موضعُه قائمةُ
    التدفّقات). فسقط معه: صافي الدين إلى الأرباح · أسوأُ رافعةٍ في الدورة
    · العائدُ عبر الدورة · هامشُ الأرباح التشغيلية — وظهر ذلك في مخرَج
    السوق: «لم يصل: صافي الدين إلى الأرباح التشغيلية» لجرير والمراعي
    ودار الأركان جميعاً، وامتناعُ نمط السلع لنقص التغطية.

    فصار يُشتقّ متدرّجاً، وحين يغيب الإهلاكُ يُستعمل الربحُ التشغيليّ
    وحده — وهو **أشدُّ تحفّظاً**: مقامٌ أصغر يرفع نسبةَ الدَّين فتبدو
    الشركةُ أثقلَ رافعةً لا أخفّ. وقاعدةُ الإطار: عند الشك يُخفَّض.
    """
    v = _n(p, "ebitda")
    if v is not None:
        return v
    op = _n(p, "operating_income")
    if op is None:
        return None
    dep = _n(p, "depreciation")
    return op + abs(dep) if dep is not None else op


def _regulatory(out: dict, ratios: dict | None, archetype: str | None) -> None:
    """النِّسَبُ الرقابية إن وصلت — كفايةُ رأس المال والمتعثّرة والمجمّعة.

    كانت تُعلَن «خارج النطاق»، وهي منشورةٌ ربعياً — فالغيابُ كان في أنبوبنا.
    وما لم يصل يبقى في `missing` صريحاً، ولا يُقدَّر ولا يُشتقّ من نظير.
    """
    r = ratios or {}
    if archetype in ("bank", "financial"):
        if r.get("car") is not None:
            out["features"]["car"] = r["car"]
            out["metrics"].append(_m("car", "كفاية رأس المال", r["car"], "%",
                                     "الحدّ النظاميّ 10.5% وما فوقه مريح", "higher"))
        else:
            out["missing"].append("كفاية رأس المال (‏CAR)")
        if r.get("npl") is not None:
            out["features"]["npl"] = r["npl"]
            out["metrics"].append(_m("npl", "القروض المتعثّرة", r["npl"], "%",
                                     "دون 1% جودةُ أصولٍ مريحة", "lower"))
        else:
            out["missing"].append("رصيدُ القروض المتعثّرة (‏NPL)")
        if r.get("npl_coverage") is not None:
            out["features"]["npl_coverage"] = r["npl_coverage"]
            out["metrics"].append(_m("npl_coverage", "تغطية المتعثّرات",
                                     r["npl_coverage"], "%",
                                     "فوق 150% تحوّطٌ كافٍ", "higher"))
    if archetype == "insurance":
        if r.get("combined_ratio") is not None:
            out["features"]["combined_ratio"] = r["combined_ratio"]
            out["metrics"].append(_m("combined_ratio", "النسبة المجمّعة",
                                     r["combined_ratio"], "%",
                                     "دون 100% ربحُ اكتتابٍ حقيقيّ", "lower"))
        else:
            out["missing"].append("النسبة المجمّعة (‏Combined Ratio)")


def compute(archetype: str, periods: list[dict] | None,
            info: dict | None = None, price: float | None = None) -> dict:
    """يُعيد {"metrics": [...], "features": {...}, "derived": [...], "missing": [...]}.

    `features` تُدمج في محرّك القواعد فتصير الأركانُ القطاعية جزءاً من
    الدرجة نفسها، لا عرضاً بجانبها.
    """
    periods = periods or []
    info = info or {}
    ratios = (info or {}).get("_regulatory_ratios")
    out: dict = {"metrics": [], "features": {}, "derived": [], "missing": []}
    if not periods:
        return out
    last = periods[-1]
    prev = periods[-2] if len(periods) > 1 else {}
    _regulatory(out, ratios, archetype)

    def _miss(name: str) -> None:
        out["missing"].append(name)

    if archetype in ("bank", "insurance", "financial"):
        assets = _avg(_n(last, "total_assets"), _n(prev, "total_assets"))
        nii = _n(last, "net_interest_income")
        # صافي دخل العمولات قد لا يُبلَّغ صافياً، فيُركَّب من طرفيه.
        if nii is None:
            gross, cost = _n(last, "interest_income"), _n(last, "interest_expense")
            if gross is not None and cost is not None:
                nii = gross - abs(cost)
        if nii is not None and assets:
            nim = nii / assets * 100
            if 0 < nim < 15:
                out["features"]["nim"] = round(nim, 2)
                out["metrics"].append(_m(
                    "nim", "هامش صافي العمولة (‏NIM)", nim, "%",
                    "‏2.5–4% نطاقٌ سليم للبنوك السعودية", "higher"))
                out["derived"].append(f"هامش صافي العمولة {nim:.2f}%")
        else:
            _miss("هامش صافي العمولة (‏NIM)")

        prov = _n(last, "credit_loss_provision")
        if prov is not None and assets:
            cor = abs(prov) / assets * 100
            if cor < 10:
                out["features"]["cost_of_risk"] = round(cor, 2)
                out["metrics"].append(_m(
                    "cost_of_risk", "تكلفة المخاطر", cor, "%",
                    "دون 0.75% جودةُ أصولٍ مريحة", "lower",
                    "تدفّقُ مخصّصات السنة — ليست نسبة التعثّر (‏NPL)، "
                    "وتلك رصيدٌ لا يُبلَّغ في القوائم العامّة."))
                out["derived"].append(f"تكلفة المخاطر {cor:.2f}%")
        else:
            _miss("تكلفة المخاطر")

        rev, op = _n(last, "revenue"), _n(last, "operating_income")
        if rev and op is not None and rev > 0:
            cir = (rev - op) / rev * 100
            if 0 < cir < 100:
                out["features"]["cost_income_ratio"] = round(cir, 2)
                out["metrics"].append(_m(
                    "cost_income_ratio", "نسبة التكلفة إلى الدخل (‏CIR)", cir, "%",
                    "دون 40% كفاءةٌ عالية", "lower"))
                out["derived"].append(f"نسبة التكلفة إلى الدخل {cir:.0f}%")
        else:
            _miss("نسبة التكلفة إلى الدخل (‏CIR)")

    # ── أركانٌ عامّة تلزم عدّة أنماط ──────────────────────────────────
    # الرافعةُ ونسبةُ الدين إلى الأرباح التشغيلية وتغطيةُ الأصول: يقرؤها
    # مجلسُ الخبراء لأنماطٍ مختلفة (الريت · الدوريّ · المالي · العامّ)،
    # فتُحسب مرّةً هنا بدل أن يُعاد اشتقاقُها في كل موضع.
    assets_l = _n(last, "total_assets")
    equity_l = _n(last, "total_equity")
    debt_l = _n(last, "total_debt")
    if assets_l and equity_l and equity_l > 0:
        out["features"]["leverage_x"] = round(assets_l / equity_l, 2)
    if assets_l and debt_l is not None and assets_l > 0:
        out["features"]["ltv_pct"] = round(abs(debt_l) / assets_l * 100, 1)
    ebitda_l = _n(last, "ebitda")
    if ebitda_l is None:
        ebitda_l = _ebitda_of(last)
    cash_l = _n(last, "ending_cash") or 0
    if ebitda_l and ebitda_l > 0 and debt_l is not None:
        out["features"]["net_debt_ebitda"] = round(
            (abs(debt_l) - cash_l) / ebitda_l, 2)

    # ── سماتُ المواصفة الجديدة ───────────────────────────────────────
    # المواصفةُ (‏archetype_spec) تطلب مؤشّراتٍ لم تكن تُحسب: العائد عبر
    # الدورة · أسوأ رافعةٍ فيها · كثافةُ المخزون ودورانُه · الإنفاقُ
    # الرأسماليّ إلى الإهلاك · الاكتتابُ إلى رأس المال · ونسبٌ تُسنِد
    # النمطَ حين يغيب القطاع. تُحسب هنا مرّةً لكلّ الأنماط.
    rev_l = _n(last, "revenue")
    inv_l = _n(last, "inventory")
    if inv_l is not None and assets_l and assets_l > 0:
        out["features"]["inventory_intensity"] = round(inv_l / assets_l * 100, 1)
    if rev_l and inv_l and inv_l > 0:
        out["features"]["inventory_turnover"] = round(rev_l / inv_l, 2)
    capex_l, dep_l = _n(last, "capex"), _n(last, "depreciation")
    if capex_l is not None and dep_l:
        out["features"]["capex_to_depreciation"] = round(abs(capex_l) / abs(dep_l), 2)
    if rev_l and rev_l > 0:
        if capex_l is not None:
            out["features"]["capex_to_revenue"] = round(abs(capex_l) / rev_l, 3)
        if dep_l is not None:
            out["features"]["depreciation_to_revenue"] = round(abs(dep_l) / rev_l, 3)
        ie = _n(last, "interest_expense")
        if ie is not None:
            out["features"]["interest_to_revenue"] = round(abs(ie) / rev_l, 3)
    if rev_l and equity_l and equity_l > 0:
        out["features"]["premium_to_equity"] = round(rev_l / equity_l, 2)
    if ebitda_l and ebitda_l > 0 and rev_l and rev_l > 0:
        out["features"]["ebitda_margin"] = round(ebitda_l / rev_l * 100, 1)

    # ── العائدُ عبر الدورة وأسوأُ رافعةٍ فيها ──
    # الدوريُّ يُقتل في القاع لا في القمّة، والمتوسّطُ وحده يخفي القاع.
    roics, levs = [], []
    for p_ in periods:
        ni_, eq_, dt_ = (_n(p_, "net_income"), _n(p_, "total_equity"),
                         _n(p_, "total_debt"))
        if ni_ is not None and eq_ and dt_ is not None and (eq_ + dt_) > 0:
            roics.append(ni_ / (eq_ + dt_) * 100)
        eb_ = _n(p_, "ebitda")
        if eb_ is None:
            eb_ = _ebitda_of(p_)
        if eb_ and eb_ > 0 and dt_ is not None:
            levs.append((abs(dt_) - (_n(p_, "ending_cash") or 0)) / eb_)
    if len(roics) >= 3:
        out["features"]["roic_cycle"] = round(sum(roics) / len(roics), 1)
    if levs:
        out["features"]["worst_leverage"] = round(max(levs), 2)

    if archetype == "asset_light":
        # ── قاعدة الأربعين ── معيارُ الشركات خفيفة الأصول (البرمجيات
        # والخدمات): النموّ + هامشُ التدفّق الحرّ ≥ 40. ومعناها أن الشركة
        # إمّا تنمو بسرعة وتحرق، أو تنمو ببطء وتُدرّ — أمّا أن تبطئ وتحرق
        # فذاك الفشل. وهي المعيار المتّبع لهذا النمط لأن الأصول الثابتة
        # فيه ضئيلة، فالعائد على رأس المال يفقد معناه التمييزيّ.
        rev_now, rev_prev = _n(last, "revenue"), _n(prev, "revenue")
        fcf = _n(last, "free_cash_flow")
        growth = ((rev_now / rev_prev - 1) * 100
                  if rev_now and rev_prev and rev_prev > 0 else None)
        margin = (fcf / rev_now * 100) if fcf is not None and rev_now else None
        if growth is not None and margin is not None:
            r40 = growth + margin
            out["features"]["rule_of_40"] = round(r40, 2)
            out["metrics"].append(_m(
                "rule_of_40", "قاعدة الأربعين", r40, "",
                "‏40 فأعلى: النموّ والتدفّق الحرّ معاً", "higher",
                f"نموُّ الإيراد {growth:.0f}% + هامش التدفّق الحرّ {margin:.0f}%"))
            out["derived"].append(f"قاعدة الأربعين {r40:.0f}")
        else:
            _miss("قاعدة الأربعين")

    if archetype == "reit":
        ni, dep = _n(last, "net_income"), _n(last, "depreciation")
        gain = _n(last, "gain_on_asset_sale")
        if ni is not None and dep is not None:
            ffo = ni + abs(dep) - (gain or 0.0)
            approx = gain is None
            shares = _n(last, "shares_outstanding")
            out["features"]["ffo"] = round(ffo, 2)
            out["metrics"].append(_m(
                "ffo", "الأموال من العمليات (‏FFO)", ffo / 1e6, "مليون",
                "المقياس الرسميّ لدخل الريت بدل الربح المحاسبيّ", "higher",
                "دون خصم مكاسب البيع — لم يُبلّغها المصدر لهذه الفترة."
                if approx else None))
            out["derived"].append("الأموال من العمليات (‏FFO)")

            capex = _n(last, "capex")
            if capex is not None:
                affo = ffo - abs(capex)
                out["features"]["affo"] = round(affo, 2)
                out["metrics"].append(_m(
                    "affo", "‏AFFO (تقريبيّ)", affo / 1e6, "مليون",
                    "‏FFO بعد الإنفاق الرأسمالي", "higher",
                    "تقريب: التعريف يطرح الإنفاق الصيانيّ وحده، "
                    "ولا يفصله المصدر عن التوسّعيّ."))

            if shares and price and ffo > 0:
                p_ffo = price / (ffo / shares)
                if 0 < p_ffo < 100:
                    out["features"]["p_ffo"] = round(p_ffo, 2)
                    out["metrics"].append(_m(
                        "p_ffo", "السعر إلى ‏FFO", p_ffo, "×",
                        "‏10–16× نطاقٌ معتاد للريت", "lower"))
                    out["derived"].append(f"السعر إلى ‏FFO {p_ffo:.1f}×")

            divs = _n(last, "dividends_paid")
            if divs is not None and ffo > 0:
                # ══ الحالةُ الأسوأ تُسقَّف ولا تُسقَط ══
                # كان الشرطُ `< 300` يُسقط النسبةَ إن تجاوزتها، فيختفي
                # **أفدحُ ما يمكن**: صندوقٌ يوزّع أربعةَ أضعاف دخله لا
                # تظهر له نسبةُ توزيعٍ إطلاقاً، ويُقرأ غيابُها نقصَ
                # بيانات. وفوق ثلاثمئة بالمئة لا فرقَ في المعنى: التوزيعُ
                # يُموَّل من غير الدخل. فتُسقَّف لتبقى مرئيةً وتُسجَّل
                # في أدنى الرتب.
                payout = min(abs(divs) / ffo * 100, 300.0)
                if payout > 0:
                    out["features"]["ffo_payout"] = round(payout, 2)
                    out["metrics"].append(_m(
                        "ffo_payout", "نسبة توزيع ‏FFO", payout, "%",
                        "‏80–95% مستدام؛ فوق 100% يُصرَف من غير الدخل", "lower"))
                    out["derived"].append(f"نسبة توزيع ‏FFO {payout:.0f}%")
        else:
            _miss("‏FFO/AFFO")

    return out
