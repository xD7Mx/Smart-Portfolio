import asyncio
import json
import os
import httpx
from fastapi import APIRouter, Depends, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.core.database import get_db
from app.core.response import success_response
from app.core.config import settings as cfg
from app.core.auth import require_owner

router = APIRouter()
# مسارات عامة (بلا مصادقة): يحتاجها شاشة القفل قبل الدخول لعرض صورة المستخدم
# واسمه الترحيبي (كنمط ماك). القراءة فقط؛ الكتابة تبقى محميّة على router.
public_router = APIRouter()


# ── تخطيط القائمة الجانبية: يُحفظ على الخادم لا في متصفح كل جهاز، فيتوحّد
#    ترتيب الأقسام وظهورها وصفحة البداية عبر كل المنصات (جوال/كمبيوتر). ──
_LAYOUT_PATH = "/app/data/layout.json" if os.path.isdir("/app/data") else os.path.join(os.getcwd(), "layout.json")


# ── تاريخ بداية المشروع: مقام الزمن في «العائد المركّب» ───────────────
@router.get("/project-start")
async def get_project_start_ep():
    from app.services.project_start import get_project_start
    d = get_project_start()
    return success_response(data={"start_date": d.isoformat() if d else None})


@router.post("/project-start")
async def set_project_start_ep(payload: dict, _: None = Depends(require_owner)):
    from app.services.project_start import set_project_start
    from fastapi import HTTPException
    try:
        d = set_project_start(payload.get("start_date"))
    except Exception:
        # كان يُعاد «نجاح» مع رسالة خطأ، فتظنّ الواجهة أن التاريخ حُفظ.
        raise HTTPException(status_code=400, detail="تاريخ غير صالح أو في المستقبل.")
    return success_response(data={"start_date": d.isoformat() if d else None},
                            message="تم حفظ تاريخ بداية المشروع.")


@router.get("/layout")
async def get_layout():
    try:
        with open(_LAYOUT_PATH, encoding="utf-8") as f:
            return success_response(data=json.load(f))
    except Exception:
        return success_response(data=None)


# الحقول المعروفة للتخطيط — مكانٌ واحد يُضاف إليه، فلا يُنسى حقلٌ في
# الحفظ ويُذكر في القراءة.
_LAYOUT_FIELDS = ("pageOrder", "hiddenPages", "startPage",
                  "layouts", "activeLayout", "portfolioCols")


