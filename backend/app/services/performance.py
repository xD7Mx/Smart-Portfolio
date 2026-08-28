"""
قياس الأداء — المحرّك الوحيد لمقاييس المحفظة المؤسسية.

خمسة مقاييس لا أكثر، اختيرت لأنها **تُقرَّر بها قرارات** لا لأنها تُزيّن شاشة:
  ١) TWR   — عائد قرارك، معزولاً عن توقيت إيداعاتك (معيار الصناديق: GIPS).
  ٢) TVPI  — DPI (ما عاد إليك) + RVPI (ما بقي قائماً).
  ٣) أقصى تراجع ومدّة التعافي — أسوأ ما مررتَ به، وكم لبثتَ حتى استعدتَه.
  ٤) التركّز — نصيب أكبر ثلاثة مراكز، حارساً من نجاحٍ مصدره ورقة واحدة.
  ٥) تقدّم الاسترداد — كم استُرِدّ من رأس المال المدفوع.

واستُبعدت عمداً: شارب وسورتينو (يحتاجان شرح الانحراف المعياري، وأقصى التراجع
يقول معناهما بلغةٍ يفهمها كل أحد)، وبيتا وألفا (انحدارٌ إحصائي بقيمةٍ عملية
ضئيلة لمحفظةٍ فردية)، وHHI (رقمٌ أكاديمي يقوله «أكبر ٣ مراكز» فوراً)، ونسبة
النجاح (مكانها محفظة المضاربة لا محفظة الاستثمار، فهي هناك المقياس الأهمّ
وهنا إغراءٌ بالمتاجرة).

ثلاث قواعد تحكم كل رقمٍ يخرج من هنا:
  • **لا رقم بلا مقامه** — كل نسبة تُعاد ومعها بسطها ومقامها، فتكون مراجعتها
    ممكنة بدل أن تُصدَّق على علّاتها.
  • **صدق النقص** — ما لا يكفي تاريخه يُعاد بعلامة «تحت التأسيس» وعدد الأشهر
    المتاحة، لا يُخفى (فيبدو كأنه لا يُقاس) ولا يُعرض رقماً مضلّلاً.
  • **مصدرٌ واحد** — «الإنتاج» تباعد في هذا التطبيق خمس مرّات حين تعدّدت
    مواضع حسابه. فكل ما هنا يقرأ portfolio_return، ولا يُعيد حساب شيء.

والعزل بالمحفظة مضمونٌ بمرشِّح القراءة العام (portfolio_scope)، فلا تختلط
محفظة المضاربة بمحفظة الاستثمار في أي مقياس.
"""
from __future__ import annotations

from datetime import date

# ١٢ شهراً — العتبة التي تعتبرها الصناديق النظامية حدّاً أدنى لمقياسٍ ذي معنى.
MATURITY_MONTHS = 12


def _pct(num: float, den: float) -> float | None:
    return round(num / den * 100, 2) if den else None


async def _snapshots(db) -> list:
    """اللقطات اليومية مرتّبةً تصاعدياً — أساس كل مقياسٍ زمني هنا."""
    from sqlalchemy import select
    from app.models.portfolio import PortfolioSnapshot
    rows = (await db.execute(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date)
    )).scalars().all()
    return rows


def _wealth(row) -> float:
    return float(row.market_value or 0) + float(row.cash_balance or 0)


