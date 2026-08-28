"""
الذكاء القاعدي للشات بوت — إجابات **حتمية** تُبنى من الأرقام الحقيقية مباشرةً.

لماذا طبقة قاعدية بجانب النموذج التوليدي:
  1. **الدقّة**: الأرقام تُحسب في بايثون لا في رأس النموذج — لا خطأ حسابي ولا هلوسة.
  2. **الصمود**: تعمل حين يغيب مفتاح الذكاء أو تنفد حصّته — فالمساعد لا يصمت أبداً.
  3. **السرعة**: إجابة فورية بلا نداء شبكة للنيّات الشائعة.

التدفّق في ai_chat: تُجرَّب النيّة القاعدية أولاً؛ فإن طابقت أُعيدت كما هي
(أرقام مضمونة)، وإلا يتولّى النموذج التوليدي بالسياق الكامل.
"""
import re

_AR_NORM = str.maketrans("أإآىئؤة", "اااييوه")
# التشكيل يكسر كل المطابقات بصمت: «العائد المركّب» لا يساوي «العائد المركب»
# حرفياً، فيسقط السؤال إلى الرسالة العامة كأن المساعد لا يعرف مقياساً هو من
# صميم تطبيقك. نُزيله من الطرفين قبل المقارنة.
# الحركات وحدها (064B–0652) + الألف الخنجرية + التطويل. الحروف العربية نفسها
# تقع قبل هذا النطاق ولا تُمسّ.
_TASHKEEL = dict.fromkeys(list(range(0x064B, 0x0653)) + [0x0670, 0x0640])


def _n(t: str) -> str:
    return (t or "").translate(_TASHKEEL).translate(_AR_NORM).lower()


def _num(v, suffix="", d=2) -> str:
    if v is None:
        return "غير متوفّر"
    try:
        f = float(v)
        if d == 0:
            return f"{int(round(f)):,}{suffix}"
        # لا نعرض كسوراً صفرية دون فقدان الدقّة:
        # 12,340.50 → 12,340.5 ؛ 8,000.00 → 8,000 ؛ 160,340.5 يبقى كما هو.
        txt = f"{round(f, d):,.{d}f}"
        if "." in txt:
            txt = txt.rstrip("0").rstrip(".")
        return f"{txt}{suffix}"
    except Exception:
        return str(v)


def _plural_co(n: int) -> str:
    """تمييز عربي سليم: شركة / شركتان / شركات."""
    n = int(n or 0)
    if n == 1:
        return "شركة واحدة"
    if n == 2:
        return "شركتان"
    return f"{n} شركات" if 3 <= n <= 10 else f"{n} شركة"


def _plural_pos(n: int, win: bool) -> str:
    """«6 مراكز رابحة» لا «6 مركزاً رابحاً» — التمييز العربي يتغيّر بالعدد."""
    n = int(n or 0)
    adj_s, adj_p = ("رابح", "رابحة") if win else ("خاسر", "خاسرة")
    if n == 0:
        return f"لا مركز {adj_s}"
    if n == 1:
        return f"مركز {adj_s} واحد"
    if n == 2:
        return f"مركزان {adj_s}ان"
    return f"{n} مراكز {adj_p}" if n <= 10 else f"{n} مركزاً {adj_s}اً"


def _sign(v) -> str:
    try:
        return "+" if float(v) >= 0 else ""
    except Exception:
        return ""


# ── النيّات: (مُطابِق, مُولِّد الإجابة) ────────────────────────────────────
def _has(q: str, *words: str) -> bool:
    n = _n(q)
    return any(_n(w) in n for w in words)


