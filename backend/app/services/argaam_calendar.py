"""
مفكرة الإفصاحات — من صفحة مفكرة «أرقام».

## لماذا هذا المصدر بالذات

المصدر الرسمي الأوّل هو «تداول»، وقد ثبت بالقياس أنه **يحجب خادمنا**: الرمز
٤٠٣ حتى على `robots.txt` نفسه بحجم ٣٨٨ بايت — جدارُ حمايةٍ يرفض عناوين مراكز
البيانات قبل أن يُسأل عن الصفحة. ولا حيلة فيه من جهتنا.

وياهو — وهو مصدرنا المؤكَّد اليوم — لا يحمل إلا ثلاثة: تاريخ الأحقية، وتاريخ
الصرف، وموعد إعلان النتائج المؤكَّد. أمّا **الجمعيات العمومية وأسهم المنحة
والمؤتمرات** فلا يعرفها. فكان المالك يخرج من تطبيقه إلى «أرقام» ليكملها.

هذه الوحدة تُنهي ذلك الخروج.

## ما هذا بالضبط — وما ليس هو

هذا **كشطُ صفحةٍ للبشر**، لا تدفّقاً رسمياً منشوراً للآلة. أقولها صراحةً لأن
الفرق يهمّ: يوم يغيّر «أرقام» تصميمه ينكسر هذا المُحلِّل. جُرّبت البدائل كلّها
قبله فسقطت: تدفّقات RSS الثلاثة، وخريطة الأخبار (تبيّن أنها الصفحة الرئيسية
متنكّرة تردّ على أي مسارٍ مجهول)، وتداول محجوب، وهيئة السوق المالية تردّ
صفحةً للبشر لا تدفّقاً.

## الانكسار الصائح

ولأنه هشّ، بُني ليَصيح لا ليَصمت: إن لم يُستخرج صفٌّ واحد، تُعاد قائمةٌ فارغة
ويُسجَّل تحذير، فتقول المفكرة «تعذّر جلب الإفصاحات» ولا تعرض قديماً كأنه جديد.
وبيانات ياهو المؤكَّدة تبقى تحته قائمةً لا تتأثّر. الأسوأ من غياب الإفصاح أن
يظنّ المالك أنه لا إفصاح.

## البنية المقروءة (مُقاسة على الصفحة الحيّة ١٩ أغسطس ٢٠٢٦)

    <h2>اليوم</h2>                       ← أو «21 أغسطس 2026»
    <div class="table calendarListing">
      <div class="row labh main"> … ترويسة الأعمدة، تُتجاوَز
      <div class="row">
        <div class="colum events">أحقية أرباح نقدية</div>
        <div class="colum eventType">موعد أحقية</div>
        <div class="colum company">أرامكو السعودية</div>

والصفحة نفسها تحمل قائمة الشركات كاملةً (٤٠٨ شركة) بالرمز والاسم ورقم أرقام:

    <li data-company="3509"><span relf-Stocksymbol="2222"
        relf-companyName="أرامكو السعودية" value="3509">

فلا نحتاج جدول ترجمةٍ خارجياً ولا صيانةً يدوية: الصفحة تعرّف نفسها بنفسها.
ومن هذا الربط تأتي فائدةٌ ثانية: **ما لا يقابله رمز تداول يُسقَط** — فلا
تدخل مفكرةَ المالك أحداثٌ ليست من سوقه (تقارير مخزونات النفط الأمريكية مثلاً
تَرِد في الصفحة نفسها).
"""

import re
import html as _html
import httpx
from datetime import date, timedelta
from loguru import logger

BASE = "https://www.argaam.com"
CAL_URL = f"{BASE}/ar/company/calendar/details/marketid/3"
# الترقيم: الصفحة تُفصح عن مسار الأيام التالية في حقلٍ مخفيّ، وتاريخُ البداية
# جزءٌ من المسار — فنمرّره نحن ونمضي أسبوعاً بعد أسبوع.
MORE_URL = BASE + "/ar/calendar/calendardetailpartial/marketid/3/startdate/{d}/type/home/0/0/0/3,14"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124 Safari/537.36")

_AR_MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4, "مايو": 5,
    "يونيو": 6, "يونيه": 6, "يوليو": 7, "يوليه": 7, "أغسطس": 8, "اغسطس": 8,
    "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
}

# ما يخصّ المالكَ فعلاً. «تقارير» و«اكتتاب» تُترك خارجاً: الأولى أحداثٌ عالمية
# لا شركاتٌ سعودية، والثانية ليست إفصاحاً عن شركةٍ يملكها.
_KEEP_TYPES = (
    "جمعية", "منحة", "أحقية", "احقية", "صرف أرباح", "مؤتمر",
    "نتائج", "إدراج", "ادراج", "تجزئة", "زيادة رأس",
)


def _txt(s: str) -> str:
    """نصٌّ نظيف من قصاصة HTML: تُنزع الوسوم ويُفكّ ترميزها ويُوحَّد فراغها."""
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = _html.unescape(s).replace(" ", " ")
    return " ".join(s.split()).strip()