async def compute_twr(db, snaps: list) -> dict:
    """**TWR — عائد قرارك.**

    يقيس جودة الاختيار لا حظّ التوقيت: يُقسَّم الزمن عند كل إيداعٍ أو سحب،
    ويُحسب عائد كل فترةٍ على حدة، ثم تُضرب الفترات. فمن أودع مبلغاً كبيراً
    قبل هبوطٍ مباشرة لا يُعاقَب على التوقيت في هذا الرقم — ومن أودع قبل صعودٍ
    لا يُكافأ عليه. وهذا تحديداً ما يجعله المعيار الذي تُقاس به الصناديق
    (GIPS)، والوحيد الذي تصحّ به مقارنة نفسك بها.

    ويُعرض بجانب XIRR لا بدلاً منه: XIRR يقول ما جنته **نقودك** فعلاً بتوقيتها،
    وTWR يقول ما جنته **قراراتك**. إخفاء أحدهما يُضلّل في اتجاه.
    """
    from sqlalchemy import select
    from app.models.transaction import CashLedger, CashLedgerKind

    if len(snaps) < 2:
        return {"value": None, "reason": "لا يكفي التاريخ — تحتاج لقطتين على الأقل."}

    ledger = (await db.execute(select(CashLedger))).scalars().all()
    # التدفّقات مجمَّعةً باليوم: الإيداع موجب، السحب سالب.
    flows: dict[date, float] = {}
    for e in ledger:
        when = getattr(e, "created_at", None)
        if when is None:
            continue
        d = when.date() if hasattr(when, "date") else when
        amt = float(e.amount or 0)
        flows[d] = flows.get(d, 0.0) + (amt if e.kind == CashLedgerKind.DEPOSIT else -amt)

    # ── مطابقة التدفّق بفترته ──────────────────────────────────────────────
    # اللقطة تُلتقط في وقتٍ محدّد من اليوم، وقد يُسجَّل الإيداع بعدها — فيظهر
    # المال في لقطة الغد لا لقطة اليوم. وطرحُ تدفّقٍ لم ينعكس بعد يُنتج عائد
    # فترةٍ سالباً مستحيلاً، ثم يقفز في الفترة التالية، فيخرج الحاصل رقماً
    # خيالياً (بلغ −١٢٤٢٪ على بياناتٍ حقيقية). فالتدفّق الذي يُنتج عائداً
    # مستحيلاً يُؤجَّل إلى الفترة التالية حيث انعكس فعلاً.
    # ── تحديد بداية القياس ────────────────────────────────────────────────
    # يومٌ تتحرّك فيه الثروة حركةً لا يفسّرها تدفّقٌ مسجَّل ليس أداءً: هو أثر
    # ترحيل المحفظة (أُدخلت المراكز يدوياً ثم سُجّلت عملياتها بتاريخٍ لاحق).
    # وتلك الأيام تبقى في السلسلة إلى الأبد، فلو عطّلت المقياس عطّلته دائماً.
    # فالقياس **يبدأ بعد آخر يومٍ شاذّ** بدل أن يُلغى: نطاقٌ أقصر معلَنٌ
    # صراحةً خيرٌ من مقياسٍ معطَّل، وخيرٌ من رقمٍ مبنيّ على فوضى الترحيل.
    def _period_returns():
        out = []
        carried = 0.0
        prev = snaps[0]
        for cur in snaps[1:]:
            start_w = _wealth(prev)
            flow = flows.get(cur.snapshot_date, 0.0) + carried
            carried = 0.0
            if start_w <= 0:
                prev = cur
                continue
            r = (_wealth(cur) - flow) / start_w
            if r <= 0 and flow:
                carried = flow      # لم ينعكس بعد — يُحمَل للفترة التالية
                prev = cur
                continue
            out.append((cur, r))
            prev = cur
        return out

    periods = _period_returns()
    if not periods:
        return {"value": None, "reason": "لا يكفي التاريخ."}

    last_bad = -1
    for i, (_row, r) in enumerate(periods):
        if r < 0.5 or r > 2.0:
            last_bad = i
    clean = periods[last_bad + 1:]
    skipped = last_bad + 1

    if len(clean) < 2:
        return {
            "value": None,
            "reason": ("تعذّر القياس: حركة الثروة في أيام الترحيل لا يفسّرها تدفّقٌ مسجَّل، "
                       "ولم تتراكم بعدها أيامٌ كافية. يبدأ القياس تلقائياً بعدها."),
            "from": snaps[0].snapshot_date.isoformat(),
            "to": snaps[-1].snapshot_date.isoformat(),
        }

    factor = 1.0
    for _row, r in clean:
        factor *= r

    start_row = clean[0][0]
    return {
        "value": round((factor - 1) * 100, 2),
        # المقام معلنٌ صراحةً: عدد الفترات وحدودها الزمنية.
        "periods": len(clean),
        "from": start_row.snapshot_date.isoformat(),
        "to": snaps[-1].snapshot_date.isoformat(),
        "flows_count": len([f for f in flows.values() if f]),
        # عدد الأيام المستبعَدة من صدر السلسلة (أيام الترحيل) — يُعلَن لا يُخفى.
        "skipped_days": skipped,
    }