def _portfolio_performance(q: str, ctx: dict):
    if not _has(q, "اداء محفظتي", "أداء المحفظة", "كيف محفظتي", "كم ربحت", "كم خسرت",
                "وضع محفظتي", "ملخص المحفظة", "عائد محفظتي", "ثروتي", "كم عندي"):
        return None
    p = ctx.get("المحفظة")
    if not p:
        return "لا توجد بيانات محفظة بعد — أضف مراكزك أولاً."
    if not p.get("عدد الشركات"):
        return "محفظتك فارغة حالياً — لا توجد مراكز مسجّلة."
    ret = p.get("العائد٪")
    lines = [
        f"**ملخّص محفظتك**",
        f"• إجمالي الثروة: {_num(p.get('إجمالي الثروة'))} ريال (قيمة سوقية {_num(p.get('القيمة السوقية'))} + نقد {_num(p.get('النقد المتاح'))})",
        f"• المبلغ المستثمر: {_num(p.get('المبلغ المستثمر'))} ريال في {_plural_co(p.get('عدد الشركات'))}",
        f"• الربح غير المحقّق: {_sign(p.get('الربح غير المحقق'))}{_num(p.get('الربح غير المحقق'))} ريال"
        + (f" ({_sign(ret)}{_num(ret)}%)" if ret is not None else ""),
    ]
    # الرقم الموحَّد في التطبيق هو **صافي الربح** لا الربح غير المحقّق؛ كان
    # الملخّص يغفله فيقرأ المالك رقماً أصغر من الذي تعرضه كل بطاقاته.
    m = ctx.get("مقاييس المخاطر") or {}
    net, growth = m.get("net_profit"), m.get("capital_growth_pct")
    if net is not None:
        lines.insert(1, f"• صافي الربح: {_sign(net)}{_num(net)} ريال"
                     + (f" ({_sign(growth)}{_num(growth)}%)" if growth is not None else ""))
    pos = [h for h in (p.get("المراكز") or []) if (h.get("العائد٪") or 0) > 0]
    neg = [h for h in (p.get("المراكز") or []) if (h.get("العائد٪") or 0) < 0]
    lines.append(f"• {_plural_pos(len(pos), True)} مقابل {_plural_pos(len(neg), False)}")
    return "\n".join(lines)


def _best_worst(q: str, ctx: dict):
    # سؤالٌ عن **القطاعات** ليس سؤالاً عن المراكز: «أي القطاعات الأفضل أداءً»
    # كان يطابق «افضل اداء» هنا فيُجاب بأفضل الشركات — إجابةٌ واثقة عن سؤالٍ
    # آخر، وهي أسوأ من الصمت لأن القارئ لا يشكّ فيها.
    if _has(q, "قطاع"):
        return None
    # المطابقة على كلمتين متباعدتين لا على عبارةٍ متلاصقة: «أفضل وأضعف مراكزي»
    # لا تحوي «افضل مركز» حرفياً، فكان يُفهم منها الشقّ الثاني وحده — يسأل عن
    # الطرفين فيرى طرفاً واحداً ويظنّ أن لا رابح لديه.
    subject = _has(q, "مركز", "مراكز", "سهم", "اسهم", "شركة", "شركات", "حيازة", "حيازات")
    best = _has(q, "اعلى ربح", "الاكثر ربح", "افضل اداء", "الرابحة") or (
        subject and _has(q, "افضل", "اقوى", "احسن", "اعلى"))
    worst = _has(q, "اكبر خسارة", "الاكثر خسارة", "اسوا اداء", "الخاسرة") or (
        subject and _has(q, "اضعف", "اسوا", "اقل", "الاسوا"))
    if not (best or worst):
        return None
    # «أفضل وأضعف مراكزي؟» سؤالٌ واحد بجوابين — كان لا يُطابَق أصلاً فيصمت.
    if best and worst:
        a = _rank_positions(ctx, True)
        b = _rank_positions(ctx, False)
        return a if not b else f"{a}\n\n{b}"
    return _rank_positions(ctx, best)


def _rank_positions(ctx: dict, best: bool):
    hs = [h for h in ((ctx.get("المحفظة") or {}).get("المراكز") or []) if h.get("العائد٪") is not None]
    if not hs:
        return "لا توجد مراكز في محفظتك لأقارن بينها."
    hs.sort(key=lambda h: h["العائد٪"], reverse=best)
    # لا نُدرج مركزاً رابحاً ضمن «الأضعف» ولا خاسراً ضمن «الأفضل» إن وُجد بديل.
    matching = [h for h in hs if (h["العائد٪"] > 0 if best else h["العائد٪"] < 0)]
    top = (matching or hs)[:3]
    head = "أفضل مراكزك أداءً:" if best else "أضعف مراكزك أداءً:"
    if best and not matching:
        head = "لا يوجد مركز رابح حالياً. الأقرب للتعادل:"
    if (not best) and not matching:
        head = "لا يوجد مركز خاسر حالياً. الأقلّ ربحاً:"
    rows = [f"{i+1}. {h.get('الشركة')} ({h.get('الرمز')}): {_sign(h['العائد٪'])}{_num(h['العائد٪'])}% "
            f"— {_sign(h.get('الربح/الخسارة'))}{_num(h.get('الربح/الخسارة'))} ريال"
            for i, h in enumerate(top)]
    return head + "\n" + "\n".join(rows)