@router.post("/layout")
async def save_layout(payload: dict, _: None = Depends(require_owner)):
    """يحفظ التخطيط **دمجاً لا استبدالاً**. للمالك فقط.

    ══ العطب الذي كان هنا ══
    كان كل حفظٍ يكتب الملف من أوّله بحقول الحمولة وحدها، وما لم يُذكر فيها
    يُكتب `null`. فأيّ عميلٍ يحفظ جزءاً — كأن يبدّل عمود جدولٍ فقط —
    **يمحو ترتيب القائمة وصفحة البداية وشبكة لوحة التحكّم معاً**.
    ولم يظهر لأن الواجهة كانت تُرسل كل الحقول في كل نداء؛ فالعطب نائمٌ
    ينتظر عميلاً واحداً ينسى حقلاً. قِيس بحفظ الأعمدة وحدها فسقط الباقي.
    فالآن: ما لم يُذكر يبقى كما هو، وما ذُكر يُكتب.
    """
    try:
        with open(_LAYOUT_PATH, encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        data = {}
    for k in _LAYOUT_FIELDS:
        if k in payload and payload[k] is not None:
            data[k] = payload[k]
    try:
        os.makedirs(os.path.dirname(_LAYOUT_PATH), exist_ok=True)
        with open(_LAYOUT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return success_response(data=data, message="تم حفظ التخطيط.")
    except Exception as e:
        logger.warning(f"save_layout failed: {e}")
        return success_response(data=None, message="تعذّر حفظ التخطيط.")


# ── الملف الشخصي: اسم العرض + صورة رمزية، تُحفظ على الخادم (تُقرأ عامّةً
#    لعرض الترحيب، وتُكتب للمالك فقط). تعيش خارج قاعدة البيانات كملفّات. ──
_DATA_DIR = "/app/data" if os.path.isdir("/app/data") else os.getcwd()
_PROFILE_PATH = os.path.join(_DATA_DIR, "profile.json")
_AVATAR_PATH = os.path.join(_DATA_DIR, "avatar.img")


@public_router.get("/server-time")
async def get_server_time():
    """الوقت الرسمي للتطبيق من الخادم مباشرةً (توقيت مكة) — مصدر الحقيقة الواحد
    الذي تعتمده لقطات المحفظة والتدوير اليومي وأطوار السوق. تُرسّخ الواجهة ساعتها
    عليه فتُطابقه حتى لو كانت ساعة جهاز المستخدم مغلوطة. عام (بلا مصادقة) ليعمل
    حتى على شاشة القفل. epoch_ms بتوقيت UTC + الإزاحة، وحالة السوق محسوبة خادميًّا."""
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc)
    local = datetime.now()   # عملية الخادم مضبوطة على مكة (main.py)
    wd = local.weekday()     # الإثنين=0 … الأحد=6
    # الأحد–الخميس تداولاً: نحوّل لترقيم أسبوع يبدأ بالأحد (0=الأحد).
    dow_sun0 = (wd + 1) % 7
    mins = local.hour * 60 + local.minute
    # القاعدةُ في `services/market_phase.py` — موضعٌ واحدٌ يقيسه الفحص،
    # بدل أوقاتٍ مكتوبةٍ في نقطةٍ لا تُستدعى إلا عبر الشبكة (‏D215).
    from app.services.market_phase import market_phase
    status = market_phase(dow_sun0, mins)
    # ══ والعطلةُ لا تعرفها الساعة ══ (D413 · بأمر المالك)
    # «اليومَ كان عطلةً للسوق ولم يكتشف التطبيقُ ذلك». والساعةُ تقول
    # الأحدَ إلى الخميس «مفتوح» في أوقاته، فالأعيادُ والعطلُ الرسميةُ
    # والإغلاقاتُ الطارئةُ خارجَ حسابها. فتُسأل حالةُ السوق من مصدرها
    # أوّلاً (‏`market_state`)، وتبقى الساعةُ احتياطاً **مُعلَناً**.
    _src, _ev = "ساعةُ الخادم", None
    try:
        from app.services.market_state import market_state
        _st = await market_state()
        status = _st.get("status") or status
        _src = _st.get("source")
        # والسببُ يُرسَل حين **يزيد** على ما يعرفه التقويم — يومَ عطلةٍ
        # أو إغلاقٍ طارئٍ أو حين ينطق المصدرُ بحالته. أمّا اليومُ العاديُّ
        # الذي حكمته الساعةُ احتياطاً فلا سببَ يُعرَض: سطرٌ لا يضيف حشوٌ،
        # والميثاقُ يمنع الحواشي التي تُقرأ ولا تُفيد.
        _ev = (_st.get("evidence")
               if _st.get("source") != "ساعةُ الخادم (احتياط)" else None)
    except Exception:                                             # noqa: BLE001
        pass
    return success_response(data={
        "epoch_ms": int(now_utc.timestamp() * 1000),  # UTC، تُحوّلها الواجهة لمكة
        "offset_minutes": 180,                          # مكة = UTC+3 ثابت
        "iso_local": local.strftime("%Y-%m-%dT%H:%M:%S"),
        "market_status": status,
        # ولا كلمةَ بلا سندها: من قال، وبأيّ دليل.
        "market_status_source": _src,
        "market_status_evidence": _ev,
    })


@public_router.get("/profile")
async def get_profile():
    name = ""
    try:
        with open(_PROFILE_PATH, encoding="utf-8") as f:
            name = (json.load(f) or {}).get("name", "")
    except Exception:
        pass
    return success_response(data={"name": name, "has_avatar": os.path.exists(_AVATAR_PATH)})


@router.post("/profile")
async def save_profile(payload: dict, _: None = Depends(require_owner)):
    """اسم العرض فقط (ترحيبي، ليس سرًّا) — بحدّ ٤٠ حرفًا."""
    name = (str(payload.get("name") or "")).strip()[:40]
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump({"name": name}, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"save_profile failed: {e}")
    return success_response(data={"name": name}, message="تم حفظ الملف الشخصي.")


@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), _: None = Depends(require_owner)):
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        from fastapi import HTTPException
        raise HTTPException(400, "حجم الصورة كبير (الحدّ ٥ ميجابايت).")
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_AVATAR_PATH, "wb") as f:
            f.write(raw)
    except Exception as e:
        logger.warning(f"upload_avatar failed: {e}")
        from fastapi import HTTPException
        raise HTTPException(500, "تعذّر حفظ الصورة.")
    return success_response(data={"has_avatar": True}, message="تم حفظ الصورة.")