def compute_drawdown(snaps: list, start_date=None) -> dict:
    """**أقصى تراجع ومدّة التعافي** — أسوأ هبوطٍ من قمّةٍ إلى قاع، وكم لبثتَ
    حتى استعدتَ القمّة.

    وهو المقياس الذي يُخفيه أكثرُ من يعرض عوائده، ولذلك تحديداً يجب أن يُعرض:
    محفظتان بعائدٍ واحد تختلفان اختلافاً جوهرياً إن كانت إحداهما هبطت ٤٠٪ في
    الطريق. وهو يغني عن شارب وسورتينو لقارئٍ غير متخصّص: «كم خسرتُ في أسوأ
    لحظة» جملةٌ يفهمها كل أحد، بخلاف «انحرافٌ معياري سالب».

    ومدّة التعافي هي وجهه المُحفِّز بحقّ — لا لأنها تُجمّل الرقم بل لأنها
    حقيقةٌ أخرى صادقة: من هبط ثم استعاد قمّته أثبت صموداً، وذلك خبرٌ عنه.
    """
    # يبدأ من نفس نقطة بداية قياس TWR: قمّةٌ مبنيّة على ثروةٍ ما قبل الترحيل
    # تُنتج «تراجعاً» هو في الحقيقة تصحيحُ إدخالٍ لا هبوطُ سوق.
    if start_date is not None:
        snaps = [r for r in snaps if r.snapshot_date >= start_date]
    if len(snaps) < 2:
        return {"value": None, "reason": "لا يكفي التاريخ."}

    peak = _wealth(snaps[0])
    peak_date = snaps[0].snapshot_date
    worst = 0.0
    worst_peak_date = worst_trough_date = None
    worst_peak_value = worst_trough_value = 0.0

    for row in snaps:
        w = _wealth(row)
        if w > peak:
            peak, peak_date = w, row.snapshot_date
            continue
        if peak > 0:
            dd = (peak - w) / peak * 100
            if dd > worst:
                worst = dd
                worst_peak_date, worst_trough_date = peak_date, row.snapshot_date
                worst_peak_value, worst_trough_value = peak, w

    if worst <= 0:
        return {"value": 0.0, "recovered": True, "note": "لم تهبط المحفظة تحت قمّتها بعد."}

    # التعافي: أول يومٍ عادت فيه الثروة إلى قمّة ما قبل التراجع.
    recovery_days = None
    recovered = False
    if worst_trough_date is not None:
        for row in snaps:
            if row.snapshot_date > worst_trough_date and _wealth(row) >= worst_peak_value:
                recovered = True
                recovery_days = (row.snapshot_date - worst_trough_date).days
                break

    return {
        "value": round(worst, 2),
        "peak_date": worst_peak_date.isoformat() if worst_peak_date else None,
        "trough_date": worst_trough_date.isoformat() if worst_trough_date else None,
        "peak_value": round(worst_peak_value, 2),
        "trough_value": round(worst_trough_value, 2),
        "recovered": recovered,
        "recovery_days": recovery_days,
    }


