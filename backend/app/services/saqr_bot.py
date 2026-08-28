"""
قناة «صقر» على تلغرام — المحفظة الذكية بلسانها الثاني.

## لماذا استطلاعٌ لا خطّاف (polling not webhook)

تلغرام **لا يقبل خطّافاً إلا على HTTPS**، وخادم المالك على HTTP اليوم.
فالخطّاف مستحيلٌ تقنياً لا مؤجَّلٌ اختياراً. والاستطلاع الطويل يعمل من خلف
أي شبكة ولا يحتاج منفذاً مفتوحاً ولا شهادة — وهو أأمن أيضاً: لا يفتح
الخادم للعالم. ويوم تُركَّب الشهادة يمكن التحويل بلا تغيير في المنطق.

## الأمان قبل الميزة (بند ٢٣)

البوت يحمل أرقام محفظةٍ حقيقية. ومعرّف البوت يمكن أن يجده أيّ أحد ويكتب
إليه. فكل تحديثٍ يُقابَل بمعرّف المحادثة المصرَّح به **قبل أي عمل**، وما
عداه يُهمَل صامتاً: الردّ على المتطفّل بـ«غير مصرَّح» يُخبره أن البوت حيّ
وأن له مالكاً — وهو ما لا يحتاج معرفته.

## السقوط المعزول

عطبُ تلغرام لا يمسّ التطبيق: الحلقة تلتقط كل استثناء، وتتراجع في المهلة
عند تكرار الفشل، وتستأنف وحدها. والخادم لا يعلم بها.
"""

import asyncio
import html
import re
from datetime import datetime, timezone

import httpx
from loguru import logger

from app.core.config import settings
from app.services.saqr_format import (
    card, reply, rows_block, bullet, numbered, num, signed, esc, stamp,
)

API = "https://api.telegram.org/bot{token}/{method}"

# ── هويّة القناة ──────────────────────────────────────────────────────────
# الاسم اسم التطبيق، والوصف يقول من يتكلّم. الصورة تُضبط من BotFather —
# واجهة البوتات لا تسمح برفع صورةٍ برمجياً، وهذا قيدٌ من تلغرام لا نقصٌ هنا.
BOT_NAME = "المحفظة الذكية"
BOT_SHORT = "صقر — مساعد محفظتك. يقرأ ولا يعدّل."
BOT_ABOUT = (
    "صقر، مساعد «المحفظة الذكية».\n"
    "يعرض ثروتك وتحليل السوق ومفكرة شركاتك وأخبارها ويجيب أسئلتك."
)

MENU = [
    [("💰 الثروة", "wealth"), ("📈 تحليل السوق", "mkt")],
    [("🗓️ المفكرة", "cal"), ("📰 الإفصاحات", "disc")],
    [("🗞️ الأخبار", "news")],
    [("📄 تقرير المحفظة", "report")],
    [("🦅 اسأل صقر", "ask")],
]

# قوائمُ فرعية: المفكرة والإفصاحات لكلٍّ نطاقان — محفظتُك والسوق كلّه.
# وكانا يقرآن **مخزن السوق وحده** فيظهران أخبار شركاتٍ لا تملكها، وتفرغ
# المفكرة إن كان المخزن بارداً. ولكلّ نطاقٍ مصدرُه في الخادم أصلاً.
CAL_MENU = [
    [("💼 شركات محفظتي", "cal:p"), ("🏛️ السوق كلّه", "cal:m")],
    [("↩︎ رجوع", "menu")],
]
DISC_MENU = [
    [("💼 شركات محفظتي", "disc:p"), ("🏛️ السوق كلّه", "disc:m")],
    [("↩︎ رجوع", "menu")],
]
# الأخبار: كانت غائبةً عن القناة رأساً — يراها المالك في التطبيق ولا يجدها
# في البوت. وبالنطاقين نفسهما، من مصدر التطبيق نفسه (‏/market/news).
NEWS_MENU = [
    [("💼 شركات محفظتي", "news:p"), ("🏛️ السوق كلّه", "news:m")],
    [("↩︎ رجوع", "menu")],
]

# قائمةُ التقرير: تتفرّع عند الضغط بدل أن تزدحم القائمة الأولى بأربعة
# أزرارٍ لا يُختار منها إلا واحد. و«رجوع» صريحٌ فلا يُحبس المالك في فرع.
REPORT_MENU = [
    [("🗓️ أسبوعي", "rep:w"), ("📆 شهري", "rep:m")],
    [("📊 ربع سنوي", "rep:q"), ("📈 سنوي", "rep:y")],
    [("↩︎ رجوع", "menu")],
]


def _fmt(n, d=0) -> str:
    if n is None:
        return "—"
    try:
        return f"{float(n):,.{d}f}"
    except Exception:
        return "—"


def _stamp() -> str:
    """لحظة القياس — بند ٢٤: ما يُقرأ بعد ساعةٍ لا يُظنّ لحظياً."""
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