def _sectors(q: str, ctx: dict):
    if not _has(q, "قطاع"):
        return None
    rows = ctx.get("أداء القطاعات")
    if not rows:
        return "لم يُحسب التحليل القطاعي بعد — يُبنى مساءً بعد إغلاق تداول."
    key, label = ("1y", "سنة")
    if _has(q, "3 اشهر", "ثلاثة اشهر", "ربع"): key, label = "3m", "3 أشهر"
    elif _has(q, "6 اشهر", "ستة اشهر", "نصف"): key, label = "6m", "6 أشهر"
    elif _has(q, "3 سنوات", "ثلاث سنوات"): key, label = "3y", "3 سنوات"
    elif _has(q, "5 سنوات", "خمس سنوات"): key, label = "5y", "5 سنوات"
    if _has(q, "توزيع"):
        ranked = sorted([r for r in rows if r.get("dividend_yield") is not None],
                        key=lambda r: -r["dividend_yield"])[:5]
        if not ranked:
            return "لم تكتمل بيانات التوزيعات القطاعية بعد."
        return "أعلى القطاعات عائد توزيعات:\n" + "\n".join(
            f"{i+1}. {r['sector']}: {_num(r['dividend_yield'])}% ({_plural_co(r.get('companies'))})"
            for i, r in enumerate(ranked))
    ranked = sorted([r for r in rows if r.get(key) is not None], key=lambda r: -r[key])[:5]
    if not ranked:
        return f"لا تتوفّر بيانات كافية لفترة {label} على مستوى القطاعات."
    return (f"أفضل القطاعات أداءً خلال {label} (وسيط عوائد شركات كل قطاع):\n" + "\n".join(
        f"{i+1}. {r['sector']}: {_sign(r[key])}{_num(r[key])}% ({_plural_co(r.get('companies'))})"
        for i, r in enumerate(ranked)))


def _dividends(q: str, ctx: dict):
    if not _has(q, "توزيع") or _has(q, "قطاع"):
        return None
    rows = ctx.get("بيانات الفرز") or []
    ranked = sorted([r for r in rows if r.get("عائد التوزيعات٪") is not None],
                    key=lambda r: -r["عائد التوزيعات٪"])[:5]
    if not ranked:
        return "بيانات التوزيعات لم تكتمل بعد — تُبنى في المسحة الليلية."
    return "أعلى الأسهم عائد توزيعات (من بيانات الفرز):\n" + "\n".join(
        f"{i+1}. {r.get('الشركة')} ({r.get('الرمز')}): {_num(r['عائد التوزيعات٪'])}%"
        + (f" · حوكمة {_num(r.get('درجة الحوكمة'), d=0)}" if r.get("درجة الحوكمة") else "")
        for i, r in enumerate(ranked))


def _governance(q: str, ctx: dict):
    if not _has(q, "حوكمة", "درجة الشركات", "متانة"):
        return None
    g = (ctx.get("حوكمة المحفظة") or {})
    comps = [c for c in (g.get("الشركات") or []) if c.get("الدرجة") is not None]
    if not comps:
        # سؤال تعريفي عن المفهوم لا عن أرقام المحفظة
        from app.data.app_knowledge import METHODOLOGY
        return METHODOLOGY["درجة الحوكمة"]
    comps.sort(key=lambda c: -(c.get("الدرجة") or 0))
    lines = [f"درجة حوكمة محفظتك العامة: {_num(g.get('الدرجة العامة'), d=0)}/100"]
    lines.append("الأقوى: " + "، ".join(f"{c.get('الاسم')} ({_num(c['الدرجة'], d=0)})" for c in comps[:3]))
    if len(comps) > 3:
        lines.append("الأضعف: " + "، ".join(f"{c.get('الاسم')} ({_num(c['الدرجة'], d=0)})" for c in comps[-3:]))
    return "\n".join(lines)