def _parse_day(header: str, today: date) -> date | None:
    """«اليوم» · «غداً» · «21 أغسطس 2026» → تاريخ. وما عداه لا يُخمَّن."""
    h = _txt(header)
    if not h:
        return None
    if h.startswith("اليوم"):
        return today
    if h.startswith("غد"):
        return today + timedelta(days=1)
    if h.startswith("أمس") or h.startswith("امس"):
        return today - timedelta(days=1)
    m = re.match(r"^(\d{1,2})\s+([^\s\d]+)\s+(\d{4})$", h)
    if not m:
        return None
    mon = _AR_MONTHS.get(m.group(2))
    if not mon:
        return None
    try:
        return date(int(m.group(3)), mon, int(m.group(1)))
    except ValueError:
        return None


def _company_index(page: str) -> dict[str, tuple[str, str]]:
    """اسم الشركة → (رمز تداول، رقم أرقام) — من قائمة الشركات في الصفحة نفسها.

    يُفهرَس الاسم كما كتبه «أرقام» بالضبط، لأن صفوف المفكرة تكتبه بالصيغة
    نفسها في الصفحة ذاتها. فلا مطابقةَ تقريبية ولا تخمينَ نسبةٍ — والنسبة
    الخاطئة أسوأ من الغياب.
    """
    idx: dict[str, tuple[str, str]] = {}
    pat = re.compile(
        r'relf-Stocksymbol="(\d{4})"[^>]*?relf-companyName="([^"]+)"[^>]*?value="(\d+)"'
    )
    for sym, name, cid in pat.findall(page):
        nm = _txt(_html.unescape(name))
        if nm:
            idx.setdefault(nm, (sym, cid))
    return idx


_ROW = re.compile(
    r'<div class="row">(.*?)<div class="colum detail">(.*?)</div>', re.S)
# معرّف قصاصة التفاصيل: `<a onclick="Detail(this)" id="65560">تفاصيل</a>`
_DETAIL_ID = re.compile(r'id="(\d+)"')
_COL = {
    "event": re.compile(r'<div class="colum events">(.*?)</div>', re.S),
    "type": re.compile(r'<div class="colum eventType">(.*?)</div>', re.S),
    "company": re.compile(r'<div class="colum company">(.*?)</div>', re.S),
}


def parse_calendar(page: str, index: dict[str, tuple[str, str]],
                   today: date) -> list[dict]:
    """يحوّل صفحةً واحدة إلى أحداثٍ مؤرَّخة منسوبةً برمز تداول.

    الترويسة `<h2>` تحكم ما بعدها حتى الترويسة التالية — فالتاريخ يُؤخذ من
    موضع الصفّ في الصفحة لا من نصّه، لأن الصفوف لا تحمل تواريخها.
    """
    heads = [(m.start(), _parse_day(m.group(1), today))
             for m in re.finditer(r"<h2>(.*?)</h2>", page, re.S)]
    out: list[dict] = []
    for m in _ROW.finditer(page):
        seg = m.group(1)
        ev = _txt(_COL["event"].search(seg).group(1)) if _COL["event"].search(seg) else ""
        ty = _txt(_COL["type"].search(seg).group(1)) if _COL["type"].search(seg) else ""
        co = _txt(_COL["company"].search(seg).group(1)) if _COL["company"].search(seg) else ""
        if not ev or not co:
            continue
        if not any(k in ty or k in ev for k in _KEEP_TYPES):
            continue
        hit = index.get(co)
        if not hit:
            # حدثٌ لا شركةَ سعودية له (تقارير عالمية، جهات غير مدرَجة) —
            # يُسقَط بلا ضجيج. مفكرة المالك لسوقه.
            continue
        sym, cid = hit
        # آخر ترويسةٍ **مفهومة** سبقت هذا الصفّ هي يومُه. وقيد «المفهومة» ليس
        # تزيّداً: بين ترويسات الأيام ترويساتٌ فارغة `<h2></h2>`، فلو أخذنا
        # آخر ترويسةٍ مطلقاً لصار تاريخ الصفّ مجهولاً ولسقط — وكان نصف
        # المفكرة يختفي صامتاً. كشفه القياس على الصفحة الحيّة.
        d = None
        for pos, dd in heads:
            if pos >= m.start():
                break
            if dd is not None:
                d = dd
        if d is None:
            continue
        did = _DETAIL_ID.search(m.group(2) or "")
        out.append({
            "symbol": sym,
            "company_name": co,
            "title": ev,
            "type": ty or ev,
            "date": d.isoformat(),
            # مفكرةُ «أرقام»: مواعيدُ قادمة لا إعلاناتٌ وقعت (D020).
            "date_kind": "event",
            "url": f"{BASE}/ar/company/companyoverview/marketid/3/companyid/{cid}",
            "argaam_id": cid,
            # معرّف نصّ الإعلان الكامل — يُجلب عند فتح البطاقة لا في كل تحديث،
            # فلا نُثقل المصدر بعشرات الطلبات يومياً لنصوصٍ قد لا تُقرأ.
            "detail_id": did.group(1) if did else None,
            "source": "أرقام",
        })
    return out