@public_router.get("/avatar")
async def get_avatar():
    from fastapi.responses import FileResponse, Response
    if os.path.exists(_AVATAR_PATH):
        return FileResponse(_AVATAR_PATH, media_type="image/jpeg")
    return Response(status_code=404)


@router.delete("/avatar")
async def delete_avatar(_: None = Depends(require_owner)):
    """حذف الصورة الشخصية نهائيًا — يعود التطبيق لإظهار أيقونة المحفظة تلقائيًا
    (في الأعلى وفي شاشة القفل)."""
    try:
        if os.path.exists(_AVATAR_PATH):
            os.remove(_AVATAR_PATH)
    except Exception as e:
        logger.warning(f"delete_avatar failed: {e}")
        from fastapi import HTTPException
        raise HTTPException(500, "تعذّر حذف الصورة.")
    return success_response(data={"has_avatar": False}, message="حُذفت الصورة.")


# ── Real connectivity checks for each external integration ──────
async def _check_yahoo() -> dict:
    """Live check: fetch a well-known symbol via Yahoo Finance."""
    if not cfg.YAHOO_FINANCE_ENABLED:
        return {"status": "disabled", "detail": "Disabled in settings"}
    # Query Yahoo's public chart API directly (more reliable than the yfinance lib,
    # which frequently breaks when Yahoo changes its internal endpoints).
    headers = {"User-Agent": "Mozilla/5.0"}
    for sym in ("2222.SR", "1120.SR", "AAPL", "MSFT"):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1d&interval=1d"
            async with httpx.AsyncClient(timeout=6, headers=headers) as client:
                r = await client.get(url)
            if r.status_code == 200:
                result = r.json().get("chart", {}).get("result")
                if result:
                    price = result[0].get("meta", {}).get("regularMarketPrice")
                    if price:
                        return {"status": "up", "detail": f"{sym} = {round(float(price), 2)}"}
        except Exception:
            continue
    return {"status": "down", "detail": "No price returned"}


async def _check_gemini() -> dict:
    """Check Gemini key by listing models (light, no generation quota)."""
    if not cfg.AI_API_KEY:
        return {"status": "not_configured", "detail": "No API key set"}
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={cfg.AI_API_KEY}"
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(url)
        if r.status_code == 200:
            return {"status": "up", "detail": "Key valid"}
        return {"status": "down", "detail": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "down", "detail": str(e)[:120]}


async def _check_sahmak() -> dict:
    """Check Sahmak provider key/connectivity."""
    if not cfg.SAHMAK_API_KEY:
        return {"status": "not_configured", "detail": "No API key set"}
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(
                cfg.SAHMAK_BASE_URL,
                headers={"Authorization": f"Bearer {cfg.SAHMAK_API_KEY}"},
            )
        if r.status_code < 500:
            return {"status": "up", "detail": f"Reachable (HTTP {r.status_code})"}
        return {"status": "down", "detail": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "down", "detail": str(e)[:120]}


def _gemini_quota() -> dict:
    try:
        from app.agents.coordinator import coordinator
        q = coordinator.quota_status()
        return {"daily_used": q.get("daily_used", 0), "daily_limit": cfg.GEMINI_DAILY_LIMIT}
    except Exception:
        return {"daily_used": 0, "daily_limit": cfg.GEMINI_DAILY_LIMIT}