def _net_profit(q: str, ctx: dict):
    """صافي الربح وعائد المحفظة والعائد المركّب واسترداد رأس المال.

    هذه هي المقاييس التي وُحّدت في التطبيق، وكان المساعد أعجز عن أبسط سؤالٍ
    عنها: «كم صافي ربحي؟» يردّ بأن مفتاح الذكاء غير مضبوط. المقاييس محسوبة
    سلفاً في بطاقة المقاييس — نقرؤها كما هي، فالمساعد لا يُعيد حساب شيء."""
    wants_profit = _has(q, "صافي الربح", "صافي ربحي", "كم ربحي", "ربحي الصافي")
    wants_return = _has(q, "عائد المحفظة", "عائد محفظتي", "نسبة العائد", "كم عائدي")
    wants_cagr = _has(q, "العائد المركب", "النمو المركب", "المركب", "سنوي مركب")
    wants_rec = _has(q, "استرداد راس المال", "استرداد رأس المال", "استرد راس مالي")
    if not (wants_profit or wants_return or wants_cagr or wants_rec):
        return None
    m = ctx.get("مقاييس المخاطر") or {}
    s = ctx.get("ملخّص المحفظة") or {}
    p = ctx.get("المحفظة") or {}

    inc = ctx.get("الدخل والتوزيعات") or {}

    def pick(*keys):
        for src in (m, s, p, inc):
            for k in keys:
                if isinstance(src, dict) and src.get(k) is not None:
                    return src[k]
        return None

    net = pick("net_profit", "صافي الربح", "total_profit")
    # النسبة تُؤخذ من **نفس المصدر** الذي أعطى الرقم. سابقاً كانت تسقط على
    # «العائد٪» وهو عائد الربح غير المحقّق، فيخرج سطرٌ يقرن ٧٤٦٢ ريالاً
    # بنسبة ٢.٧٣٪ لا تخصّه — رقمان صحيحان في جملةٍ كاذبة.
    ret = pick("capital_growth_pct", "portfolio_return_pct")
    cagr = pick("cagr_pct", "compound_return_pct")
    start = pick("project_start")
    lines = []
    if (wants_profit or wants_return) and net is not None:
        lines.append(f"• صافي الربح: {_sign(net)}{_num(net)} ريال"
                     + (f" ({_sign(ret)}{_num(ret)}% من تكلفة مراكزك)" if ret is not None else ""))
    if (wants_cagr or wants_return) and cagr is not None:
        lines.append(f"• العائد المركّب السنوي: {_sign(cagr)}{_num(cagr)}%"
                     + (f" (منذ بداية المشروع في {start})" if start else ""))
    if wants_rec:
        # نفس حساب شريط «استرداد رأس المال» في لوحة التحكّم: صافي الربح منسوباً
        # إلى هدف النموّ المحرَّر. نقرأ الهدف من إعداداتك لا من رقمٍ مفترض،
        # فيتطابق ما يقوله المساعد مع ما يراه الشريط تماماً.
        # نفس القيمة الافتراضية التي تستعملها لوحة التحكّم (١٠٠٪ = مضاعفة رأس
        # المال) حين لا يكون الهدف محرَّراً — وإلا اختلف رقم المساعد عن الشريط.
        target_pct = None
        try:
            from app.api.v1.endpoints.goals import _load_builtin_cfg
            target_pct = (_load_builtin_cfg() or {}).get("growth_target_pct") or 100.0
        except Exception:
            target_pct = 100.0
        if ret is not None and target_pct:
            done = ret / float(target_pct) * 100
            lines.append(f"• استرداد رأس المال: {_num(done)}% من هدفك "
                         f"({_num(target_pct)}% نمواً على تكلفة مراكزك)")
        else:
            lines.append("• استرداد رأس المال: لم يُضبط هدف النموّ بعد — اضبطه من "
                         "«الأهداف الاستثمارية» في لوحة التحكّم.")
    if not lines:
        return None
    # الشرح يُذكر فقط حين يُذكر صافي الربح — لا يُصدَّر سؤالٌ عن الاسترداد بتعريفٍ
    # لمقياسٍ آخر.
    head = ("صافي الربح هو الرقم الموحَّد في تطبيقك: (القيمة السوقية + النقد) − صافي "
            "ما أودعته. وعائد المحفظة هو النسبة نفسها منسوبةً إلى تكلفة مراكزك.\n"
            if (wants_profit or wants_return) else "")
    return head + "\n".join(lines)


