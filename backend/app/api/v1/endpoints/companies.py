from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.response import success_response, error_response
from app.core.auth import require_owner
from app.models import Company
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter()

def _serialize(c: Company) -> dict:
    from app.services import maqasid
    r = maqasid.rating(c.symbol)
    sharia = r.get("status") if r else c.sharia_status
    purif = r.get("purification") if r else None
    sharia_source = r.get("source") if r else None
    return {
        "id": c.id,
        "symbol": c.symbol,
        "name": c.company_name,
        "name_ar": c.company_name,
        "company_name": c.company_name,
        "sector": c.sector,
        "industry": c.industry,
        "exchange": c.exchange,
        "currency": c.currency,
        "status": c.status,
        "sharia_status": sharia,
        "purification": purif,
        "sharia_source": sharia_source,
        "finance_score": float(c.finance_score or 0),
        "technical_score": float(c.technical_score or 0),
        "color": c.color,
        "logo_url": c.logo_url,
    }

class CompanyCreate(BaseModel):
    symbol: str
    name: Optional[str] = None
    company_name: Optional[str] = None
    name_ar: Optional[str] = None
    exchange: Optional[str] = None
    market: Optional[str] = None
    sector: Optional[str] = None
    currency: str = "SAR"
    notes: Optional[str] = None

    def resolved_name(self) -> str:
        # Arabic-first UI: prefer the Arabic name when provided.
        return self.name_ar or self.company_name or self.name or self.symbol

@router.get("")
async def get_companies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.status != "ARCHIVED"))
    companies = result.scalars().all()
    return success_response(data=[_serialize(c) for c in companies])

@router.get("/directory")
async def market_directory():
    """Full Saudi market directory (symbol / Arabic name / English name) from
    Sahmk's /companies/ — cached monthly. Powers company search autocomplete
    with the real, live list. Empty until a Sahmak API key is configured."""
    from app.services.sahmak_library import company_library
    data = await company_library()
    return success_response(data=data)

@router.post("")
async def add_company(data: CompanyCreate, db: AsyncSession = Depends(get_db)):
    from app.models.portfolio import Holding
    # Symbol is unique — an archived (deleted) company must be revivable,
    # and re-adding an active one is a friendly error, not a 500.
    existing = (await db.execute(select(Company).where(Company.symbol == data.symbol))).scalar_one_or_none()
    if existing:
        if existing.status != "ARCHIVED":
            raise HTTPException(status_code=400, detail="هذه الشركة موجودة بالفعل في المحفظة.")
        existing.status = "ACTIVE"
        existing.company_name = data.resolved_name()
        existing.sector = data.sector or existing.sector
        existing.exchange = data.exchange or data.market or existing.exchange
        existing.currency = data.currency
        has_holding = (await db.execute(select(Holding.id).where(Holding.company_id == existing.id))).scalar_one_or_none()
        if has_holding is None:
            db.add(Holding(company_id=existing.id, quantity=0, average_cost=0, invested_amount=0, market_value=0))
        await db.flush()
        # إعادة بناء الحيازة من سجلّها الباقي: الحذف أرشفةٌ لا محو، فعمليات
        # الشركة تبقى كاملةً وتعود معها. ولو أُنشئ صفّ حيازةٍ جديد (لأن القديم
        # فُقد بفورمات أو ترحيل) لظهرت الشركة بصفر سهمٍ رغم وجود عملياتها —
        # فيبدو السجل حاضراً والحيازة فارغة. إعادة التشغيل تُطابقهما دائماً.
        try:
            from app.api.v1.endpoints.transactions import recompute_holding
            await recompute_holding(db, existing.id)
        except Exception:
            pass
        await db.commit()
        await db.refresh(existing)
        return success_response(data=_serialize(existing), message="Company restored.")
    company = Company(
        symbol=data.symbol,
        company_name=data.resolved_name(),
        exchange=data.exchange or data.market,
        sector=data.sector,
        currency=data.currency,
        notes=data.notes,
    )
    db.add(company)
    await db.flush()
    # Every company gets a holding row immediately so it appears in the
    # portfolio table right away (with zero shares until a transaction).
    from app.models.portfolio import Holding
    db.add(Holding(company_id=company.id, quantity=0, average_cost=0,
                   invested_amount=0, market_value=0))
    await db.commit()
    await db.refresh(company)
    return success_response(data=_serialize(company), message="Company added successfully.")