# Cache the health-check result so the settings page auto-refresh (every 30s) does
# NOT hammer the providers on every load — this protects paid quotas (e.g. Sahmak
# 100/day) and avoids triggering Yahoo rate-limits. Providers are re-checked at most
# once per _HEALTH_TTL seconds regardless of how many clients are watching.
import time as _time
_health_cache = {"ts": 0.0, "data": None}
_HEALTH_TTL = 120  # seconds


@router.get("/integrations")
async def get_integrations(refresh: bool = False):
    """Health status + usage quota of every data source. Cached for _HEALTH_TTL
    seconds so it never drains provider quotas. Pass ?refresh=true to force a live check."""
    from app.services.usage_tracker import usage

    now = _time.time()
    if not refresh and _health_cache["data"] and (now - _health_cache["ts"] < _HEALTH_TTL):
        cached = _health_cache["data"]
    else:
        async def _safe(coro):
            try:
                return await asyncio.wait_for(coro, timeout=8)
            except Exception as e:
                return {"status": "down", "detail": str(e)[:120] or "Timeout"}

        yahoo, gemini, sahmak = await asyncio.gather(
            _safe(_check_yahoo()), _safe(_check_gemini()), _safe(_check_sahmak())
        )
        cached = {"yahoo": yahoo, "gemini": gemini, "sahmak": sahmak}
        _health_cache["ts"] = now
        _health_cache["data"] = cached

    # Quota counters are always live (cheap, in-memory) even when health is cached.
    yahoo = {**cached["yahoo"], **usage("yahoo")}
    sahmak = {**cached["sahmak"], **usage("sahmak")}
    gemini = {**cached["gemini"], **_gemini_quota()}

    data = [
        {"id": "yahoo",  "name": "Yahoo Finance", "name_ar": "ياهو المالية", "kind": "market", **yahoo},
        {"id": "sahmak", "name": "Sahmak",        "name_ar": "سهمك",         "kind": "market", **sahmak},
        {"id": "gemini", "name": "AI Engine",     "name_ar": "الذكاء الاصطناعي", "kind": "ai",   **gemini},
    ]
    return success_response(data=data)

def _serial() -> str:
    """رقم تسلسلي ثابت يميّز كل نسخة من المحفظة: SP-XXX-A (الأساسية) وSP-XXX-B
    (النسخة الثانية). الجزء الأوسط مشتقّ بثبات من SECRET_KEY (يختلف تلقائياً
    بين النسختين ولا يتغيّر بعد ذلك)، والوسم من SP_COPY. لا يتعدى 8 خانات."""
    import hashlib
    mid = hashlib.sha256((cfg.SECRET_KEY or "x").encode()).hexdigest()[:6]
    mid3 = str(int(mid, 16))[-3:].rjust(3, "0")  # ثلاثة أرقام ثابتة
    tag = (cfg.SP_COPY or "A").strip().upper()[:1] or "A"
    return f"SP-{mid3}-{tag}"


@router.get("")
async def get_settings():
    return success_response(data={"app": cfg.APP_NAME, "version": cfg.APP_VERSION, "currency": cfg.DEFAULT_CURRENCY, "serial": _serial(), "ai_provider": cfg.AI_PROVIDER, "ai_model": cfg.AI_MODEL, "telegram_enabled": cfg.TELEGRAM_ENABLED, "backup_enabled": cfg.BACKUP_ENABLED})

@router.get("/system")
async def get_system_settings():
    return success_response(data={"env": cfg.APP_ENV, "debug": cfg.DEBUG, "scheduler": cfg.SCHEDULER_ENABLED})

@router.get("/ai")
async def get_ai_settings():
    return success_response(data={"provider": cfg.AI_PROVIDER, "model": cfg.AI_MODEL, "temperature": cfg.AI_TEMPERATURE, "max_tokens": cfg.AI_MAX_TOKENS, "key_configured": bool(cfg.AI_API_KEY)})