async def compute_multiples(db) -> dict:
    """**TVPI = DPI + RVPI** — الصورة الكاملة بثلاثة أرقام.

      DPI  = المحصول ÷ رأس المال المدفوع        (ما عاد إلى يدك فعلاً)
      RVPI = القيمة السوقية القائمة ÷ المدفوع    (ما بقي ينضج)
      TVPI = مجموعهما                            (كل ما صنعه رأس مالك)

    ولماذا الثلاثة معاً لا واحد: DPI وحده يكافئ من يبيع رابحه ويُبقي خاسره —
    يرتفع رقمه بينما محفظته تسوء. وRVPI وحده يكافئ من لا يحصد أبداً. ومجموعهما
    محصَّنٌ من الحيلتين، ولذلك تعرضه صناديق الملكية الخاصة ثلاثةً دائماً.
    """
    from app.services.portfolio_return import compute_production
    from app.api.v1.endpoints.portfolio import _get_holdings

    p = await compute_production(db)
    paid_in = float(p["capital_base"])
    if paid_in <= 0:
        return {"tvpi": None, "reason": "لا رأس مال مدفوع بعد."}

    holdings = await _get_holdings(db)
    residual = sum(float(h.market_value or 0) for h in holdings)

    # التقريب قبل الجمع لا بعده: تقريبُ كلٍّ على حدة ثم جمعُ الأصلين يجعل
    # المعروضَ لا يجمع المعروض (0.20 + 1.03 تُعرض 1.24 بينما مجموعها 1.23)،
    # فيرى المالك متطابقةً رياضية منكسرة أمام عينيه — وذلك وحده يهدم الثقة
    # في كل رقمٍ آخر مهما كان صحيحاً. اكتشفه فحص السلامة لا المراجعة.
    dpi = round(p["total"] / paid_in, 2)
    rvpi = round(residual / paid_in, 2)
    return {
        "dpi": dpi,
        "rvpi": rvpi,
        "tvpi": round(dpi + rvpi, 2),
        # البسط والمقام معلنان — لا مضاعف بلا ما بُني عليه.
        "distributed": p["total"],
        "residual": round(residual, 2),
        "paid_in": round(paid_in, 2),
    }


async def compute_concentration(db) -> dict:
    """**التركّز** — نصيب أكبر ثلاثة مراكز من القيمة السوقية.

    حارسٌ من أخطر وهمٍ في قياس الأداء: عائدٌ ممتاز مصدره ورقةٌ واحدة يُقرأ
    مهارةً وهو حظّ. ولا يُعرض كحكمٍ («تركيزك سيّئ») بل كواقعةٍ مع عتبةٍ
    معلنة — فالتركيز قرارٌ مشروع متى كان **مقصوداً ومعلوماً**، والخطر أن يقع
    بلا أن يراه صاحبه.
    """
    from app.api.v1.endpoints.portfolio import _get_holdings

    holdings = await _get_holdings(db)
    rows = [(float(h.market_value or 0), (h.company.company_name if h.company else "—"))
            for h in holdings if float(h.market_value or 0) > 0]
    total = sum(v for v, _ in rows)
    if total <= 0:
        return {"top3_pct": None, "reason": "لا مراكز قائمة."}

    rows.sort(reverse=True)
    top3 = rows[:3]
    top3_sum = sum(v for v, _ in top3)
    return {
        "top3_pct": _pct(top3_sum, total),
        "top1_pct": _pct(rows[0][0], total),
        "top1_name": rows[0][1],
        "names": [n for _, n in top3],
        "positions": len(rows),
        "market_value": round(total, 2),
        # عتبةٌ معلنة لا حكمٌ مبهم: فوقها يُلوَّن تنبيهاً، لا أكثر.
        "threshold_pct": 60.0,
    }