class SaqrBot:
    def __init__(self) -> None:
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.owner = str(settings.TELEGRAM_CHAT_ID or "").strip()
        self.enabled = bool(settings.TELEGRAM_ENABLED and self.token and self.owner)
        self._offset = 0
        self._waiting_question: set[str] = set()

    # ── نقل ────────────────────────────────────────────────────────────
    async def _call(self, method: str, **payload):
        if not self.token:
            return None
        try:
            async with httpx.AsyncClient(timeout=65) as c:
                r = await c.post(API.format(token=self.token, method=method), json=payload)
                data = r.json()
                if not data.get("ok"):
                    logger.warning(f"🦅 تلغرام رفض {method}: {data.get('description')}")
                    return None
                return data.get("result")
        except Exception as e:
            logger.warning(f"🦅 تلغرام {method} تعذّر: {e}")
            return None

    async def send(self, text: str, keyboard: bool = True, chat: str | None = None,
                   menu: list | None = None):
        rows = menu if menu is not None else MENU
        kb = {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row]
                                  for row in rows]} if keyboard else None
        return await self._call(
            "sendMessage", chat_id=chat or self.owner, text=text,
            parse_mode="HTML", disable_web_page_preview=True,
            **({"reply_markup": kb} if kb else {}),
        )

    async def send_file(self, data: bytes, filename: str, caption: str = "",
                        chat: str | None = None):
        """إرسال ملف — `multipart` لا JSON، فواجهة تلغرام لا تقبل الملفّات
        في جسمٍ JSON. ولا يُرمى استثناء: فشلُ الملف لا يبتلع الرسالة."""
        if not self.token:
            return None
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(
                    API.format(token=self.token, method="sendDocument"),
                    data={"chat_id": chat or self.owner, "caption": caption[:1000],
                          "parse_mode": "HTML"},
                    files={"document": (filename, data, "application/pdf"
                                        if filename.endswith(".pdf") else "text/html")},
                )
                d = r.json()
                if not d.get("ok"):
                    logger.warning(f"🦅 تلغرام رفض الملف: {d.get('description')}")
                    return None
                return d.get("result")
        except Exception as e:
            logger.warning(f"🦅 إرسال الملف تعذّر: {e}")
            return None

    # ── الهويّة ────────────────────────────────────────────────────────
    async def apply_identity(self):
        """الاسم والوصف والأوامر — تُضبط برمجياً مرّةً عند الإقلاع.

        الصورة وحدها تبقى يدويةً: تلغرام لا يتيح رفعها من واجهة البوتات.
        """
        await self._call("setMyName", name=BOT_NAME)
        await self._call("setMyShortDescription", short_description=BOT_SHORT)
        await self._call("setMyDescription", description=BOT_ABOUT)
        await self._call("setMyCommands", commands=[
            {"command": "start", "description": "القائمة"},
            {"command": "wealth", "description": "الثروة"},
            {"command": "market", "description": "تحليل السوق"},
            {"command": "calendar", "description": "مفكرة الشركات"},
            {"command": "news", "description": "أخبار المحفظة والسوق"},
            {"command": "report", "description": "تقرير المحفظة"},
        ])

    # ── المحتوى ────────────────────────────────────────────────────────
    async def _cash(self, db) -> float:
        """السيولة من جدول `Cash` مباشرةً — مصدرُها الذي يقرأه التطبيق كلّه.

        ══ العطب الذي كان هنا ══
        كان يُقرأ `available_cash` من ملخّص المحفظة، و**الملخّص لا يحمل هذا
        المفتاح أصلاً**. فكانت السيولة صفراً دائماً، ويتبعها خطآن:
          • «إجمالي الثروة» = القيمة السوقية وحدها، ناقصةً كلَّ النقد.
          • «السيولة المتاحة» تُعرض صفراً وهي ليست صفراً.
        ولم يظهر العطب استثناءً لأن `or 0` ابتلع الغياب صامتاً — وهذا أخطر
        من الخطأ نفسه: رقمٌ خاطئ يبدو سليماً.

        والتطبيق يقرأها من مسار السيولة لا من الملخّص، فاختلف اللسانان عن
        بعضهما. والآن يقرأ صقر من المنبع الذي تقرأ منه كل خدمةٍ أخرى
        (`portfolio_return` و`snapshots` و`ai_chat`) — فيستحيل التباعد.
        """
        from sqlalchemy import select
        from app.models.transaction import Cash
        row = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
        return float(row.available_cash or 0) if row else 0.0

    async def _wealth(self, db) -> str:
        from app.api.v1.endpoints.portfolio import get_portfolio_summary
        s = (await get_portfolio_summary(db)) or {}
        d = s.get("data") or s
        mv = d.get("total_current_value"); inv = d.get("total_cost")
        cash = await self._cash(db)

        # الثروة من المقياس الموحّد متى توفّر — هو نفسه الذي يغذّي باند
        # الثروة في التطبيق. والجمع المحلّي احتياطٌ لا أصل.
        wealth = d.get("np_wealth")
        if wealth is None:
            wealth = (mv or 0) + cash

        net = d.get("net_profit")                 # الثروة − صافي المساهمات
        growth = d.get("capital_growth_pct")      # عائد المحفظة (بند الميثاق)
        contributed = d.get("contributed_capital")

        u = (mv or 0) - (inv or 0)                # ارتفاعٌ سعريّ لا ربحٌ محقّق
        pct = (u / inv * 100) if inv else None
        body = rows_block([
            ("إجمالي الثروة", num(wealth)),
            ("القيمة السوقية", num(mv)),
            ("السيولة المتاحة", num(cash)),
            ("إجمالي المدفوع", num(inv)),
            ("غير المحقّق", f"{signed(u)}  ({signed(pct, 2)}%)" if pct is not None else signed(u)),
            ("صافي المساهمات", num(contributed)),
            ("صافي الربح", signed(net)),
            ("عائد المحفظة", f"{signed(growth, 2)}%" if growth is not None else "—"),
        ])
        return card("💰", "الثروة", body)

    async def _events(self, db, announced: bool, scope: str = "p") -> str:
        """المفكرة والإفصاحات — بنطاقٍ صريح ومصدرٍ يخصّه.

        ══ العطبان اللذان كانا هنا ══
        كان كلاهما يقرأ `market_wide_events()` وحده:
          • فالإفصاحات تعرض شركاتٍ لا يملكها المالك — «ليست للمحفظة».
          • والمفكرة تفرغ متى كان مخزن السوق بارداً، بلا سببٍ ظاهر.
        وللتطبيق مصدران مستقلّان أصلاً: مفكرةُ المحفظة تُجمَّع من تقويم كل
        شركةٍ يملكها (`/market/events`)، ومفكرةُ السوق من المخزن العامّ.
        فصار النطاق اختياراً صريحاً لا افتراضاً صامتاً.
        """
        scope_ar = "محفظتك" if scope == "p" else "السوق"
        icon, kind = ("📰", "الإفصاحات") if announced else ("🗓️", "المفكرة")
        title = f"{kind} — {scope_ar}"
        try:
            if scope == "p":
                from app.api.v1.endpoints.market import get_events
                res = await get_events(db)
                rows = (res or {}).get("data") or []
            else:
                from app.services.content_engine import market_wide_events
                rows = await market_wide_events()
        except Exception as e:                                    # noqa: BLE001
            logger.warning(f"🦅 {title} تعذّرت: {e}")
            return card(icon, title, "تعذّر جلبها الآن.")

        rows = [e for e in (rows or [])
                if bool(e.get("date_kind") == "announced") == announced][:8]
        if not rows:
            # لا شيء ≠ عطب: يُقال أيّ نطاقٍ فُحص، ويُدلّ على النطاق الآخر.
            other = "السوق كلّه" if scope == "p" else "شركات محفظتك"
            return card(icon, title,
                        f"لا شيء في {scope_ar} حالياً.\nجرّب «{other}» من القائمة.")
        items = []
        for e in rows:
            nm = esc(e.get("company_name") or e.get("symbol") or "")
            t = esc(str(e.get("title") or ""))[:80]
            items.append(f"<b>{nm}</b> — {t}\n  <code>{esc(e.get('date') or '—')}</code>")
        return card(icon, title, bullet(items))

    async def _news(self, db, scope: str = "p") -> str:
        """الأخبار — من مصدر التطبيق نفسه (`/market/news`) بالنطاقين.

        `portfolio_only=True` يُرشِّح العناوين برموز الشركات المملوكة فعلاً،
        وهو المِصفاة نفسها التي تُغذّي «أخبار المحفظة» في التطبيق — فلا
        يفترق ما يراه المالك على الشاشة عمّا يصله في القناة.
        """
        scope_ar = "محفظتك" if scope == "p" else "السوق"
        title = f"الأخبار — {scope_ar}"
        try:
            from app.api.v1.endpoints.market import get_news
            res = await get_news(portfolio_only=(scope == "p"), db=db)
            rows = (res or {}).get("data") or []
        except Exception as e:                                    # noqa: BLE001
            logger.warning(f"🦅 {title} تعذّرت: {e}")
            return card("🗞️", title, "تعذّر جلبها الآن.")
        rows = rows[:8]
        if not rows:
            other = "السوق كلّه" if scope == "p" else "شركات محفظتك"
            return card("🗞️", title,
                        f"لا شيء في {scope_ar} حالياً.\nجرّب «{other}» من القائمة.")
        items = []
        for n in rows:
            head = esc(str(n.get("headline") or ""))[:110]
            # المصدر والوقت في سطرٍ خافت: الخبر بلا مصدرٍ لا يُوزن، وبلا
            # وقتٍ يُقرأ لحظياً وقد يكون من أمس (بند ٢٤).
            meta = " · ".join(x for x in (esc(n.get("source") or ""),
                                          esc((n.get("published") or "")[:16].replace("T", " ")))
                              if x and x != "—")
            co = n.get("company")
            lead = f"<b>{esc(co)}</b> — " if co else ""
            items.append(f"{lead}{head}\n  <code>{meta}</code>")
        return card("🗞️", title, bullet(items))

    async def _market(self, db) -> str:
        """تحليل السوق — **بطاقة نبض السوق كاملةً** كما في أعلى شاشة السوق،
        والتحليل تحتها.

        حلّت محلّ زرّ «الأداء»: كان يعرض فروق ستّة أشهر من اللقطات — رقمان
        في عمودٍ لا يقولان للمالك شيئاً لا يعرفه، ووصفه بالابتذال في محلّه.
        وما يُسأل عنه صباحاً هو **السوق**: أين تاسي، وكم صعد وكم هبط، ومن
        تصدّر ومن تأخّر، ولماذا.

        والمصادر هي مصادر الشاشة نفسها (`/market/overview` · `/market/movers`
        · `/market/summary`) — فلا رقمَ في تلغرام يخالف رقماً في الشاشة.
        """
        from app.api.v1.endpoints import market as M
        ov = mv = sm = {}
        try:
            ov = ((await M.market_overview(db)) or {}).get("data") or {}
        except Exception as e:                                    # noqa: BLE001
            logger.warning(f"🦅 نظرة السوق تعذّرت: {e}")
        try:
            mv = ((await M.get_market_movers()) or {}).get("data") or {}
        except Exception as e:                                    # noqa: BLE001
            logger.warning(f"🦅 حركة السوق تعذّرت: {e}")
        try:
            sm = ((await M.get_market_summary(db)) or {}).get("data") or {}
        except Exception as e:                                    # noqa: BLE001
            logger.warning(f"🦅 تحليل السوق تعذّر: {e}")

        tasi = ov.get("tasi") or {}
        brent = ov.get("brent") or {}
        price, chg = tasi.get("price"), tasi.get("change_pct")
        # صفرٌ بلا إغلاقٍ سابق ليس تعادلاً بل جهلاً بالتغيّر — كما في الشريط.
        if tasi.get("prev_close") is None:
            chg = None
        arrow = "▲" if (chg or 0) > 0 else ("▼" if (chg or 0) < 0 else "•")

        parts = [rows_block([
            ("تاسي", f"{num(price, 2)}  {arrow} {signed(chg, 2)}%" if chg is not None
                     else f"{num(price, 2)}  (لا إغلاقَ سابقاً)"),
            ("برنت", f"{num(brent.get('price'), 2)}  {signed(brent.get('change_pct'), 2)}%"
                     if brent.get("price") is not None else "—"),
        ])]

        up, dn = mv.get("advancers"), mv.get("decliners")
        if up is not None or dn is not None:
            mood = ((mv.get("sentiment") or {}).get("label")) or ""
            parts.append(rows_block([
                ("صاعدة", num(up)), ("هابطة", num(dn)),
                ("ثابتة", num(mv.get("unchanged"))),
                ("مزاج السوق", mood or "—"),
            ]))

        def _names(rows, sign):
            out = []
            for x in (rows or [])[:3]:
                c = x.get("change_pct")
                if c is None:
                    continue
                out.append(f"{esc(x.get('name') or x.get('symbol'))} {signed(c, 2)}%")
            return out

        g, l = _names(mv.get("gainers"), 1), _names(mv.get("losers"), -1)
        if g:
            parts.append("<b>أعلى الرابحين</b>\n" + bullet(g))
        if l:
            parts.append("<b>أعلى الخاسرين</b>\n" + bullet(l))

        # أقوى وأضعف **بالقيمة لا بالموضع**: الاعتماد على أوّل القائمة
        # وآخرها يفترض ترتيباً يضمنه مصدرٌ واحد. قِيس في المختبر فأعطى
        # «أضعف قطاع: الاتصالات ‎+0.35٪» بينما الطاقة ‎−0.73٪ — أي أن
        # البطاقة تقول أضعفَ ما ليس بأضعف.
        secs = [x for x in (mv.get("sectors") or []) if x.get("avg_change_pct") is not None]
        if secs:
            best = max(secs, key=lambda x: x["avg_change_pct"])
            worst = min(secs, key=lambda x: x["avg_change_pct"])
            parts.append(rows_block([
                ("أقوى قطاع", f"{best.get('sector')} {signed(best.get('avg_change_pct'), 2)}%"),
                ("أضعف قطاع", f"{worst.get('sector')} {signed(worst.get('avg_change_pct'), 2)}%"),
            ]))

        if sm.get("summary"):
            # المصدر يُعلَن: قراءةٌ آلية ليست تحليلَ ذكاء، والفرق يُقال.
            src = "" if sm.get("source") == "AI" else "  <i>(قراءة آلية)</i>"
            parts.append(f"<b>تحليل السوق</b>{src}\n{esc(sm['summary'])}")

        if not parts:
            return card("📈", "تحليل السوق", "لم تصل بيانات السوق بعد.")
        return card("📈", "تحليل السوق", "\n\n".join(parts))

    # ── التقارير الدورية ──────────────────────────────────────────────
    PERIODS = {
        "w": (7,   "الأسبوعي"),
        "m": (30,  "الشهري"),
        "q": (90,  "الربع سنوي"),
        "y": (365, "السنوي"),
    }

    async def _period_block(self, db, days: int) -> str:
        """أداءُ الفترة — والضخُّ مطروحٌ منه.

        الفرق بين ثروتَي طرفَي الفترة **ليس أداءً**: إيداعُ عشرة آلاف يرفع
        الثروة عشرة آلاف بلا ربحِ ريال. فيُطرح صافي الضخّ المسجَّل في
        الفترة نفسها — وهو تطبيقٌ لقاعدة الميثاق في صافي الربح، مقصوراً
        على نافذةٍ زمنية.

        ولا يُختلق مرجعٌ إن لم توجد لقطةٌ في أوّل الفترة: يُقال «لا مرجع».
        """
        from datetime import date, timedelta
        from sqlalchemy import select
        from app.models.portfolio import PortfolioSnapshot
        from app.models.transaction import CashLedger, CashLedgerKind

        start = date.today() - timedelta(days=days)
        base = (await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.snapshot_date >= start)
            .order_by(PortfolioSnapshot.snapshot_date.asc()).limit(1)
        )).scalars().first()
        if not base:
            return "لا لقطة مسجَّلة في أوّل الفترة — فلا مرجع يُقاس عليه."

        then = float(base.market_value or 0) + float(base.cash_balance or 0)
        s = (await self._summary(db))
        mv = s.get("total_current_value") or 0
        now = s.get("np_wealth")
        if now is None:
            now = mv + await self._cash(db)

        # صافي الضخّ داخل الفترة وحدها — لا منذ البداية.
        ledger = (await db.execute(
            select(CashLedger).where(CashLedger.created_at >= start)
        )).scalars().all()
        flow = sum(float(e.amount or 0) * (1 if e.kind == CashLedgerKind.DEPOSIT else -1)
                   for e in ledger)

        gain = now - then - flow

        # ══ المقام: رأس المال المتاح للعمل، لا ثروة أوّل الفترة ══
        # قسمةُ الربح على ثروة البداية وحدها تنتج أرقاماً سخيفة متى ضُخّ
        # مالٌ كبير في المنتصف: قِيس في المختبر −١٠٣٪ لفترةٍ بدأت بـ٨٢ ألفاً
        # وضُخّ فيها ٣٣١ ألفاً — والنسبة تقول إن المحفظة خسرت أكثر ممّا
        # تملك، وهو محال. والسبب أن البسط يحمل أثر ٤١٣ ألفاً والمقام يحمل
        # ٨٢ ألفاً وحدها.
        #
        # فالمقام «رأس المال المرجَّح بالزمن» (طريقة ديتز المعدَّلة، وهي
        # المعيار المتعارف لقياس عائد فترةٍ فيها تدفّقات): كل ضخّةٍ تدخل
        # المقام بنسبة ما بقي من الفترة بعدها — فمالٌ دخل في اليوم الأخير
        # لا يُحاسَب كأنه عمل الفترة كلّها.
        #
        # وقيدٌ يُقال ولا يُخفى: `CashLedger` لا يحمل تاريخ قيمةٍ بل تاريخ
        # **تسجيل**. فإن سُجّلت ضخّةٌ قديمة متأخّرةً حُسب وزنها من يوم
        # تسجيلها. لا علاج لذلك إلا عمودُ تاريخٍ جديد في السجل.
        T = float(days)
        weighted = 0.0
        for e in ledger:
            amt = float(e.amount or 0) * (1 if e.kind == CashLedgerKind.DEPOSIT else -1)
            ts = e.created_at
            elapsed = (ts.date() - start).days if ts else 0
            w = max(0.0, min(1.0, (T - elapsed) / T)) if T else 0.0
            weighted += amt * w
        denom = then + weighted
        pct = (gain / denom * 100) if denom > 0 else None

        return rows_block([
            (f"من {base.snapshot_date.strftime('%Y-%m-%d')}", num(then)),
            ("إلى اليوم", num(now)),
            ("صافي الضخّ", signed(flow)),
            ("رأس المال المرجَّح", num(denom)),
            ("أداء الفترة", f"{signed(gain)}  ({signed(pct, 2)}%)" if pct is not None else signed(gain)),
        ])

    async def _summary(self, db) -> dict:
        from app.api.v1.endpoints.portfolio import get_portfolio_summary
        s = (await get_portfolio_summary(db)) or {}
        return s.get("data") or s

    async def _report(self, db, period: str | None = None) -> str:
        """التقرير من محرّك التطبيق نفسه — لا نصٌّ ثانٍ يُكتب هنا فيختلفان."""
        from app.services import portfolio_analytics
        from app.api.v1.endpoints.ai import (
            _portfolio_snapshot, _target_weights,
            _performance_context, _capital_recovery_context,
        )
        h, cash = await _portfolio_snapshot(db)
        ev = portfolio_analytics.evaluate(
            h, cash, await _target_weights(db),
            await _performance_context(db, h), await _capital_recovery_context(db))
        # ══ تقييمُ القناة = تقييمُ التطبيق ══ (بأمر المالك)
        # المحرّك كان واحداً أصلاً (`portfolio_analytics.evaluate`)، لكنّ
        # القناة كانت تعرض أربعة أرقامٍ عارية بينما التطبيق يعرض لكلّ
        # مقياسٍ **حكمَه** (جيد · متوسط · ضعيف) ثم قراراً بجملةٍ واحدة.
        # فالرقم نفسه يُقرأ في الشاشتين قراءتين. وُحّدت الصياغة: العتبات
        # هي عتبات صفحة الذكاء حرفياً (‏70 و45)، والقرار بنصّه.
        def _band(v):
            if v is None:
                return "غير متاح"
            return "جيد" if v >= 70 else "متوسط" if v >= 45 else "ضعيف"

        _sc = ev.get("overall_score")
        verdict = ("المحفظة في وضع جيد" if (_sc or 0) >= 70
                   else "المحفظة في وضع متوسط، تحتاج مراجعة" if (_sc or 0) >= 45
                   else "المحفظة تحتاج إعادة نظر")
        rows = [
            ("التقييم العام", f"{num(_sc)} / 100  · {_band(_sc)}"),
            ("التنويع", f"{num(ev.get('diversification_score'))}  · {_band(ev.get('diversification_score'))}"),
            ("المخاطر", f"{num(ev.get('risk_score'))}  · {_band(ev.get('risk_score'))}"),
            ("العائد الكلي", (signed(ev.get("total_return_pct"), 1) + "%")
                             if ev.get("total_return_pct") is not None else "—"),
        ]
        if ev.get("performance_boost"):
            rows.append(("الأداء ضد السوق", f"{signed(ev['performance_boost'])} نقطة"))
        if ev.get("unplanned_pct"):
            rows.append(("بلا نسبة مستهدفة", f"{num(ev['unplanned_pct'], 1)}%"))
        parts = [rows_block(rows), f"<b>القرار:</b> {esc(verdict)}"]
        if ev.get("summary"):
            # جدارُ نصٍّ على شاشة الجوّال لا يُقرأ. الفصل عند نهايات الجمل
            # يجعل كلَّ جملةٍ معلومةً قائمة، ويُبقي المعنى كما كتبه المحرّك.
            sents = [x.strip() for x in re.split(r"(?<=[.؟!])\s+", ev["summary"]) if x.strip()]
            parts.append(bullet([esc(x) for x in sents[:6]]))
        steps = [esc(x) for x in (ev.get("improvement_steps") or [])][:4]
        if steps:
            parts.append("<b>خطوات التحسين</b>\n" + numbered(steps))

        title = "تقرير المحفظة"
        if period in self.PERIODS:
            days, label = self.PERIODS[period]
            title = f"التقرير {label}"
            # الفترة تتصدّر: هي سبب اختيار المالك لهذا الزرّ دون غيره.
            parts.insert(0, await self._period_block(db, days))
        return card("📄", title, "\n\n".join(parts))

    # الأطوار الأربعة بمصطلح محرّك التقارير نفسه — لا ترجمةَ بينهما.
    RTYPE = {"w": "WEEKLY", "m": "MONTHLY", "q": "QUARTERLY", "y": "ANNUAL"}

    async def _report_pdf(self, db, period: str | None):
        """ورقةُ التقرير — من **محرّك تقارير التطبيق** لا من حسابٍ موازٍ.

        كنتُ أجمع الأرقام هنا بيدي وأرسمها في ورقةٍ من تصميمي، فسأل المالك
        لماذا لا تشبه تقرير التطبيق — ولم تكن تشبهه فعلاً. والعلاج ليس
        تجميلَ ورقتي بل إسقاطها: يُستدعى `generate_report` — وهو نفسه الذي
        يبني ما يُعرض في «التقارير» — ثمّ تُقرأ نتيجته وتُرسم بنقلٍ حرفيّ
        لمكوّن `ReportDocument`.

        وأثرٌ مقصود: التقرير الذي يصلك في تلغرام **يُحفظ في أرشيف التطبيق**
        أيضاً. فما تقرؤه في جوّالك تجده في شاشتك بالرقم نفسه لا بمثله.
        """
        from app.services import saqr_report as R
        from app.api.v1.endpoints.reports import generate_report
        from app.models.market import Report
        from sqlalchemy import select

        rtype = self.RTYPE.get(period or "", "WEEKLY")
        res = await generate_report(rtype, db)
        rid = ((res or {}).get("data") or {}).get("id")
        row = (await db.execute(select(Report).where(Report.id == rid))).scalars().first() if rid else None
        if not row:
            raise RuntimeError("لم يُنتج محرّك التقارير صفّاً")

        data = row.summary or {}
        gen = row.generated_at.strftime("%Y-%m-%d") if row.generated_at else stamp()
        html = R.build_html(data, period=row.report_period or "", generated_at=gen)
        stem = f"تقرير-{(row.report_period or rtype).replace(' ', '')}"
        pdf = await R.to_pdf(html)
        if pdf:
            return pdf, f"{stem}.pdf", ""
        return (html.encode("utf-8"), f"{stem}.html",
                "\n<i>لا متصفّح في الخادم — أُرسلت الصفحة تُفتح في أي جهاز.</i>")

    async def _ask(self, db, question: str) -> str:
        """صقر نفسه يجيب — من `ai_chat.answer`، لا شخصيةٌ ثانية تُكتب هنا.

        تعدّد المصادر يُنتج مساعدَين باسمٍ واحد يختلفان في الجواب.
        """
        from app.services.ai_chat import answer
        try:
            # `prefer_llm`: في التطبيق تسبق الطبقةُ القاعدية النموذجَ لأنها
            # فورية ومضمونة الحساب. وفي القناة وصف المالك جوابها بالثابت
            # المبتذل — وهو وصفٌ دقيق: قوالبُ جاهزة لنيّاتٍ معدودة.
            # فمن يضغط «اسأل صقر» يريد **الذكاء** لا القالب. والقاعدية تبقى
            # شبكةَ أمانٍ إن غاب المفتاح أو نفدت الحصّة.
            res = await answer(db, question, prefer_llm=True)
            # المفتاح `reply` — تحقّقتُ منه في `ai_chat.answer` بدل افتراضه.
            txt = (res or {}).get("reply")
            return reply(esc(txt or "لم أفهم السؤال."))
        except Exception as e:
            logger.warning(f"🦅 صقر تعذّر عليه الجواب: {e}")
            return reply("تعذّر عليّ الجواب الآن.")

    # ── التوجيه ────────────────────────────────────────────────────────
    async def _handle(self, upd: dict):
        msg = upd.get("message") or upd.get("edited_message")
        cbq = upd.get("callback_query")
        chat = str(((cbq or {}).get("message") or msg or {}).get("chat", {}).get("id", ""))

        # بند ٢٣: المالك وحده. وما عداه يُهمَل صامتاً — لا ردّ يفيد المتطفّل.
        if not chat or chat != self.owner:
            if chat:
                logger.warning(f"🦅 محادثةٌ غير مصرَّح بها حاولت: {chat}")
            return

        data = (cbq or {}).get("data")
        text = (msg or {}).get("text") or ""
        if cbq:
            await self._call("answerCallbackQuery", callback_query_id=cbq["id"])

        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            if data == "ask" or text.startswith("/ask"):
                self._waiting_question.add(chat)
                await self.send("اكتب سؤالك لصقر…", keyboard=False)
                return
            # **أيّ نصٍّ ليس أمراً فهو سؤال.** كان الجواب مشروطاً بضغط زرّ
            # «اسأل صقر» أولاً، فمن كتب سؤاله مباشرةً رُدّ عليه بالقائمة —
            # وهو أوّل ما يفعله أيّ أحد. قِيس ذلك: «كم عدد شركاتي؟» أعادت
            # القائمة. المساعد يتفاعل أو لا يكون مساعداً.
            if text and not text.startswith("/"):
                self._waiting_question.discard(chat)
                await self._call("sendChatAction", chat_id=chat, action="typing")
                await self.send(await self._ask(db, text))
                return

            key = data or {
                "/start": "menu", "/menu": "menu",
                "/wealth": "wealth", "/market": "mkt",
                "/calendar": "cal", "/report": "report",
                "/news": "news",
            }.get(text.split("@")[0].strip(), "menu")

            if key == "wealth":
                await self.send(await self._wealth(db))
            elif key == "mkt":
                await self._call("sendChatAction", chat_id=chat, action="typing")
                await self.send(await self._market(db))
            elif key == "cal":
                await self.send(card("🗓️", "المفكرة", "أيّ نطاقٍ تريد؟"),
                                menu=CAL_MENU)
            elif key == "disc":
                await self.send(card("📰", "الإفصاحات", "أيّ نطاقٍ تريد؟"),
                                menu=DISC_MENU)
            elif key == "news":
                await self.send(card("🗞️", "الأخبار", "أيّ نطاقٍ تريد؟"),
                                menu=NEWS_MENU)
            elif key.startswith("news:"):
                await self._call("sendChatAction", chat_id=chat, action="typing")
                await self.send(await self._news(db, scope=key.split(":")[1]))
            elif key.startswith("cal:"):
                await self.send(await self._events(db, announced=False, scope=key.split(":")[1]))
            elif key.startswith("disc:"):
                await self.send(await self._events(db, announced=True, scope=key.split(":")[1]))
            elif key == "report":
                # الضغطة الأولى تفتح الفروع ولا تُصدر تقريراً: إصدارُ تقريرٍ
                # لم يُطلب مدّةً محدّدة له يجعل الزرّ يقول شيئاً ويفعل آخر.
                await self.send(card(
                    "📄", "تقرير المحفظة",
                    "اختر المدّة التي يُقاس عليها الأداء:",
                    foot="التقييم والتحليل واحدٌ في الأربعة — المتغيّر نافذةُ القياس"),
                    menu=REPORT_MENU)
            elif key.startswith("rep:"):
                p = key.split(":", 1)[1]
                if p not in self.PERIODS:
                    await self.send(card("📄", "تقرير المحفظة", "مدّةٌ غير معروفة."))
                else:
                    # ══ الملفّ وحده ══
                    # كان يُرسَل نصٌّ مطوَّل ثمّ الورقة، فيقرأ المالك الشيء
                    # مرّتين — والورقة هي المقصودة. بأمره: لا نصّ، الملف فقط.
                    # ويبقى إشعارُ الانتظار (`upload_document`) فلا يظنّ
                    # الضغطةَ ضاعت أثناء الطباعة.
                    await self._call("sendChatAction", chat_id=chat, action="upload_document")
                    try:
                        data, name, note = await self._report_pdf(db, p)
                        await self.send_file(data, name, note.strip() or "", chat=chat)
                    except Exception as e:
                        logger.warning(f"🦅 ورقة التقرير تعذّرت: {e}")
                        # الصمت عند الفشل يترك المالك ينتظر ملفاً لن يأتي.
                        await self.send(card("📄", "تقرير المحفظة",
                                             "تعذّر بناء الورقة الآن."))
            else:
                await self.send(card(
                    "🦅", "المحفظة الذكية",
                    "أنا <b>صقر</b>، مساعدك.\n"
                    "اختر من الأزرار، أو اكتب سؤالك مباشرةً."))

    # ── الحلقة ─────────────────────────────────────────────────────────
    async def run(self):
        if not self.enabled:
            logger.info("🦅 قناة صقر متوقّفة (لا رمز أو لا معرّف محادثة).")
            return
        # ══ إرثُ بوتٍ سابق ══
        # هذا البوت كان لمشروعٍ آخر (d7m v5) أُلغي. وبوتٌ مستعمَلٌ قد يحمل:
        #  ١) **خطّافاً مثبَّتاً** من المشروع القديم — وحينها يرفض تلغرام
        #     `getUpdates` بـ٤٠٩ تعارض، فلا يعمل صقر أبداً ولا يظهر سببٌ
        #     في السجل إلا سطرُ رفضٍ غامض.
        #  ٢) **طابوراً من رسائل قديمة** تصل عند أول تشغيل فيردّ عليها صقر
        #     كأنها الآن — وقد تكون رسائل مشروعٍ لا علاقة له بالمحفظة.
        # الحذف مع إسقاط الطابور يعالج الأمرين، وهو آمنٌ إن لم يكن ثمّة
        # خطّاف أصلاً: يُعيد نجاحاً بلا أثر.
        await self._call("deleteWebhook", drop_pending_updates=True)
        await self.apply_identity()
        logger.info("🦅 قناة صقر تعمل — استطلاعٌ طويل (وأُسقط إرثُ البوت السابق).")
        backoff = 1
        while True:
            try:
                res = await self._call("getUpdates", offset=self._offset, timeout=50) or []
                backoff = 1
                for upd in res:
                    self._offset = max(self._offset, int(upd.get("update_id", 0)) + 1)
                    try:
                        await self._handle(upd)
                    except Exception as e:
                        logger.warning(f"🦅 تعذّرت معالجة تحديث: {e}")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # تراجعٌ متصاعد: انقطاعُ الشبكة لا يُغرق السجل ولا يُرهق الخادم
                logger.warning(f"🦅 حلقة صقر تعثّرت ({e}) — إعادة بعد {backoff}ث")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 300)


bot = SaqrBot()


async def start_bot():
    """تُستدعى عند إقلاع الخادم. لا ترفع استثناءً مهما حدث."""
    try:
        if bot.enabled:
            asyncio.create_task(bot.run())
    except Exception as e:
        logger.warning(f"🦅 تعذّر تشغيل قناة صقر: {e}")