def _read_only(q: str, ctx: dict):
    """طلب تنفيذ عملية. المساعد للقراءة فقط، والصمت هنا خطر: من لم يُخبَر بأن
    الطلب لم يُنفَّذ قد يظنّ أنه نُفِّذ."""
    if not _has(q, "بع لي", "بِع ", "اشتر لي", "اشتري ", "احذف", "امسح", "عدل ",
                "غيّر ", "غير لي", "سجل عملية", "اضف صفقة", "نفذ امر"):
        return None
    return ("لا أستطيع تنفيذ أي عملية — مساعد المحفظة للقراءة والتحليل فقط، ولا "
            "يملك صلاحية تعديل بياناتك. طلبك لم يُنفَّذ ولم يتغيّر شيء في محفظتك.\n"
            "التعديل يتمّ منك مباشرةً من صفحة الحيازات أو سجلّ العمليات.")


def _about_app(q: str, ctx: dict):
    if not _has(q, "ما هذا التطبيق", "ماذا يفعل", "مميزات", "المميزات", "ما التطبيق",
                "وش يسوي", "شنو التطبيق", "عرّفني", "عرفني بالتطبيق", "اقسام التطبيق"):
        return None
    from app.data.app_knowledge import APP_IDENTITY, SECTIONS
    lines = [f"**{APP_IDENTITY['الاسم']}** — {APP_IDENTITY['السوق']}.",
             f"المبدأ: {APP_IDENTITY['الفلسفة']}", "", "الأقسام:"]
    lines += [f"• **{k}**: {v}" for k, v in SECTIONS.items()]
    return "\n".join(lines)


def _portfolio_facts(q: str, ctx: dict):
    """حقائق مباشرة عن المحفظة: النقد · عدد الشركات · التركّز · التنويع.

    كانت تسقط كلها إلى الرسالة العامة رغم أنها أبسط ما في البيانات — يسأل
    المالك «كم النقد المتاح؟» فيُقال له إن مفتاح الذكاء غير مضبوط."""
    p = ctx.get("المحفظة") or {}
    if not p:
        return None
    pos = p.get("المراكز") or []
    if _has(q, "النقد", "كاش", "السيوله", "المتاح للشراء"):
        return (f"النقد المتاح: {_num(p.get('النقد المتاح'))} ريال، "
                f"أي {_num((p.get('النقد المتاح') or 0) / (p.get('إجمالي الثروة') or 1) * 100)}% "
                f"من إجمالي ثروتك ({_num(p.get('إجمالي الثروة'))} ريال).")
    if _has(q, "عدد الشركات", "كم شركة", "كم عدد شركاتي", "كم سهم املك", "كم مركز"):
        return (f"محفظتك تضمّ {_plural_co(p.get('عدد الشركات'))}، بقيمة سوقية "
                f"{_num(p.get('القيمة السوقية'))} ريال وتكلفة {_num(p.get('المبلغ المستثمر'))} ريال.")
    if _has(q, "المبلغ المستثمر", "كم استثمرت", "التكلفه", "راس المال المستثمر"):
        return (f"المبلغ المستثمر في مراكزك القائمة: {_num(p.get('المبلغ المستثمر'))} ريال، "
                f"وقيمتها السوقية الآن {_num(p.get('القيمة السوقية'))} ريال.")
    if _has(q, "الثروه", "اجمالي ثروتي", "كم عندي", "كم املك"):
        return (f"إجمالي ثروتك {_num(p.get('إجمالي الثروة'))} ريال: قيمة سوقية "
                f"{_num(p.get('القيمة السوقية'))} + نقد {_num(p.get('النقد المتاح'))}.")
    if _has(q, "وزن", "تركز", "التركيز", "اكبر مركز", "متنوع", "التنويع", "تنويع"):
        rows = sorted([h for h in pos if h.get("الوزن٪") is not None],
                      key=lambda h: -(h["الوزن٪"] or 0))[:3]
        if not rows:
            # الوزن غير محسوب: نشتقّه من القيمة السوقية بدل الصمت.
            mv = p.get("القيمة السوقية") or 0
            rows = sorted(pos, key=lambda h: -(h.get("القيمة السوقية") or 0))[:3]
            rows = [{**h, "الوزن٪": (h.get("القيمة السوقية") or 0) / mv * 100 if mv else None}
                    for h in rows]
        if not rows:
            return "لا مراكز في محفظتك لأقيس تركّزها."
        top = rows[0]
        lines = [f"أعلى مراكزك وزناً:"]
        lines += [f"{i+1}. {h.get('الشركة')}: {_num(h.get('الوزن٪'))}%" for i, h in enumerate(rows)]
        w = top.get("الوزن٪") or 0
        read = ("تركّزٌ مرتفع في مركز واحد" if w >= 30 else
                "تركّزٌ معتدل" if w >= 20 else "توزيعٌ متوازن نسبياً")
        lines.append(f"القراءة: {read} — أعلى مركز يمثّل {_num(w)}% من مراكزك، "
                     f"وعددها {_plural_co(p.get('عدد الشركات'))}.")
        return "\n".join(lines)
    return None