@router.get("/{company_id}")
async def get_company(company_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    return success_response(data=_serialize(company))

@router.put("/{company_id}")
async def update_company(company_id: int, data: CompanyCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    company.symbol = data.symbol
    company.company_name = data.resolved_name()
    company.exchange = data.exchange or data.market or company.exchange
    company.sector = data.sector
    company.currency = data.currency
    await db.commit()
    await db.refresh(company)
    return success_response(data=_serialize(company), message="Company updated successfully.")

@router.delete("/{company_id}")
async def delete_company(company_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    company.status = "ARCHIVED"
    await db.commit()
    return success_response(message="Company archived successfully.")

@router.post("/sync-sharia")
async def sync_sharia(db: AsyncSession = Depends(get_db)):
    """Resolve Sharia-compliance for portfolio companies — once per company,
    ever (AI primary, Sahmak fallback). Already-resolved companies skipped."""
    from app.services.sharia_sync import sync_portfolio_sharia_status
    result = await sync_portfolio_sharia_status(db)
    return success_response(data=result, message="Sharia sync complete.")

@router.post("/{company_id}/resolve-sharia")
async def resolve_sharia(company_id: int, db: AsyncSession = Depends(get_db)):
    """Resolve one company's Sharia status on demand (when its stock page is
    opened). Once resolved it is stored and never fetched again."""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    # 1) Al-Maqasid (authoritative, offline, includes purification) — no call.
    from app.services import maqasid
    r = maqasid.rating(company.symbol)
    if r:
        return success_response(data={"sharia_status": r.get("status"),
                                      "purification": r.get("purification"),
                                      "source": r.get("source"), "cached": True})

    if company.sharia_status and str(company.sharia_status) not in ("UNKNOWN", "ShariaStatus.UNKNOWN"):
        return success_response(data={"sharia_status": company.sharia_status, "cached": True})

    # 2) AI (honest — returns UNKNOWN rather than guessing), 3) Sahmak fallback.
    from app.services.ai_sharia import ai_lookup_sharia_status
    from app.services.market_data import SahmakAdapter
    base = company.symbol.replace(".SR", "")
    status = None
    if base.isdigit():
        status = await ai_lookup_sharia_status(base, company.company_name)
        if not status:
            status = await SahmakAdapter().get_sharia_status(base)
    if status:
        company.sharia_status = status
        await db.commit()
    return success_response(data={"sharia_status": status, "source": "الذكاء الاصطناعي", "cached": False})




# ── نبذة نشاط الشركة (Yahoo وحده) ─────────────────────────────────────────
class CompanyProfileUpdate(BaseModel):
    """تحرير المالك للنبذة. None = لا تغيير؛ نصٌّ فارغ = عُد للجلب الآلي."""
    description: Optional[str] = None


@router.get("/by-symbol/{symbol}/profile")
async def get_company_profile_by_symbol(symbol: str, db: AsyncSession = Depends(get_db)):
    """النبذةُ نفسُها لورقةٍ يُبحث عنها في السوق ولا تملك صفّاً في المحفظة.

    ══ لغةُ عرضٍ واحدة ══ (بأمر المالك · D209)
    كانت النبذةُ والإدارةُ تظهران في صفحة الشركة المملوكة وحدَها، لأن
    المسارَ يطلب مُعرِّفَ صفٍّ في قاعدة البيانات. فرأى المالكُ شاشتين
    لشيءٍ واحد: إحداهما تعرّف بالشركة والأخرى لا.

    وإن كانت الورقةُ مملوكةً فصفُّها يُوجد بالرمز، فيُخدَم من المسار
    نفسِه بنصّ المالك المحفوظ — لا نسخةٌ ثانيةٌ من المنطق.
    """
    sym = (symbol or "").replace(".SR", "").strip()
    company = (await db.execute(
        select(Company).where(Company.symbol.in_([sym, f"{sym}.SR"])))).scalars().first()
    if company:
        return await get_company_profile(company.id, db)

    # لا صفَّ لها: تُبنى النبذةُ من ياهو مباشرةً بلا حفظٍ في قاعدة البيانات.
    from app.data.market_universe import MARKET_UNIVERSE
    meta = MARKET_UNIVERSE.get(sym) or {}
    payload = await _yahoo_profile(sym, meta.get("name_ar") or sym, meta.get("sector"))
    return success_response(data=payload)


async def _yahoo_profile(symbol: str, name: str, sector: str | None) -> dict:
    """نبذةٌ وإدارةٌ من ياهو — المنطقُ نفسُه الذي يخدم صفحةَ الشركة."""
    executives: list[dict] = []
    website = employees = description = None
    source = None
    try:
        from app.services.market_data import market_service
        ap = await market_service.get_asset_profile(symbol)
    except Exception:                                             # noqa: BLE001
        ap = None
    if ap:
        executives = ap.get("executives") or []
        for e in executives:
            e.setdefault("name_en", e.get("name"))
        try:
            from app.services.ai_content import exec_titles_ar, exec_names_ar
            tmap = await exec_titles_ar([e.get("title") for e in executives])
            if tmap:
                executives = [{**e, "title": tmap.get((e.get("title") or "").strip(), e.get("title"))}
                              for e in executives]
            nmap = await exec_names_ar([e.get("name") for e in executives])
            if nmap:
                executives = [{**e, "name": nmap.get((e.get("name_en") or "").strip(), e.get("name"))}
                              for e in executives]
        except Exception:                                         # noqa: BLE001
            pass
        website, employees = ap.get("website"), ap.get("employees")
        if ap.get("summary_en"):
            try:
                from app.services.ai_content import company_brief_ar
                brief = await company_brief_ar(name, ap["summary_en"], sector)
                if brief:
                    description, source = brief, "ai"
            except Exception:                                     # noqa: BLE001
                pass
            if not description:
                description, source = ap["summary_en"], "yahoo"
    return {"description": description, "description_source": source,
            "website": website, "employees": employees, "executives": executives}


@router.get("/{company_id}/profile")
async def get_company_profile(company_id: int, db: AsyncSession = Depends(get_db)):
    """نبذة نشاط الشركة وإدارتها التنفيذية — **من Yahoo حصراً**.

    المصدر واحد بأمر المالك: وحدة assetProfile في Yahoo. فما لا يوفّره Yahoo
    لا يُستجدى من مصدرٍ آخر ولا يُختلق — يُلغى عرضه ببساطة، وتُخفي الواجهة
    البطاقة كلها بدل أن تُبقي عنواناً فوق فراغ.

    ترتيب النبذة:
      ١) نصّ المالك المحفوظ (manual) — يتقدّم دائماً ولا يُستبدَل.
      ٢) وصف Yahoo الإنجليزي مُترجَماً بالذكاء (ai) — يُوسَم «مترجَمة آلياً»
         بلون تحذيري، فنصٌّ مترجَم لا يجوز أن يُقرأ كإفصاحٍ رسمي.
      ٣) الإنجليزي كما هو (yahoo) إن تعذّرت الترجمة — نصٌّ صادق أفضل من لا شيء،
         والواجهة تعرضه بـ dir=ltr فلا تنكسر العربية حوله.

    والإدارة التنفيذية (companyOfficers) **ليست مجلس الإدارة** — Yahoo لا
    يُوفّر تشكيل المجالس أصلاً، فقُصر العرض على ما يوفّره باسمه الصحيح.

    ما يُجلَب يُحفَظ في قاعدة البيانات، فلا يُنادى Yahoo ولا الذكاء إلا مرّة
    واحدة لكل شركة.
    """
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    description = (company.description or "").strip() or None
    source = company.description_source if description else None
    executives: list[dict] = []
    website = None
    employees = None

    ap = None
    try:
        from app.services.market_data import market_service
        ap = await market_service.get_asset_profile(company.symbol)
    except Exception:
        ap = None
    if ap:
        executives = ap.get("executives") or []
        # تعريب المسمّيات الوظيفية بنفس مسار النبذة. وما لا مقابل له يبقى
        # إنجليزياً بدل أن يُخترع له مسمّى.
        try:
            from app.services.ai_content import exec_titles_ar
            mapping = await exec_titles_ar([e.get("title") for e in executives])
            if mapping:
                executives = [{**e, "title": mapping.get((e.get("title") or "").strip(),
                                                         e.get("title"))}
                              for e in executives]
        except Exception:
            pass
        # وكتابة الأسماء بالحروف العربية — بأمر المالك. وهو نقلٌ صوتيّ لا
        # ترجمة، وأكثر هؤلاء سعوديّون فهو ردُّ الاسم إلى أصله لا اختراعُ صيغة.
        # ويُرسَل الاسم اللاتينيّ معه (`name_en`) فلا يضيع أصلُ ما يُبحث به،
        # وتعرضه الواجهة عند المرور. وفشلُ الذكاء يترك الاسم كما هو.
        for e in executives:
            e.setdefault("name_en", e.get("name"))
        try:
            from app.services.ai_content import exec_names_ar
            nmap = await exec_names_ar([e.get("name") for e in executives])
            if nmap:
                executives = [{**e, "name": nmap.get((e.get("name_en") or "").strip(),
                                                     e.get("name"))}
                              for e in executives]
        except Exception:
            pass
        website = ap.get("website")
        employees = ap.get("employees")

    if not description and ap and ap.get("summary_en"):
        try:
            from app.services.ai_content import company_brief_ar
            brief = await company_brief_ar(company.company_name, ap["summary_en"], company.sector)
            if brief:
                description, source = brief, "ai"
        except Exception:
            pass
        if not description:
            description, source = ap["summary_en"], "yahoo"

    # حفظ ما جُلب آلياً. لا يُلمس نصّ المالك (manual) — الشرط أعلاه يمنع الوصول
    # إلى هذا الفرع حين يكون محفوظاً أصلاً.
    if description and source and source != company.description_source:
        company.description = description
        company.description_source = source
        await db.commit()

    return success_response(data={
        "description": description,
        "description_source": source,
        "website": website,
        "employees": employees,
        # الإدارة التنفيذية — لا مجلس الإدارة. الاسم صريح كي لا يُخلطا.
        "executives": executives,
    })


@router.put("/{company_id}/profile", dependencies=[Depends(require_owner)])
async def update_company_profile(company_id: int, data: CompanyProfileUpdate,
                                 db: AsyncSession = Depends(get_db)):
    """تحرير المالك للنبذة. النصّ المحرَّر يُوسَم manual فيتقدّم على Yahoo ولا
    يُعاد جلبه. وإفراغه يُعيد الجلب الآلي في الطلب التالي لا يحذفه نهائياً."""
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    if data.description is not None:
        text = data.description.strip()
        if text:
            company.description = text
            company.description_source = "manual"
        else:
            company.description = None
            company.description_source = None

    await db.commit()
    await db.refresh(company)
    return success_response(data={
        "description": company.description,
        "description_source": company.description_source,
    }, message="تم الحفظ.")