async def fetch_argaam_calendar(weeks: int = 3) -> list[dict]:
    """الإفصاحات القادمة — الصفحة الأولى ثمّ أسابيعُ الترقيم بعدها.

    لا يرفع استثناءً أبداً: كل فشلٍ يُسجَّل ويُعاد ما جُمع. وإن لم يُجمع شيء
    عادت قائمةٌ فارغة — وهي إشارة «تعذّر» الصريحة التي تعرضها الواجهة، لا
    صمتاً يُقرأ كأنه «لا إفصاحات».
    """
    today = date.today()
    items: list[dict] = []
    index: dict[str, tuple[str, str]] = {}
    try:
        async with httpx.AsyncClient(
            timeout=30, follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "ar,en;q=0.8"},
        ) as client:
            r = await client.get(CAL_URL)
            r.raise_for_status()
            page = r.text
            index = _company_index(page)
            if not index:
                logger.warning("📅 أرقام: قائمة الشركات لم تُقرأ — تغيّرت البنية.")
                return []
            items += parse_calendar(page, index, today)

            # الأسابيع التالية: كلٌّ يبدأ من اليوم التالي لآخر يومٍ مقروء.
            cursor = today + timedelta(days=7)
            for _ in range(max(0, weeks - 1)):
                try:
                    rr = await client.get(MORE_URL.format(d=cursor.strftime("%d-%m-%Y")))
                    if rr.status_code != 200:
                        break
                    got = parse_calendar(rr.text, index, cursor)
                    if not got:
                        break
                    items += got
                except Exception as e:
                    logger.warning(f"📅 أرقام: تعذّر أسبوعُ {cursor}: {e}")
                    break
                cursor += timedelta(days=7)
    except Exception as e:
        logger.warning(f"📅 أرقام: تعذّر الوصول للمفكرة: {e}")
        return items

    # إزالة التكرار: الحدث نفسه للشركة نفسها في اليوم نفسه.
    seen: set = set()
    uniq: list[dict] = []
    for it in items:
        k = (it["symbol"], it["date"], it["title"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(it)

    if not uniq:
        logger.warning("📅 أرقام: لم يُستخرج صفٌّ واحد — البنية تغيّرت على الأرجح.")
    else:
        logger.info(f"📅 أرقام: {len(uniq)} إفصاحاً عبر {weeks} أسابيع.")
    return uniq


async def fetch_detail(detail_id: str) -> str | None:
    """نصّ الإعلان الكامل — مقدار التوزيع، جدول أعمال الجمعية، نسبة المنحة.

    قصاصةُ HTML تُجلب بالمعرّف وتُنظَّف إلى نصٍّ عربيّ مقروء. تُطلب عند فتح
    البطاقة فقط: التفاصيل التي لا تُقرأ لا تُجلب.

    وعند أي تعذّر يُعاد None — فتقول البطاقة «التفاصيل غير متوفّرة» ولا
    تختلق، ولا يمنع ذلك عرض الإعلان نفسه.
    """
    if not detail_id or not str(detail_id).isdigit():
        return None
    try:
        async with httpx.AsyncClient(
            timeout=20, follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "ar,en;q=0.8",
                     "X-Requested-With": "XMLHttpRequest"},
        ) as client:
            r = await client.get(f"{BASE}/ar/calendar/calendardetail/{detail_id}")
            if r.status_code != 200:
                return None
            # الوسوم البنيوية تُبدَّل بفواصل أسطر قبل النزع، وإلا التصق آخر
            # سطرٍ بأوّل ما بعده فصار النصّ كتلةً واحدة لا تُقرأ.
            raw = re.sub(r"<(br|/p|/div|/tr|/li|/h[1-6])[^>]*>", "\n", r.text, flags=re.I)
            raw = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)
            lines = [_txt(x) for x in raw.split("\n")]
            text = "\n".join(x for x in lines if x)
            return text[:2000] or None
    except Exception as e:
        logger.warning(f"📅 أرقام: تعذّر جلب تفاصيل {detail_id}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════
#  الإفصاحات — ما يصدر لحظةَ صدوره، لا ما يُجدوَل
#
#  المفكرة تقول «جمعية أرامكو يوم ٢١». والإفصاح يقول «باعظيم وقّعت عقداً
#  اليوم». الأوّل موعدٌ قادم والثاني خبرٌ وقع، وكلاهما يخصّ المالك.
#
#  وبينهما فرقٌ تقنيّ يفرض حذراً: في المفكرة الشركةُ **عمودٌ مستقلّ** يُربط
#  برمزه يقيناً. وفي الإفصاحات اسمُها داخل نصّ العنوان — فالنسبة مطابقةُ
#  اسمٍ لا قراءةُ حقل. ولذلك:
#    • يُجرَّب الاسم الأطول أولاً (كيلا يبتلع «سابك» اسمَ «سابك للمغذيات»).
#    • ويُشترط أن يقع الاسم بين فاصلَين لا داخل كلمة.
#    • وما لا يُنسب بيقين يُترك — لا يدخل مفكرة المالك منسوباً بالظنّ.
# ══════════════════════════════════════════════════════════════════════════

DISC_URL = BASE + "/ar/company/disclosure/sectionid/245/marketid/3/pageNo/{p}"

_ART = re.compile(
    r'<div class="article-tbl[^"]*">(.*?)<div class="source"', re.S)
_D_DATE = re.compile(r'<div class="date">\s*(\d{4})/(\d{2})/(\d{2})')
_D_LINK = re.compile(r'<a href="(/ar/article/articledetail/id/\d+)"[^>]*>(.*?)</a>', re.S)

# حروفٌ تعدّ جزءاً من الكلمة العربية — ما عداها فاصل. لام التعريف وحروف
# الجرّ الملتصقة تُعامل فواصلَ عبر تجريبها صراحةً في المطابقة.
_AR_LETTER = r"ء-ي"


def _match_company(title: str, names: list[str],
                   index: dict[str, tuple[str, str]]) -> tuple[str, str] | None:
    """اسمُ شركةٍ داخل عنوان → (رمز، رقم أرقام). و`None` إن لم يُتيقَّن."""
    for nm in names:
        # الاسم بين فاصلَين: بدايةُ نصٍّ أو غيرُ حرفٍ عربيّ من الجهتين. بلا
        # هذا القيد يطابق «علم» داخل «معلومات» و«العلمية».
        pat = rf"(?:^|[^{_AR_LETTER}])(?:ال)?{re.escape(nm)}(?:$|[^{_AR_LETTER}])"
        if re.search(pat, title):
            return index[nm]
    return None


async def fetch_argaam_disclosures(pages: int = 2) -> list[dict]:
    """الإفصاحات المنشورة — العنوان والتاريخ والرابط، منسوبةً حين يُتيقَّن.

    يُعيد ما نُسب فقط: إفصاحٌ بلا شركةٍ معروفة لا مكان له في مفكرة المالك،
    ومكانُه قسم الأخبار. وعند أي تعذّر تُعاد قائمةٌ فارغة — انكسارٌ صائح.
    """
    out: list[dict] = []
    try:
        async with httpx.AsyncClient(
            timeout=30, follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "ar,en;q=0.8"},
        ) as client:
            index: dict[str, tuple[str, str]] = {}
            names: list[str] = []
            for p in range(1, max(1, pages) + 1):
                r = await client.get(DISC_URL.format(p=p))
                if r.status_code != 200:
                    break
                page = r.text
                if not index:
                    index = _company_index(page)
                    if not index:
                        logger.warning("📰 أرقام/إفصاحات: قائمة الشركات لم تُقرأ.")
                        return []
                    # الأطول أولاً — وإلا ابتلع الاسمُ القصير نظيرَه الأطول.
                    names = sorted(index, key=len, reverse=True)
                for m in _ART.finditer(page):
                    seg = m.group(1)
                    dm = _D_DATE.search(seg)
                    lm = _D_LINK.search(seg)
                    if not dm or not lm:
                        continue
                    title = _txt(lm.group(2))
                    if not title:
                        continue
                    hit = _match_company(title, names, index)
                    if not hit:
                        continue
                    sym, cid = hit
                    out.append({
                        "symbol": sym,
                        "title": title,
                        # الموضع الثالث الذي كان يُمرّر العنوان وسماً — أمسكه
                        # الحارس بعد إصلاح الأوّلين، ولم يكن في الحسبان.
                        "type": cp_kind(title),
                        "date": f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}",
                        # هذا تاريخُ **صدور** الإعلان لا موعدُ حدثٍ قادم.
                        # الواجهة تقرأ هذا الوسم فتكتب «أُعلن: …» — بلا ذلك
                        # يقرؤه المالك تحت «اليوم» كأنه موعدُ اليوم.
                        "date_kind": "announced",
                        "url": BASE + lm.group(1),
                        "argaam_id": cid,
                        "source": "أرقام",
                    })
    except Exception as e:
        logger.warning(f"📰 أرقام/إفصاحات: تعذّر الوصول: {e}")
        return out

    seen: set = set()
    uniq = []
    for it in out:
        k = (it["symbol"], it["date"], it["title"])
        if k not in seen:
            seen.add(k)
            uniq.append(it)
    if not uniq:
        logger.warning("📰 أرقام/إفصاحات: لم يُنسب إفصاحٌ واحد — راجع البنية.")
    else:
        logger.info(f"📰 أرقام: {len(uniq)} إفصاحاً منسوباً.")
    return uniq