@router.get("/telegram")
async def get_telegram_settings():
    """حالة قناة «صقر» — بلا قيمةِ رمزٍ ولا معرّف.

    `enabled` وحدها كانت تكذب: تُقرأ من `TELEGRAM_ENABLED` فتقول «مُفعّل»
    ولو غاب الرمز أو معرّف المحادثة، والقناة صامتة. فالبوت نفسه يشترط
    الثلاثة معاً — وهذا ما يُعرض هنا: كلٌّ على حِدة، مضبوطٌ أو لا، من غير
    كشف قيمة. (لا تُعاد الأسرار في ردٍّ يمرّ بالمتصفّح.)
    """
    return success_response(data={
        "enabled": cfg.TELEGRAM_ENABLED,
        "username": cfg.TELEGRAM_BOT_USERNAME,
        "token_configured": bool(cfg.TELEGRAM_BOT_TOKEN),
        "chat_configured": bool(cfg.TELEGRAM_CHAT_ID),
    })


@router.post("/telegram/test")
async def test_telegram(_: None = Depends(require_owner)):
    """اختبارٌ حقيقيّ: يسأل تلغرام عن البوت **ويرسل رسالةً فعلية**.

    زرّ «اختبار الاتصال» كان بلا معالجٍ أصلاً — يُضغط فلا يقع شيء. وهو
    عيبُ زرّ المشاركة نفسه: واجهةٌ تَعِد بما لا تفعل. والاختبار الذي
    يكتفي بـ`getMe` يكذب أيضاً: الرمز قد يصحّ ومعرّف المحادثة خطأ فلا
    تصل رسالةٌ أبداً. فالوصول وحده هو الدليل.

    للمالك وحده: يُشغّل نداءً خارجياً ويُظهر تفاصيل الإعداد.
    """
    from app.services.saqr_bot import bot
    from app.services.saqr_format import card

    if not cfg.TELEGRAM_BOT_TOKEN:
        return success_response(data={"ok": False, "reason": "لا رمز بوت في إعدادات الخادم."})
    if not cfg.TELEGRAM_CHAT_ID:
        return success_response(data={"ok": False, "reason": "لا معرّف محادثة — شغّل scripts/saqr_setup.sh."})

    me = await bot._call("getMe")
    if not me:
        return success_response(data={"ok": False, "reason": "تلغرام رفض الرمز أو تعذّر الوصول إليه."})

    sent = await bot.send(card(
        "🦅", "اختبار القناة",
        "وصلت هذه الرسالة من خادم المحفظة الذكية.\nالقناة تعمل.",
        foot="اختبارٌ يدويّ من الإعدادات"), keyboard=False)

    return success_response(data={
        "ok": bool(sent),
        "username": me.get("username"),
        "reason": None if sent else "الرمز صحيح لكنّ الرسالة لم تصل — راجع معرّف المحادثة (اضغط Start في البوت).",
    })

@router.get("/providers")
async def get_providers():
    return success_response(data={"primary": cfg.PRIMARY_MARKET_PROVIDER, "secondary": cfg.SECONDARY_MARKET_PROVIDER, "daily_limit": cfg.DAILY_API_LIMIT})