def _goals_answer(q: str, ctx: dict):
    """الأهداف الاستثمارية — الثلاثة المدمجة وما أضافه المالك."""
    if not _has(q, "هدف", "اهداف", "الاهداف"):
        return None
    g = ctx.get("الأهداف") or []
    m = ctx.get("مقاييس المخاطر") or {}
    lines = ["أهدافك الاستثمارية الثلاثة المدمجة في لوحة التحكّم: "
             "بلوغ المليون · عائد المحفظة · استرداد رأس المال."]
    net, growth = m.get("net_profit"), m.get("capital_growth_pct")
    if net is not None:
        lines.append(f"• صافي ربحك الحالي {_sign(net)}{_num(net)} ريال"
                     + (f" ({_sign(growth)}{_num(growth)}%)" if growth is not None else "")
                     + " — وهو الرقم الذي تتغذّى منه شريطا العائد والاسترداد.")
    p = ctx.get("المحفظة") or {}
    if p.get("إجمالي الثروة") is not None:
        w = p["إجمالي الثروة"]
        lines.append(f"• بلوغ المليون: ثروتك {_num(w)} ريال، أي {_num(w / 1e6 * 100)}% من المليون.")
    if g:
        lines.append("• أهداف أضفتها بنفسك: "
                     + "، ".join(str(x.get("goal_name") or x.get("name")) for x in g[:5]))
    lines.append("والأشرطة تُرتَّب تلقائياً بالأكثر امتلاءً أولاً.")
    return "\n".join(lines)


def _data_sources(q: str, ctx: dict):
    if not _has(q, "مصادر", "مصدر بياناتك", "من اين تاتي البيانات", "مصدر الارقام"):
        return None
    from app.data.app_knowledge import DATA_SOURCES
    if isinstance(DATA_SOURCES, dict):
        return "مصادر بيانات التطبيق:\n" + "\n".join(f"• {k}: {v}" for k, v in DATA_SOURCES.items())
    return "مصادر بيانات التطبيق:\n" + "\n".join(f"• {s}" for s in DATA_SOURCES)