async def compute_performance(db) -> dict:
    """الحزمة الكاملة — نداءٌ واحد يخدم صفحة «قياس الأداء».

    كل مقياسٍ داخل حارسه: سقوط مصدرٍ واحد لا يُسقط الصفحة كلها (وهي علّةٌ
    وقعت في سياق المساعد فأسكتته تماماً)."""
    from app.services.portfolio_return import compute_cagr_pct

    snaps = await _snapshots(db)
    months = 0
    if len(snaps) >= 2:
        months = ((snaps[-1].snapshot_date.year - snaps[0].snapshot_date.year) * 12
                  + snaps[-1].snapshot_date.month - snaps[0].snapshot_date.month)

    # ── نطاقان مختلفان لا نطاق واحد ────────────────────────────────────────
    # المحفظة تبدأ بأول صفقة في السجل، واللقطات اليومية تبدأ يوم شُغّل التطبيق
    # — وقد يفصل بينهما شهور. فمن اشترى قبل سنة وبدأ التسجيل قبل شهر يرى TWR
    # لشهرٍ واحد ويقرأه عائدَ محفظته كلّها، ويرى أقصى تراجعٍ ضئيلاً لأن اللقطات
    # لم تشهد الهبوط أصلاً. وذلك تضليلٌ بالصمت: الرقم صحيحٌ ونطاقه مخفيّ.
    # فنُعلن النطاقين صراحةً، ونقول لكل مقياسٍ من أين يقيس.
    from sqlalchemy import select, func as _f
    from app.models.transaction import Transaction
    first_tx = (await db.execute(select(_f.min(Transaction.executed_at)))).scalar()
    inception = first_tx.date() if hasattr(first_tx, "date") else first_tx
    ledger_months = 0
    if inception and snaps:
        ledger_months = ((snaps[-1].snapshot_date.year - inception.year) * 12
                         + snaps[-1].snapshot_date.month - inception.month)
    gap_months = max(0, ledger_months - months)

    out: dict = {
        "history_months": months,
        "history_days": len(snaps),
        # «تحت التأسيس»: لا يُخفى المقياس ولا يُعرض رقمٌ مضلّل — يُعرض ومعه
        # تصريحٌ بأن تاريخه لم يكتمل. وهو ما تفعله الصناديق النظامية.
        "mature": months >= MATURITY_MONTHS,
        "maturity_months": MATURITY_MONTHS,
        # تأسيس المحفظة الحقيقي (أول صفقة) مقابل بداية التسجيل اليومي.
        "inception": inception.isoformat() if inception else None,
        "ledger_months": ledger_months,
        "snapshot_start": snaps[0].snapshot_date.isoformat() if snaps else None,
        # فجوةٌ ذات دلالة: مقاييس اللقطات لا ترى هذه الشهور إطلاقاً.
        "history_gap_months": gap_months,
        "snapshot_blind": gap_months >= 1,
    }

    async def _safe(key, coro):
        try:
            out[key] = await coro
        except Exception as e:                                   # noqa: BLE001
            out[key] = {"value": None, "reason": f"تعذّر الحساب: {e}"}

    await _safe("twr", compute_twr(db, snaps))
    await _safe("multiples", compute_multiples(db))
    await _safe("concentration", compute_concentration(db))
    try:
        _tw = out.get("twr") or {}
        _from = _tw.get("from")
        _sd = None
        if _from:
            from datetime import date as _d
            _sd = _d.fromisoformat(_from)
        out["drawdown"] = compute_drawdown(snaps, start_date=_sd)
    except Exception as e:                                       # noqa: BLE001
        out["drawdown"] = {"value": None, "reason": f"تعذّر الحساب: {e}"}
    try:
        out["xirr_pct"] = await compute_cagr_pct(db)
    except Exception:
        out["xirr_pct"] = None
    try:
        from app.services.portfolio_return import compute_production as _cp
        _p = await _cp(db)
        out["bonus"] = {"shares": _p["bonus_shares"],
                        "market_value": _p["bonus_market_value"],
                        "at_grant": _p["bonus_at_grant"]}
    except Exception:
        out["bonus"] = None
    try:
        from app.services.portfolio_return import compute_capital_recovery
        out["recovery"] = await compute_capital_recovery(db)
    except Exception:
        out["recovery"] = None
    return out