@router.post("/refresh-portfolio-data")
async def refresh_portfolio_data(db: AsyncSession = Depends(get_db)):
    """تحديث بيانات المحفظة — a deliberate, manual batch refresh of رأي
    الذكاء + المفكرة (per company), plus قسم تحليل الذكاء (portfolio-level AI
    evaluation/risk narratives) and قسم الحوكمة (governance — scores + prices
    it's built from), instead of all of these being pulled automatically on
    every page view. The AI calls all cache 24h (stock_opinion, portfolio
    evaluation, portfolio risk) and المفكرة caches 2h/symbol-set, so calling
    this repeatedly in the same window costs nothing extra — the point is
    giving the owner a single explicit moment to spend that quota, rather
    than it draining silently across scattered page visits for other things."""
    from app.api.v1.endpoints.portfolio import _get_holdings
    from app.api.v1.endpoints.ai import _portfolio_snapshot, _performance_context, _weekly_context
    from app.services.analysis import analyze_company
    from app.services.ai_content import stock_opinion, portfolio_evaluation, portfolio_risk
    from app.services.news_fetcher import fetch_corporate_events
    from app.services.scores import refresh_company_scores
    from app.services.governance import get_portfolio_governance
    from app.models.market import MarketNews
    from sqlalchemy import select

    holdings = await _get_holdings(db)
    companies = [(h.company.symbol, h.company.company_name) for h in holdings if h.company]
    if not companies:
        return success_response(data={"companies": 0, "opinions_updated": 0, "events_fetched": 0, "sections_refreshed": []})

    events = await fetch_corporate_events(companies)

    opinions_updated = 0
    for symbol, name in companies:
        try:
            ysym = f"{symbol}.SR" if symbol.isdigit() else symbol
            analysis = await analyze_company(ysym, name, db=db)
            if not analysis:
                continue
            rows = (await db.execute(
                select(MarketNews.headline).where(MarketNews.company_symbol == symbol)
                .order_by(MarketNews.published_at.desc().nullslast()).limit(5)
            )).scalars().all()
            opinion = await stock_opinion(symbol, name, analysis, headlines=list(rows))
            if opinion:
                opinions_updated += 1
        except Exception as e:
            logger.warning(f"refresh_portfolio_data: opinion failed for {symbol}: {e}")

    sections_refreshed = []
    try:
        snap_holdings, cash = await _portfolio_snapshot(db)
        _perf = await _performance_context(db, snap_holdings)
        _weekly = await _weekly_context(db, snap_holdings, _perf)
        await portfolio_evaluation(snap_holdings, cash, _weekly)
        await portfolio_risk(snap_holdings, cash)
        sections_refreshed.append("تحليل الذكاء")
    except Exception as e:
        logger.warning(f"refresh_portfolio_data: تحليل الذكاء failed: {e}")
    try:
        await refresh_company_scores(db)
        await get_portfolio_governance(db)
        sections_refreshed.append("الحوكمة")
    except Exception as e:
        logger.warning(f"refresh_portfolio_data: الحوكمة failed: {e}")

    return success_response(data={
        "companies": len(companies),
        "opinions_updated": opinions_updated,
        "events_fetched": len(events),
        "sections_refreshed": sections_refreshed,
    }, message="تم تحديث بيانات المحفظة.")


async def apply_tradingview_logos(db: AsyncSession) -> int:
    """Applies the committed, real TradingView logo data (app/data/
    tradingview_logos.json — collected live, never guessed) to EXISTING
    portfolio companies. Scoped ONLY to companies that already have a
    Holding row (real portfolio positions) — never creates a new Company
    row, so this cannot repeat the directory-ghost incident. Called
    automatically at startup (see main.py) — no button needed."""
    from sqlalchemy import select as _select
    from app.models.portfolio import Company, Holding
    # Single source of truth — the unified Saudi directory (name+sector+logo).
    from app.data.saudi_directory import SYMBOL_TO_LOGO, SYMBOL_TO_NAME

    companies = (await db.execute(
        _select(Company).join(Holding, Holding.company_id == Company.id)
        .where(Company.status != "ARCHIVED")
    )).scalars().all()
    updated = 0
    dirty = False
    for c in companies:
        base = c.symbol.replace(".SR", "")
        # Logo: fill only when missing (don't replace a working one).
        logo = SYMBOL_TO_LOGO.get(base)
        if logo and not c.logo_url:
            c.logo_url = logo
            updated += 1
            dirty = True
        # Name: the unified directory is the source of truth — SYNC the stored
        # name to it whenever they differ, so corrected/official names (e.g.
        # 4071 العربية للخدمات, 4081 النايفات) propagate everywhere including
        # the "سلامة المحفظة" tab, not just newly-added companies.
        directory_name = SYMBOL_TO_NAME.get(base)
        if directory_name and c.company_name != directory_name:
            c.company_name = directory_name
            dirty = True
    if dirty:
        await db.commit()
    return updated


# Owner-confirmed real portfolio symbols (given explicitly, 2026-07) — an
# unconditional allowlist the cleanup below can NEVER delete regardless of
# any other signal, as a second, independent safety net on top of the
# Transaction-based one. Update this if the real portfolio composition
# changes; it only ever protects, never causes a deletion by itself.
CONFIRMED_REAL_SYMBOLS = {
    "2222",  # أرامكو السعودية
    "1120",  # مصرف الراجحي
    "1150",  # مصرف الإنماء
    "4190",  # جرير
    "4164",  # النهدي الطبية
    "7202",  # سلوشنز
    "2020",  # سابك للمغذيات الزراعية
    "4340",  # الراجحي ريت
    "7010",  # إس تي سي
    "2270",  # سدافكو
}