# ── أخبار «أرقام» — الثالثة من مرآة الزرّ ───────────────────────────────────
# طلب المالك أن يُعكس محتوى «افتح في أرقام» داخل التطبيق بثلاثة أوجه:
# المفكرة والإفصاحات والأخبار. والأوّلان يقرآن الصفحتين أعلاه؛ وهذا الثالث.
#
# ولماذا نُضيفه وأرقام أصلاً في سجلّ المصادر: هو يصلنا اليوم **بالواسطة**
# عبر Google News RSS — عناوينُ منتقاة لا كلُّ ما ينشره، وبتأخيرٍ وبصياغة
# الوسيط. وهذا يقرأ صفحته هو.
#
# ⚠ **لم يُقَس على صفحةٍ حيّة.** شبكة التطوير محجوبة عن argaam.com (‏403
# عند بوّابة الشبكة)، فبُني المُحلِّل على البنية المقيسة نفسها التي تخدم
# الإفصاحات (روابط `/ar/article/articledetail/id/…` وكتلة `date`). فإن
# اختلفت صفحةُ الأخبار عنها لم يُستخرج شيء — ويُقال ذلك في السجلّ ولا
# يُعرض قديمٌ كأنه جديد.
# الرابط مُقاسٌ على الخادم لا مخمَّن: جُرّبت ثمانيةُ مرشّحات، فردّ سبعةٌ
# منها 404 (ومنها تخميني الأوّل)، وردّ هذا **200 بمئةٍ وسبعة عشر رابط
# مقال**. فالمقياس هو الذي اختار، لا الاجتهاد.
NEWS_URL = BASE + "/ar/articles"

_N_ITEM = re.compile(r'<a href="(/ar/article/articledetail/id/\d+)"[^>]*>(.*?)</a>', re.S)
_N_DATE = re.compile(r'(\d{4})/(\d{2})/(\d{2})')


