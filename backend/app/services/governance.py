"""
Portfolio-wide governance/oversight — one aggregate view across every
holding, answering the fiduciary question a governance page should
actually answer: "is my portfolio, as a whole, safe and under control?"

Deliberately distinct from the single-stock deep dive (AIPage's search,
CompanyPage's per-holding tabs): this never looks at one company at a
time — every number here is a roll-up across the whole portfolio, built
entirely from data already computed and persisted (Company.finance_score,
Company.sharia_status via the maqasid layer, cached get_financials for the
handful of held companies) — no new provider calls beyond normal cache
hits, so opening this page costs nothing extra.
"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.portfolio import Holding
from app.services import maqasid

# A single sector holding more than this share of the portfolio's value is
# flagged as a concentration risk — a common, reasonable rule-of-thumb
# threshold, not a fabricated one.
CONCENTRATION_THRESHOLD_PCT = 30.0


def _label_for_score(score: float) -> tuple[str, str]:
    """اللون يُعاد **كرمزٍ من نظام التصميم** لا كقيمة ثابتة.

    كان الخادم يُملي ألواناً سداسية مصمَّمة لخلفيةٍ داكنة، فتصل الواجهة جاهزة
    ويعجز نظام المظاهر عن تصحيحها: «تحتاج مراجعة» كان 3.41:1 على الورق الفاتح
    — أضعف نصٍّ في الشاشة وهو يحمل حكم المحفظة كلّها. الرمز يترك القرار
    اللوني للواجهة، ويظلّ العقد نفسه (سلسلة لون CSS صالحة)."""
    if score >= 70:
        return "مستقرة وآمنة", "var(--pos-ink)"
    if score >= 50:
        return "مستقرة بشكل عام مع نقاط تحتاج متابعة", "var(--warn-ink)"
    return "تحتاج مراجعة", "var(--neg-ink)"


def _rule_governance_narrative(overall_score, label, rows, sectors, sharia_counts) -> str:
    """Deterministic positive-leaning ONE-LINE description of the portfolio's
    governance — the permanent reliability floor beneath the AI narrative.
    Leads with the state + strongest holdings; adds compliance if it applies.
    Always available, no API, no quota."""
    scored = [r for r in rows if r["finance_score"] is not None]
    # المفتاحُ يحمل حارسَه ولو كان المصدرُ مُرشَّحاً أعلاه: الأمانُ الذي
    # يعتمد على سطرٍ بعيد يسقط أوّلَ ما يُعاد ترتيبُ السطرين. (D167)
    leaders = sorted([r for r in scored if (r["finance_score"] or 0) >= 70],
                     key=lambda r: -(r["finance_score"] or 0))[:2]
    line = f"محفظتك {label} بدرجة {overall_score}/100"
    if leaders:
        line += "، بقيادة " + " و".join(r["name"] for r in leaders)
    if scored and not sharia_counts.get("NON_COMPLIANT"):
        line += "، وجميع مراكزها متوافقة شرعياً"
    return line + "."


async def get_portfolio_governance(db) -> dict:
    from app.api.v1.endpoints.holdings import refresh_holdings_prices, yahoo_symbol
    from app.services.market_data import market_service

    result = await db.execute(select(Holding).options(selectinload(Holding.company)))
    holdings = [h for h in result.scalars().all() if h.company and h.company.status != "ARCHIVED"]
    await refresh_holdings_prices(db, holdings)

    total_value = sum(float(h.market_value or 0) for h in holdings)
    if not holdings or total_value <= 0:
        return {
            "has_data": False,
            "companies_count": len(holdings),
        }

    sector_values: dict[str, float] = {}
    sharia_counts = {"COMPLIANT": 0, "NON_COMPLIANT": 0, "UNKNOWN": 0}
    rows = []
    weighted_score_sum = 0.0
    scored_value = 0.0
    attention: list[dict] = []

    for h in holdings:
        c = h.company
        value = float(h.market_value or 0)
        weight_pct = round(value / total_value * 100, 1) if total_value else 0
        sector = c.sector or "غير مصنّف"
        sector_values[sector] = sector_values.get(sector, 0) + value

        r = maqasid.rating(c.symbol)
        sharia = (r.get("status") if r else c.sharia_status) or "UNKNOWN"
        sharia_counts[sharia] = sharia_counts.get(sharia, 0) + 1
        if sharia == "NON_COMPLIANT":
            attention.append({
                "severity": "high", "symbol": c.symbol, "name": c.company_name,
                "message": "غير متوافقة شرعياً",
            })

        # ONE source of truth: the exact same governance engine the per-company
        # panel (✨) uses — evaluate_company. The portfolio row's score/decision
        # is therefore always identical to what its own panel shows; there is
        # no second, drifting computation here anymore.
        score = None
        insufficient = False
        try:
            from app.services.governance_engine import evaluate_company
            status_value = c.status.value if hasattr(c.status, "value") else c.status
            gov = await evaluate_company(yahoo_symbol(c.symbol), db=db, company_status=status_value, sector=c.sector)
            if gov:
                insufficient = gov.get("evaluable") is False
                score = gov.get("finance_score")  # already None when abstaining
        except Exception as e:
            from loguru import logger
            logger.debug(f"governance evaluate_company failed for {c.symbol}: {e}")

        # Fall back to the stored score only when we simply lack live data —
        # NOT when we deliberately abstained (insufficient data): showing a
        # stale grade there would defeat the whole point.
        if score is None and not insufficient and c.finance_score is not None:
            score = float(c.finance_score)

        if score is not None:
            weighted_score_sum += score * value
            scored_value += value
            if score < 45:
                attention.append({
                    "severity": "high", "symbol": c.symbol, "name": c.company_name,
                    "message": f"درجة سلامة مالية منخفضة ({round(score)}/100)",
                })
            elif score < 60:
                attention.append({
                    "severity": "medium", "symbol": c.symbol, "name": c.company_name,
                    "message": f"درجة سلامة مالية متوسطة ({round(score)}/100)",
                })

        rows.append({
            "id": c.id,
            "symbol": c.symbol,
            "name": c.company_name,
            "sector": sector,
            "finance_score": score,
            "insufficient_data": insufficient,
            "sharia_status": sharia,
            "weight_pct": weight_pct,
            "market_value": value,
            "total_dividends_received": float(h.total_dividends_received or 0),
        })

    overall_score = round(weighted_score_sum / scored_value) if scored_value > 0 else None
    label, color = _label_for_score(overall_score) if overall_score is not None else ("بيانات غير كافية", "var(--ink-muted)")

    unscored = [h for h in holdings if float(h.market_value or 0) > 0
                and not any(r["symbol"] == h.company.symbol and r["finance_score"] is not None for r in rows)]
    sectors = sorted(
        [{"sector": s, "value": v, "weight_pct": round(v / total_value * 100, 1)} for s, v in sector_values.items()],
        key=lambda x: -x["value"],
    )
    if sectors and sectors[0]["weight_pct"] >= CONCENTRATION_THRESHOLD_PCT:
        attention.append({
            "severity": "medium", "symbol": None, "name": None,
            "message": f"تركّز مرتفع في قطاع {sectors[0]['sector']} ({sectors[0]['weight_pct']}% من المحفظة)",
        })

    # A narrative describing the governance state — رأي الذكاء الاصطناعي أولاً
    # (نبرة إيجابية بنّاءة)، والذكاء القاعدي احتياطاً إن غاب المفتاح/تعذّرت
    # الاستجابة، فالوصف لا يفشل أبداً. يحل محل السطور السلبية القديمة.
    if overall_score is None:
        narrative = "لا تتوفر درجات حوكمة بعد لأي شركة في المحفظة — يظهر الوصف فور توفّرها."
    else:
        all_compliant = not sharia_counts.get("NON_COMPLIANT")
        narrative = None
        try:
            from app.services.ai_content import governance_narrative
            narrative = await governance_narrative(overall_score, label, rows, sectors, all_compliant)
        except Exception as e:
            from loguru import logger
            logger.debug(f"AI governance narrative failed, using rule-based: {e}")
        if not narrative:
            narrative = _rule_governance_narrative(overall_score, label, rows, sectors, sharia_counts)

    rows.sort(key=lambda r: (r["finance_score"] is None, r["finance_score"] or 0))
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    attention.sort(key=lambda a: severity_rank.get(a["severity"], 3))

    return {
        "has_data": True,
        "companies_count": len(holdings),
        "overall_score": overall_score,
        "overall_label": label,
        "overall_color": color,
        "overall_narrative": narrative,
        "sharia": sharia_counts,
        "sectors": sectors,
        "holdings": rows,
        "attention": attention,
    }


async def get_sector_map(db) -> dict:
    """One payload powering the clickable Sector Performance map: EVERY sector
    from the unified directory, each with ALL its companies (name + logo),
    today's move, and the SAME governance score shown in the Governance
    page's market tab. Scores come from the market-governance scan (non-held)
    + the stored Company.finance_score (held) — so no company is missing a
    score it already has. Companies with truly insufficient data carry a null
    score (rendered as «لا ينطبق»)."""
    from collections import defaultdict
    from sqlalchemy import select as _select
    from app.models.portfolio import Company
    from app.data.saudi_directory import SAUDI_DIRECTORY
    from app.services.market_movers import get_cached_market_movers

    # 1) governance scores — exactly the market-tab source (+ held from DB).
    # Cache-ONLY: never trigger the heavy Yahoo scan from here (it would risk a
    # rate-limit/timeout and make the map fail to load). If the market scan
    # isn't warm yet, warm it in the BACKGROUND and serve held scores now.
    score: dict[str, float] = {}
    try:
        market = await get_market_governance(db, compute=False)
        if market is None:
            import asyncio
            from app.core.database import AsyncSessionLocal

            async def _warm():
                try:
                    async with AsyncSessionLocal() as bg:
                        await get_market_governance(bg, compute=True)
                except Exception:
                    pass
            asyncio.create_task(_warm())
        for o in (market or {}).get("opportunities", []):
            if o.get("finance_score") is not None:
                score[str(o["symbol"]).replace(".SR", "")] = float(o["finance_score"])
    except Exception as e:
        from loguru import logger
        logger.debug(f"sector-map: market governance unavailable: {e}")
    for sym, fs in (await db.execute(_select(Company.symbol, Company.finance_score))).all():
        if fs is not None:
            score[str(sym).replace(".SR", "")] = float(fs)
    # ══ الحكمُ العميق المحفوظ مصدرٌ ثالث ══
    # مفتاحُ كاش مسح السوق يحمل نسخةَ القواعد، فكلُّ تعديلٍ في ملفّ القواعد
    # يُبطله — وتبقى خريطةُ القطاعات فارغةً حتى يكتمل مسحٌ جديد لأربعمئة
    # شركة، وهو محكومٌ بحصّة المصدر فقد يتأخّر يوماً. فيرى المالك «لا
    # ينطبق» في الخريطة بينما صفحةُ الشركة تعرض درجتها.
    # ومخزنُ `governance:deep` لا يحمل نسخةَ قواعد ولا ينقضي، فيُقرأ ثالثاً
    # لكلّ رمزٍ لم تصل درجتُه من المصدرين الأوّلين.
    try:
        from app.services import lastgood as _lg
        for sym, row in (_lg.load("governance:deep") or {}).items():
            if sym not in score and (row or {}).get("finance_score") is not None:
                score[str(sym)] = float(row["finance_score"])
    except Exception:                                             # noqa: BLE001
        pass

    # 2) today's move — from the cached market scan (no extra provider calls).
    stocks = (get_cached_market_movers() or {}).get("stocks", {}) or {}

    # 3) group the WHOLE directory by sector.
    by_sector: dict[str, list] = defaultdict(list)
    for sym, v in SAUDI_DIRECTORY.items():
        sec = v.get("sector") or "غير مصنّف"
        by_sector[sec].append({
            "symbol": sym,
            "name": v.get("name") or sym,
            "logo_url": v.get("logo"),
            "finance_score": score.get(sym),
            "change_pct": stocks.get(sym),
        })

    sectors = []
    for sec, comps in by_sector.items():
        chgs = [c["change_pct"] for c in comps if c["change_pct"] is not None]
        scored = [c["finance_score"] for c in comps if c["finance_score"] is not None]
        comps.sort(key=lambda c: (c["finance_score"] is None, -(c["finance_score"] or 0)))
        sectors.append({
            "sector": sec,
            "count": len(comps),
            "scored_count": len(scored),
            "avg_change_pct": round(sum(chgs) / len(chgs), 2) if chgs else None,
            "avg_score": round(sum(scored) / len(scored)) if scored else None,
            "companies": comps,
        })
    sectors.sort(key=lambda s: (s["avg_change_pct"] is None, -(s["avg_change_pct"] if s["avg_change_pct"] is not None else -999)))
    return {"has_data": True, "sectors": sectors}


async def get_market_governance(db, compute: bool = True) -> dict | None:
    """السوق mode — the SAME weighted, disciplined methodology (real
    multi-year financial-statement score + شرعية status), but scanning the
    site's own read-only market universe (~395 symbols, app/data/
    market_universe.py) instead of just what's already held — for spotting
    new opportunities, not just auditing existing ones. Deliberately never
    touches the Company/Holding tables (no DB writes, no new rows created)
    so this can never repeat the directory-ghost-company incident; it's a
    pure read/compute view over static data + cached provider calls.
    Companies already held are excluded — this is for what's NOT yet in
    the portfolio."""
    import asyncio
    from sqlalchemy import select as _select
    from app.models.portfolio import Company, Holding
    from app.data.market_universe import MARKET_UNIVERSE
    from app.services.analysis import analyze_company
    from app.api.v1.endpoints.holdings import yahoo_symbol

    from app.services import cache
    held_symbols = set((await db.execute(
        _select(Company.symbol).join(Holding, Holding.company_id == Company.id)
        .where(Holding.quantity > 0)
    )).scalars().all())

    # Scanning ~395 companies' financial statements is real work even with
    # concurrency — cached for 2h so switching the toggle back and forth
    # doesn't repeat it, without going as stale as the 24h per-symbol
    # analysis cache underneath it.
    # Include the governance-rules version so ANY rules edit (e.g. the REIT
    # scoring change) busts this whole-market cache immediately — otherwise
    # the market REITs/companies keep serving pre-change scores for up to the
    # cache TTL even though the per-symbol analysis underneath already updated.
    from app.services.governance_rules import rules_version
    ck = f"governance:market:v2:{rules_version()}:" + ",".join(sorted(held_symbols))
    cached = cache.get(ck)
    if cached is not None:
        return cached
    # Cache-only callers (e.g. the sector map) must NOT trigger the heavy
    # ~380-company Yahoo scan synchronously — that risks a rate-limit/timeout
    # and would make the caller fail to load. They warm it in the background.
    if not compute:
        return None

    candidates = [(sym, meta) for sym, meta in MARKET_UNIVERSE.items() if sym not in held_symbols]

    sem = asyncio.Semaphore(15)

    async def _score_one(sym: str, meta: dict) -> dict | None:
        async with sem:
            try:
                # Market-wide scan (~395 companies) NEVER spends the scarce
                # Sahmak quota — Yahoo + Phase-A enrichment only; the
                # abstention gate honestly handles anything still too thin.
                a = await analyze_company(yahoo_symbol(sym), meta.get("name_ar") or sym, db=db, allow_supplement=False)
            except Exception:
                a = None
        # الحكم العميق المحفوظ يسبق: إن كانت الشركة قد فُحصت بعمقٍ من قبل
        # (فتح المالك صفحتها) فحكمُها معروف، ولا معنى لأن تقول الخريطة عنها
        # «لا ينطبق» بينما صفحتها تعرض درجة.
        deep = None
        try:
            from app.services import lastgood
            deep = ((lastgood.load("governance:deep") or {})
                    .get(str(sym).replace(".SR", "")))
        except Exception:                                         # noqa: BLE001
            deep = None
        if not a:
            if not deep:
                return None
            a = {"financial": {"score": deep.get("finance_score")},
                 "ai_score": deep.get("ai_score"), "decision": deep.get("decision"),
                 "price": None}
        fin = a.get("financial") or {}
        score = fin.get("score")
        if score is None and deep:
            score = deep.get("finance_score")
            a = {**a, "ai_score": a.get("ai_score") or deep.get("ai_score"),
                 "decision": a.get("decision") or deep.get("decision")}
        # ══ الشركةُ تبقى ولو تعذّرت درجتُها ══ (بأمر المالك)
        # كان الصفُّ يُسقط كلَّه حين تتعذّر الدرجة، فتختفي الشركة من
        # الخريطة اختفاءً تامّاً بينما صفحتُها تعرض درجةً — وهو أسوأ من
        # «لا ينطبق»: الغيابُ لا يُفسَّر ولا يُسأل عنه، والمالك يظنّ
        # القائمة تامّة وفيها ثغرة.
        # وقال المالك إن كل شركةٍ مدرجة **مُلزَمة** بإيداع قوائمها وإلا
        # شُطبت، فتعذُّرُ الدرجة ليس صفةً في الشركة بل نقصٌ في مصدرنا.
        # فيبقى الصفُّ موسوماً بـ`insufficient_data` — وهو الوسم نفسه
        # الذي تعرفه الواجهة أصلاً في صفوف المحفظة، فتُظهر «—».
        if score is None:
            r = maqasid.rating(sym)
            return {
                "symbol": sym,
                "name": meta.get("name_ar") or sym,
                "sector": meta.get("sector") or "غير مصنّف",
                "logo_url": meta.get("logo_url"),
                "finance_score": None,
                "insufficient_data": True,
                "sharia_status": (r.get("status") if r else None) or "UNKNOWN",
                "price": (a or {}).get("price"),
                "ai_score": None,
                "decision": None,
                "fair_value": (a or {}).get("fair_value"),
                "fair_value_upside_pct": (a or {}).get("fair_value_upside_pct"),
                "governance_standard": ((a or {}).get("governance_standard") or {}).get("name"),
            }
        r = maqasid.rating(sym)
        sharia = (r.get("status") if r else None) or "UNKNOWN"
        return {
            "symbol": sym,
            "name": meta.get("name_ar") or sym,
            "sector": meta.get("sector") or "غير مصنّف",
            "logo_url": meta.get("logo_url"),
            "finance_score": score,
            "insufficient_data": False,
            "sharia_status": sharia,
            "price": a.get("price"),
            "ai_score": a.get("ai_score"),
            "decision": a.get("decision"),
            # ══ القيمة العادلة تُحمل مع الصفّ ══ (بأمر المالك)
            # سأل: أجاهزٌ القرارُ لكل شركةٍ في السوق أم لِما أملك؟ وكانت
            # القيمة العادلة تُحسب في مسح السوق نفسه ثم تُهمل عند تركيب
            # الصفّ، فلا تظهر إلا لمن يفتح صفحة الشركة واحدةً واحدة.
            # وحملُها هنا يجعل الفرز على «الأرخص من قيمته» ممكناً للسوق
            # كلّه، ويجعل التغطية قابلةً للقياس بدل الادّعاء.
            "fair_value": a.get("fair_value"),
            "fair_value_upside_pct": a.get("fair_value_upside_pct"),
            "governance_standard": ((a.get("governance_standard") or {}).get("name")),
        }

    results = await asyncio.gather(*(_score_one(sym, meta) for sym, meta in candidates))
    rows = [r for r in results if r is not None]
    # ══ الصفُّ بلا درجةٍ يُفرَز آخِراً ولا يُسقط الفرزَ كلَّه ══ (D167)
    # قُضي أعلاه — بأمر المالك — أن تبقى الشركةُ في الخريطة ولو تعذّرت
    # درجتُها، لأنّ غيابَها لا يُفسَّر. لكنّ الفرزَ بقي يقارن الدرجةَ خاماً،
    # و`None < None` يرفع TypeError. فمتى تعذّرت الدرجةُ على شركتين
    # **سقط تبويبُ السوق كلُّه** — مقيسٌ على الخادم: مسارٌ لا يردّ شيئاً.
    # والمفتاحُ الثنائيّ يُبقي المُدرَجَ أوّلاً تنازلياً ويدفع المتعذَّرَ إلى
    # الذيل، وهو النمطُ المستعمَل أصلاً في هذا الملفّ (سطرا ‎176 و‎269) —
    # فالعطبُ أنّ موضعاً واحداً تخلّف عنه.
    rows.sort(key=lambda r: (r.get("finance_score") is not None,
                             r.get("finance_score") or 0), reverse=True)

    result = {
        "has_data": bool(rows),
        "scanned_count": len(candidates),
        "scored_count": len(rows),
        "excluded_held_count": len(held_symbols),
        "opportunities": rows,
    }
    # الحوكمة تتغيّر ببطء (قوائم مالية سنوية/ربعية + قواعد ثابتة) — تخزين
    # يومي يكفي تماماً، وإبطال الكاش يجري تلقائياً عبر rules_version في المفتاح
    # عند تعديل القواعد، وعبر المجدول اليومي الذي يعيد حساب الدرجات.
    cache.set(ck, result, 24 * 60 * 60)
    return result