def _capabilities(q: str, ctx: dict):
    """«هل تنفّذ الصفقات؟» سؤالٌ عن الصلاحية لا أمرٌ بالتنفيذ — يستحقّ جواباً
    صريحاً لا رسالةً عامة."""
    if not _has(q, "هل تنفذ", "هل تشتري", "هل تبيع", "هل تستطيع", "ماذا تستطيع",
                "هل يمكنك", "صلاحياتك", "ماذا تفعل"):
        return None
    return ("لا. مساعد المحفظة للقراءة والتحليل فقط، ولا يملك أي صلاحية تنفيذ أو "
            "تعديل — والتطبيق كلّه لا ينفّذ صفقات، بل يقيس ويعرض ويترك القرار لك.\n"
            "ما أستطيعه: قراءة أداء محفظتك ومقاييسها · تحليل أي شركة في حيازاتك أو "
            "في السوق (تقييم · متانة · فنّي · أساسي · أحداث) · قراءة تاسي وقطاعاته · "
            "مواعيد شركاتك والتقويم الاقتصادي · شرح مصطلحات التطبيق ومنهجياته.")


def _no_guarantee(q: str, ctx: dict):
    """طلب توصيةٍ أو ضمان. المعيار الثامن في ميثاق «نِصاب»: لا توصية ولا ضمان."""
    if not _has(q, "توصيه", "توصية", "مضمون", "مضمونه", "اضمن", "سهم يطلع",
                "افضل سهم للشراء", "وش اشتري", "ماذا اشتري"):
        return None
    return ("لا أُصدر توصيات ولا يوجد عائد مضمون في سوق الأسهم — وأي جهةٍ تَعِدك "
            "بذلك تُضلّلك.\n"
            "ما أفعله بدلاً منه: أعرض عليك إشارات الشركة الداعمة والضاغطة بأرقامها "
            "ومصادرها (التقييم · المتانة المالية · القراءة الفنّية · الأحداث)، "
            "والقرار يبقى قرارك. اسألني: «حلل سهم كذا» وسأعطيك الميزان كاملاً.")


def _out_of_scope(q: str, ctx: dict):
    """خارج نطاق التطبيق. الصمت هنا يبدو عجزاً؛ والجواب الصريح يرسم الحدّ."""
    if _has(q, "بيتكوين", "العملات الرقميه", "كريبتو", "الذهب العالمي", "فوركس",
            "ناسداك", "الاسهم الامريكيه", "اس اند بي"):
        return ("خارج نطاقي: التطبيق مخصّص للسوق السعودي (تداول) وحده، ولا يحمل "
                "بيانات للعملات الرقمية أو الأسواق الخارجية. لن أخمّن رقماً لا أملكه.")
    if _has(q, "كم عمرك", "من انت", "من صنعك", "هل انت انسان", "ما اسمك", "صقر"):
        return ("أنا صقر، مساعدك الاستثماري داخل «المحفظة الذكية» — أقرأ بياناتك "
                "المسجّلة في التطبيق وأحلّلها. لا أعرف عن نفسي أكثر من ذلك، ولا "
                "أتحدّث خارج نطاق محفظتك والسوق السعودي.")
    return None


def _governance_board(q: str, ctx: dict):
    """من يضمن جودة ما تراه — سؤالٌ مشروع لمن يبني قراراته على هذه الأرقام."""
    if not _has(q, "نصاب", "مجلس الادارة", "من يشرف", "الحوكمة والاعتماد",
                "لجنة المراجعة", "من يراجع", "من يضمن"):
        return None
    from app.data.app_knowledge import GOVERNANCE as G
    lines = [f"{G['الاسم']}.", G["التعريف"], "", "أهمّ معاييره:"]
    lines += [f"• {m}" for m in G["أهم معاييره"]]
    lines.append("")
    lines.append(G["حدّ صلاحيته"])
    return "\n".join(lines)


def _glossary(q: str, ctx: dict):
    """تعريف مصطلح أو شرح منهجية — من قاعدة معرفة التطبيق حصراً."""
    from app.data.app_knowledge import GLOSSARY, METHODOLOGY
    n = _n(q)
    # المطابقة على **أطول** مصطلح وارد في السؤال، بلا اشتراط صيغة سؤالٍ بعينها.
    # الاشتراط السابق («ما هو/اشرح…») كان يُسقط «مكرر الربحية؟» و«فرز الأسهم»
    # وكل صياغةٍ مختصرة — والمصطلح إن ورد فالسؤال عنه غالباً.
    # أقسام التطبيق تُشرَح من تعريفها المخزَّن: «كيف يعمل فرز الأسهم؟» كان
    # يسقط لأن الشرح موجودٌ في SECTIONS لا في قاموس المصطلحات.
    from app.data.app_knowledge import SECTIONS as _SEC
    best = None
    for term, meaning in {**METHODOLOGY, **GLOSSARY, **_SEC}.items():
        t = _n(term)
        if len(t) >= 3 and t in n and (best is None or len(t) > len(_n(best[0]))):
            best = (term, meaning)
    if best:
        return f"{best[0]}: {best[1]}"
    return None