async def fetch_argaam_news(pages: int = 1) -> list[dict]:
    """عناوين «أرقام» بتواريخها وروابطها — أو قائمةٌ فارغة وتحذير.

    لا يُنسب الخبر إلى شركةٍ إلا إن ورد اسمُها في العنوان (بقائمة الصفحة
    نفسها، كما في الإفصاحات) — وما لا يُنسب يبقى خبراً عامّاً للسوق، وهذا
    صحيحٌ لا نقص: أكثر أخبار «أرقام» عن السوق لا عن شركةٍ بعينها.
    """
    out: list[dict] = []
    try:
        async with httpx.AsyncClient(
            timeout=30, follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "ar,en;q=0.8"},
        ) as client:
            index: dict[str, tuple[str, str]] = {}
            names: list[str] = []
            for _ in range(1):        # صفحةٌ واحدة غير مرقَّمة
                r = await client.get(NEWS_URL)
                if r.status_code != 200:
                    logger.warning(f"📰 أرقام/أخبار: HTTP {r.status_code}")
                    break
                page = r.text
                if not index:
                    index = _company_index(page)
                    names = sorted(index, key=len, reverse=True) if index else []
                for m in _N_ITEM.finditer(page):
                    href, raw = m.group(1), m.group(2)
                    title = _txt(raw)
                    if not title or len(title) < 12:
                        continue
                    # التاريخ يُلتمس في محيط الرابط — والغيابُ لا يُختلق له
                    # بديل: خبرٌ بلا تاريخ يُرسَل بلا تاريخ وتتصرّف الواجهة.
                    around = page[max(0, m.start() - 400): m.end() + 400]
                    dm = _N_DATE.search(around)
                    hit = _match_company(title, names, index) if names else None
                    out.append({
                        "headline": title,
                        "url": BASE + href,
                        "source": "أرقام",
                        "published": f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" if dm else None,
                        "symbol": hit[0] if hit else None,
                    })
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"📰 أرقام/أخبار: تعذّر الوصول: {e}")
        return []

    seen: set = set()
    uniq = []
    for it in out:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        uniq.append(it)
    if not uniq:
        logger.warning("📰 أرقام/أخبار: لم يُستخرج عنوانٌ واحد — راجع البنية.")
    else:
        logger.info(f"📰 أرقام: {len(uniq)} خبراً.")
    return uniq


# ── صفحةُ الشركة نفسها — الطريق الذي يفتحه الزرّ ────────────────────────────
# لماذا هذا الطريق لا مفكرة السوق العامّة:
#   قال المالك إن التطبيق لم يُغنِه عن الذهاب إلى «أرقام»، وأن زرّ «افتح في
#   أرقام» هو محكُّه. والصفحة التي يفتحها تحمل **جدول مفكرة الشركة وإفصاحاتها
#   كاملةً** — بينما مفكرة السوق العامّة نافذةٌ زمنية ضيّقة (ثلاثة أسابيع)
#   تمرّ على السوق كلّه، فتسقط منها جمعيةٌ في مايو أو صرفٌ خارج النافذة.
#   وقِيس في مخرَج المالك: أرقام يعرض للنهدي جمعيةً في 2026-05-19 وصرفاً في
#   2026-08-26، ولا يظهر منهما شيءٌ في المفكرة العامّة.
#
# ولماذا لا يُقرأ بالذكاء (وقد اقترحه المالك):
#   نداءٌ لكل شركة يستهلك حصّةً يومية محدودة، وناتجُه غير حتميّ — يقرأ الصفحة
#   مرّتين فيعطي صيغتين للحدث الواحد فيدخل المخزنَ مرّتين. والجدول هنا
#   **مُهيكل** (صفٌّ فيه تاريخٌ وحدث)، فقراءتُه المباشرة أرخص وأدقّ وقابلة
#   للاختبار. ويبقى الذكاء احتياطاً إن انكسر التركيب — لا طريقاً أوّل.
#
# البنية أدناه مبنيّةٌ على لقطة المالك من الصفحة الحيّة، ولم تُقَس من بيئة
# التطوير (محجوبة، 403). ولذلك يُرفق `probe_company_page` يردّ عيّنةً خاماً
# عند الفشل — فيُصحَّح من مخرَجٍ حقيقيّ لا من تخمينٍ ثانٍ.