@router.post("/cleanup-directory-companies")
async def cleanup_directory_companies(db: AsyncSession = Depends(get_db)):
    """Removes the /audit-logos misstep's ghost companies. The original
    signal (Company with no Holding row) stopped being reliable once
    GET /holdings' own self-heal started unconditionally creating a
    zero-share Holding for every Company with none — which resurrected
    every ghost the moment the portfolio page was opened (that self-heal
    is now fixed too, see holdings.py). The real signal is: does this
    company have at least one actual Transaction ever? A ghost never does.
    A genuine company always does UNLESS the owner deliberately added it as
    a not-yet-bought watchlist entry — which CONFIRMED_REAL_SYMBOLS protects
    against being swept up by mistake, as an explicit second safety net.
    One-shot; safe to call even if already clean (deletes nothing)."""
    from sqlalchemy import select as _select
    from app.models.portfolio import Company, Holding
    from app.models.transaction import Transaction

    transacted = set((await db.execute(_select(Transaction.company_id).distinct())).scalars().all())
    companies = (await db.execute(_select(Company))).scalars().all()

    # ══ شركةٌ يتعلّق بها صفٌّ للمالك ليست وهماً ══ (D323)
    # قِيس في سجلّ خادم المالك: `null value in column "company_id" of
    # relation "allocation" violates not-null constraint` ثمّ
    # `Startup snapshot skipped`. والسببُ أنّ هذا المنظّف يحذف صفَّ
    # الملكية (`Holding`) للوهم ولا يحذف بقيّةَ أبنائه، فتُفرَّغ مفاتيحُهم
    # (nullify) وعمودُها لا يقبل الفراغ — فتُرَدّ المعاملةُ وتسقط معها
    # لقطةُ الإقلاع وكلُّ ما بعدها.
    #
    # والعلاجُ **لا يكون بحذفٍ أوسع**: وزنٌ مستهدفٌ أو توزيعٌ أو قسطٌ
    # أرقامُ المالك، ولا تُحذف باجتهادٍ من منظّفٍ آليّ (الخطّ الأحمر
    # الأوّل). فالشركةُ التي يتعلّق بها صفٌّ من هذه **تُستثنى وتُسمّى**:
    # لا تُحذف، ولا تُسقط الإقلاع.
    from app.models.market import Allocation
    from app.models.transaction import BonusShare, Dividend, Installment

    kept: dict[str, str] = {}
    _held: dict[str, set] = {}
    for label, model in (("وزنٌ مستهدف", Allocation), ("توزيعٌ", Dividend),
                         ("أسهمُ منحة", BonusShare), ("قسطٌ", Installment)):
        _held[label] = set(
            (await db.execute(
                _select(model.company_id).distinct())).scalars().all())

    def _attached(cid: int) -> str | None:
        for label, ids in _held.items():
            if cid in ids:
                return label
        return None

    ghosts = []
    for c in companies:
        if c.id in transacted or c.symbol.replace(".SR", "") in CONFIRMED_REAL_SYMBOLS:
            continue
        why = _attached(c.id)
        if why:
            kept[c.symbol] = why
            continue
        ghosts.append(c)
    if kept:
        logger.info(
            "المنظّف أبقى {} شركةً يتعلّق بها صفٌّ للمالك: {}",
            len(kept), " · ".join(f"{s}({w})" for s, w in kept.items()))
    removed = [c.symbol for c in ghosts]
    ghost_ids = {c.id for c in ghosts}
    if ghost_ids:
        await db.execute(Holding.__table__.delete().where(Holding.company_id.in_(ghost_ids)))
        for c in ghosts:
            await db.delete(c)
        await db.commit()
    return success_response(
        data={"removed_count": len(removed), "removed_symbols": removed,
              "kept_count": len(kept), "kept": kept},
        message=f"أُزيلت {len(removed)} شركة وهمية بلا أي عملية شراء حقيقية — محفظتك الفعلية محمية بقائمة تأكيد صريحة.",
    )