def _market_read(q: str, ctx: dict):
    """قراءة تاسي — سؤالٌ عن السوق لا عن محفظتك."""
    if not _has(q, "سوق", "تاسي", "مؤشر"):
        return None
    if _has(q, "محفظتي", "مراكزي"):
        return None
    from app.services.ai_analyst import market_analysis
    return market_analysis(ctx)


def _movers(q: str, ctx: dict):
    """أعلى الرابحين والخاسرين **في السوق** — لا في محفظتك.

    التمييز مقصود: «أعلى الرابحين» بلا قيدٍ تعني السوق، أما «أفضل مراكزي»
    فتعني حيازاتك. خلطهما يُنتج إجابةً واثقة عن سؤالٍ آخر."""
    if _has(q, "محفظتي", "مراكزي", "حيازاتي"):
        return None
    up = _has(q, "الرابحين", "الاكثر ارتفاع", "اعلى ارتفاع", "الصاعده", "المرتفعه")
    dn = _has(q, "الخاسرين", "الاكثر انخفاض", "اعلى انخفاض", "الهابطه", "المنخفضه")
    if not (up or dn):
        return None
    from app.services import cache
    mv = cache.get("market:movers") or {}
    out = []
    for want, key, title in ((up, "gainers", "أعلى الرابحين اليوم"),
                             (dn, "losers", "أعلى الخاسرين اليوم")):
        if not want:
            continue
        rows = (mv.get(key) or [])[:3]
        if not rows:
            out.append(f"{title}: لم تُحدَّث بيانات السوق بعد في تطبيقك.")
            continue
        out.append(f"{title}:\n" + "\n".join(
            f"{i+1}. {r.get('name') or r.get('symbol')}: {_sign(r.get('change_pct'))}"
            f"{_num(r.get('change_pct'))}%" for i, r in enumerate(rows)))
    return "\n\n".join(out) if out else None


def _macro(q: str, ctx: dict):
    """الفائدة الأمريكية وما يشبهها — تُسأل كثيراً لأنها تحرّك البنوك لديك."""
    # جذورٌ بلا أداة تعريف: «للفائدة» لا تحوي «الفائدة» حرفياً، فكانت النيّة
    # تسقط أمام أبسط صياغة عربية.
    if not _has(q, "فائدة", "فيدرالي", "فوميك", "fomc", "ساما", "الفدرالي"):
        return None
    from app.services.ai_analyst import macro_section
    sec = macro_section()
    return sec or "لا مواعيد مسجّلة في التقويم الاقتصادي بتطبيقك حالياً."


# الترتيب مقصود: النيّات **الأضيق** أولاً. الأوسع (أداء المحفظة) تبتلع
# أسئلةً أدقّ منها لو سبقتها، فتأتي إجابةٌ صحيحة عن سؤالٍ لم يُطرح.
# الترتيب مقصود: الحارس أوّلاً، ثم الأضيق فالأوسع. النيّة الواسعة تبتلع
# أسئلةً أدقّ منها لو سبقتها، فتأتي إجابةٌ صحيحة عن سؤالٍ لم يُطرح.
INTENTS = [_read_only, _no_guarantee, _out_of_scope, _capabilities,
           _governance_board, _data_sources, _macro, _movers, _market_read,
           _about_app, _glossary, _goals_answer, _net_profit,
           _sectors, _best_worst, _governance, _dividends,
           _portfolio_facts, _portfolio_performance]


def rule_based_answer(question: str, ctx: dict) -> str | None:
    """يُعيد إجابة حتمية إن طابقت نيّة معروفة، وإلا None ليتولّى النموذج."""
    for fn in INTENTS:
        try:
            ans = fn(question, ctx)
        except Exception:
            ans = None
        if ans:
            return ans
    return None