# التاريخُ يُكتب في «أرقام» بشرطةٍ في موضعٍ وبمائلةٍ في آخر (‏2026/08/26
# في جدول التوصيات) — فيُقبلان معاً، وإلّا سقط التاريخُ صامتاً.
_CP_DATE = re.compile(r"(\d{4})[-/](\d{2})[-/](\d{2})")
_CP_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
# ── تصنيف صفّ «أرقام» إلى وسمٍ يعرفه التطبيق ────────────────────────────
# كان `"type": title` — أي **العنوان نفسه** يُمرَّر وسماً. والواجهة تُطابق
# الوسم بجدولٍ مغلق (DIVIDEND · AGM · BONUS…)، فكلُّ عنوانٍ لا يطابقه حرفياً
# يسقط إلى OTHER = «إعلان». ولهذا كان صفُّ «صرف أرباح» يُوسَم إعلاناً وهو
# توزيع — الوسم يقول شيئاً والسطر يقول غيره.
# والترتيب مقصود: تُفحص الجمعيةُ أوّلاً لأن جدول أعمالها قد يذكر التوزيع
# فتُوسَم به خطأً. و«الأحقية» تُفحص قبل «الصرف» ولا تُطوى فيه: الأحقيةُ
# تاريخُ الاستحقاق والصرفُ تاريخُ وصول النقد — قراران مختلفان.
_CP_KIND = (
    ("جمعية", "جمعية"), ("الجمعية", "جمعية"),
    ("منحة", "منحة"),
    ("تجزئة", "تجزئة"),
    ("حقوق أولوية", "حقوق أولوية"), ("زيادة رأس المال", "زيادة رأس المال"),
    ("اندماج", "اندماج"), ("استحواذ", "استحواذ"),
    ("النتائج", "نتائج"), ("نتائج", "نتائج"),
    ("أحقية", "أحقية"), ("احقية", "أحقية"),   # لا تُطوى في «توزيع»: الأحقيةُ استحقاقٌ والصرفُ وصولُ نقد
    ("صرف", "توزيع"), ("توزيع", "توزيع"), ("أرباح", "توزيع"),
)


def cp_kind(title: str) -> str:
    """وسمُ الصفّ من عنوانه — بألفاظ المفكرة التي تعرفها الواجهة."""
    t = title or ""
    for needle, kind in _CP_KIND:
        if needle in t:
            return kind
    return "إعلان"


_CP_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
# ── جداولُ «أرقام» ليست كلُّها <table> ────────────────────────────────
# مفكرةُ الشركة نفسها تُبنى بـ`<div class="colum …">` لا بـ`<td>` (انظر
# العيّنة أعلى الملفّ). فمن يقرأ الخلايا بـ`<td>` وحده يرى صفحةً بلا
# صفوفٍ ويقول «لا توصيات» — وهي معروضةٌ على الموقع.
# رأى المالك ذلك بنفسه: فتح صفحة الشركة في «أرقام» فوجد أربع توصيات،
# والتطبيقُ يقول «لا توجد توصيات متاحة».
_CP_DIVSTART = re.compile(r'<div[^>]*class="[^"]*\brow\b[^"]*"', re.S)
_CP_DIVCELL = re.compile(r'<div[^>]*class="[^"]*\bcolum\b[^"]*"[^>]*>(.*?)</div>', re.S)


def _rows_of(page: str) -> list[list[str]]:
    """صفوفُ الجدول خلايا نصّية — من `<tr>` أو من شبكة `<div class="colum">`.

    ولا يُفترض شكلٌ واحد: يُقرأ الشكلان ويُضمّ مخرَجهما، فما وُجد وُجد.
    """
    out: list[list[str]] = []
    for m in _CP_ROW.finditer(page):
        cells = [x for x in (_txt(y) for y in _CP_CELL.findall(m.group(1))) if x]
        if len(cells) >= 2:
            out.append(cells)
    # الصفُّ في الشبكة يبدأ عند `class="row"` وينتهي عند بداية الصفّ
    # التالي — لا عند أوّل `</div>`، فالخلايا نفسها عناصرُ مغلقة داخله.
    marks = [m.start() for m in _CP_DIVSTART.finditer(page)] + [len(page)]
    for a, b in zip(marks, marks[1:]):
        cells = [x for x in (_txt(y) for y in _CP_DIVCELL.findall(page[a:b])) if x]
        if len(cells) >= 2:
            out.append(cells)
    return out
_CP_ART = re.compile(r'<a href="(/ar/article/articledetail/id/\d+)"[^>]*>(.*?)</a>', re.S)


def _company_url(cid: str) -> str:
    return f"{BASE}/ar/company/companyoverview/marketid/3/companyid/{cid}"


async def _company_id(symbol: str) -> str | None:
    from app.services.argaam_ids import build as _build, snapshot as _snap
    try:
        await _build()
        return (_snap().get("ids") or {}).get(str(symbol))
    except Exception:
        return None


async def fetch_company_page(symbol: str, company_id: str | None = None) -> dict:
    """مفكرةُ شركةٍ بعينها وإفصاحاتُها — من صفحتها في «أرقام».

    تُعاد {"calendar": [...], "disclosures": [...]}، وقد يكون كلاهما فارغاً.
    والفراغ يُسجَّل تحذيراً ولا يُملأ بشيء.
    """
    out: dict = {"calendar": [], "disclosures": [], "url": None}
    cid = company_id or await _company_id(symbol)
    if not cid:
        logger.warning(f"أرقام/شركة {symbol}: لا مُعرِّف صفحةٍ معروف.")
        return out
    url = _company_url(cid)
    out["url"] = url
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                     headers={"User-Agent": UA,
                                              "Accept-Language": "ar,en;q=0.8"}) as c:
            r = await c.get(url)
        if r.status_code != 200:
            logger.warning(f"أرقام/شركة {symbol}: HTTP {r.status_code}")
            return out
        page = r.text
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"أرقام/شركة {symbol}: تعذّر الوصول: {e}")
        return out

    for cells in _rows_of(page):
        dm = next((_CP_DATE.fullmatch(c) for c in cells if _CP_DATE.fullmatch(c)), None)
        if not dm:
            continue
        title = next((c for c in cells if not _CP_DATE.fullmatch(c)), "")
        if not title or len(title) > 90:
            continue
        out["calendar"].append({
            "symbol": str(symbol), "title": title, "type": cp_kind(title),
            "date": f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}",
            "date_kind": "event", "url": url, "source": "أرقام",
        })

    for m in _CP_ART.finditer(page):
        title = _txt(m.group(2))
        if not title or len(title) < 12:
            continue
        around = page[max(0, m.start() - 300): m.end() + 300]
        dm = re.search(r"(\d{4})/(\d{2})/(\d{2})", around)
        out["disclosures"].append({
            "symbol": str(symbol), "title": title, "type": cp_kind(title),
            "date": f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" if dm else None,
            "date_kind": "announced", "url": BASE + m.group(1), "source": "أرقام",
        })

    if not out["calendar"] and not out["disclosures"]:
        logger.warning(f"أرقام/شركة {symbol}: الصفحة وصلت ولم يُقرأ منها شيء — راجع البنية.")
    else:
        logger.info(f"أرقام/شركة {symbol}: مفكرة={len(out['calendar'])} إفصاحات={len(out['disclosures'])}")
    return out


async def probe_company_page(symbol: str) -> dict:
    """ما يكفي لتصحيح المُحلِّل من مخرَجٍ حقيقيّ بلا تخمينٍ ثانٍ."""
    cid = await _company_id(symbol)
    if not cid:
        return {"symbol": symbol, "error": "لا مُعرِّف صفحة"}
    url = _company_url(cid)
    async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                 headers={"User-Agent": UA,
                                          "Accept-Language": "ar,en;q=0.8"}) as c:
        r = await c.get(url)
    page = r.text or ""
    i = page.find("المفكرة")
    got = await fetch_company_page(symbol, cid)
    return {"url": url, "http": r.status_code, "bytes": len(page),
            "tables": page.count("<table"), "rows": page.count("<tr"),
            "iso_dates": len(_CP_DATE.findall(page)),
            "parsed_calendar": len(got["calendar"]),
            "parsed_disclosures": len(got["disclosures"]),
            "raw": page[max(0, i - 100): i + 900] if i > -1 else page[:600]}


# ── توصيات المحللين من «أرقام» ──────────────────────────────────────────
# طلب المالك تبويباً ثالثاً بجانب المفكرة والإفصاحات يقرأ من زرّ «أرقام».
#
# ولستُ أعرف مسار الصفحة يقيناً: المختبر بلا إنترنت، فلا أستطيع فتح
# «أرقام» لأرى بنيتها. وقد جرّبتُ التخمين مرّةً في مسار الأخبار فأخطأتُ،
# ثم صحّحه القياسُ على خادم المالك (‏٧ من ٨ مرشّحين أعادوا 404). فبُني
# هذا على المبدأ نفسه: **قائمةُ مرشّحين تُجرَّب واحداً واحداً**، ويُعتمد
# أوّلُ ما يُعيد 200 ويُقرأ منه صفٌّ واحد على الأقلّ. والذي نجح يُسجَّل
# في السجلّ باسمه كي يُعرف — لا يُخمَّن مرّةً أخرى.
_REC_PATHS = (
    "/ar/company/recommendations/marketid/3/companyid/{cid}",
    "/ar/company/companyrecommendations/marketid/3/companyid/{cid}",
    "/ar/company/analystrecommendations/marketid/3/companyid/{cid}",
    "/ar/company/targetprices/marketid/3/companyid/{cid}",
    "/ar/company/companyoverview/marketid/3/companyid/{cid}",
)
# ألفاظ التوصية كما تكتبها بيوت الخبرة العربية.
_REC_WORDS = ("شراء قوي", "شراء", "زيادة", "تفوق", "احتفاظ", "حياد",
              "محايد", "تخفيض", "بيع", "أقل من السوق")
_REC_NUM = re.compile(r"^\d{1,3}(?:[.,]\d{1,2})?$")


def _rec_row(cells: list[str]) -> dict | None:
    """صفُّ توصيةٍ من خلايا جدول — أو None إن لم يكن صفَّ توصية.

    الشرط الأدنى: خليّةٌ تحمل لفظ توصيةٍ معروفاً. وبلا ذلك لا يُقبل الصفّ
    مهما بدا شكله جدولاً — فجدولٌ آخر في الصفحة ليس توصيات.
    """
    verdict = next((c for c in cells
                    if any(c.strip().startswith(w) for w in _REC_WORDS)), None)
    if not verdict:
        return None
    dm = next((_CP_DATE.search(c) for c in cells if _CP_DATE.search(c)), None)
    target = next((c for c in cells
                   if _REC_NUM.fullmatch(c.strip()) and c != verdict), None)
    house = next((c for c in cells
                  if c not in (verdict, target) and not _CP_DATE.search(c)
                  and not _REC_NUM.fullmatch(c.strip()) and 2 < len(c) < 60), None)
    return {
        "house": house, "verdict": verdict.strip(),
        # السعر المستهدف قد يغيب، ولا يُختلق: يبقى None وتقول الواجهة «—».
        "target": float(target.replace(",", ".")) if target else None,
        "date": f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" if dm else None,
        "source": "أرقام",
    }


async def fetch_company_recommendations(symbol: str,
                                        company_id: str | None = None) -> dict:
    """توصياتُ المحللين لشركةٍ بعينها من «أرقام».

    تُعاد {"rows": [...], "url": ..., "tried": [...]}. والفراغ يبقى فراغاً:
    لا إجماعَ ياهو يُدسّ مكانها ولا رقمَ يُختلق — التبويب يقول «غير
    متوفّرة من أرقام» ويترك زرّ المصدر ظاهراً.
    """
    out: dict = {"rows": [], "url": None, "tried": []}
    cid = company_id or await _company_id(symbol)
    if not cid:
        logger.warning(f"أرقام/توصيات {symbol}: لا مُعرِّف صفحةٍ معروف.")
        return out
    async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                 headers={"User-Agent": UA,
                                          "Accept-Language": "ar,en;q=0.8"}) as c:
        for path in _REC_PATHS:
            url = BASE + path.format(cid=cid)
            try:
                r = await c.get(url)
            except Exception as e:                                # noqa: BLE001
                out["tried"].append({"url": url, "http": f"خطأ: {e}"})
                continue
            out["tried"].append({"url": url, "http": r.status_code})
            if r.status_code != 200:
                continue
            rows = []
            # ══ الخلايا الخام تُحفظ للمسبار ══ (بأمر المالك)
            # ظهرت التوصيات بحكمٍ وتاريخٍ بلا اسم بيت خبرةٍ ولا سعرٍ
            # مستهدف — أي أن المحلّل لم يجد الخليّتين. وتخمينُ تخطيط
            # الجدول من بعيد هو بعينه ما أوقعنا في أخطاء سابقة، فتُعرض
            # الخلايا كما وصلت ويُبنى المحلّل على شكلها الحقيقيّ.
            out.setdefault("خلايا_خام", [])
            for cells in _rows_of(r.text):
                if len(out["خلايا_خام"]) < 6:
                    out["خلايا_خام"].append(cells)
                row = _rec_row(cells)
                if row:
                    row["symbol"] = str(symbol)
                    rows.append(row)
            if rows:
                out["rows"], out["url"] = rows, url
                logger.info(f"أرقام/توصيات {symbol}: {len(rows)} صفّاً من {url}")
                return out
    logger.warning(f"أرقام/توصيات {symbol}: لم يُقرأ صفٌّ من أيّ مرشّح — "
                   f"جُرّب {len(out['tried'])}.")
    return out


# ── نِسَبٌ رقابية تُقرأ من «أرقام» ───────────────────────────────────────
# كنّا نُعلن أن كفاية رأس المال والقروض المتعثّرة والنسبة المجمّعة «خارج
# النطاق». وراجعٌ خارجيّ صحّح ذلك: هي **منشورة** ربعياً في إفصاحات
# الركيزة الثالثة وعروض المستثمرين وصفحات «أرقام» — فالبندُ غائبٌ عن
# أنبوبنا لا عن السوق، والفرقُ جوهريّ: الأوّل نقصٌ نصلحه، والثاني حدٌّ
# نُقرّ به. ولا يجوز أن نصف قصورَنا بأنه طبيعةُ السوق.
#
# فتُقرأ من جدول الصفحة بمطابقة عناوينها العربية. وما لم يُقرأ يبقى
# غائباً صراحةً — لا يُقدَّر ولا يُشتقّ من نظير.
_RATIO_LABELS = {
    "كفاية رأس المال": "car",
    "كفاية رأس المال الأساسي": "car_tier1",
    "القروض المتعثرة": "npl",
    "القروض المتعثّرة": "npl",
    "نسبة التعثر": "npl",
    "تغطية المتعثرات": "npl_coverage",
    "مخصص التعثرات": "npl_coverage",
    "النسبة المجمعة": "combined_ratio",
    "النسبة المجمّعة": "combined_ratio",
    "نسبة الخسائر": "loss_ratio",
    "هامش الملاءة": "solvency_margin",
}
_RATIO_NUM = re.compile(r"-?\d+(?:[.,]\d+)?")


async def fetch_company_ratios(symbol: str,
                               company_id: str | None = None) -> dict:
    """النِّسَبُ الرقابية لشركةٍ من «أرقام» — ما وُجد منها فقط.

    تُعاد {"ratios": {...}, "url": ..., "خلايا_خام": [...]}. والفراغُ
    يبقى فراغاً: لا يُشتقّ رقمٌ من قطاعٍ ولا من سنةٍ أخرى.
    """
    out: dict = {"ratios": {}, "url": None, "خلايا_خام": []}
    cid = company_id or await _company_id(symbol)
    if not cid:
        return out
    url = _company_url(cid)
    out["url"] = url
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                     headers={"User-Agent": UA,
                                              "Accept-Language": "ar,en;q=0.8"}) as c:
            r = await c.get(url)
        if r.status_code != 200:
            return out
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"أرقام/نِسَب {symbol}: تعذّر الوصول: {e}")
        return out

    for cells in _rows_of(r.text):
        if len(out["خلايا_خام"]) < 8:
            out["خلايا_خام"].append(cells)
        label = next((c for c in cells if any(k in c for k in _RATIO_LABELS)), None)
        if not label:
            continue
        key = next(v for k, v in _RATIO_LABELS.items() if k in label)
        num = next((_RATIO_NUM.search(c) for c in cells
                    if c is not label and _RATIO_NUM.search(c)), None)
        if num:
            try:
                out["ratios"][key] = float(num.group(0).replace(",", "."))
            except ValueError:
                pass
    if out["ratios"]:
        logger.info(f"أرقام/نِسَب {symbol}: {list(out['ratios'])}")
    return out
