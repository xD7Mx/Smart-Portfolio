#!/usr/bin/env python3
"""فحوص لجنة كشف الأعطال — الطبقة الساكنة (تقرأ الشيفرة، لا تشغّل شيئاً).

كل فحصٍ هنا **وُلد من عطبٍ وقع فعلاً** في هذا المشروع، ورقمُه مسجَّل في
`registry.json`. وهذا هو معنى أن تتراكم خبرة اللجنة: العطب يُصلَح مرّة،
والفحص يمنع عودته إلى الأبد — وعودةُ العطب نفسه بعد إصلاحه أسوأ من وقوعه
أوّل مرّة، لأنها تعني أننا لم نتعلّم.

    تشغيل:  python3 scripts/audit/static.py
    الخروج: 0 إن نظُف، و1 إن وُجدت ملاحظة (يصلح بوّابةً قبل التسليم).
"""

import json
import pathlib
import ast
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
findings: list[tuple[str, str, str]] = []       # (رمز الفحص، الموضع، الوصف)


def note(check: str, where: str, what: str) -> None:
    findings.append((check, where, what))


# ── S-DEADBTN — زرٌّ يَعِد ولا يفعل (D006) ────────────────────────────────
def check_dead_buttons() -> None:
    """زرٌّ بلا معالج ولا إرسالٍ ضمنيّ. الاستثناءان المشروعان:
    زرٌّ يمرّر `props` من مكوّنٍ أعلى، وزرٌّ داخل `form` يُرسلها."""
    for f in (ROOT / "frontend/src").rglob("*.tsx"):
        src = f.read_text(encoding="utf-8")
        for m in re.finditer(r"<button\b", src):
            i = m.start()
            j = src.find(">", i)
            tag = src[i:j + 1]
            if any(k in tag for k in ("onClick", "onMouseDown", "onPointerDown",
                                      "{...props}", 'type="submit"')):
                continue
            # داخل نموذج؟ ابحث عن <form قبله بلا إغلاقٍ بينهما
            before = src[:i]
            if before.rfind("<form") > before.rfind("</form>"):
                continue
            note("S-DEADBTN", f"{f.relative_to(ROOT)}:{before.count(chr(10)) + 1}",
                 "زرٌّ بلا معالج ولا إرسالٍ ضمنيّ")


# ── S-FABRICATED — استبدال الغائب بقيمةٍ مختلَقة (D005) ───────────────────
_ALLOWED_SUBSTITUTIONS = {
    # اشتقاقٌ من مصدرٍ آخر، لا اختلاق
    "app/services/tadawul_announcements.py",
    # أجلُ جلسةٍ احتياطيّ — بيانُ نظامٍ لا بيانُ مالك
    "app/core/sessions.py",
    # مُصلَح: يحتفظ بـprev_close=None ليُعرف أن الصفر بلا مرجع
    "app/services/market_data.py",
}


def check_fabricated() -> None:
    pat = re.compile(r"^\s*(\w+)\s*=\s*.*\bif\s+\1\b\s+else\s+(?!None\b)(\S.*)$")
    for f in (ROOT / "backend/app").rglob("*.py"):
        rel = str(f.relative_to(ROOT / "backend"))
        if rel in _ALLOWED_SUBSTITUTIONS:
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
            if pat.match(line):
                note("S-FABRICATED", f"{f.relative_to(ROOT)}:{i}",
                     f"غائبٌ يُستبدل بقيمةٍ أخرى: {line.strip()[:90]}")


# ── S-MERGE — حفظٌ يمحو ما لم يُذكر (D004) ────────────────────────────────
def check_merge_save() -> None:
    """مسار حفظ التخطيط يجب أن يقرأ الملف ويدمج، لا أن يكتبه من الصفر."""
    f = ROOT / "backend/app/api/v1/endpoints/settings.py"
    src = f.read_text(encoding="utf-8")
    i = src.find("async def save_layout")
    if i < 0:
        note("S-MERGE", str(f.relative_to(ROOT)), "لم يُعثر على مسار حفظ التخطيط")
        return
    body = src[i:i + 1600]
    if "json.load" not in body:
        note("S-MERGE", str(f.relative_to(ROOT)),
             "الحفظ لا يقرأ المحفوظ قبل الكتابة — أيّ حمولةٍ جزئية تمحو الباقي")


# ── S-SECRETS — سرٌّ في ملفٍّ متتبَّع (D008) ───────────────────────────────
_SECRET = re.compile(
    r"[0-9]{8,12}:AA[A-Za-z0-9_-]{30,}"      # رمز بوت تلغرام
    r"|sk-[A-Za-z0-9]{20,}"                   # مفاتيح OpenAI-style
    r"|AIza[A-Za-z0-9_-]{30,}"                # مفاتيح Google
)


def check_secrets() -> None:
    try:
        files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                               text=True, check=True).stdout.split("\n")
    except Exception as e:                                        # noqa: BLE001
        note("S-SECRETS", "git", f"تعذّر سرد الملفّات المتتبَّعة: {e}")
        return
    for rel in files:
        if not rel:
            continue
        p = ROOT / rel
        if not p.is_file() or p.stat().st_size > 2_000_000:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:                                         # noqa: BLE001
            continue
        if _SECRET.search(txt):
            note("S-SECRETS", rel, "رمزٌ سرّيٌّ حيّ داخل ملفٍّ متتبَّع")


# ── S-HARDCOLOR — لونٌ ثابت خارج الرموز ───────────────────────────────────
def check_hardcoded_colors() -> None:
    """الألوان من رموز `globals.css` وحدها. تُستثنى الرموزُ نفسها، وما
    يجلس على سطحٍ ثابت لا يتبدّل بالمظهر (لسان الشريط) — وهو موثَّق."""
    allow = re.compile(r"#fff\b|#ffffff\b|#000\b|#000000\b|transparent")
    hexpat = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    # ══ أسطحٌ ثابتةٌ بقرار، لا بسهو ══
    # فحصٌ يصرخ في وجه ما هو صحيح يُدرَّب المالك على تجاهله، فيصمت يوم
    # يصدق. فتُستثنى الأسطح التي **لا تتبع المظهر بتصميمها**، ولكلٍّ سببه:
    exempt = {
        "reports/ReportDocument.tsx": "ورقةُ تقريرٍ تُطبع: ورقٌ كريميّ وذهبٌ، هويّةٌ مستقلّة عن مظهر الشاشة",
        "common/Logo.tsx": "علامةُ التطبيق — ثابتةٌ بتعريفها",
        "common/CompanyLogo.tsx": "حرفُ الشركة على تدرّج لونها هي",
        "pages/LoginPage.tsx": "شاشةُ القفل: سطحٌ داكنٌ واحد قبل الدخول، لا مظهرَ للمستخدم بعد",
        "common/MarketTicker.tsx": "لسانٌ بنفسجيّ لا يتبدّل بالمظهر — ألوانه الثلاث بأمر المالك",
    }
    for f in (ROOT / "frontend/src").rglob("*.tsx"):
        rel = str(f.relative_to(ROOT))
        if any(k in rel for k in exempt):
            continue
        # ══ التعليق ليس شيفرة ══
        # كان الفحص يتخطّى السطر إن **بدأ** بعلامة تعليق، فيمرّ على سطرٍ
        # في وسط تعليقٍ متعدّد الأسطر ويقرأ لوناً مذكوراً في شرحٍ يصف
        # عطباً قديماً. وقع هذا فعلاً: تعليقٌ يشرح لماذا أُزيل ‎#2f2f2f
        # أوقف البوّابة بسببه هو نفسه.
        # فتُمحى كتل التعليق أوّلاً **بحفظ الأسطر** كي تبقى المواضع صحيحة.
        src = re.sub(r"/\*.*?\*/",
                     lambda m: re.sub(r"[^\n]", " ", m.group(0)),
                     f.read_text(encoding="utf-8"), flags=re.S)
        for i, line in enumerate(src.split("\n"), 1):
            if line.strip().startswith(("//", "*", "/*")):
                continue
            # احتياطُ `tok("--x", "#hex")` مشروع: هو ما يُرسم إن تعذّرت
            # قراءة الرمز. والرمز يبقى المصدر، والاحتياط شبكةُ أمان.
            # ويشمل ذلك `tokA("--x", "#hex", .4)` — نفسه بشفافيةٍ للوحة
            # الرسم، التي لا تفهم `var()` ولا `color-mix`.
            stripped = re.sub(r'tokA?\(\s*"--[\w-]+"\s*,\s*"[^"]*"\s*(?:,[^)]*)?\)', "", line)
            # خلفيةُ تصدير التقرير صورةً: ورقُ التقرير نفسه، وهو سطحٌ ثابت.
            if "backgroundColor" in stripped and "faf6ee" in stripped:
                continue
            for m in hexpat.finditer(stripped):
                if allow.search(m.group(0)):
                    continue
                note("S-HARDCOLOR", f"{rel}:{i}",
                     f"لونٌ ثابت خارج الرموز: {m.group(0)}")
                break


# ── S-VARLEAK — رمزُ تصميمٍ يُوضع حيث لا يُقرأ (D009 · D010) ───────────────
# ══ لماذا المحدِّد ضيّقٌ عمداً ══
# أوّل صياغةٍ لهذا الفحص وسمت كل `color: "var(--…)"` فأطلقت أربعين إنذاراً
# على شيفرةٍ **صحيحة**: كائناتُ بياناتٍ يذهب لونها إلى `style` في DOM،
# وهناك تُحلّ الرموز بلا مشكلة. وفحصٌ يصرخ في وجه الصواب يُدرَّب المالك
# على تجاهله فيصمت يوم يصدق — وهي القاعدة نفسها التي طبّقناها على فحص
# الألوان. فحُصر في الموضعين اللذين **لا تُحلّ فيهما** حقاً.
_CANVAS_API = re.compile(
    r"createChart\(|applyOptions\(|add(?:Line|Area|Candlestick|Histogram|Bar|Baseline)Series\(")
# ملحوظةُ قياسٍ نقضت اعتقاداً: ظننتُ أن `fill="var(--x)"` لا تُحلّ في
# خصائص وسوم SVG — وهو ما كتبتُه يوماً سبباً لاختفاء أرقام الرسوم. فقِستُه
# في المتصفّح بعنصرٍ مصنوعٍ لهذا الغرض: `fill="var(--pos-ink)"` أعطى
# `rgb(4,120,87)`، ومسارات الرسم الفعلية كذلك. فالخصائص تُعامَل معاملة
# إعلاناتٍ نمطية وتُحلّ فيها الرموز. أُسقطت القاعدة — وسببُ اختفاء الأرقام
# كان غير ما ظننت. الفحص يبقى على ما **قِيس** أنه يتسرّب حقاً.
_OPT_VAR = re.compile(r'\b(?:color|borderColor|textColor|topColor|bottomColor|upColor|'
                      r'downColor|wickUpColor|wickDownColor|lineColor|baseLineColor)\s*:\s*"var\(--')
_ALPHA_CONCAT = re.compile(r'\b\w+\s*\+\s*"[0-9a-fA-F]{2}"')


def check_var_leak() -> None:
    """`var()` لا تُحلّ فيما يُمرَّر إلى مكتبةٍ ترسم على `canvas`: النصّ
    يذهب إلى سياقٍ ليس CSS أصلاً، فتسقط المكتبة إلى لونها الافتراضي.
    وقع ذلك في هذا المشروع في تسعة مواضع (محاور · شبكة · متوسّطات · RSI ·
    MACD) بلا خطأٍ يظهر.

    وثالثةٌ من جنسها: إلحاقُ خانتَي شفافية برمز (`c + "22"`) ينتج نصّاً
    غير صالح يسقطه المتصفّح صامتاً — وعلاجها `color-mix`."""
    for f in (ROOT / "frontend/src").rglob("*.tsx"):
        rel = str(f.relative_to(ROOT))
        lines = f.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines, 1):
            if line.strip().startswith(("//", "*", "/*")):
                continue
            # نافذةٌ من ثلاثة أسطر: خيارات المكتبة تُكتب على أسطرٍ متتالية
            window = "\n".join(lines[max(0, i - 3):i + 2])
            if _OPT_VAR.search(line) and _CANVAS_API.search(window):
                note("S-VARLEAK", f"{rel}:{i}", "رمزٌ يُمرَّر إلى مكتبة رسمٍ على canvas — لا يُحلّ")
                continue
            # سطرٌ يشرح العطب في تعليقٍ ليس عطباً: يُنزع ما بين العلامتين
            # الخلفيتين قبل الفحص، وهو موضع الاقتباس في تعليقات هذا المشروع.
            code = re.sub(r"`[^`]*`", "", line)
            if _ALPHA_CONCAT.search(code) and "var(--" in "".join(lines[max(0, i - 8):i + 1]):
                note("S-VARLEAK", f"{rel}:{i}",
                     "شفافيةٌ تُلحَق برمز — نصٌّ غير صالح (استعمل color-mix)")


# ── S-BOTSCOPE — قناةُ صقر: نطاقٌ صريح وطرفٌ بالقيمة (D011 · D012) ────────
def check_bot_scope() -> None:
    """خاصّيّتان في قناة صقر وقع فيهما عطبٌ فصارتا محروستين.

    الأولى: المفكرة والإفصاحات لهما **نطاقان** (محفظة · سوق) ومصدران
    مختلفان في الخادم. وقراءة مصدرٍ واحدٍ لكليهما تعرض على المالك شركاتٍ
    لا يملكها، وتُفرغ مفكرته متى برد مخزن السوق.

    والثانية: الأطراف (أقوى/أضعف) تُؤخذ بالقيمة لا بالموضع — فترتيبُ
    القائمة افتراضٌ عن مصدرٍ قد يتغيّر، والخطأ فيه لا يُرى إلا بمقارنة.
    """
    f = ROOT / "backend/app/services/saqr_bot.py"
    if not f.exists():
        return
    src = f.read_text(encoding="utf-8")
    if "scope" not in src or "def _events(self, db, announced" not in src:
        note("S-BOTSCOPE", "saqr_bot.py", "المفكرة/الإفصاحات بلا نطاقٍ صريح")
    for needed, why in (("get_events", "مصدر مفكرة المحفظة"),
                        ("market_wide_events", "مصدر مفكرة السوق")):
        if needed not in src:
            note("S-BOTSCOPE", "saqr_bot.py", f"{why} غير مستعمل — نطاقٌ بلا مصدره")
    for i, line in enumerate(src.split("\n"), 1):
        if line.strip().startswith("#"):
            continue
        if re.search(r"(?:secs|sectors)\s*\[\s*(?:0|-1)\s*\]", line):
            note("S-BOTSCOPE", f"backend/app/services/saqr_bot.py:{i}",
                 "طرفٌ يُؤخذ بالموضع — استعمل min/max بالقيمة")


# ── S-DUPTOKEN — رمزٌ بتعريفين، والثاني يبتلع الأوّل صامتاً (D013) ────────
def check_duplicate_tokens() -> None:
    """رمزُ لونٍ (custom property) مُعرَّف أكثر من مرّة لنفس المُحدِّق.

    ولماذا هذا عطبٌ يستحقّ حارساً: كان `--pos-ink` للمظهر الفاتح مُعرَّفاً
    مرّتين في `globals.css`، والثاني يغلب الأوّل بالترتيب. فعُدّل الأوّل،
    وبُني المشروع **بنجاح**، ولم يتغيّر على الشاشة شيء. لا خطأ بناء ولا
    تحذير — تعديلٌ يبدو أنه نُفِّذ. ولولا أن القيمة المحسوبة قُرئت من
    المتصفّح لسُلّمت الحزمة ويُظنّ اللون قد تغيّر.

    والقاعدة الناتجة: للرمز موضعٌ واحد لكل مظهر. فإن لزم استثناءٌ يوماً
    فليُكتب سببه هنا صراحةً — لا أن يُترك تعريفان يتنازعان بالترتيب.
    """
    css = ROOT / "frontend/src/styles/globals.css"
    if not css.exists():
        return
    raw = css.read_text(encoding="utf-8")
    # التعليقات تُمحى **بحفظ الأطوال والأسطر**، لا تُحذف: حذفُها يُزيح كل
    # ما بعدها فتخرج أرقام الأسطر خاطئة — وموضعٌ خاطئ في بلاغٍ صحيح يُضيّع
    # وقت من يتبعه. (وقع هذا في أوّل تشغيل، فصُحّح.)
    text = re.sub(r"/\*.*?\*/",
                  lambda m: re.sub(r"[^\n]", " ", m.group(0)), raw, flags=re.S)

    # مسحٌ بالمحارف لا بالأسطر: العطب الأصليّ كان في كتلةٍ **من سطرٍ واحد**
    # (`html.light { --pos-ink: …; --neg-ink: …; }`)، وقارئُ الأسطر يمرّ
    # عليها بلا أن يراها. جُرّب ذلك فعلاً: النسخة الأولى من هذا الفحص
    # ظنّت الملفّ نظيفاً بعد إعادة العطب حرفياً — فحارسٌ لا يُختبَر بإعادة
    # عطبِه ليس حارساً.
    seen: dict[tuple[str, str], list[int]] = {}
    stack: list[str] = []
    buf = ""
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "{":
            stack.append(buf.strip().replace("\n", " "))
            buf = ""
        elif ch == "}":
            _flush(buf, stack, text, i, seen)
            buf = ""
            if stack:
                stack.pop()
        elif ch == ";":
            _flush(buf, stack, text, i, seen)
            buf = ""
        else:
            buf += ch
        i += 1

    for (sc, tok), lines in sorted(seen.items()):
        if len(lines) > 1:
            note("S-DUPTOKEN", f"frontend/src/styles/globals.css:{lines[0]}",
                 f"«{tok}» مُعرَّف {len(lines)} مرّات لـ«{sc}» "
                 f"(أسطر {', '.join(map(str, lines))}) — الأخير يغلب، وتعديلُ "
                 f"غيره لا يُغيّر شيئاً على الشاشة")


# الرموز المحروسة: كلُّ رمزٍ **قيمتُه لون**. وكان الحارس محصوراً في
# (‏ink · hairline · brand-a/b)، فمرّ من تحته ازدواجٌ حقيقيّ: `--st-open`
# وأخواتها مُعرَّفة في السطر 567 بلوحةٍ فاتحة ثم **مُعادةً** أدنى الملفّ
# باللوحة المعتَّمة القديمة (‏#047857 · #b3261e). والمتأخّر يغلب، فبقي
# التعتيم حيّاً على أوسمة حالة السوق بعد رفعه عن بقيّة التطبيق — والمالك
# هو من رآه، لا الحارس. فوُسّع المعيار من قائمة أسماءٍ إلى **طبيعة
# القيمة**: أيُّ رمزٍ يحمل لوناً يُحرَس، فلا تنجو عائلةٌ لم تخطر ببالنا.
_GUARDED = re.compile(r"^(--[a-zA-Z0-9-]+)\s*:\s*("
                      r"#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\(|color-mix\()")


def _flush(buf, stack, text, pos, seen) -> None:
    """يُسجّل تصريحاً واحداً إن كان رمزاً محروساً داخل كتلةٍ حقيقية."""
    decl = buf.strip()
    m = _GUARDED.match(decl)
    if not m or not stack:
        return
    # المُحدِّق الفعليّ هو أعمق كتلةٍ لا كلّ المكدّس، لكن `@media` يُضمّ
    # إليه: `:root` داخل استعلامٍ ليس هو `:root` خارجه.
    scope = " » ".join(s for s in stack if s)
    seen.setdefault((scope, m.group(1)), []).append(text.count("\n", 0, pos) + 1)


# ── S-AIFACT — ذكاءٌ يُطلب منه اختراع واقعة (D015) ────────────────────────
_FACT_WORDS = re.compile(
    r"متوقّ?ع|محتمل|قادم(?:ة|ين)?|القادمة|توقّ?ع|استشراف|"
    r"مواعيد|تواريخ|جدول(?:ة)?\s+أحداث"
)


def check_ai_fabricates_facts() -> None:
    """مُوجِّهٌ يطلب من النموذج **واقعةً** لا صياغة.

    الحدّ الفاصل الذي وُلد منه هذا الفحص: الذكاء في هذا التطبيق يُستعمل
    فوق بياناتٍ موجودة — يترجم، يعرّب مسمّى، يصوغ سرداً حول أرقامٍ حقيقية.
    أمّا أن يُسأل «اكتب ستّة مواعيد متوقعة» فهو توليدُ الواقعة نفسها: أسماء
    شركاتٍ وتواريخُ أحداثٍ لا مصدر لها، تُعرض في مفكرة المالك ثم تُكتب في
    قاعدة البيانات فتصير غير مميَّزة عن الحقيقيّ.

    والفحص يقرأ نصوص المُوجِّهات في `ai_content.py` وحدها: كلمةٌ تطلب
    استشراف حدثٍ (متوقّع · قادم · مواعيد · تواريخ) داخل موجِّهٍ يطلب JSON
    فيه حقل `date` — تلك هي البصمة. ولا يُوسَم موجِّهٌ يصف أرقاماً معطاةً
    له في النصّ نفسه.
    """
    f = ROOT / "backend/app/services/ai_content.py"
    if not f.exists():
        return
    src = f.read_text(encoding="utf-8")
    for m in re.finditer(r'prompt\s*=\s*f?"""(.*?)"""', src, re.S):
        body = m.group(1)
        line = src.count("\n", 0, m.start()) + 1
        asks_date = '"date"' in body or "YYYY-MM-DD" in body
        if asks_date and _FACT_WORDS.search(body):
            snippet = " ".join(body.split())[:80]
            note("S-AIFACT", f"backend/app/services/ai_content.py:{line}",
                 f"مُوجِّهٌ يطلب من النموذج تواريخ أحداثٍ لا مصدر لها: «{snippet}…»")


# ── S-UNSTABLEKEY — `hash()` يُشتقّ منه مُعرِّفٌ دائم (D017) ────────────────
TRIPLE_D = re.compile(chr(34)*3 + r"(?:.|\n)*?" + chr(34)*3)
TRIPLE_S = re.compile(chr(39)*3 + r"(?:.|\n)*?" + chr(39)*3)


def check_unstable_key() -> None:
    """`hash()` المدمَجة على نصٍّ **مُملَّحةٌ لكل عملية**.

    وهي مصمَّمةٌ لجداول الذاكرة داخل العملية الواحدة، ومُملَّحةٌ عمداً
    (‏PYTHONHASHSEED) ضدّ هجمات التصادم. فاشتقاقُ مُعرِّفٍ **يُحفظ** منها
    — مفتاحُ مخزن، مُعرِّفُ صفٍّ يُرسَل للواجهة — يعمل ما دامت العملية
    حيّة ويسقط عند أوّل إقلاع.

    وثمنُه في هذا المشروع لم يكن نظرياً: مفتاح مخزن المفكرة كان كذلك،
    فتراكم المكرَّر مع كلّ إقلاعٍ حتى امتلأ السقف (500 حدث) **وطرد أحداث
    أرقام الحقيقية** — فبقيت مفكرة الشركة تعرض حدثاً واحداً أربع مرّات
    ولا تعرض جمعيتها العمومية.

    والبديل `hashlib` — ثابتٌ عبر العمليات والأجهزة.
    """
    pat = re.compile(r"\bhash\(")
    for f in (ROOT / "backend/app").rglob("*.py"):
        # تُمحى التعليقات **وسلاسل التوثيق** بحفظ الأسطر: شرحُ عطبٍ يذكر
        # الدالّة ليس استعمالاً لها. وقع هذا فعلاً — وسم الفحصُ توثيقَه هو.
        raw = f.read_text(encoding="utf-8")
        blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))
        src = re.sub(TRIPLE_D, blank, raw)
        src = re.sub(TRIPLE_S, blank, src)
        src = re.sub(r"#[^\n]*", "", src)
        for i, line in enumerate(src.split("\n"), 1):
            if not pat.search(line):
                continue
            # الاستعمال المشروع: داخل `__hash__` أو مقارنةٍ عابرة لا تُحفظ.
            if "def __hash__" in line:
                continue
            note("S-UNSTABLEKEY", f"{f.relative_to(ROOT)}:{i}",
                 f"مُعرِّفٌ من `hash()` المملَّحة — استعمل hashlib: {line.strip()[:80]}")



# ── S-OVERDARK — درجةٌ داكنة بلا داعٍ في المظهر الفاتح (D019) ─────────────
# أدكن ثلاث أرضياتٍ يقع عليها الحبر في المظهر الفاتح.
_LIGHT_GROUNDS = ("#ffffff", "#f7f4ee", "#eef2f7")
# المعيار **متّسعٌ لا سقفُ تباين**. جُرّب السقف أوّلاً (فوق 6.5:1 = معتَّم)
# فأخفق في اختباره: أُعيد العطب الأصليّ (‏#8a5a2b) فمرّ، لأن تباينه 5.22
# على أدكن أرضية — تحت السقف. وحارسٌ لا يُمسك عطبَه ليس حارساً.
# فالمقياس الصحيح: كم بقي من **المتّسع** حتى العتبة؟ يُحسب أقصى لمعانٍ
# يعبر 4.5:1 على أدكن أرضياتنا (‏0.1575)، فإن كان لمعان اللون دونه بهامشٍ
# واسع فثمّة درجةٌ أفتح من عائلته تعبر أيضاً — والتعتيم لم يشترِ قراءة.
#   #8a5a2b → 82٪   #2c5c93 → 65٪   (عطبا D019)
#   #c2410c → 97٪   #2563eb → 97٪   (بعد الإصلاح)
# والفحص أحاديّ الاتجاه: يشكو الأدكنَ ولا يشكو الأفتح أبداً — فالإفراط في
# الإضاءة يمسكه حارسُ التباين، وقرارُ المالك بلونٍ ساطع لا يُنقَض بحارس.
_OVERDARK_FLOOR = 0.90
_ACCENT_INK = re.compile(r"^--(warn|info|pos|neg)-ink$")


def _lum(h: str) -> float:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    v = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    v = [c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4 for c in v]
    return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]


def _contrast(a: str, b: str) -> float:
    x, y = sorted((_lum(a), _lum(b)), reverse=True)
    return (x + .05) / (y + .05)


def check_overdark_ink() -> None:
    """حبرُ دلالةٍ في المظهر الفاتح أدكنُ ممّا تفرضه القراءة.

    وُلد هذا الفحص من عطبٍ رآه المالك ولم تره اللجنة: بعد أن رُفع التعتيم
    عن حبرَي الربح والخسارة، بقي `--warn-ink` بنّياً طينياً (‏#8a5a2b) و
    `--info-ink` أزرقَ رمادياً (‏#2c5c93). وكلاهما «يجتاز» — بل يجتاز
    بفارقٍ واسع (‏5.87 و6.86). وهنا الخلل: الميثاق يفرض عتبةً **دنيا**
    ولا يفرض سقفاً، فما عُتّم بلا داعٍ يمرّ صامتاً ما دام مقروءاً.

    والفحص يقلب السؤال: لا «هل يُقرأ؟» بل «هل كان لا بدّ أن يكون بهذه
    العتمة كي يُقرأ؟». فإن تجاوز التباين السقف على **أدكن** أرضياتنا،
    فثمّة درجةٌ أفتح من العائلة نفسها تعبر أيضاً — والأفتحُ أولى، لأن
    التعتيم لم يشترِ قراءةً بل أخذ لوناً.
    """
    css = ROOT / "frontend/src/styles/globals.css"
    if not css.exists():
        return
    text = re.sub(r"/\*.*?\*/",
                  lambda m: re.sub(r"[^\n]", " ", m.group(0)),
                  css.read_text(encoding="utf-8"), flags=re.S)
    # التصاريح داخل كتلٍ يخصّ المظهر الفاتح وحده (‏:root أو html.light)
    for m in re.finditer(r"(--[a-zA-Z-]+)\s*:\s*(#[0-9a-fA-F]{6})", text):
        tok, val = m.group(1), m.group(2)
        if not _ACCENT_INK.match(tok):
            continue
        head = text[:m.start()]
        # آخر كتلةٍ مفتوحة قبل التصريح: نتجاهل ما يخصّ المظهر الداكن
        opened = head.rfind("{")
        sel = head[head.rfind("}", 0, opened) + 1:opened] if opened > 0 else ""
        if "html.light" not in sel and ":root" not in sel:
            continue
        if "html.dark" in sel or "prefers-color-scheme: dark" in sel:
            continue
        ground = min(_lum(g) for g in _LIGHT_GROUNDS)
        headroom = (ground + .05) / 4.5 - .05     # أقصى لمعانٍ يعبر العتبة
        share = _lum(val) / headroom if headroom > 0 else 1
        if share < _OVERDARK_FLOOR:
            line = text.count("\n", 0, m.start()) + 1
            note("S-OVERDARK", f"frontend/src/styles/globals.css:{line}",
                 f"«{tok}» = {val} يشغل {share * 100:.0f}٪ من المتّسع "
                 f"المتاح حتى عتبة 4.5:1 — معتَّمٌ بلا داعٍ: في عائلته "
                 f"درجةٌ أفتح تعبر العتبة أيضاً")



# ── S-GHOSTFILTER — إعادةُ بناءٍ تُسقط حقلاً شقيقاً (D020) ────────────────
# حقولٌ متلازمة: من حمل الأوّل لزمه الثاني، لأن الثاني **معنى** الأوّل.
# `date` بلا `date_kind` تاريخٌ لا يُعرف أهو موعدٌ قادم أم إعلانٌ وقع.
_SIBLINGS = {"date": "date_kind"}
# ولا يُطبَّق إلا على صفوف **التقويم**، وعلامتُها `company_name`: صفُّ
# النقد يحمل `date` و`symbol` أيضاً، لكنه يسمّي الشركة `company` — وهو
# ختمُ عمليةٍ لا موعدُ حدث، فلا معنى لصنف التاريخ فيه.
_ROW_MARK = "company_name"


def check_ghost_filter() -> None:
    """قاموسٌ يُعيد بناء صفِّ تقويمٍ فيُسقط حقلاً شقيقاً.

    وُلد الفحص من تبويبٍ فارغٍ أبداً: قناة صقر تفرز الإفصاحات عن المفكرة
    بـ`date_kind`. و`company_calendar` يُنتجه، لكن `get_events` بينهما
    يُعيد بناء الصفّ بقائمة حقولٍ **مكتوبةٍ يدوياً** فيُسقطه. فصار الشرط
    يقارن بالعدم: كلُّ صفٍّ في المفكرة، ولا صفَّ في الإفصاحات. ولا استثناء
    ولا تحذير — تبويبٌ فارغ يُقرأ «لا جديد»، والمالك يفترض أنّ ما لم يصله
    لم يقع.

    ومسار بناء هذا الفحص نفسه درسٌ يُكتب لا يُخفى:
      • أوّل صياغة: «الحقل يُقرأ في ملفٍّ لا يُكتب فيه» — أطلقت ثلاثة
        بلاغاتٍ على مستهلكين سليمين. القراءة عبر الملفّات هي الأصل.
      • ثانية: مطابقةٌ نصّية للقواميس — **مرّ العطب من تحتها** عند إعادته
        عمداً، لأن القاموس المعطوب يحوي f-string بأقواسٍ معقوفة فانكسرت
        المطابقة. حارسٌ يُجرَّب على شيفرةٍ نظيفة وحدها يُصادق على نفسه.
      • فالثالثة على شجرة الإعراب (ast): تقرأ القاموس كما يقرؤه المفسّر.
    """
    root = ROOT / "backend/app"
    if not root.exists():
        return
    for f in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except Exception:                                         # noqa: BLE001
            continue
        rel = str(f.relative_to(ROOT))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            keys = {k.value for k in node.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)}
            if _ROW_MARK not in keys:
                continue
            for key, sib in _SIBLINGS.items():
                if key not in keys or sib in keys:
                    continue
                note("S-GHOSTFILTER", f"{rel}:{node.lineno}",
                     f"قاموسٌ يبني صفَّ تقويمٍ بـ«{key}» ويُسقط شقيقه "
                     f"«{sib}» — ومن يفرز به بعدُ يقارن بالعدم، فيخرج "
                     f"تبويبٌ فارغ يُقرأ «لا جديد»")



# ── S-FREETAG — عنوانٌ حرٌّ يُمرَّر وسماً مغلقاً (D021) ────────────────────
# المفاتيح التي تقرؤها الواجهة بجدولٍ مغلق ثم تُسقط المجهول إلى قيمةٍ
# افتراضية. تمريرُ نصٍّ حرٍّ فيها لا يُنتج خطأً — يُنتج وسماً خاطئاً بثقة.
_CLOSED_KEYS = ("type", "kind")
# النصوص الحرّة المعروفة في هذا المشروع: عنوانُ الحدث ورأسُ الخبر.
_FREE_VALUES = ("title", "headline")


def check_free_tag() -> None:
    """‏«type» أو «kind» تأخذ قيمتها من عنوانٍ حرّ.

    وُلد الفحص من وسمٍ كاذب رآه المالك: صفُّ «صرف أرباح» في مفكرة الشركة
    يحمل وسم «إعلان». والسبب `"type": title` في بنّاء صفوف «أرقام» — أي
    العنوان يُمرَّر وسماً. والواجهة تُطابقه بجدولٍ مغلق (DIVIDEND · AGM …)
    فلا يطابق، فتُسقطه إلى OTHER = «إعلان».

    وخُبثُ العطب في معقولية الافتراضيّ: لو كان البديل صارخاً لانكشف في
    أوّل عرض. لكنّ «إعلان» وسمٌ محتملٌ لأي صفّ، فيمرّ سنةً بلا شكوى —
    ويقرأ المالك توزيعاً على أنه إعلان.

    فالقاعدة: ما تقرؤه الواجهة من مجموعةٍ مغلقة يُصنَّف عند المنبع بدالّة
    تصنيف، ولا يُمرَّر إليه نصٌّ حرّ.
    """
    root = ROOT / "backend/app"
    if not root.exists():
        return
    for f in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except Exception:                                         # noqa: BLE001
            continue
        rel = str(f.relative_to(ROOT))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for k, v in zip(node.keys, node.values):
                if not (isinstance(k, ast.Constant) and k.value in _CLOSED_KEYS):
                    continue
                # اسمٌ مجرّد (‏title) أو قراءةٌ منه (‏it.get("title"))
                name = None
                if isinstance(v, ast.Name):
                    name = v.id
                elif (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                      and v.func.attr == "get" and v.args
                      and isinstance(v.args[0], ast.Constant)):
                    name = v.args[0].value
                elif isinstance(v, ast.Subscript) and isinstance(v.slice, ast.Constant):
                    name = v.slice.value
                if name in _FREE_VALUES:
                    note("S-FREETAG", f"{rel}:{node.lineno}",
                         f"«{k.value}» تأخذ قيمتها من «{name}» — نصٌّ حرٌّ في "
                         f"موضع وسمٍ مغلق. الواجهة تُسقط ما لا تعرفه إلى "
                         f"«إعلان»، فيخرج وسمٌ خاطئ بلا شكوى: صنِّفه عند المنبع")



# ── S-FALLBACKCHAIN — سلسلةٌ تقف عند «موجود» لا «صالح» (D022) ─────────────
# سلسلةُ `||` ينتهي طرفُها الأخير بقيمةٍ افتراضية ثابتة، وفي وسطها بحثٌ في
# جدولٍ (`MAP[x]`). القيمةُ الافتراضية تبتلع كلَّ مجهول بلا شكوى، فإن سبق
# المرشّحَ المُترجَمَ مرشّحٌ خامٌّ **موجودٌ دائماً** لم يُبلَغ المترجِم قطّ.
_CHAIN = re.compile(
    r"""(?:const|let|var)\s+\w+\s*=\s*\(?          # إسنادٌ
        (?P<chain>[^;]*?\|\|[^;]*?\[[^\]]+\][^;]*?  # سلسلةٌ فيها بحثُ جدول
        \|\|\s*["'][A-Z_]{3,}["'])""",
    re.X)


def check_fallback_chain() -> None:
    """مرشّحٌ مُترجَم يقع **بعد** مرشّحٍ خامٍّ في سلسلة `||`.

    وُلد الفحص من وسمٍ كاذب على كل صفٍّ في مفكرة الشركة: «موعد أحقية»
    و«صرف أرباح» و«الجمعية العمومية» كلُّها تُعرض «إعلان». والسطر:

        const t = e.type || e.event_type || KIND_TO_TYPE[e.kind] || "OTHER";

    والخادم يرسل `type` بالعربية، فيُلتقط أوّلاً — ويُبحث عنه في جدولٍ
    مفاتيحُه إنجليزية فلا يوجد، فيسقط إلى الافتراضيّ. والمترجِم
    (`KIND_TO_TYPE`) مكتوبٌ في السطر نفسه ولم يُبلَغ قطّ.

    والعلّة أن `||` تسأل «هل هذه القيمة موجودة؟» ولا تسأل «هل هي مفهومة؟».
    والعلاج بنيويّ: مرورٌ على المرشّحين واحداً واحداً، وكلٌّ يُجرَّب في كل
    جدولٍ ممكن — فلا يحجب موجودٌ صالحاً.
    """
    src = ROOT / "frontend/src"
    if not src.exists():
        return
    for f in sorted(list(src.rglob("*.tsx")) + list(src.rglob("*.ts"))):
        text = f.read_text(encoding="utf-8")
        # التعليقات تُمحى بحفظ الأسطر
        clean = re.sub(r"/\*.*?\*/",
                       lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
        clean = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), clean)
        for m in _CHAIN.finditer(clean):
            chain = m.group("chain")
            # موضع البحث في الجدول داخل السلسلة، وما قبله من مرشّحين خامّين
            lookup = chain.index("[")
            before = chain[:lookup]
            if before.count("||") < 1:
                continue        # المترجِم أوّلُ المرشّحين — لا حجب
            line = clean.count("\n", 0, m.start()) + 1
            note("S-FALLBACKCHAIN", f"{str(f.relative_to(ROOT))}:{line}",
                 "سلسلةُ `||` تضع مرشّحاً خامّاً قبل البحث في الجدول وتنتهي "
                 "بقيمةٍ افتراضية تبتلع المجهول — فإن كان الخامُّ موجوداً "
                 "دائماً لم يُبلَغ المترجِم قطّ، ويُعرض الافتراضيّ بثقة. "
                 "مُرّ على المرشّحين واحداً واحداً وجرّب كلاًّ في كل جدول")



# ── S-NAMEDVALUE — رقمٌ يُعرض باسمٍ ليس اسمه (D023) ───────────────────────
# أسماءٌ لها معنىً محدَّد في المالية، ومصادرُ لا يجوز أن تُغذّيها.
# `fair_value` قيمةٌ جوهرية تُحسب من مالية الشركة؛ فإسنادُها إلى متوسطٍ
# متحرّك للسعر أو إلى هدفِ محلّلين تسميةٌ كاذبة لا خطأ حساب.
# المفتاح **جذرُ** الاسم لا الاسم كاملاً: أوّل صياغةٍ طابقت «fair_value»
# حرفياً، فمرّ من تحتها متغيّرٌ اسمه `fair` — وهو الاسم نفسه مختصراً.
_NAMED = {
    "fair": ("sma", "sma200", "sma50", "avg_basis", "mean_basis",
             "target_mean_price"),
}


def check_named_value() -> None:
    """اسمٌ ماليٌّ محجوز يأخذ قيمته من مصدرٍ لا يُنتج ذلك المفهوم.

    وُلد الفحص من رقمٍ رآه المالك خطّاً أحمر: «القيمة العادلة» كانت
    متوسطاً متحرّكاً للسعر في شاشة، وهدفَ محلّلين في أخرى. وكلاهما رقمٌ
    صحيحٌ من مصدرٍ حقيقيّ — والكذب في **التسمية**.

    ولهذا لا يمسكه اختبارُ قيمةٍ ولا مراجعةُ حساب: لا شيء ينهار، ولا رقم
    يخرج شاذّاً. يظهر العطب فقط حين يقارن قارئٌ شاشتين، أو حين يبني على
    الرقم قراراً يظنّه مسنوداً إلى تقييمٍ وهو مسنودٌ إلى متوسط سعر.

    والقاعدة: الاسم المحجوز يُحسب في موضعه المخصّص، ولا يُسنَد إلى مصدرٍ
    يحمل مفهوماً آخر.
    """
    root = ROOT / "backend/app"
    if not root.exists():
        return
    for f in sorted(root.rglob("*.py")):
        if f.name == "fair_value.py":
            continue          # موضع الحساب المخصّص — هو المرجع لا المخالف
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except Exception:                                         # noqa: BLE001
            continue
        rel = str(f.relative_to(ROOT))
        # مفتاحُ قاموسٍ **أو** متغيّرٌ يحمل الاسم المحجوز. أوّل صياغةٍ
        # اكتفت بالقاموس، فأُعيد العطب عمداً في صورة إسنادٍ لمتغيّر
        # (‏fair = f.get("target_mean_price")) فمرّ من تحتها. والاسم يكذب
        # سواءٌ حمله مفتاحٌ أو متغيّر.
        def _flag(name: str, value_node, line: int) -> None:
            key = next((n for n in _NAMED if n in name), None)
            if not key:
                return
            src = ast.dump(value_node)
            bad = [w for w in _NAMED[key] if f"'{w}'" in src]
            if bad:
                note("S-NAMEDVALUE", f"{rel}:{line}",
                     f"«{name}» تأخذ قيمتها من «{bad[0]}» — وهو مفهومٌ آخر "
                     f"(متوسطُ سعرٍ أو هدفُ محلّلين لا قيمةٌ جوهرية). "
                     f"احسبها في fair_value.py أو سمِّ الحقل باسم ما يحمله")

        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        _flag(k.value, v, node.lineno)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        _flag(t.id, node.value, node.lineno)



# ── S-FOOTNOTE — حاشيةٌ أو شرحٌ في واجهة التطبيق ──────────────────────────
# حذّر المالك مرّتين ثم ثالثةً بصيغة «لا تقع فيه نهائياً»: التطبيق أداةٌ
# رسمية لا مدوّنة، فلا يشرح نفسه ولا يبرّر ولا يرشد بجملةٍ تحت البطاقة.
# والصيغ أدناه هي شكلُ الحاشية كما وقعت فعلاً في هذا المشروع.
_FOOTNOTE = re.compile(
    r"(—\s*(?:أضِف|اضغط|جرّب|حدّده|حدّدها|راجع|من\s+زرّ|من\s+تبويب)"
    r"|ملاحظة\s*:|وهذا يعني|أي\s+أن\b|سؤال منفصل"
    r"|يُقصد بذلك|والمقصود|تنبيه\s*:)"
)


def check_footnote() -> None:
    """جملةٌ تشرح أو ترشد أو تبرّر داخل نصٍّ معروض للمالك.

    الحدُّ الفاصل الذي يعمل به هذا الفحص: **الحقيقة تُعرض، والشرح يُحذف.**
    «لا أهداف مضافة» حقيقة. «لا أهداف مضافة — أضِف هدفاً من زرّ + أعلى
    البطاقة» حقيقةٌ ألصق بها إرشاد. والثاني هو ما نهى عنه المالك: الزرّ
    ظاهرٌ أمامه ولا يحتاج من يدلّه عليه، والجملة تُثقل الشاشة وتُشعره أن
    التطبيق يخاطبه كمبتدئ.

    ولا يشمل الفحص التعليقات في الشيفرة — تلك تُكتب للمطوّر لا للمالك،
    والميثاق يطلبها. المقصود ما يظهر على الشاشة وحده.
    """
    src = ROOT / "frontend/src"
    if not src.exists():
        return
    for f in sorted(list(src.rglob("*.tsx")) + list(src.rglob("*.ts"))):
        text = f.read_text(encoding="utf-8")
        # التعليقات تُمحى بحفظ الأسطر: حاشيةٌ في تعليقٍ ليست حاشيةً على الشاشة
        clean = re.sub(r"/\*.*?\*/",
                       lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
        clean = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), clean)
        lines = clean.split("\n")
        for i, line in enumerate(lines, 1):
            # نصٌّ معروض: بين وسمين، أو داخل سلسلةٍ عربية
            if not re.search(r"[\u0600-\u06FF]", line):
                continue
            # `aria-label` و`title` و`alt` ليست حواشيَ على الشاشة: الأولى
            # اسمٌ للقارئ الصوتيّ لا يراه أحد، والثانية تلميحٌ لا يظهر إلا
            # بالتحويم. وحذفُ الإرشاد منهما يُفقر الوصول بلا أن يُنظّف شاشة.
            # النظرُ إلى سطرين قبله أيضاً: السمة قد تُفتح في سطرٍ ويقع نصّها
            # في التالي (‏title={cond\n  ? "…"}) — وقد أفلتت من أوّل صياغةٍ
            # كانت تفحص السطر وحده.
            window = "\n".join(lines[max(0, i - 3):i])
            if re.search(r"(aria-label|title|alt|placeholder)\s*=", window):
                continue
            m = _FOOTNOTE.search(line)
            if m:
                note("S-FOOTNOTE", f"{str(f.relative_to(ROOT))}:{i}",
                     f"نصٌّ يشرح أو يرشد داخل الواجهة («{m.group(0).strip()}») — "
                     f"التطبيق يعرض الحقيقة ولا يشرح نفسه: احذف الجملة "
                     f"وأبقِ المعلومة")



# ── S-NOSTANDARD — محرّك التقييم بلا نموذج الخصم (D024) ───────────────────
def check_no_standard() -> None:
    """محرّك القيمة العادلة يجب أن يحمل نموذج التدفّق المخصوم.

    القيمة الجوهرية لها معيارٌ مهنيّ واحد معترف به: خصمُ التدفّقات الحرّة.
    والمضاعفات مساندة — تقيس ما يدفعه السوق للنظائر، فإن كان القطاع كلُّه
    مبالغاً فيه صادقت على المبالغة. والمالك يتّخذ هذا الرقم أداةَ قرار.

    والحارس يمنع انحساراً صامتاً: حذفُ النموذج لا يُسقط شيئاً ولا يُنتج
    خطأً — تبقى المضاعفات تُخرج رقماً معقولاً، ويختفي المعيار بلا شكوى.
    """
    f = ROOT / "backend/app/services/fair_value.py"
    if not f.exists():
        note("S-NOSTANDARD", "backend/app/services/fair_value.py",
             "محرّك القيمة العادلة غير موجود")
        return
    text = f.read_text(encoding="utf-8")
    # الاسم بقوسه: «def _dcf» وحدها تُطابق «def _dcf_disabled» أيضاً —
    # جُرّب ذلك بإعادة العطب فمرّ، والمطابقة الجزئية عيبٌ متكرّر في
    # الحرّاس. فالقوس يجعلها اسماً كاملاً.
    missing = [n for n in ("def _dcf(", "TERMINAL_GROWTH", "DCF_YEARS")
               if n not in text]
    if missing:
        note("S-NOSTANDARD", "backend/app/services/fair_value.py",
             f"نموذج التدفّق المخصوم ناقص ({'، '.join(missing)}) — القيمة "
             f"العادلة بلا معيارها المهنيّ تصير مضاعفاتٍ تُصادق على السوق")
    # ويجب أن يُستدعى فعلاً لا أن يبقى معرَّفاً
    if "def _dcf" in text and "_dcf(" not in text.split("def _dcf", 1)[1]:
        note("S-NOSTANDARD", "backend/app/services/fair_value.py",
             "النموذج معرَّفٌ ولا يُستدعى — شيفرةٌ ميتة تُقرأ كأنها تعمل")



# ── S-STALEGUARD — فحصُ سلامةٍ يقارن بمقياسٍ لا يقرؤه مصدره (D025) ────────
# أزواجٌ متلازمة: الفحص ومصدرُه يجب أن يقرآ الدالّة نفسها.
_PAIRS = (("backend/app/services/integrity.py",
           "backend/app/api/v1/endpoints/goals.py",
           "sale_harvest", "sale_profit", "نمو العائد"),)


def check_stale_guard() -> None:
    """فحصُ سلامةٍ يتوقّع تعريفاً غيرَ الذي ينتجه المصدر.

    وقع هذا فعلاً: منحنى «نمو العائد» صُحِّح ليقرأ المحصول، ولم يُصحَّح
    معه الفحصُ الذي يقارنه بالربح المحقّق. فصار يفشل دائماً بفارقٍ ثابت
    هو رأس المال المستردّ — بلاغٌ حرِج على بياناتٍ سليمة.

    وأثرُه أسوأ من الصمت: المالك إمّا أن يقلق من سليم، أو يتعوّد تجاهل
    البلاغات. وحارسٌ يُتجاهَل أسوأ من حارسٍ غائب، لأن غيابه معروف
    ووجودَه الكاذب يُطمئن.

    فإن قرأ منتِجُ المقياس `sale_harvest` وجب أن يقارن الفحصُ بالمحصول
    (‏total) لا بالربح المحقّق (‏realized_profit).
    """
    for guard_f, src_f, harvest, profit, label in _PAIRS:
        g, sc = ROOT / guard_f, ROOT / src_f
        if not (g.exists() and sc.exists()):
            continue
        src_text = sc.read_text(encoding="utf-8")
        g_text = g.read_text(encoding="utf-8")
        # التعليقات تُمحى: ذكرُ الدالّة في شرحٍ ليس قراءةً لها
        code = re.sub(r"#[^\n]*", "", src_text)
        # النطاق دالّةُ الفحص وحدها لا الملفّ كلَّه: أوّل صياغةٍ فحصت
        # الملفّ فأطلقت بلاغاً على شيفرةٍ سليمة، لأن `realized_profit`
        # يُقرأ في فحصٍ آخر من الملفّ نفسه بحقّ.
        m = re.search(r"async def _income_timeline_matches.*?(?=\nasync def |\Z)",
                      g_text, re.S)
        gcode = re.sub(r"#[^\n]*", "", m.group(0)) if m else ""
        reads_harvest = f"{harvest}(" in code
        expects_profit = 'p["realized_profit"]' in gcode
        if reads_harvest and expects_profit:
            note("S-STALEGUARD", guard_f,
                 f"«{label}» يقرأ {harvest} (محصولاً) والفحص يقارنه بالربح "
                 f"المحقّق — فارقٌ دائم مقداره رأس المال المستردّ، وبلاغٌ "
                 f"حرِج على بياناتٍ سليمة. قارِنه بـ total")



# ── S-AICONTEXT — سياق الذكاء يحسب مقياساً بدل قراءته (D026) ──────────────
def check_ai_context() -> None:
    """حسابُ مقياسٍ موحَّدٍ داخل سياق المحادثة بدل قراءته من مصدره.

    وقع هذا فعلاً: `_portfolio_context` كان يحسب «العائد٪» محلّياً (ربحٌ
    غير محقّق ÷ المستثمر)، فقال صقر 12.53٪ وقالت الشاشة 10.27٪ — رقمان
    لمفهومٍ واحد يراهما المالك في دقيقةٍ واحدة.

    وأثرُه أبعد من الرقم: نموذجٌ يتلقّى أرقاماً **بلا حكم التطبيق** يستورد
    معياره من تدريبه العامّ. وقد فعل: عدّ السيولة الوفيرة «معطّلة ونقص
    كفاءة»، بينما محرّك التطبيق يعدّها جاهزيةً ويعاقب على غيابها. فالحكم
    لم يكن قاسياً وحسب — كان بمعيارٍ يرفضه التطبيق صراحةً.
    """
    f = ROOT / "backend/app/services/ai_chat.py"
    if not f.exists():
        return
    text = f.read_text(encoding="utf-8")
    m = re.search(r"async def _portfolio_context.*?(?=\nasync def |\ndef |\Z)",
                  text, re.S)
    if not m:
        return
    body = re.sub(r"#[^\n]*", "", m.group(0))
    # حسابُ نسبةِ عائدٍ داخل السياق: قسمةٌ في مئة على مفتاحٍ اسمه عائد
    if re.search(r'"[^"]*عائد[^"]*"\s*:\s*round\(\s*\(?[a-z_]+\s*/', body):
        note("S-AICONTEXT", "backend/app/services/ai_chat.py",
             "سياق المحادثة يحسب «العائد» محلّياً بدل قراءته من المقياس "
             "الموحّد — رقمان لمفهومٍ واحد على شاشتين")
    if "compute_net_profit" not in body:
        note("S-AICONTEXT", "backend/app/services/ai_chat.py",
             "السياق لا يقرأ المقياس الموحّد (compute_net_profit) — "
             "نموذجٌ بلا حكم التطبيق يستورد معياره من تدريبه")



# ── S-THINPEER — مقارنةُ نظائر بلا وسيطٍ ولا حدٍّ أدنى (D028) ─────────────
def check_thin_peer() -> None:
    """مرجعٌ قطاعيّ يُبنى بمتوسطٍ حسابيّ أو بلا حدٍّ أدنى للأقران.

    وقع هذا: «متوسط القطاع» كان يُحسب من شركات المالك نفسه — قرينٌ واحد
    في أكثر القطاعات — ويُقدَّم مرجعاً تُبنى عليه القيمة العادلة.

    وشرطا أيّ مقارنة نظائر تُقدَّم لمستثمر:
      • **الوسيط لا المتوسط**: مضاعفٌ شاذّ واحد يجرّ المتوسط ولا يُزحزح
        الوسيط، والمضاعفات في السوق ملتوية التوزيع بطبعها.
      • **حدٌّ أدنى للعدد**: أقلّ من ثلاثة ليس قطاعاً يُقاس عليه.
    وغيابُهما يُنتج رقماً يبدو مرجعاً وليس مرجعاً — ولا يشكو منه شيء.
    """
    f = ROOT / "backend/app/services/valuation.py"
    if not f.exists():
        return
    text = re.sub(r"#[^\n]*", "", f.read_text(encoding="utf-8"))
    if re.search(r"sector_avg_p[eb]\s*=\s*round\(\s*sum\(", text):
        note("S-THINPEER", "backend/app/services/valuation.py",
             "مرجع القطاع بمتوسطٍ حسابيّ (sum/len) — المضاعفات ملتوية "
             "التوزيع، فالوسيط هو المعيار")
    if "_market_sector_multiples" not in text:
        note("S-THINPEER", "backend/app/services/valuation.py",
             "المرجع لا يُقرأ من مسح السوق — أقران المحفظة ليسوا القطاع")



# ── S-NOAUDIT — تقييمٌ بلا تدقيق الأساسيات مقابل القوائم (D029) ───────────
def check_no_audit() -> None:
    """محرّك التقييم يستهلك الأساسيات الخام بلا تدقيقها مقابل القوائم.

    القوائم بنودٌ مدقَّقة، والملخَّص مشتقٌّ منها بوتيرةٍ مختلفة — فيتأخّر
    بعد ربعٍ جديد، ويبقى على عدد أسهمٍ قديم بعد منحةٍ أو تجزئة. وقِيس
    أثرُ ذلك مرّةً: 22.47 صارت 28.09، فارقُ ٢٥٪ في رقمٍ يُبنى عليه قرار.

    ولا يُمسَك هذا بمراجعة حساب: كلُّ خطوةٍ صحيحة، والمدخل وحده قديم.
    فالحارس يشترط وجود طبقة التدقيق واستدعاءها فعلاً.
    """
    fv = ROOT / "backend/app/services/fair_value.py"
    dq = ROOT / "backend/app/services/data_quality.py"
    if not fv.exists():
        return
    if not dq.exists():
        note("S-NOAUDIT", "backend/app/services/data_quality.py",
             "طبقة تدقيق الأساسيات غير موجودة — التقييم يقرأ الملخَّص "
             "بلا مقارنته بالقوائم")
        return
    text = re.sub(r"#[^\n]*", "", fv.read_text(encoding="utf-8"))
    if "data_quality" not in text or "audit(" not in text:
        note("S-NOAUDIT", "backend/app/services/fair_value.py",
             "التقييم لا يستدعي تدقيق الأساسيات — رقمٌ من ملخَّصٍ قديم "
             "يمرّ بلا شكوى")



# ── S-AUDITSCOPE — تدقيقٌ عند المستهلك لا عند المنبع (D031) ───────────────
def check_audit_scope() -> None:
    """تدقيقُ الأساسيات يجب أن يقع في `analyze_company` قبل بناء السمات.

    وقع العطب مرّتين في هذا المشروع بصورتين: تدقيقٌ داخل محرّك التقييم
    وحده، فتُصحَّح الأساسيات للقيمة العادلة وتبقى الخام لدرجة الحوكمة —
    والدرجة تقرأ العائد على حقوق الملكية في عتباتها مباشرة.

    والقاعدة: ما يُصحَّح يُصحَّح عند **المنبع** مرّةً، لا عند كل مستهلكٍ
    على حدة. وإلا صار التصحيح نفسه مصدرَ تناقض: الشركة الواحدة بأساسيّتين
    مختلفتين على شاشتين.
    """
    f = ROOT / "backend/app/services/analysis.py"
    if not f.exists():
        return
    text = re.sub(r"#[^\n]*", "", f.read_text(encoding="utf-8"))
    m = re.search(r"async def analyze_company.*?(?=\nasync def |\ndef |\Z)", text, re.S)
    if not m:
        return
    body = m.group(0)
    if "data_quality" not in body:
        note("S-AUDITSCOPE", "backend/app/services/analysis.py",
             "التدقيق لا يقع في المنبع — كلُّ مستهلكٍ يقرأ الأساسيات الخام")
        return
    # يجب أن يسبق بناءَ السمات وإلا فالحوكمة تقرأ الخام
    i_audit = body.index("data_quality")
    i_feat = body.find("_financial_from_statements(")
    if i_feat != -1 and i_audit > i_feat:
        note("S-AUDITSCOPE", "backend/app/services/analysis.py",
             "التدقيق يقع **بعد** بناء سمات الحوكمة — فتُصحَّح الأساسيات "
             "للتقييم وتبقى الخام للدرجة، والشركة الواحدة بأساسيّتين")


# ── S-DECLAREDONLY — إطارٌ يُعلَن ولا يُقاس (D032) ─────────────────────────
def check_declared_only() -> None:
    """أركانُ الإطار القطاعيّ يجب أن **تدخل الدرجة**، لا أن تُعلَن وحسب.

    وقع العطب هكذا: أُعلن أن الشركة تُقاس بـ CAMELS وNAREIT، ثم كان كلُّ
    ما يُقاس فعلاً هو المؤشّرات العامّة نفسها لكل القطاعات — والأركانُ
    الخاصّة (الهامش · تكلفة المخاطر · الأموال من العمليات) مكتوبةٌ في خانة
    «يتعذّر» لأنها لم تُطلَب من المصدر، لا لأنها غير موجودة فيه.

    وذلك أسوأ من غياب الإطار: اسمُ معيارٍ معترف به فوق درجةٍ لا تقيسه
    يمنح ثقةً لا يقابلها قياس. فيُفحص هنا أن الأركان المشتقّة تُحسب،
    وأنها تُغذّي قواعد فعلية، وأنها تصل إلى محرّك الدرجات.
    """
    sm = ROOT / "backend/app/services/sector_metrics.py"
    if not sm.exists():
        note("S-DECLAREDONLY", "backend/app/services/sector_metrics.py",
             "لا محرّك لأركان الإطار القطاعيّ — الإطار يُعلَن ولا يُقاس")
        return
    body = sm.read_text(encoding="utf-8")
    for key, label in (("nim", "هامش صافي العمولة"),
                       ("cost_of_risk", "تكلفة المخاطر"),
                       ("cost_income_ratio", "نسبة التكلفة إلى الدخل"),
                       ("ffo", "الأموال من العمليات")):
        if f'"{key}"' not in body:
            note("S-DECLAREDONLY", "backend/app/services/sector_metrics.py",
                 f"ركنُ «{label}» غير مشتقّ رغم توفّر بنوده في القوائم")

    y = (ROOT / "backend/app/data/governance_rules.yaml").read_text(encoding="utf-8")
    # الاسم يُطابَق بحدّه لا بجذره: «‏feature: nim» موجودةٌ داخل
    # «‏feature: nim_x» فيمرّ فحصٌ ساذجٌ على سمةٍ لا وجود لها.
    for key, label in (("nim", "هامش صافي العمولة"),
                       ("cost_of_risk", "تكلفة المخاطر"),
                       ("p_ffo", "السعر إلى الأموال من العمليات"),
                       ("ffo_payout", "نسبة توزيع الأموال من العمليات")):
        if not re.search(rf"feature:\s*{key}\s*,", y):
            note("S-DECLAREDONLY", "backend/app/data/governance_rules.yaml",
                 f"«{label}» يُحسب ولا تقرأه أيُّ قاعدة — مقياسٌ معروض لا محتسَب")

    # الأركانُ تُضاف في **البانية المشتركة** لا في محرّكٍ بعينه (D043):
    # موضعٌ واحد يبني السمات، والمحرّكان يقرآن منه.
    fs = (ROOT / "backend/app/services/four_scores.py").read_text(encoding="utf-8")
    if not re.search(r"def build_company_features\(", fs) or not re.search(r"\bsector_metrics\b", fs):
        note("S-DECLAREDONLY", "backend/app/services/four_scores.py",
             "أركانُ الإطار لا تصل محرّك الدرجات — تُعرض بجانب الدرجة لا فيها")
    for rel in ("backend/app/services/analysis.py",
                "backend/app/services/governance_engine.py"):
        if "build_company_features" not in (ROOT / rel).read_text(encoding="utf-8"):
            note("S-DECLAREDONLY", rel,
                 "هذا المحرّك يبني سماته بنفسه — فيرى غيرَ ما يراه الآخر")

    # وبند المصدر: لا اشتقاق بلا طلبِ بنوده من المزوّد.
    md = (ROOT / "backend/app/services/market_data.py").read_text(encoding="utf-8")
    for f_, label in (("NetInterestIncome", "صافي دخل العمولات"),
                      ("CreditLossesProvision", "مخصّص خسائر الائتمان"),
                      ("DepreciationAndAmortization", "الإهلاك والإطفاء")):
        if not re.search(rf'{f_}"', md):        # الحدُّ لا الجذر — كما أعلاه
            note("S-DECLAREDONLY", "backend/app/services/market_data.py",
                 f"بندُ «{label}» لا يُطلب من المصدر — الركن سيبقى «يتعذّر» بلا سبب")


# ── S-SCOPEGAP — قياسٌ يغطّي غير محلّ السؤال (D033) ───────────────────────
def check_scope_gap() -> None:
    """التغطية تُقاس للسوق كما تُقاس للمحفظة، والقيمة العادلة تُحمل مع الصفّ.

    وقع العطب هكذا: بُني مسارُ قياسٍ للتغطية ليُجيب «أهي أداةُ قرارٍ أم
    ديكور؟»، وكان يمرّ على ما يملكه المالك وحده. فلمّا سُئل عن **السوق
    كلّه** لم يكن في اليد ما يقيسه — والجواب حينئذٍ رأيٌ لا قياس.

    ومعه عطبٌ توأم: القيمة العادلة تُحسب في مسح السوق فعلاً ثم تُهمَل عند
    تركيب صفّ الشركة، فلا تظهر إلا لمن يفتح صفحة كل شركةٍ على حدة —
    حسابٌ يُنفَق ثم يُرمى.
    """
    f = ROOT / "backend/app/api/v1/endpoints/market.py"
    if f.exists():
        t = f.read_text(encoding="utf-8")
        m = re.search(r"async def fair_value_coverage\(.*?\n(?=@router|\Z)", t, re.S)
        if not m:
            note("S-SCOPEGAP", "backend/app/api/v1/endpoints/market.py",
                 "لا مسار لقياس تغطية القيمة العادلة — الجواب رأيٌ لا قياس")
        elif "MARKET_UNIVERSE" not in m.group(0):
            note("S-SCOPEGAP", "backend/app/api/v1/endpoints/market.py",
                 "التغطية تُقاس للمحفظة وحدها — لا يُجاب بها عن سؤال السوق كلّه")

    g = ROOT / "backend/app/services/governance.py"
    if g.exists():
        t = g.read_text(encoding="utf-8")
        m = re.search(r"async def _score_one\(.*?\n(?=\s{4}\S|\Z)", t, re.S)
        # المفتاح لا القيمة: «‏a.get("fair_value")» موجودةٌ في الطرف الأيمن
        # ولو حُذف المفتاح من الصفّ — فيُطابَق المفتاح بنقطتيه.
        if m and '"fair_value":' not in m.group(0):
            note("S-SCOPEGAP", "backend/app/services/governance.py",
                 "صفُّ مسح السوق لا يحمل القيمة العادلة — تُحسب ثمّ تُرمى، "
                 "ولا تظهر إلا لمن يفتح كل شركةٍ على حدة")


# ── S-PEAKVALUE — تقييمُ الدوريّ بسنةٍ واحدة (D035) ────────────────────────
def check_peak_value() -> None:
    """الدوريّ يُقيَّم على أساسٍ مسوّىً، والقيمة تُتبَع بسعر دخول.

    ‏١٥٧ شركة في السوق دوريّة. وبناءُ خصم التدفّقات على آخر سنةٍ يقلب
    الأداة على صاحبها: في القمّة يبدو السهم رخيصاً وهو في ذروته فتدفعه
    الأداة إلى الشراء، وفي القاع يبدو غالياً وهو في أرخص أوقاته فتدفعه
    إلى البيع. وقياسُ ذلك جرى بالأرقام: شركةٌ قفز تدفّقها إلى 900م في
    سنة القمّة قُدّرت بـ166 ريالاً للسهم، وبالتسوية 49.5.

    ومعه شرطُ القرار: قيمةٌ بلا **هامش أمان** لا تقول متى يُدخَل. الشراء
    عند القيمة العادلة دفعٌ لكامل ما تستحقّه الشركة بشرط ألّا يخطئ
    التقدير — وكلُّ تقييمٍ يخطئ.
    """
    f = ROOT / "backend/app/services/fair_value.py"
    if not f.exists():
        return
    t = f.read_text(encoding="utf-8")
    m = re.search(r"def _dcf\(.*?\n(?=def |\Z)", t, re.S)
    if m and "cyclical" not in m.group(0):
        note("S-PEAKVALUE", "backend/app/services/fair_value.py",
             "خصمُ التدفّقات يبني على آخر سنة لكل نمط — الدوريّ يُقيَّم "
             "بأرباح قمّته فيبدو رخيصاً في ذروته")
    # ولا يُخصم تدفّقٌ حرٌّ حيث لا معنى له: نموُّ دفتر القروض يظهر تدفّقاً
    # تشغيليّاً سالباً وهو نموٌّ صحّيّ. ومحرّك الحوكمة يعرف ذلك ويُعطّل
    # قواعد التدفّق للبنوك والتأمين والتمويل — فكان محرّك التقييم يخصم
    # رقماً يعرف المحرّكُ الآخر أنه بلا معنى.
    if "NO_DCF" not in t:
        note("S-PEAKVALUE", "backend/app/services/fair_value.py",
             "الخصمُ يُطبَّق على البنوك والتأمين والريت — تدفّقُها الحرّ "
             "ليس نقداً قابلاً للتوزيع، والمحرّك الآخر يعرف ذلك")
    elif not re.search(r"archetype\s+in\s+NO_DCF\s+else\s+_dcf", t):
        note("S-PEAKVALUE", "backend/app/services/fair_value.py",
             "قائمةُ الأنماط المستثناة معرَّفةٌ ولا تُستعمل عند الاستدعاء")

    # ولا يُجمع نموذجُ خمس مراحل مع نماذج النموّ الدائم بوسيطٍ أعمى:
    # الشركةُ النامية تخرج من الأوّل أعلى ومن الآخرَين أدنى حتماً، فوسيطُ
    # الأربعة لا يمثّل أيّاً منها. والأوزان تُعلَن ولا تُخفى.
    if "WEIGHTS" not in t or '"weighting"' not in t:
        note("S-PEAKVALUE", "backend/app/services/fair_value.py",
             "المسارات تُلخَّص بوسيطٍ أعمى — نموذجُ المراحل ونماذجُ النموّ "
             "الدائم أفقُهما مختلف، وجمعُهما يُنتج رقماً لا يمثّل أيّاً منهما")

    # ولا يدخل رأيٌ في حساب القيمة: هدفُ المحلّل منسوبٌ إلى السعر القائم،
    # فإدخالُه يجعل التقييم يقيس السوقَ بنفسه — وهو محتسَبٌ أصلاً في درجة
    # الحوكمة، فيدخل مرّتين.
    body_fv = re.sub(r"#[^\n]*", "", t)
    if re.search(r'"name":\s*"إجماع أهداف المحللين"', body_fv):
        note("S-PEAKVALUE", "backend/app/services/fair_value.py",
             "أهدافُ المحللين مسارٌ في حساب القيمة — رأيٌ لا حساب، "
             "ومنسوبٌ إلى السعر القائم، ومحتسَبٌ أصلاً في الدرجة")

    for key, why in (('"entry_price"', "سعر الدخول"),
                     ('"margin_of_safety_pct"', "هامش الأمان")):
        if key not in t:
            note("S-PEAKVALUE", "backend/app/services/fair_value.py",
                 f"لا {why} مع القيمة — تقديرٌ بلا قاعدةِ دخول لا يُقرَّر به")
    # والنمط يجب أن يصل فعلاً، وإلا فالتسوية معطَّلة صامتةً
    a = (ROOT / "backend/app/services/analysis.py").read_text(encoding="utf-8")
    if not re.search(r"archetype=_std\.get", a):
        note("S-PEAKVALUE", "backend/app/services/analysis.py",
             "النمط القطاعيّ لا يصل محرّك القيمة العادلة — تسويةُ الدورة "
             "مكتوبةٌ ولا تعمل")


# ── S-FLATPAGE — رقمٌ واثقٌ من نفسه، بلا تبرير (D036) ─────────────────────
def check_flat_page() -> None:
    """صفحة تقييم الأداء تتصدّرها الخلاصة، ولا تُتبَع بنثرٍ يبرّرها.

    وقع العطبُ طرفين متقابلين. أوّلاً: ثماني بطاقاتٍ متساوية الوزن، تقع
    فيها درجةُ الحوكمة والقيمة العادلة — خلاصةُ المحرّك كلّه — في وزن
    شبكةِ أرقامٍ خام. ثمّ عولج بجمع القيود في «تعقيب»، فكان العلاج عطباً
    آخر: **الرقم لا يُبرَّر**. المحرّك يمتنع حين لا يثق، ويُخرج رقماً حين
    يثق — فسطرُ اعتذارٍ تحته يُضعف رقماً هو أصلاً ناتجُ امتناعٍ اجتيزَ.
    ومن أراد المدخلات فمحلُّها القوائم لا حاشيةُ الحكم.
    """
    f = ROOT / "frontend/src/components/analysis/AnalysisPanel.tsx"
    if not f.exists():
        return
    t = f.read_text(encoding="utf-8")
    body = re.sub(r"/\*.*?\*/", "", t, flags=re.S)      # التعليقات ليست عرضاً
    # الثابتُ المحروس هو **وجودُ الخلاصة**: درجةٌ وقيمةٌ عادلة تتصدّران —
    # لا لفظُ التسمية. وكان الفحصُ يشترط لفظ «درجة الحوكمة» حرفياً، فلمّا
    # صحّت التسميةُ إلى «الجودة المالية» (‏D096) فشل الحارسُ على تصحيحٍ لا
    # على عطب. والحارسُ الذي يحرس اللفظَ بدل المعنى يمنع الإصلاح.
    # الاسمُ المعتمَد «السعر العادل» (والقديمُ يُقبل هنا للتاريخ لا للعرض).
    if (("السعر العادل" not in body and "القيمة العادلة" not in body)
            or not re.search(r"درجة (الحوكمة|الجودة المالية)", body)):
        note("S-FLATPAGE", "frontend/src/components/analysis/AnalysisPanel.tsx",
             "الخلاصة (درجةٌ ورقم) لا تتصدّر الصفحة")
    # النثرُ المبرِّر: كلُّ هذه أُزيلت بأمر المالك، وعودةُ أيٍّ منها عودةُ العطب
    for frag, why in (("التعقيب", "بطاقة التعقيب"),
                      ("m.band", "النطاق المرجعيّ تحت كل ركن"),
                      ("m.note", "ملاحظةُ الركن"),
                      ("m.inputs", "مدخلات كل مسار"),
                      ("governance_provenance", "بيان مصدر الدرجة"),
                      ("assumptions", "الافتراضات تحت القيمة"),
                      ("age_days", "عمر الأرقام تحت القيمة")):
        if frag in body:
            note("S-FLATPAGE", "frontend/src/components/analysis/AnalysisPanel.tsx",
                 f"عاد «{why}» — تبريرٌ تحت رقمٍ لا يحتاج تبريراً")


# ── S-TWOFAIR — قيمةٌ عادلة ثانية بمصدرٍ آخر (D037) ───────────────────────
def check_two_fair_values() -> None:
    """«القيمة العادلة» اسمٌ محجوزٌ لمصدرٍ واحد في التطبيق كلّه.

    وقع العطب مرّتين بصورتين. أولاهما رقمان مختلفان باسمٍ واحد على
    شاشتين: متوسّطٌ متحرّك للسعر في صفحة الشركة، وإجماعُ أهداف المحلّلين
    في صفحة الذكاء. وثانيتهما أخفى: عولج المحرّك فأُعيد الحقل إلى اسمه
    (`mean_basis`)، وبقيت الواجهة تقرأ `technical.fair_value` — حقلاً لا
    وجود له. فالبطاقة صامتةٌ لا لأنها صحيحة بل لأن مصدرها اختفى، ولو عاد
    الاسم يوماً لعرضت الرقم الخطأ بلا إنذار.
    """
    for rel in ("frontend/src/pages/CompanyPage.tsx",
                "frontend/src/pages/AIPage.tsx",
                "frontend/src/components/market/StockView.tsx"):
        f = ROOT / rel
        if not f.exists():
            continue
        t = re.sub(r"/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=re.S)
        if re.search(r"technical[\?\.]*\.fair_value", t):
            note("S-TWOFAIR", rel,
                 "«القيمة العادلة» تُقرأ من المؤشّر الفنّي — ذاك متوسّطُ "
                 "السعر لا قيمةً جوهرية، والحقل نفسه لم يعد موجوداً")
        # ══ الاسمُ المعتمَد انقلب بقرار المالك ══ (D147 → اليوم)
        # كان «السعر العادل» اسماً ثانياً متنازعاً فمُنع. ثمّ قرّر المالك
        # أنه **الاسمُ الوحيد** وأن مصدرَه إجماعُ أهداف المحلّلين. فصار
        # الاسمُ القديم «القيمة العادلة» هو الممنوعُ عرضاً — والقاعدةُ
        # نفسُها لم تتغيّر: اسمٌ واحدٌ لمصدرٍ واحد.
        # وتُفحص التسمياتُ المعروضة وحدها: التعليقاتُ تحكي التاريخ ولا
        # تُعرض، ومنعُها فيها يمحو سببَ القرار من الشيفرة.
        _shown = [ln for ln in t.splitlines()
                  if "القيمة العادلة" in ln
                  and not ln.strip().startswith(("//", "*", "/*"))
                  and ("label=" in ln or "card-title" in ln
                       or ">القيمة العادلة<" in ln)]
        if _shown:
            note("S-TWOFAIR", rel,
                 "اسمٌ ثانٍ للقيمة العادلة («السعر العادل») — اسمٌ واحد "
                 "لمصدرٍ واحد، وإلا قرأ المالك رقمين متناقضين")


# ── S-SYMBOL — رمزٌ بلونٍ مختلف في كل صفحة (D038) ─────────────────────────
def check_symbol_consistency() -> None:
    """نجمةُ الذكاء ذهبيّةٌ في كل موضع، وشريطُ الدرجة بلون الهويّة.

    كانت النجمة تُلوَّن بأربعة ألوان حسب الصفحة: بنفسجيُّ العلامة في
    المحادثة، وحبرُها في تقييم الأداء، وبرتقاليُّ التحذير في السوق
    والمكتبة، ولونٌ موروث في مواضع أخرى. والرمزُ الواحد بأربعة ألوان
    يفقد كونه رمزاً: العينُ تتعلّم الشكلَ ولونَه معاً.

    ومعها شريطُ التحليل الفنّي: كان يُملأ بلون **الحكم** (‏--warn-ink
    برتقاليٌّ محروق عند «متوسط») فيخرج عن لغة التطبيق، ويقول شيئاً
    مرّتين — الكلمةُ إلى جانبه تحمل الحكم ولونَه بالفعل. والشريط مقياسٌ
    لا حكم.
    """
    css = ROOT / "frontend/src/styles/globals.css"
    if css.exists():
        c = css.read_text(encoding="utf-8")
        if "--ai-star" not in c:
            note("S-SYMBOL", "frontend/src/styles/globals.css",
                 "لا رمز لِلون نجمة الذكاء — كلُّ صفحةٍ تختار لوناً")
        else:
            # لا بدّ من تعريفٍ للمظهرين، ومن حافّةٍ تحمل التباين: لا ذهبَ
            # حقيقيّ يعبر ٣:١ على أرضياتنا الفاتحة.
            if not re.search(r"html\.light\s*\{[^}]*--ai-star:", c):
                note("S-SYMBOL", "frontend/src/styles/globals.css",
                     "لون النجمة معرَّفٌ لمظهرٍ واحد — يذوب في الآخر")
            if "--ai-star-edge" not in c or "paint-order" not in c:
                note("S-SYMBOL", "frontend/src/styles/globals.css",
                     "الذهب بلا حافّة — يقيس 1.92:1 على البياض فيختفي")

    for f in sorted((ROOT / "frontend/src").rglob("*.tsx")):
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(r"<Sparkles\b[^>]*>", t):
            if "ai-star" not in m.group(0):
                note("S-SYMBOL", str(f.relative_to(ROOT)),
                     "نجمةُ ذكاءٍ بلا اللون الذهبيّ الموحَّد")

    a = ROOT / "frontend/src/components/analysis/AnalysisPanel.tsx"
    if a.exists():
        t = re.sub(r"/\*.*?\*/", "", a.read_text(encoding="utf-8"), flags=re.S)
        if re.search(r"background:\s*verdictColor\(", t):
            note("S-SYMBOL", "frontend/src/components/analysis/AnalysisPanel.tsx",
                 "شريطُ الدرجة يُملأ بلون الحكم — مقياسٌ يلبس لون حكمٍ "
                 "تحمله الكلمةُ إلى جانبه أصلاً")
        # ومقياسا الانحراف من التعريف المشترك لا من نسخةٍ محلّية: نسخةٌ
        # ثانية تتطابق اليوم وتتباعد مع أوّل تعديل — وهي علّةُ هذا
        # التطبيق المتكرّرة، ولها ملفٌّ قائم يقول ذلك في صدره.
        # الاستعمالُ لا الاستيراد: سطرُ الاستيراد يبقى بعد حذف المقياس
        if "<TrendBar" not in t or "<FairValueBar" not in t:
            note("S-SYMBOL", "frontend/src/components/analysis/AnalysisPanel.tsx",
                 "مقياسُ الانحراف غيرُ مأخوذ من تعريفه المشترك — نسخةٌ "
                 "ثانية تتباعد عن أصلها مع أوّل تعديل")
    # ══ ألوانُ المقاييس لا تتفرّق بين مظهرين ══ (بأمر المالك)
    # رضي درجاتِ الداكن وطلب اعتمادها في الفاتح. ورمزٌ يُعاد تعريفه تحت
    # `html.light` يُعيد التفرقة صامتاً — فيُمنع. أمّا `--gauge-edge`
    # فيجب أن يُعاد تعريفه: هو فصلٌ عن الأرضية لا لون، ولا يصحّ أن يبقى
    # واحداً على أرضيتين متضادّتين.
    if css.exists():
        c = css.read_text(encoding="utf-8")
        if "--gauge-pos" not in c:
            note("S-SYMBOL", "frontend/src/styles/globals.css",
                 "لا رموز موحَّدة لألوان المقاييس")
        else:
            for tok in ("--gauge-pos", "--gauge-warn", "--gauge-neg"):
                if re.search(r"html\.light\s*\{[^}]*" + tok + r"\s*:", c):
                    note("S-SYMBOL", "frontend/src/styles/globals.css",
                         "«" + tok + "» أُعيد تعريفه للمظهر الفاتح — عادت "
                         "التفرقة اللونية بين المظهرين")
            if not re.search(r"html\.light\s*\{[^}]*--gauge-edge\s*:", c):
                note("S-SYMBOL", "frontend/src/styles/globals.css",
                     "حافّةُ المقياس واحدةٌ على أرضيتين متضادّتين — "
                     "تذوب في إحداهما")

    v = ROOT / "frontend/src/components/common/ValueBars.tsx"
    if v.exists():
        c = v.read_text(encoding="utf-8")
        # العلامةُ نفسها لا تُكرَّر: كانت منسوخةً حرفياً في شريطين
        if len(re.findall(r'filter:\s*"blur\(2px\)"', c)) > 1:
            note("S-SYMBOL", "frontend/src/components/common/ValueBars.tsx",
                 "علامةُ الشريط مكرّرة — تعريفٌ واحد يخدم المقاييس كلَّها")



# ── S-TIERSTACK — درجاتُ مؤشّرٍ واحد تتراكم (D040) ─────────────────────────
def check_tier_stacking() -> None:
    """فحصٌ **سلوكيّ** لا نصّيّ: يُشغّل المحرّك على حدٍّ فاصل ويقيس خرجه.

    القواعد المتدرّجة يُقصد بها التمييز لا التراكم، لكنّ حدودها تتلامس:
    «ممتاز ‏≥٢٠٪» و«جيّد ‏[١٢،٢٠]» تصدُقان معاً عند ٢٠ بالضبط. وكان
    المقام يعدّ المؤشّر مرّةً عند أعلى درجاته والبسطُ يجمع الدرجتين —
    فيتجاوز البسطُ مقامَه وتُسقَف الدرجة عند مئة.

    ولا يُمسك هذا بمطابقة نصّ: الخلل في الحساب لا في الكتابة، وحدٌّ
    جديد يُضاف غداً يُعيده صامتاً. فيُقاس بتشغيل المحرّك نفسه.
    """
    # يُحمَّل المحرّك في عمليةٍ مستقلّة بمسار الخادم نفسه: تحميله يدوياً
    # من مسار الملفّ يكسر استيراداته النسبية.
    import subprocess, json as _json
    probe = r"""
import sys, json
sys.path.insert(0, "backend")
from app.services import governance_rules as gr
cfg = gr.load_rules()
edges = []
for r in cfg.get("quality", []) + cfg.get("safety", []):
    if r.get("kind") != "bonus":
        continue
    v = r.get("value")
    if r.get("op") == "between" and isinstance(v, list) and len(v) == 2:
        edges.append((r["feature"], float(v[1])))
    elif r.get("op") == "gte" and isinstance(v, (int, float)):
        edges.append((r["feature"], float(v)))
bad = []
for feature, edge in edges:
    res = gr.evaluate({feature: edge})
    for cat, hits in res.hits_by_category.items():
        b = [h.id for h in hits if h.kind == "bonus" and h.feature == feature]
        if len(b) > 1:
            bad.append([feature, edge, b])
print(json.dumps(bad, ensure_ascii=False))
"""
    try:
        r = subprocess.run([sys.executable, "-c", probe], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=60)
        bad = _json.loads((r.stdout or "[]").strip().splitlines()[-1])
    except Exception as e:                                        # noqa: BLE001
        note("S-TIERSTACK", "backend/app/services/governance_rules.py",
             f"تعذّر تشغيل محرّك القواعد للفحص: {str(e)[:60]}")
        return
    for feature, edge, ids in bad:
        note("S-TIERSTACK", "backend/app/services/governance_rules.py",
             f"«{feature}» عند {edge:g} أطلق {len(ids)} مكافآت "
             f"({', '.join(ids)}) — مؤشّرٌ واحد يُدفع له مرّتين، "
             "والبسطُ يتجاوز مقامه")
    return



# ── S-VANISH — شركةٌ تختفي من شاشةٍ وتظهر في أخرى (D041) ──────────────────
def check_vanishing_company() -> None:
    """كلُّ مدرَجٍ يبقى في كل شاشةٍ تستدعيه، ولو تعذّرت درجتُه.

    قال المالك إن كل شركةٍ في تداول **مُلزَمة** بإيداع قوائمها وإلا
    شُطبت — فتعذُّرُ الدرجة ليس صفةً في الشركة بل نقصٌ في مصدرنا أو
    تأخّرٌ في الإفصاح، وهو استثناءٌ شاذّ لا قاعدة.

    وكان مسحُ السوق يُسقط الصفَّ كلَّه حين تتعذّر الدرجة، فتختفي الشركة
    من الخريطة اختفاءً تامّاً بينما صفحتُها تعرض درجة. والاختفاءُ أسوأ
    من «بانتظار القوائم»: الغيابُ لا يُفسَّر ولا يُسأل عنه، والقائمة
    تبدو تامّةً وفيها ثغرة.
    """
    g = ROOT / "backend/app/services/governance.py"
    if g.exists():
        body = re.sub(r"#[^\n]*", "", g.read_text(encoding="utf-8"))
        m = re.search(r"async def _score_one\(.*?\n(?=\s{4}\S|\Z)", body, re.S)
        if m and re.search(r"if score is None:\s*\n\s*return None", m.group(0)):
            note("S-VANISH", "backend/app/services/governance.py",
                 "الشركةُ تُحذف من مسح السوق حين تتعذّر درجتُها — تختفي "
                 "من الخريطة وتظهر في صفحتها، والغيابُ لا يُفسَّر")
        if m and '"insufficient_data"' not in m.group(0):
            note("S-VANISH", "backend/app/services/governance.py",
                 "صفوفُ مسح السوق بلا وسم `insufficient_data` — لا تُفرّق "
                 "الواجهةُ بين درجةٍ غائبة ودرجةٍ منخفضة")

    # التعليقُ يشرح العطب القديم بلفظه، فيُستثنى — العبرةُ بما يُعرض.
    # ولا تُحسب الدرجةُ مرّتين في استجابةٍ واحدة: `analyze_company` يحسبها،
    # فاستدعاءُ `evaluate_company` بعده يُنتج رقماً ثانياً يفترق بأول
    # اختلافٍ في وسائطه (قطاعٌ من مصدرٍ آخر · حالةُ شركةٍ ناقصة).
    m = ROOT / "backend/app/api/v1/endpoints/market.py"
    if m.exists():
        body = re.sub(r"#[^\n]*", "", m.read_text(encoding="utf-8"))
        fn = re.search(r"async def get_company_analysis\(.*?\n(?=@router)", body, re.S)
        if fn and "evaluate_company" in fn.group(0):
            note("S-VANISH", "backend/app/api/v1/endpoints/market.py",
                 "الدرجةُ تُحسب مرّتين في استجابةٍ واحدة — شارةُ الترويسة "
                 "وبطاقةُ التقييم رقمان لشركةٍ واحدة")

    d = ROOT / "backend/app/services/decision_engine.py"
    if d.exists() and "بيانات هذه الشركة غير كافية" in re.sub(
            r"#[^\n]*", "", d.read_text(encoding="utf-8")):
        note("S-VANISH", "backend/app/services/decision_engine.py",
             "الامتناعُ يُنسب إلى الشركة — والقوائم مُلزِمةٌ لكل مدرَج، "
             "فالنقصُ في مصدرنا لا فيها")



# ── S-EVTAG — وسمٌ يطمس نوعه (D042) ───────────────────────────────────────
def check_event_tags() -> None:
    """«موعد الأحقية» نوعٌ قائمٌ بذاته، ووسومُ المفكرة حبرٌ لا حشو.

    كان «أحقية» يُطابَق إلى DIVIDEND فيُكتب على الوسمين «توزيع أرباح»
    معاً. وهما قراران مختلفان: الأحقيةُ تاريخُ الاستحقاق — من ملك السهم
    قبله استحقّ — والصرفُ تاريخُ وصول النقد. فمن يمسح القائمة بصرياً
    يراهما سواءً، ولا يُفرَّق إلا بقراءة السطر الصغير تحتهما.

    ووسمُ الحدث رقعةٌ صلبة — أعادها المالك بعد أن جُعلت حبراً على شفّاف
    ولم يكن ذلك ما طلبه. فالشكلُ الصلب قرارُه، ولا يُغيَّر باجتهاد.
    """
    f = ROOT / "frontend/src/components/market/EventsList.tsx"
    if not f.exists():
        return
    t = re.sub(r"/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=re.S)
    if '"أحقية": "DIVIDEND"' in t or "ELIGIBILITY" not in t:
        note("S-EVTAG", "frontend/src/components/market/EventsList.tsx",
             "«موعد الأحقية» يلبس وسم «توزيع أرباح» — تاريخُ الاستحقاق "
             "وتاريخُ الصرف قراران مختلفان بوسمٍ واحد")
    if not re.search(r"background:\s*meta\.bg", t):
        note("S-EVTAG", "frontend/src/components/market/EventsList.tsx",
             "وسمُ الحدث بلا أرضيةٍ صلبة — والشكلُ الصلب قرارُ المالك")

    css = ROOT / "frontend/src/styles/globals.css"
    if css.exists():
        c = css.read_text(encoding="utf-8")
        if re.search(r"\.ev-tag\s*\{[^}]*background:\s*transparent", c):
            note("S-EVTAG", "frontend/src/styles/globals.css",
                 "‏`.ev-tag` تُفرَّغ أرضيتُها عالمياً — عودةٌ إلى شكلٍ ردَّه المالك")
        if "--tag-eligibility" not in c:
            note("S-EVTAG", "frontend/src/styles/globals.css",
                 "لا لونَ لوسم الأحقية — فيتساوى بصرياً مع وسمٍ آخر")


# ── S-TWOENGINES — محرّكان لسؤالٍ واحد (D043 · D044 · D045) ───────────────
def check_two_engines() -> None:
    """الشركةُ الواحدة تُبنى سماتُها في موضعٍ واحد، ولا تُقرأ من مسارٍ أعور.

    رأى المالك التضادّ بعينه: نافذةُ الحوكمة تقول «شراء · ثقة ٨٤٫٧٪»
    بمؤشّرين أخضرين، وصفحةُ الشركة تقول «انتظار» بثلاثة مؤشّرات حمراء
    ودرجة ٥٧ — في الشركة نفسها واللحظة نفسها. والسببُ محرّكان يبنيان
    السمات كلٌّ على حدة، فأحدهما يُدقّق ويضيف أركان الإطار والآخر لا.

    وحكمان متضادّان أسوأ من حكمٍ خاطئ: الخطأ يُصحَّح، أمّا التضادّ
    فيُبطل الثقة بالأداة كلّها.
    """
    for rel in ("backend/app/services/analysis.py",
                "backend/app/services/governance_engine.py"):
        f = ROOT / rel
        if not f.exists():
            continue
        body = re.sub(r"#[^\n]*", "", f.read_text(encoding="utf-8"))
        if "build_company_features" not in body:
            note("S-TWOENGINES", rel,
                 "محرّكٌ يبني سماته بنفسه — يرى غيرَ ما يراه المحرّك الآخر "
                 "عن الشركة نفسها")
        elif re.search(r"^\s*features\s*=\s*build_features\(", body, re.M):
            note("S-TWOENGINES", rel,
                 "بانيةٌ محلّية إلى جانب المشتركة — أيُّهما يحكم؟")

    # والربعيُّ له مسارُ احتياطٍ كما للسنويّ: بيانٌ يسقط لأننا لم نسأل
    # عنه في موضعه الثاني ليس بياناً غائباً.
    md = ROOT / "backend/app/services/market_data.py"
    if md.exists() and "_quarterly_from_summary" not in md.read_text(encoding="utf-8"):
        note("S-TWOENGINES", "backend/app/services/market_data.py",
             "الربعيُّ على مسارٍ واحد بينما للسنويّ مساران — تسقط أرباعُ "
             "شركاتٍ لها قوائم سنوية")

    # وجدولُ القوائم لا يُقرأ بتمريرٍ أفقيّ على الجوّال: الجدولُ أداةُ
    # مقارنة، فإن لم تظهر أعمدتُه معاً بطل سببُ وجوده.
    ft = ROOT / "frontend/src/components/analysis/FinancialsTable.tsx"
    if ft.exists():
        c = ft.read_text(encoding="utf-8")
        if "md:hidden" not in c or "hidden md:block" not in c:
            note("S-TWOENGINES", "frontend/src/components/analysis/FinancialsTable.tsx",
                 "جدولٌ عرضُه 520px على شاشةٍ 390 بلا شكلٍ بديل — تُقرأ "
                 "فترةٌ واحدة والمقارنةُ خارج الشاشة")
        # التوسيطُ يُكتب على كل عنصرٍ في البطاقة: الوراثةُ لا تكفي، لأن
        # قاعدةً عامّة تُحاذي كلَّ رقمٍ لاتينيّ يميناً وخصوصيّتها أعلى.
        m = re.search(r'md:hidden.*?(?=<div className="overflow-x-auto)', c, re.S)
        if m and m.group(0).count("text-center") < 3:
            note("S-TWOENGINES", "frontend/src/components/analysis/FinancialsTable.tsx",
                 "عنصرٌ في بطاقة الجوّال بلا توسيطٍ صريح — القاعدةُ العامّة "
                 "تختطفه إلى اليمين والرقمُ تحته على المحور")

    css = ROOT / "frontend/src/styles/globals.css"
    if css.exists():
        g = css.read_text(encoding="utf-8")
        if re.search(r'\[dir="ltr"\]\.tabular-nums\s*,', g) and \
           not re.search(r'\[dir="ltr"\]\.tabular-nums:not\(\.text-center\)', g):
            note("S-TWOENGINES", "frontend/src/styles/globals.css",
                 "قاعدةُ محاذاة الأرقام تغلب التوسيطَ الصريح — من كتب "
                 "`text-center` قصده، والقاعدةُ العامّة تنسحب أمامه")


# ── S-FVCEIL — قرارٌ يُعرض بلا مرورٍ على سقف القيمة العادلة (D053) ───────
def check_fair_value_ceiling() -> None:
    """القرارُ يُبنى في `analysis.py` بلا سقفِ القيمة العادلة.

    رأى المالك «التعاونية للتأمين»: قيمةٌ عادلة ١٠٤٫٨٧ وسعرٌ ١٤١٫٤٠،
    والشريطُ «مبالغ فيه»، والحكمُ «فوق القيمة العادلة» — والقرار «شراء».
    لأن ركنَ التسعير في محرّك القرار يقرأ مضاعفات القطاع ولا يقرأ القيمة
    التي يحسبها التطبيق ويعرضها في الصفحة نفسها. أن تحسب قيمةً ثم تتجاهلها
    في قرارك أسوأ من ألّا تحسبها.
    """
    f = ROOT / "backend/app/services/analysis.py"
    if not f.exists():
        return
    src = f.read_text(encoding="utf-8")
    if not re.search(r"apply_fair_value_ceiling\s*\(", src):
        note("S-FVCEIL", "backend/app/services/analysis.py",
             "قرارُ الشركة يُركَّب بلا `apply_fair_value_ceiling` — فقد "
             "يقول «شراء» وسعرُ السهم فوق القيمة العادلة في الشاشة نفسها")
    g = ROOT / "backend/app/services/decision_engine.py"
    if g.exists() and not re.search(r"def apply_fair_value_ceiling\b",
                                    g.read_text(encoding="utf-8")):
        note("S-FVCEIL", "backend/app/services/decision_engine.py",
             "سقفُ القيمة العادلة غائبٌ عن محرّك القرار")


# ── S-FINARCH — نمطٌ ماليٌّ يسقط من فرعه في المجلس (D054) ────────────────
def check_financial_archetypes() -> None:
    """`is_financial` تُقصر على «financial» فيسقط البنكُ والتأمين.

    خريطةُ القطاعات أظهرت **خمساً وعشرين شركة تأمين** بـ«لا ينطبق» بينما
    صفحةُ «التعاونية» تعرض ٨٤ (صورةُ المالك). والسبب أن فرع بافيت المالي
    كان مشروطاً بالنمط «financial» وحده، فيهبط البنكُ والتأمين إلى الفرع
    العامّ الذي يقرأ الهامشَ والتدفّقَ الحرّ — ولا يُقاسان فيهما. فيصمت
    الخبير، فيقلّ عددُ من حكموا عن عتبة البوّابة، فيمتنع المحرّك عن قطاعٍ
    بأكمله. والامتناعُ الجماعيّ ليس تحفّظاً بل عمًى.
    """
    f = ROOT / "backend/app/services/expert_panel.py"
    if not f.exists():
        return
    src = f.read_text(encoding="utf-8")
    m = re.search(r"is_financial\s*=\s*(.+)", src)
    if m and not ("bank" in m.group(1) and "insurance" in m.group(1)):
        note("S-FINARCH", "backend/app/services/expert_panel.py",
             "‏`is_financial` لا تشمل البنك والتأمين — ينزلان إلى فرعٍ "
             "يقرأ مؤشّراتٍ لا تُقاس فيهما فيمتنع المجلس عن قطاعٍ كامل")
    if "_pillar_entries(features, archetype)" not in src:
        note("S-FINARCH", "backend/app/services/expert_panel.py",
             "أركانُ الإطار القطاعيّ تدخل الدرجة ولا تدخل المجلس — "
             "فتبقى الأنماطُ المالية دون عتبة البوّابة")


# ── S-ELIGIBILITY — الأحقيةُ تُطوى في «صرف أرباح» (D055) ────────────────
def check_eligibility_tag() -> None:
    """تاريخُ الاستحقاق يُوسَم وسمَ وصول النقد.

    رأى المالك في مفكرة «أرامكو» صفّاً عنوانه «موعد أحقية» ووسمُه «صرف
    أرباح». وهما قراران مختلفان: من ملك السهم قبل الأحقية استحقّ، والصرفُ
    وصولُ المال بعدُ. ومن قرأ الوسمَ ظنّ المال واصلاً.
    وكان الفصلُ قد أُضيف في الواجهة وحدها، والخادمُ يطوي النوعَ قبل أن
    يصل إليها — فالإصلاحُ في طرفٍ واحدٍ من السلسلة لا يُصلح شيئاً.
    """
    f = ROOT / "backend/app/services/content_engine.py"
    if f.exists():
        s = f.read_text(encoding="utf-8")
        if not re.search(r"def _cal_type\b", s):
            note("S-ELIGIBILITY", "backend/app/services/content_engine.py",
                 "صفوفُ المفكرة تُوسَم بـ`_event_type` مباشرةً — فالأحقيةُ "
                 "تُطوى في «صرف أرباح»")
    g = ROOT / "backend/app/services/argaam_calendar.py"
    if g.exists():
        s = g.read_text(encoding="utf-8")
        if re.search(r'\("أحقية",\s*"توزيع"\)', s):
            note("S-ELIGIBILITY", "backend/app/services/argaam_calendar.py",
                 "تصنيفُ «أرقام» يطوي الأحقيةَ في التوزيع")


# ── S-DIVGRID — قراءةُ جدولٍ بشكلٍ واحدٍ مفترَض (D056) ───────────────────
def check_div_grid() -> None:
    """قارئُ «أرقام» يفترض `<td>` فيرى صفحةً عامرةً فارغة.

    فتح المالك صفحة الشركة في «أرقام» فوجد أربع توصيات محللين، والتطبيقُ
    يقول «لا توجد توصيات متاحة». و«أرقام» تبني بعض جداولها بشبكة
    `<div class="colum">` لا بـ`<table>` — والعيّنةُ المحفوظة أعلى الملفّ
    نفسها كذلك. فمن قرأ بشكلٍ واحدٍ رأى فراغاً وقاله بثقة.
    والفراغُ المُدّعى أخطرُ من الخطأ الظاهر: لا شيءَ في الشاشة يدعو للشكّ.
    """
    f = ROOT / "backend/app/services/argaam_calendar.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if not re.search(r"def _rows_of\b", s):
        note("S-DIVGRID", "backend/app/services/argaam_calendar.py",
             "لا قارئَ موحَّداً للصفوف — الشكلُ المفترَض وحده يُقرأ")
    if not re.search(r'_CP_DATE = re\.compile\(r"\(\\d\{4\}\)\[-/\]', s):
        note("S-DIVGRID", "backend/app/services/argaam_calendar.py",
             "تاريخُ الجدول يُقرأ بشرطةٍ وحدها — و«أرقام» تكتبه بمائلة")


# ── S-BLINDMEDIAN — نمطٌ يسقط إلى الوسيط الأعمى (D057) ──────────────────
def check_blind_median() -> None:
    """الترجيحُ مشروطٌ بنموذجٍ لا تملكه الأنماط المالية.

    أدان محرّكُ القيمة الوسيطَ الأعمى ثم طبّقه على قطاعٍ كامل: الترجيحُ
    كان لا يعمل إلا بوجود النموذج متعدّد المراحل، والبنكُ والتأمين والريت
    لا خصمَ تدفّقٍ لها أصلاً — فتُلخَّص جميعاً بالوسيط. ولهذا خرج
    «الراجحي» بمدى 59.60–127.00 في مسح السوق.
    """
    f = ROOT / "backend/app/services/fair_value.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if not re.search(r"if archetype in NO_DCF:\s*\n(\s*#.*\n)*\s*WEIGHTS", s):
        note("S-BLINDMEDIAN", "backend/app/services/fair_value.py",
             "لا أوزانَ للأنماط التي لا خصمَ تدفّقٍ لها — تسقط إلى الوسيط "
             "الأعمى الذي مُنع منه غيرُها")
    if 'if "متعدّد المراحل" in buckets' in s or '_DDM' in s:
        note("S-BLINDMEDIAN", "backend/app/services/fair_value.py",
             "الترجيحُ مشروطٌ بنموذجٍ واحدٍ بعينه لا بعدسةِ النمط الأولى")


# ── S-UNEXPLAINED — درجةٌ لا يفسّرها مجلسها (D058) ───────────────────────
def check_unexplained_score() -> None:
    """الرقمُ المنخفض تحت مجلسٍ كلُّه أخضر.

    أخرج المسحُ ثلاثَ شركاتٍ درجتُها ٢٧ و٣٥ و٣٩ ولا خبيرَ سلبيّ فيها.
    والدرجةُ لم تكن خاطئة — كانت **غيرَ مفسَّرة**: تنزل بعقوبةٍ تشتعل أو
    بإشاراتٍ إيجابية قليلة، ولا يظهر أيٌّ منهما في المجلس. والرقمُ الذي لا
    يُفسَّر لا يُوثَق به ولو كان صحيحاً.
    وصفوفُ التفسير `role: driver` لا تُحسب في نصاب البوّابة — وإلّا بلغت
    شركةٌ عاريةٌ من الشواهد نصابَها بعقوباتها هي.
    """
    f = ROOT / "backend/app/services/expert_panel.py"
    if f.exists():
        s = f.read_text(encoding="utf-8")
        if 'role="driver"' not in s:
            note("S-UNEXPLAINED", "backend/app/services/expert_panel.py",
                 "المجلسُ لا يحمل ما خفض الدرجة — رقمٌ منخفضٌ بلا سبب ظاهر")
    g = ROOT / "backend/app/services/decision_engine.py"
    if g.exists() and 'role") != "driver"' not in g.read_text(encoding="utf-8"):
        note("S-UNEXPLAINED", "backend/app/services/decision_engine.py",
             "نصابُ البوّابة يعدّ صفوفَ التفسير آراءً — فتُجيز نفسَها")
    for path in ("backend/app/services/analysis.py",
                 "backend/app/services/governance_engine.py"):
        p = ROOT / path
        if p.exists() and re.search(r"build_expert_panel\([^)]*\)", p.read_text(encoding="utf-8")):
            m = re.search(r"build_expert_panel\(([^)]*)\)", p.read_text(encoding="utf-8"))
            if m and m.group(1).count(",") < 2:
                note("S-UNEXPLAINED", path,
                     "المجلسُ يُبنى بلا درجاتٍ — فلا يعرف ما خفضها")


# ── S-FUNDGRADE — صندوقٌ يُقاس بمقاييس شركة (D059) ──────────────────────
def check_fund_archetype() -> None:
    """الصناديقُ المتداولة أوعيةٌ لا شركات.

    أضيفت صناديقُ السوق (‏9400–9409) إلى الدليل بعد أن بحث عنها المالك فلم
    يجدها. ولو دخلت بلا نمطٍ خاصّ لقيست بمقاييس شركةٍ تشغيلية: هامشٌ
    وتدفّقٌ حرّ وقيمةٌ دفترية لا وجودَ لها فيها — فتخرج بأرقامٍ لا معنى
    لها، أو بقيمةٍ عادلة مختلَقة لوعاءٍ سعرُه صافي أصوله.
    """
    y = ROOT / "backend/app/data/governance_rules.yaml"
    if y.exists():
        t = y.read_text(encoding="utf-8")
        if '"صناديق المؤشرات المتداولة": fund' not in t:
            note("S-FUNDGRADE", "backend/app/data/governance_rules.yaml",
                 "قطاعُ الصناديق بلا نمطٍ خاصّ — يُقاس بمقاييس الشركات")
        if not re.search(r"^  fund:", t, re.M):
            note("S-FUNDGRADE", "backend/app/data/governance_rules.yaml",
                 "نمطُ «fund» بلا إطارٍ مُعلَن")
    f = ROOT / "backend/app/services/fair_value.py"
    if f.exists() and 'archetype == "fund"' not in f.read_text(encoding="utf-8"):
        note("S-FUNDGRADE", "backend/app/services/fair_value.py",
             "الصندوقُ يُقدَّر له سعرٌ عادل — وسعرُه صافي أصوله")
    # ── والاسمُ لا يكون رمزاً ──
    # كان كونُ السوق يقرأ الأسماء من شعارات TradingView وحدها، فمن لا شعارَ
    # له يصير اسمُه رقمَه: «9405» اسماً على الشاشة. ورآه المالك «بلا قيمة
    # ولا صورة» — وهو صفٌّ موجودٌ بلا هويّة، أسوأ من الغياب.
    u = ROOT / "backend/app/data/market_universe.py"
    if u.exists() and "saudi_directory import SAUDI_DIRECTORY" not in u.read_text(encoding="utf-8"):
        note("S-FUNDGRADE", "backend/app/data/market_universe.py",
             "كونُ السوق لا يقرأ أسماءه من الدليل — من لا شعارَ له يصير "
             "اسمُه رمزَه")


# ── S-BLAMESYMBOL — الفراغُ يُنسب إلى الورقة لا إلى مصدرنا (D060) ───────
def check_blame_symbol() -> None:
    """‏«لا توجد بيانات لهذا الرمز» — والرمزُ سليم.

    فتح المالك «صندوق البلاد التقني» فقرأ أنه بلا بيانات، وكان مسعَّراً على
    ياهو في اللحظة نفسها (‏25.50 ريالاً في صورته). والسبب أن مسحةَ السوق
    استنفدت حصّةَ ياهو اليومية، فكلُّ رمزٍ غيرِ مخزَّنٍ يعود فارغاً.
    والعبارةُ الأولى تدفعه إلى حذف ورقةٍ سليمة، والثانية تقول «انتظر» —
    وهي الصادقة. وهذا هو مبدأ D041 نفسه في موضعٍ جديد: لا يُنسب نقصُ
    أداتنا إلى ما نقيسه.
    """
    f = ROOT / "backend/app/api/v1/endpoints/market.py"
    if f.exists():
        t = f.read_text(encoding="utf-8")
        if "unavailable_reason" not in t or "usage_tracker import usage" not in t:
            note("S-BLAMESYMBOL", "backend/app/api/v1/endpoints/market.py",
                 "مسارُ الشركة يردّ فراغاً بلا سبب — فتقول الواجهة إن "
                 "الرمزَ بلا بيانات وهو سليم")
    v = ROOT / "frontend/src/components/market/StockView.tsx"
    if v.exists():
        t = v.read_text(encoding="utf-8")
        if "unavailable_reason" not in t:
            note("S-BLAMESYMBOL", "frontend/src/components/market/StockView.tsx",
                 "الواجهةُ تكتب نصّاً ثابتاً بدل سبب الخادم")
    # والمسحُ لا يستنفد حصّةَ المالك فيُعمي تطبيقه بقيّة اليوم
    m = ROOT / "scripts/audit/market_sweep.py"
    if m.exists() and "RESERVE" not in m.read_text(encoding="utf-8"):
        note("S-BLAMESYMBOL", "scripts/audit/market_sweep.py",
             "المسحُ بلا احتياطيٍّ محجوز — يأكل حصّةَ اليوم فيُعمي التطبيق")


# ── S-UNGATED — شرطٌ مكتوبٌ لا يُنفَّذ (D061) ────────────────────────────
def check_ungated_ddm() -> None:
    """خصمُ التوزيعات يعمل على أيّ توزيعٍ رغم شرطه المكتوب.

    قال تعليقُ المسار منذ كُتب: «يصلح للشركة الموزِّعة المستقرّة وحدها»،
    والشيفرةُ تحته تشتغل على أيّ `dps > 0`. فشركةٌ تحتجز تسعةَ أعشار ربحها
    يُقدَّر جوردون قيمتَها بعُشر قيمتها — وليس ذلك تضارباً بل **مساراً لا
    ينطبق**، ثم يُقرأ تضارباً فيُمتنع عن تسعير الشركة كلَّها.
    والقاعدة أعمّ من هذا المسار: شرطٌ يُكتب في تعليقٍ ولا يُنفَّذ في شيفرة
    هو وعدٌ كاذب — وقد وقع مثلُه في مجلس الخبراء (‏D054).
    """
    f = ROOT / "backend/app/services/fair_value.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    # صار المساران واحداً (‏D063)، فالحارسُ يحرس ما حلّ محلّهما: النموُّ
    # الدائم يُشتقّ من الاحتجاز ولا يُفترض صفراً، ولا يعود مسارُ توزيعٍ
    # مستقلٌّ يُقاس اختلافُه عن توأمه تشتّتاً.
    if not re.search(r"g\s*=\s*min\(max\(g,\s*g_sust\)", s):
        note("S-UNGATED", "backend/app/services/fair_value.py",
             "النموُّ الدائم لا يُشتقّ من الاحتجاز — فيُخصم توزيعُ المحتجِز "
             "بنموٍّ صفر، وذلك افتراضٌ يناقض نفسه")
    if '"خصم التوزيعات"' in s:
        note("S-UNGATED", "backend/app/services/fair_value.py",
             "عاد خصمُ التوزيعات مساراً مستقلّاً — وهو النموذجُ نفسه الذي "
             "يُعبّر عنه مضاعفُ الدفترية المبرَّر")


# ── S-CHEAPRISK — عائدٌ مطلوبٌ بلا أرضية · وتدفّقٌ فوق طاقة الأرباح (D062)
def check_cheap_risk() -> None:
    """معدّلُ الخصم ينزل تحت ما تعطيه الصكوك، والتدفّقُ يُخصم بلا سقف.

    أخرج مسحُ السوق «الأندلس» بتشتّتٍ 18.4×: الخصمُ يقول 58.05 والسعرُ
    15.08 ومضاعفُ الدفترية يقول 3.16. ولم يكن ذلك اختلافَ نماذج بل
    **مدخلين فاسدين**:
      ١) العائدُ المطلوب خرج ‎5.4٪ لأن بيتا المقيسة ‎0.16 — وسهمٌ قليل
         التداول تخرج بيتاه صغيرةً من قلّة الحركة لا من قلّة المخاطرة.
         فتُعدَّل بتعديل بلوم وتوضع أرضيةٌ للعائد المطلوب.
      ٢) تدفّقٌ حرّ 141 مليوناً يُخصم إلى الأبد وعائدُ حقوق الملكية ‎1.6٪.
         ولا يجتمعان في شركةٍ سليمة: ذاك نقدٌ عابر — إفراجُ رأسِ مالٍ عامل
         أو بيعُ أصل — لا طاقةَ كسبٍ دائمة. فيُسقَّف الأساسُ بضعفَي متوسّط
         الربح، ومن لا ربحَ له لا يُخصم تدفّقُه.
    """
    f = ROOT / "backend/app/services/fair_value.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    for token, msg in (
        ("MIN_EQUITY_PREMIUM", "العائدُ المطلوب بلا أرضية — بيتا صغيرةٌ "
                               "تُنتج خصماً أرخص من الصكوك"),
        ("BETA_FLOOR", "بيتا تُقرأ خاماً بلا تعديل بلوم"),
    ):
        if token not in s:
            note("S-CHEAPRISK", "backend/app/services/fair_value.py", msg)
    # والسقفُ رقمٌ يُقاس لا كلمةٌ تُذكر: فوق ‎1.5 من متوسّط الربح يعود
    # النموذجُ إلى نفخ ما ليس طاقةَ كسبٍ دائمة.
    # والشاهدُ الأضعف يُستبعد قبل الامتناع: الامتناعُ مع اتّفاق المسارات
    # الجوهرية تنازلٌ عن معرفةٍ نملكها إرضاءً لشاهدٍ نعرف ضعفَه.
    if 'out["excluded"]' not in s:
        note("S-CHEAPRISK", "backend/app/services/fair_value.py",
             "لا يُستبعد مضاعفُ القطاع الشاذّ قبل الامتناع — فتُحجب قيمةٌ "
             "تتّفق عليها المساراتُ الجوهرية")
    # صار القيدُ إعادةَ استثمارٍ لا سقفاً ثابتاً (‏D065): النموُّ يُموَّل
    # من الربح، فلا يبقى حرّاً إلا ما بعد ‎g÷ROIC.
    if not re.search(r"keep\s*=\s*max\(0\.10,\s*1\.0\s*-\s*min\(0\.9,\s*g1\s*/\s*base_return", s):
        note("S-CHEAPRISK", "backend/app/services/fair_value.py",
             "أساسُ الخصم بلا قيد إعادة استثمار — نموٌّ بلا إنفاقٍ رأسماليّ")
    # ويُقاس القيدُ بعائد رأس المال المستثمر لا بحقوق الملكية: قياسُه
    # بالحقوق يجعل القيدَ سخيّاً للشركات المرفوعة — وهي أحوجُها إليه.
    if "roic" not in s:
        note("S-CHEAPRISK", "backend/app/services/fair_value.py",
             "إعادةُ الاستثمار تُقاس بحقوق الملكية لا برأس المال المستثمر")


# ── S-UNFALSIFIABLE — محرّكٌ لا يمكن تكذيبه (D065) ───────────────────────
def check_falsifiable() -> None:
    """لا سجلَّ تشغيلاتٍ — فلا يُثبَت خطأُ ثابتٍ ولا صوابُه.

    أخطرُ ما أخرجته مراجعةٌ خارجية للمحرّك: مدخلاتُه تأتي حيّةً وتُخزَّن
    مؤقّتاً، ولا يُحفَظ أيُّ مخرَج. فلا يستطيع المالك أن يسأل «ماذا قال
    المحرّك عن هذه الشركة قبل سنة وماذا حدث؟» — ويبقى كلُّ جدالٍ عن
    الثوابت رأياً مقابل رأي، ويبقى هو يشتري بأداةٍ لا يقدر أيُّ دليلٍ على
    إصلاحها. والقيدُ يجعل الانحدارَ ممكناً: صعودٌ متوقَّع مقابل عائدٍ
    محقَّق بعد سنة.
    """
    f = ROOT / "backend/app/services/fair_value.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if "_log_run" not in s or "valuation_runs" not in s:
        note("S-UNFALSIFIABLE", "backend/app/services/fair_value.py",
             "لا سجلَّ تشغيلاتٍ يُقيَّد — فالمحرّك غير قابلٍ للتكذيب")
    a = ROOT / "backend/app/services/analysis.py"
    if a.exists() and "symbol=symbol" not in a.read_text(encoding="utf-8"):
        note("S-UNFALSIFIABLE", "backend/app/services/analysis.py",
             "التقييمُ يُستدعى بلا رمزٍ — فالسجلّ يخرج بلا هويّة")


# ── S-EVERLASTING — عائدٌ يدوم أبداً · وقيدٌ رياضيّ غائب (D066) ──────────
def check_everlasting_roe() -> None:
    """‏(ROE−g)÷(r−g) تفترض بقاءَ العائد الحاليّ إلى الأبد.

    وهو أشدُّ افتراضٍ تفاؤلاً في التقييم: العوائدُ ترتدّ إلى الوسط
    والمنافسةُ تأكل الفائض. وقِيس أثرُه: 42.91 بدل 21.74 — انتفاخٌ ‎97٪.
    ومعه قيدٌ رياضيّ غائب: من عائدُه دون المطلوب يُدمّر قيمةً، فلا يخرج
    تقديرُه فوق دفتريته مهما قال مضاعفُ القطاع.
    """
    f = ROOT / "backend/app/services/fair_value.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if "FADE_YEARS" not in s or "pv_ri" not in s:
        note("S-EVERLASTING", "backend/app/services/fair_value.py",
             "العائدُ يُفترض دائماً بلا تلاشٍ — ودخلٌ متبقٍّ غائب")
    if "capped_at_book" not in s:
        note("S-EVERLASTING", "backend/app/services/fair_value.py",
             "لا سقفَ عند الدفترية حين يقلّ العائد عن المطلوب")
    if 'archetype == "insurance"' not in s:
        note("S-EVERLASTING", "backend/app/services/fair_value.py",
             "التأمينُ يُقيَّم بمضاعف دفترية — والنسبةُ المجمّعة جوهرُ "
             "اقتصاده ولا يوفّرها مصدرنا")


# ── S-ABSTAINBUY — الامتناعُ رخصةَ شراء (D067) ──────────────────────────
def check_abstain_is_not_license() -> None:
    """من عجزنا عن تقييمه كان الوحيد الذي يمرّ بلا بوّابة سعر.

    سقفُ القيمة العادلة كان يُعيد القرار كما هو حين تكون القيمة `None` —
    وهي حالُ أربعين شركةً ممتنعةً للتشتّت، وقطاعِ التأمين كلِّه، والصناديق.
    فكلّما ازداد تحفّظُنا اتّسعت الثغرة، وانقلب معنى الامتناع إلى نقيضه.
    ومعه بوّابتان: عقوبةٌ حرجة تمنع الشراء (‏25 نقطةً لا تكفي وحدها
    لإسقاط شركةٍ كاملة الدرجة تحت العتبة)، وتغطيةٌ دون ‎60٪ تمنعه أيضاً —
    فالدرجةُ العالية على شاهدين ليست شهادةَ سلامة.
    """
    f = ROOT / "backend/app/services/decision_engine.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if "بلا_قيمة_عادلة" not in s:
        note("S-ABSTAINBUY", "backend/app/services/decision_engine.py",
             "لا قيمةَ عادلة ⇒ القرارُ يمرّ بلا بوّابة سعر — الامتناعُ صار "
             "رخصةَ شراء")
    if 'severity", None) == "critical"' not in s:
        note("S-ABSTAINBUY", "backend/app/services/decision_engine.py",
             "عقوبةٌ حرجة لا تمنع الشراء")
    if "coverage < 0.60" not in s:
        note("S-ABSTAINBUY", "backend/app/services/decision_engine.py",
             "لا بوّابةَ تغطية على الشراء")
    g = ROOT / "backend/app/services/four_scores.py"
    if g.exists() and "coverage ** 0.5" not in g.read_text(encoding="utf-8"):
        note("S-ABSTAINBUY", "backend/app/services/four_scores.py",
             "الدرجةُ لا تنكمش بجذر التغطية — فالدرجةُ الكاملة على شاهدٍ "
             "واحد تساوي الكاملة على عشرة")


# ── S-GENERICPANEL — مجلسٌ عامٌّ لكل الأنماط (D070) ──────────────────────
def check_generic_panel() -> None:
    """المجلسُ يقيس البنكَ بما يقيس به المصنع.

    طلب المالك «ميزان خبراء لكل شركة باحترافية تامة حسب نوعها وقطاعها».
    وكان المجلسُ عامّاً — بافيت ولينش والمحللون والعائد والتوزيع — صالحاً
    للصناعيّ، ضعيفاً للبنك، غريباً عن الريت. فلكلّ نمطٍ ثلاثةُ أركانٍ
    بعتباتٍ رقمية مُعلَنة، ومن لا تتوفّر بياناتُ ركنه يبقى صامتاً.
    """
    f = ROOT / "backend/app/services/expert_panel.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if "_ARCH_PILLARS" not in s:
        note("S-GENERICPANEL", "backend/app/services/expert_panel.py",
             "لا أركانَ خاصّة بالأنماط — المجلسُ يقيس الجميع بمسطرةٍ واحدة")
        return
    m = re.search(r"_ARCH_PILLARS[^=]*=\s*\{(.*?)\n\}", s, re.S)
    body = m.group(1) if m else ""
    for arch in ("bank", "insurance", "financial", "reit", "cyclical",
                 "inventory_retail", "capital_infra", "asset_light", "general"):
        if f'"{arch}": [' not in body:
            note("S-GENERICPANEL", "backend/app/services/expert_panel.py",
                 f"النمط «{arch}» بلا أركانٍ في المجلس")



# ── S-COVSERIAL — تغطيةٌ تُحسب ولا تُسلسَل (D082) ────────────────────────
def check_coverage_serialized() -> None:
    """بوّابةٌ لا تصل إليها بياناتُها شيفرةٌ ميتة.

    كان `CategoryScore.coverage` محسوباً على الكائن ومحذوفاً من
    `to_dict()`، فيصل إلى بوّابة الشراء `None` دائماً — أي أن شرط
    «لا شراءَ دون تغطية ‎60٪» لم يُقيَّم في أيٍّ من ‎406 شركة.
    """
    f = ROOT / "backend/app/services/four_scores.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    m = re.search(r"def to_dict\(self\)[^\n]*:\n(.*?)\n\n", s, re.S)
    if not m or '"coverage"' not in m.group(1):
        note("S-COVSERIAL", "backend/app/services/four_scores.py",
             "‏`to_dict()` لا يُخرج التغطية — بوّابةُ الشراء لا تراها فلا تُقيَّم")
    a = ROOT / "backend/app/services/analysis.py"
    if a.exists() and "coverage=_cov" not in a.read_text(encoding="utf-8"):
        note("S-COVSERIAL", "backend/app/services/analysis.py",
             "التغطيةُ لا تُمرَّر إلى بوّابة السعر")


# ── S-SANEBAND — حدُّ العقل عند المسار لا عند المزيج (D083) ───────────────
def check_sane_band() -> None:
    """مسارٌ عند ‎0.42 وآخرُ عند ‎0.38: يمرّ الأوّل ويسقط الثاني، فتخرج
    النقطةُ عند حافّة اللامعقول ولم يُفحص المزيجُ قطّ."""
    f = ROOT / "backend/app/services/fair_value.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    m = re.search(r"SANE_LOW,\s*SANE_HIGH\s*=\s*([\d.]+),\s*([\d.]+)", s)
    if not m:
        note("S-SANEBAND", "backend/app/services/fair_value.py",
             "حدُّ العقل غائب")
        return
    lo, hi = float(m.group(1)), float(m.group(2))
    if lo < 0.40 - 1e-9 or hi > 2.50 + 1e-9:
        note("S-SANEBAND", "backend/app/services/fair_value.py",
             f"حدُّ العقل ({lo}–{hi}) أوسعُ من ‎0.40–2.50 الذي نصّت عليه المواصفة")
    # الثابتُ المحروس: أن تُفحص **النقطةُ المرجَّحة** بالنسبة إلى السعر،
    # وأن يُوسَم الشذوذُ لا يُمحى الرقم. وكان الفحصُ يمسك عبارةً بعينها
    # فأخفق على تصحيحٍ غيّرها — وهي العلّةُ الرابعة من نوعها.
    if not re.search(r"_r\s*=\s*out\[.value.\]\s*/\s*price", s):
        note("S-SANEBAND", "backend/app/services/fair_value.py",
             "لا فحصَ لحدّ العقل بعد الترجيح — يُفحص المسارُ ولا يُفحص المزيج")
    if 'out["implausible"] = True' not in s:
        note("S-SANEBAND", "backend/app/services/fair_value.py",
             "الشذوذُ يُمحى بدل أن يُوسَم — والرقمُ محسوبٌ فيُدّعى أنه معدوم")
    # ولا يعود السعرُ يقرّر أيُّ المسارات ينجو
    m = re.search(r"def _sane\(.*?\n(?=\n\n)", s, re.S)
    if m and re.search(r"price \* SANE_LOW", m.group(0)):
        note("S-SANEBAND", "backend/app/services/fair_value.py",
             "السعرُ يُصفّي المساراتِ — فالقيمةُ الجوهرية تصير دالّةً فيه، "
             "ويُحذف عند الغلاء المسارُ القائل إن السهم أرخص")


# ── S-SINGLEPATH — مسارٌ واحد يُبنى عليه شراء (D084) ─────────────────────
def check_single_path_gate() -> None:
    """‏١١٦ شركة قرارُها من مسارٍ يتيم لا شاهدَ يكذّبه، ووسيطُ نسبتها
    ‎0.613 مقابل ‎0.960 لمسارين."""
    f = ROOT / "backend/app/services/fair_value.py"
    d = ROOT / "backend/app/services/decision_engine.py"
    if f.exists() and 'out["single_path"]' not in f.read_text(encoding="utf-8"):
        note("S-SINGLEPATH", "backend/app/services/fair_value.py",
             "لا يُعلَن أن التقدير من مسارٍ واحد")
    if d.exists():
        s = d.read_text(encoding="utf-8")
        if "single_path" not in s or "مسار_واحد" not in s:
            note("S-SINGLEPATH", "backend/app/services/decision_engine.py",
                 "المسارُ اليتيم يُبنى عليه قرارُ شراء")


# ── S-NOFVABSTAIN — العجزُ عن التقييم يُعرض بلون الرسوب (D085) ───────────
def check_no_fv_abstains() -> None:
    """«تجنّب» حكمٌ يقول إن الشركة رديئة. ولا يجوز أن يصدر عن عجزنا عن
    تقييمها: ‎87٪ من أحكام التجنّب في مسح السوق كانت جهلاً لا رسوباً."""
    d = ROOT / "backend/app/services/decision_engine.py"
    if d.exists():
        s = d.read_text(encoding="utf-8")
        if not re.search(r"if \(not fair_value or fair_value <= 0\)[^\n]*hard_filter", s):
            note("S-NOFVABSTAIN", "backend/app/services/decision_engine.py",
                 "غيابُ القيمة العادلة لا يُنتج امتناعاً — الحكمُ يمرّ كما هو")
        if not re.search(r"decision=ABSTAIN,\s*\n\s*matched_rule_id=f\"\{decision\.matched_rule_id\}\+بلا_قيمة_عادلة", s):
            note("S-NOFVABSTAIN", "backend/app/services/decision_engine.py",
                 "لا امتناعَ صريح عند غياب القيمة العادلة")
    y = ROOT / "backend/app/data/governance_rules.yaml"
    if y.exists():
        t = y.read_text(encoding="utf-8")
        # ══ العتبةُ تُقاس بمقياس الدرجة لا برقمٍ موروث ══
        # كان الشرطُ «عتبةُ التجنّب ≥ 52» صحيحاً حين كانت الدرجةُ **مطلقة**
        # (‎52 تعني دون المستوى). ثم صارت الدرجةُ **رتبةً مئوية في القطاع**
        # وسيطُها ‎50 بالبناء، فصار الشرطُ نفسُه يوجب إدانةَ نصف السوق —
        # وقِيس: ‎52٪ «تجنّب». والحارسُ الذي يحمل افتراضاً تجاوزه المقياسُ
        # يفرض العطبَ بدل أن يمنعه.
        # والمحروسُ الآن: ألّا تبلغ العتبةُ الوسيطَ. فـ«تجنّب» حكمٌ على
        # خللٍ لا على مرتبةٍ في ترتيب، وفي كلّ قطاعٍ رُبعٌ أدنى بالضرورة.
        m = re.search(r"id: avoid_weak_quality\n(?:\s*#[^\n]*\n)*\s*conditions:\n\s*-\s*\{[^}]*value:\s*(\d+)", t)
        if m and int(m.group(1)) >= 40:
            note("S-NOFVABSTAIN", "backend/app/data/governance_rules.yaml",
                 f"عتبةُ التجنّب ({m.group(1)}) تقارب وسيطَ التوزيع المئينيّ — "
                 f"فيُدان نصفُ السوق على مرتبةٍ لا على خلل")


# ── S-NOMU — السوق الموازية بمسطرة الرئيسة (D086) ────────────────────────
def check_nomu_discount() -> None:
    """قيمةٌ لا تُسيَّل ليست قيمةً كاملة: ‎136 صفّاً من «نمو» كان وسيطُها
    ‎0.879 مقابل ‎0.738 للسوق الرئيسة."""
    f = ROOT / "backend/app/services/fair_value.py"
    if f.exists():
        s = f.read_text(encoding="utf-8")
        if 'startswith("9")' not in s or "liquidity_discount_pct" not in s:
            note("S-NOMU", "backend/app/services/fair_value.py",
                 "لا خصمَ سيولةٍ لرموز «نمو» (9xxx)")
    d = ROOT / "backend/app/services/decision_engine.py"
    if d.exists() and "سوق_موازية" not in d.read_text(encoding="utf-8"):
        note("S-NOMU", "backend/app/services/decision_engine.py",
             "قرارُ «نمو» غيرُ مسقَّف — والخصمُ يعالج السعرَ لا تعذّرَ الخروج")


# ── S-ARCHLENS — عدسةُ النمط في التقييم (D087) ───────────────────────────
def check_archetype_lens() -> None:
    """أفقُ تلاشي البنك عشرٌ لا خمسَ عشرة (قِيس ‎1.489 منتفخاً)، والريتُ
    عدستُه الأولى رسملةُ التوزيع لا مضاعفُ الدفترية."""
    f = ROOT / "backend/app/services/fair_value.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if not re.search(r'FADE_YEARS\s*=\s*10 if archetype in \("bank", "financial"\)', s):
        note("S-ARCHLENS", "backend/app/services/fair_value.py",
             "أفقُ تلاشي البنك كأفق الشركة الصناعية — فائضُه يُخصم خمسَ عشرةَ سنة")
    if "عائدٌ توزيعيّ مرسمَل" not in s:
        note("S-ARCHLENS", "backend/app/services/fair_value.py",
             "الريتُ بلا مسار رسملةٍ للتوزيع — يُقاس بعدستين لا تخصّانه")
    m = re.search(r'archetype in NO_DCF:.*?WEIGHTS = \{_PB: ([\d.]+)', s, re.S)
    if m and float(m.group(1)) > 0.50 + 1e-9:
        note("S-ARCHLENS", "backend/app/services/fair_value.py",
             f"وزنُ الدخل المتبقّي للمالية ({m.group(1)}) فوق النصف — مضاعفةٌ لانحيازٍ مقيس")


# ── S-ARCHFALLBACK — نمطٌ يسقط صامتاً (D088) ─────────────────────────────
def check_archetype_fallback() -> None:
    """ثلاثةُ رموز خرجت درجتُها من مسطرةٍ لا تخصّها، لأن السقوطَ الأخير
    إلى `asset_light` لم يكن يميّز «حُلَّ إليه» من «سقط إليه»."""
    f = ROOT / "backend/app/services/spec_score.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if "resolve_archetype_ex" not in s:
        note("S-ARCHFALLBACK", "backend/app/services/spec_score.py",
             "حلُّ النمط لا يُعيد حالةَ الحلّ — السقوطُ الافتراضيّ صامت")
        return
    if not re.search(r"if not resolved:\s*\n\s*return SpecScore", s):
        note("S-ARCHFALLBACK", "backend/app/services/spec_score.py",
             "نمطٌ غيرُ محلول تخرج له درجةٌ كأنها معلومة")



# ── S-PHASESHAPE — الطورُ يُحمل باللون وحده (D089) ───────────────────────
def check_phase_shape() -> None:
    """اللونُ أضعفُ حاملٍ للمعنى، وحالُ السوق لا تخصّ شركةً بعينها.

    كانت الأيقونةُ شكلاً واحداً في الأطوار الثلاثة المفتوحة، واللونُ وحده
    يفرّقها — فمن لا يميّز البرتقاليَّ من الأزرق يراها طوراً واحداً. وكانت
    تتكرّر بجانب كلّ اسم شركةٍ في المحفظة وصفحة الشركة، وهي حالُ السوق
    كلِّه لا حالُ تلك الشركة.
    """
    f = ROOT / "frontend/src/components/common/BroadcastIcon.tsx"
    if not f.exists():
        note("S-PHASESHAPE", "frontend/src/components/common/BroadcastIcon.tsx",
             "أيقونةُ حال السوق مفقودة")
        return
    s = f.read_text(encoding="utf-8")
    for ph in ('"pre"', '"preclose"', '"closed"'):
        if f"ph === {ph}" not in s:
            note("S-PHASESHAPE", "frontend/src/components/common/BroadcastIcon.tsx",
                 f"الطور {ph} بلا شكلٍ خاصّ — اللونُ وحده يحمله")
    if "bcast-blink" not in s:
        note("S-PHASESHAPE", "frontend/src/components/common/BroadcastIcon.tsx",
             "لا وميضَ لطور ما قبل الافتتاح")
    if "mask" not in s:
        note("S-PHASESHAPE", "frontend/src/components/common/BroadcastIcon.tsx",
             "لا هلالَ لطور ما قبل الإغلاق")
    c = ROOT / "frontend/src/styles/globals.css"
    if c.exists() and "bcast-blink" not in c.read_text(encoding="utf-8"):
        note("S-PHASESHAPE", "frontend/src/styles/globals.css",
             "حركةُ الوميض غيرُ معرَّفة — الطبقةُ بلا أثر")
    # ولا تعود العلامةُ بجانب الشركات
    for page in ("frontend/src/pages/PortfolioPage.tsx",
                 "frontend/src/pages/CompanyPage.tsx",
                 "frontend/src/components/market/StockView.tsx"):
        g = ROOT / page
        if g.exists() and "MarketStatusDot" in g.read_text(encoding="utf-8"):
            note("S-PHASESHAPE", page,
                 "علامةُ حال السوق عادت بجانب الشركات — وهي حالُ السوق لا حالُها")


# ── S-LIQBARS — بطاقةُ السيولة برأسٍ بلا جسم (D090) ──────────────────────
def check_liquidity_bars() -> None:
    """الاحتياطُ كان (إغلاق تاسي × حجمه) وياهو لا يُعيد حجماً للمؤشّر،
    فيُصفّى كلُّ عمودٍ ولا يبلغ الرسمُ نصابَه أبداً."""
    f = ROOT / "frontend/src/components/market/MarketWidgets.tsx"
    if f.exists():
        s = f.read_text(encoding="utf-8")
        m = re.search(r"export function LiquidityCard.*?\n}", s, re.S)
        body = m.group(0) if m else s
        if "p.close * p.volume" in body:
            note("S-LIQBARS", "frontend/src/components/market/MarketWidgets.tsx",
                 "احتياطٌ ميّت: أعمدةٌ من حجم المؤشّر، وياهو لا يُعيده — "
                 "فتظهر البطاقةُ بلا أعمدة")
        if "liquidity_series" not in body:
            note("S-LIQBARS", "frontend/src/components/market/MarketWidgets.tsx",
                 "الأعمدةُ لا تُقرأ من سلسلة السيولة")
    g = ROOT / "backend/app/services/market_movers.py"
    if g.exists():
        t = g.read_text(encoding="utf-8")
        if 'src": "sample"' not in t:
            note("S-LIQBARS", "backend/app/services/market_movers.py",
                 "لا ملءَ رجعيّ للسلسلة — البطاقةُ بلا أعمدة حتى يمرّ يومان")
        if 'if snapshot["market_liquidity"] > 0:' not in t:
            note("S-LIQBARS", "backend/app/services/market_movers.py",
                 "نقطةٌ صفرية تُقيَّد — يومُ العطلة يُقرأ سيولةً منخفضة "
                 "ويكسر مقياس البطاقة")



# ── S-SHADOWENGINE — محرّكٌ يُحسب ولا يحكم (D091) ─────────────────────────
def check_shadow_engine() -> None:
    """حقلٌ يُحسب ولا يُستعمل أخطرُ من حقلٍ لا يُحسب: الأوّل يُظنّ عاملاً.

    ══ نُسخ شرطُه بقرار المالك ══ (D149)
    كان يشترط أن تحلّ درجةُ المواصفة محلَّ ركن الجودة في الدرجة المعروضة.
    ثم قرّر المالكُ أن **منطق بطاقة السلامة** (‏`governance_engine`) هو
    منطقُ الحوكمة في التطبيق كلِّه، والبطاقةُ لا تستبدل ركنَ الجودة. فصار
    الاستبدالُ نفسُه هو المخالفة، لا غيابُه.

    فبقي من هذا الفحص ما لم يُنسخ: أن يُقال أيُّ محرّكٍ أنتج الدرجة، وألّا
    يعود الاستبدالُ خِلسة. وتطابقُ الرقمين بين البطاقة والشاشة يفحصه
    `gov_one_engine.py` سلوكياً — لا بقراءة الشيفرة.
    """
    f = ROOT / "backend/app/services/analysis.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if "spec_score" not in s:
        note("S-SHADOWENGINE", "backend/app/services/analysis.py",
             "محرّكُ المواصفة لا يُستدعى أصلاً")
        return
    if re.search(r"four\.quality\s*=\s*CategoryScore\(\s*\n?\s*score=spec\.score", s):
        note("S-SHADOWENGINE", "backend/app/services/analysis.py",
             "ركنُ الجودة يُستبدَل بدرجة المواصفة — والبطاقةُ لا تفعل، "
             "فتخرج الشركةُ الواحدة بدرجتين (D149)")
    if '"score_engine"' not in s:
        note("S-SHADOWENGINE", "backend/app/services/analysis.py",
             "لا يُقال أيُّ محرّكٍ أنتج الدرجة")




# ── S-ONEARCH — محلِّلا نمطٍ لا يتّفقان (D092) ────────────────────────────
def check_one_archetype_resolver() -> None:
    """أركانُ البطاقة تُحسب لنمطٍ وتُقرأ لنمطٍ آخر.

    ‏`sector_metrics` كانت تُغذّى بالنمط من خريطة الـYAML، والبطاقةُ تُقرأ
    بالنمط من خريطة المواصفة — واختلفتا في ‎51 قطاعاً من ‎63. فمقاييسُ
    البنك لا تُحسب لبنكٍ قطاعُه إنجليزيّ، ثم تُعدّ أركانُه «غائبة».
    """
    f = ROOT / "backend/app/services/four_scores.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if re.search(r"sector_metrics\.compute\(\s*archetype_for\(", s):
        note("S-ONEARCH", "backend/app/services/four_scores.py",
             "مقاييسُ القطاع تُحسب بمحلِّلٍ غير محلِّل البطاقة — الأركانُ "
             "تُحسب لنمطٍ وتُقرأ لآخر")
    if "resolve_archetype_ex" not in s:
        note("S-ONEARCH", "backend/app/services/four_scores.py",
             "محلِّلُ المواصفة لا يُستعمل في تغذية مقاييس القطاع")


# ── S-BLENDCOV — الدرجةُ تُضرب في التغطية (D093) ─────────────────────────
def check_score_not_blended() -> None:
    """رقمٌ واحد لا يحمل جوابين.

    كانت الدرجةُ تنكمش نحو الخمسين بجذر التغطية، فيخلط الرقمُ «الشركةُ
    متوسّطة» بـ«لم نستطع قياسها» — وهما نقيضان في القرار. وقياسُه على
    السوق: صفرُ شركةٍ فوق ‎75 من ‎386، ونصفُها تحت ‎42. فصارا رقمين
    يُعرضان ولا يُدمجان، وللتغطية حدٌّ أدنى دونه امتناعٌ صريح.
    """
    f = ROOT / "backend/app/services/spec_score.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if re.search(r"\(\s*(eff_cov|coverage)\s*\*\*\s*0\.5\s*\)", s):
        note("S-BLENDCOV", "backend/app/services/spec_score.py",
             "الدرجةُ تُضرب في التغطية — رقمٌ واحد يخلط «متوسّطة» بـ«لم تُقَس»")
    if "MIN_PILLARS" not in s or "MIN_COVERAGE" not in s:
        note("S-BLENDCOV", "backend/app/services/spec_score.py",
             "لا حدَّ أدنى للتغطية — تخرج درجةٌ من ركنٍ واحد")
    if not re.search(r"if len\(reads\) < MIN_PILLARS or coverage < MIN_COVERAGE", s):
        note("S-BLENDCOV", "backend/app/services/spec_score.py",
             "الحدُّ الأدنى معرَّفٌ ولا يُفحص")


# ── S-RANKBASIS — عتبةٌ مخترَعة بدل رتبةٍ في القطاع (D094) ────────────────
def check_rank_basis() -> None:
    """العتبةُ لا تُعرف بالرأي — والرتبةُ في القطاع تُعرف من بياناتٍ عامّة."""
    f = ROOT / "backend/app/services/spec_score.py"
    if f.exists():
        s = f.read_text(encoding="utf-8")
        if not re.search(r"_pd\.cuts_for\(|peer_distribution as _pd", s) or \
                "_pd.percentile_of(" not in s:
            note("S-RANKBASIS", "backend/app/services/spec_score.py",
                 "التقييمُ بعتباتٍ مخترَعة لا برتبةٍ بين الأقران")
        if 'basis' not in s:
            note("S-RANKBASIS", "backend/app/services/spec_score.py",
                 "لا يُقال أيُّ أساسٍ حكم — رتبةٌ أم عتبة")
    for path in ("backend/app/services/peer_distribution.py",
                 "backend/app/services/red_lines.py",
                 "backend/app/services/governance_pillar.py"):
        if not (ROOT / path).exists():
            note("S-RANKBASIS", path, "مفقود — ركنٌ من أركان القرار غائب")
    g = ROOT / "backend/app/services/peer_distribution.py"
    if g.exists() and "MIN_COHORT" not in g.read_text(encoding="utf-8"):
        note("S-RANKBASIS", "backend/app/services/peer_distribution.py",
             "لا حدَّ أدنى لعيّنة النمط — رتبةٌ من أربع شركاتٍ ضجيج")


# ── S-SHADOWENGINE — محرّكٌ يُحسب ولا يحكم (D091) ─────────────────────────
def check_shadow_engine() -> None:
    """حقلٌ يُحسب ولا يُستعمل أخطرُ من حقلٍ لا يُحسب: الأوّل يُظنّ عاملاً.

    بقيت درجةُ المواصفة تُحسب في حقلٍ جانبيّ ولا تحكم يومين كاملين، فكلُّ
    ضبطٍ لها جرى في محرّكٍ لا تراه الشاشة — والمالكُ يرى الرقمَ نفسه بعد
    كلّ جولة. فيُشترط أن تدخل نتيجةُ المواصفة في الدرجة التي تُعرض وتُقرّر.
    """
    f = ROOT / "backend/app/services/analysis.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if "spec_score" not in s:
        note("S-SHADOWENGINE", "backend/app/services/analysis.py",
             "محرّكُ المواصفة لا يُستدعى أصلاً")
        return
    if re.search(r"four\.quality\s*=\s*CategoryScore\(\s*\n?\s*score=spec\.score", s):
        note("S-SHADOWENGINE", "backend/app/services/analysis.py",
             "ركنُ الجودة يُستبدَل بدرجة المواصفة — والبطاقةُ لا تفعل، "
             "فتخرج الشركةُ الواحدة بدرجتين (D149)")
    if '"score_engine"' not in s:
        note("S-SHADOWENGINE", "backend/app/services/analysis.py",
             "لا يُقال أيُّ محرّكٍ أنتج الدرجة")




# ── S-ONEARCH — محلِّلا نمطٍ لا يتّفقان (D092) ────────────────────────────
def check_one_archetype_resolver() -> None:
    """أركانُ البطاقة تُحسب لنمطٍ وتُقرأ لنمطٍ آخر.

    ‏`sector_metrics` كانت تُغذّى بالنمط من خريطة الـYAML، والبطاقةُ تُقرأ
    بالنمط من خريطة المواصفة — واختلفتا في ‎51 قطاعاً من ‎63. فمقاييسُ
    البنك لا تُحسب لبنكٍ قطاعُه إنجليزيّ، ثم تُعدّ أركانُه «غائبة».
    """
    f = ROOT / "backend/app/services/four_scores.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if re.search(r"sector_metrics\.compute\(\s*archetype_for\(", s):
        note("S-ONEARCH", "backend/app/services/four_scores.py",
             "مقاييسُ القطاع تُحسب بمحلِّلٍ غير محلِّل البطاقة — الأركانُ "
             "تُحسب لنمطٍ وتُقرأ لآخر")
    if "resolve_archetype_ex" not in s:
        note("S-ONEARCH", "backend/app/services/four_scores.py",
             "محلِّلُ المواصفة لا يُستعمل في تغذية مقاييس القطاع")


# ── S-ATTAINABLE — أُزيل مع ما كان يحرسه ────────────────────────────────
# كان يشترط وجودَ `ATTAINABLE` وسكربتَ إعادة قياسها. وقد تبيّن أنّ
# الجدولَ لم يقرأه أحدٌ قطُّ: `spec_score` يحسب التغطيةَ من الأوزان
# مباشرةً. وتبيّن أنّ هذا الفحصَ نفسَه **لم يُسجَّل** في جدول الفحوص،
# فلم يعمل يوماً — واحدٌ من اثنين وسبعين، والباقي مسجَّلٌ كلُّه.
# فحُذف الثلاثة معاً: جدولٌ لا يُقرأ، وسكربتٌ يقيسه، وفحصٌ يحرسه.



# ── S-REDLINE — الترتيبُ النسبيّ يُنجّي أسوأَ القطاع (D095) ───────────────
def check_red_lines() -> None:
    """الرتبةُ نسبية: شركةٌ خاسرةٌ ثلاثَ سنواتٍ تخرج عاليةً إن كان أقرانُها
    أسوأ. فوقائعُ مطلقة تُبطِل ولا تُخصم — والخصمُ يذوب في المتوسّط."""
    f = ROOT / "backend/app/services/red_lines.py"
    if not f.exists():
        note("S-REDLINE", "backend/app/services/red_lines.py",
             "لا خطوطَ حمراء — الترتيبُ النسبيّ بلا حارسٍ مطلق")
        return
    s = f.read_text(encoding="utf-8")
    # ══ يُحرَس المعنى لا الاسم ══
    # فشل هذا الحارسُ ثلاثَ مرّات على **تصحيحاتٍ** لا أعطاب: تسميةٌ
    # تغيّرت، عتبةٌ شُدّت، اتّجاهٌ أُضيف. والحارسُ الذي يمسك الحرفَ يمنع
    # الإصلاح. فالمحروسُ هنا: عددُ الخطوط الأدنى، وأن عتباتِها لا تعود
    # أرخى من الإطار المهنيّ الذي اعتمده المالك.
    fired = len(re.findall(r'\n\s*add\("', s))
    if fired < 7:
        note("S-REDLINE", "backend/app/services/red_lines.py",
             f"{fired} خطوطٍ حمراء فقط — الإطارُ المهنيّ يوجب أكثر")
    checks = {
        "خسارةٌ متّصلة": r"streak >= 3",
        "حقوقُ ملكيةٍ سالبة": r"eqs\[-1\] < 0",
        "تدفّقٌ تشغيليّ سالب": r"ocf\[-3:\]",
        "تدفّقٌ حرٌّ سالب": r"fcf\[-3:\]",
        "تغطيةُ فوائد": r"_IC_FLOOR\s*=\s*1\.5",
        # الحدُّ الافتراضيّ يبقى ‎6× كما في الإطار؛ ورفعُه لنمطٍ بعينه
        # (‏ريت · بنية) قرارٌ قطاعيّ معلَنٌ في `_DEBT_CAP`.
        "الدَّينُ إلى الأرباح": r'_DEBT_CAP\.get\(archetype or "", 6\.0\)',
        "فجوةُ الربح والنقد": r"a > 10 for a in accr",
    }
    for name, pat in checks.items():
        if not re.search(pat, s):
            note("S-REDLINE", "backend/app/services/red_lines.py",
                 f"«{name}» مفقودٌ أو عتبتُه أرخى من الإطار المهنيّ")

    # ══ والخطُّ واقعةٌ ثابتة لا لقطةُ سنة ══ (D127)
    # خطّا الرافعة كانا يُقرآن من آخر فترةٍ وحدها، فسنةٌ دوريّةٌ ضعيفة
    # تُشعل خطّاً يقول «إعسارٌ فنّيّ» ويُبطل الحكمَ كلَّه: ‎105 إشعالاتٍ
    # من أصل ‎212 على السوق الحقيقيّ. فالمحروسُ أن يمرّا بشرط الثبات.
    if "def _persistent" not in s:
        note("S-REDLINE", "backend/app/services/red_lines.py",
             "لا شرطَ ثباتٍ — الخطُّ الأحمر يُشعَل بلقطةِ سنةٍ واحدة")
    else:
        for name, pat in (("تغطيةُ فوائد",
                           r"_persistent\(ics,"),
                          ("الدَّينُ إلى الأرباح",
                           r"_persistent\(ndes,")):
            if not re.search(pat, s):
                note("S-REDLINE", "backend/app/services/red_lines.py",
                     f"«{name}» لا يمرّ بشرط الثبات — سنةٌ عابرةٌ تُبطِل حكماً")
    # ولا يُشعَل على تقدير: الأرباحُ قبل الإهلاك للخطّ تُحسب صارمةً، فلا
    # يستبدل الربحُ التشغيليّ بها فينفخ النسبةَ فوق الحدّ بلا دَينٍ ثقيل.
    if "def _ebitda_strict" not in s:
        note("S-REDLINE", "backend/app/services/red_lines.py",
             "الرافعةُ تُدين بتقديرٍ للأرباح — الخطُّ يوجّه تهمةً لا تُراجَع")

    # ══ وما لا يُثبته بيانُنا يُخفض ولا يُبطِل ══ (D127)
    # عددُ الأسهم لا يميّز أسهمَ المنحة من إصدارٍ لطرفٍ ثالث، فلا يقطع
    # بالتخفيف. ونقلُه إلى الحوكمة قرارُ المجلس — لا إسقاطُه: الإشارةُ
    # تبقى معروضةً للمستثمر، فيُحرَس بقاؤها هناك.
    if re.search(r'add\("dilution"', s):
        note("S-REDLINE", "backend/app/services/red_lines.py",
             "«تخفيفُ الحصّة» خطٌّ أحمر — وعددُ الأسهم لا يميّز المنحةَ "
             "من التخفيف، فيُبطِل حكماً بشاهدٍ ظنّيّ")
    g = ROOT / "backend/app/services/governance_pillar.py"
    if not (g.exists() and "dilution" in g.read_text(encoding="utf-8")):
        note("S-REDLINE", "backend/app/services/governance_pillar.py",
             "«تخفيفُ الحصّة» سقط من الحوكمة بعد نقله إليها — "
             "أُسقطت الإشارةُ بدل أن تُنقل")
    # ══ والخطُّ يُنسب إلى نموذج العمل ══
    # الإطارُ المهنيّ نفسه ينصّ أن العتبات «تتغيّر حسب القطاع». وتطبيقُها
    # موحَّدةً أدان بنكاً سليماً نامياً بثلاثة خطوط (نموُّ دفتر القروض
    # يظهر تدفّقاً تشغيليّاً سالباً) وريتاً برافعةٍ طبيعية.
    for tok in ("_NO_CASHFLOW_LINES", "_NO_INTEREST_LINE", "_DEBT_CAP",
                "_UNIVERSAL"):
        if tok not in s:
            note("S-REDLINE", "backend/app/services/red_lines.py",
                 f"‏{tok} مفقود — الخطُّ الأحمر موحَّدٌ على الأنماط، "
                 f"فيُدان من كان نموذجُ عمله هو السبب")
    d = ROOT / "backend/app/services/decision_engine.py"
    if d.exists():
        t = d.read_text(encoding="utf-8")
        if "red_lines" not in t or 'matched_rule_id="red_line"' not in t:
            note("S-REDLINE", "backend/app/services/decision_engine.py",
                 "الخطُّ الأحمر لا يُبطِل القرار — يُحسب ولا يحكم")
    a = ROOT / "backend/app/services/analysis.py"
    if a.exists() and "red_lines=(fin.get" not in a.read_text(encoding="utf-8"):
        note("S-REDLINE", "backend/app/services/analysis.py",
             "الخطوطُ الحمراء لا تُمرَّر إلى بوّابة القرار")


# ── S-TIERANK — التعادلُ يُعاقَب بصفر (D097) ──────────────────────────────
def check_tie_rank() -> None:
    """من ساوى كلَّ أقرانه فهو وسطُهم لا أدناهم.

    كانت القيمةُ المساوية لأدنى نقطةِ قطعٍ تُعطى صفراً، فتساوي القطاعِ
    كلِّه في مؤشّرٍ يُخرج **الجميع** بصفر — عقوبةٌ على التشابه لا قياس.
    """
    f = ROOT / "backend/app/services/peer_distribution.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if "cuts[0] == cuts[-1]" not in s:
        note("S-TIERANK", "backend/app/services/peer_distribution.py",
             "التوزيعُ المتعادلُ كلُّه لا يُعالَج — الجميعُ يخرج بطرفٍ لا بوسط")
    if not re.search(r"if value < cuts\[0\]", s):
        note("S-TIERANK", "backend/app/services/peer_distribution.py",
             "القيمةُ المساوية للحدّ الأدنى تُعامَل معاملةَ ما دونه")


# ── S-GOVNAME — اسمٌ يخلط معنيين (D096) ───────────────────────────────────
def check_governance_naming() -> None:
    """اسمُ الشاشة «حوكمة» وما تقيسه جودةٌ مالية.

    وفي سوقٍ كثيرُ شركاته عائليُّ السيطرة، تركّزُ الملكية وتخفيفُ الحصّة
    قد يضرّ حائزاً طويلَ الأجل أكثرَ من نسبةِ ربحيةٍ ضعيفة.
    """
    f = ROOT / "backend/app/services/governance_pillar.py"
    if not f.exists():
        note("S-GOVNAME", "backend/app/services/governance_pillar.py",
             "لا ركنَ حوكمةٍ حقيقيّ — الاسمُ بلا مُسمّى")
        return
    s = f.read_text(encoding="utf-8")
    for k in ("insider_ownership", "free_float", "share_dilution", "payout_funding"):
        if f'"{k}"' not in s:
            note("S-GOVNAME", "backend/app/services/governance_pillar.py",
                 f"ركنُ «{k}» مفقود")
    if '"blind"' not in s and "blind" not in s:
        note("S-GOVNAME", "backend/app/services/governance_pillar.py",
             "ما لا نراه غيرُ معلَن — يُوهَم أن الركن يغني عنه")
    a = ROOT / "backend/app/services/analysis.py"
    if a.exists() and '"governance": gov_pillar' not in a.read_text(encoding="utf-8"):
        note("S-GOVNAME", "backend/app/services/analysis.py",
             "ركنُ الحوكمة يُحسب ولا يصل الشاشة")
    # ولا يبقى الاسمُ القديم على الدرجة المالية
    for page in ("frontend/src/components/analysis/AnalysisPanel.tsx",
                 "frontend/src/components/market/StockView.tsx"):
        g = ROOT / page
        if g.exists() and "درجة الحوكمة</" in g.read_text(encoding="utf-8"):
            note("S-GOVNAME", page,
                 "الدرجةُ المالية ما زالت تُسمّى «حوكمة» — اسمٌ واحد لمعنيين")



# ── S-BANDRANK — النطاقُ الصحّيّ يُرتَّب (D100) ────────────────────────────
def check_band_not_ranked() -> None:
    """المخالفةُ تتصدّر حين يُرتَّب ما ليس الأكثرُ فيه خيراً.

    صندوقٌ يوزّع ‎150٪ من أمواله من العمليات — يوزّع من دَينه، وهو أحدُ
    خطوطنا الحمراء — كان يخرج في قمّة قطاعه، لأن `band` سقط في خانة
    «الأكثرُ خير». ومؤشّراتُ النطاق قيمتُها الصحيحة بنيويّة لا نسبية.
    """
    f = ROOT / "backend/app/services/spec_score.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    # الثابتُ المحروس: اتّجاهاتٌ بعينها لا تدخل الترتيب أبداً — لا صيغةُ
    # السطر. وحين أُضيفت `higher_abs`/`lower_abs` (معاييرُ منشورة: بازل ·
    # النسبةُ المجمّعة) تغيّر السطرُ فأخفق الحارسُ على توسعةٍ صحيحة.
    if not re.search(r"cuts\s*=\s*None if direction in NO_RANK", s):
        note("S-BANDRANK", "backend/app/services/spec_score.py",
             "مؤشّرُ النطاق الصحّيّ يدخل الترتيب — فالمخالفةُ الجسيمة "
             "تُرتَّب في القمّة")
    m = re.search(r"NO_RANK\s*=\s*\(([^)]*)\)", s)
    body = m.group(1) if m else ""
    for d in ('"band"', '"higher_abs"', '"lower_abs"'):
        if d not in body:
            note("S-BANDRANK", "backend/app/services/spec_score.py",
                 f"الاتّجاه {d} يدخل الترتيب — والمعيارُ المنشور يُقاس "
                 f"بحدّه لا برتبته")



# ── S-ADVICE — صيغةُ أمرٍ للعموم (D103) ───────────────────────────────────
def check_public_voice() -> None:
    """ما ينطق به التطبيق للجمهور غيرُ ما ينطق به لمالكه.

    كلّف المالكُ المجلسَ ألّا تُسبّب المخرَجاتُ إحراجاً عند النشر العامّ.
    والتطبيقُ ينطق «شراء قوي» و«تجنب» على أوراقٍ مسمّاة في تداول — صيغةُ
    أمرٍ لا صيغةُ قياس. وهي لمالكٍ يقرّر لنفسه أداةٌ خاصّة، وتوجيهُها إلى
    الجمهور بابٌ لا يُفتح بلا ترخيص. والعلاجُ لا يُنقص التحليل: كلُّ ما
    يعرفه المحرّك وقائعُ قابلةٌ للتحقّق تُقال كما هي.
    """
    f = ROOT / "backend/app/services/decision_engine.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if "PUBLIC_LABEL" not in s or "def public_label" not in s:
        note("S-ADVICE", "backend/app/services/decision_engine.py",
             "لا مفرداتِ نشرٍ عامّ — «شراء قوي» تصل الجمهورَ كما هي")
    if "def is_public_mode" not in s:
        note("S-ADVICE", "backend/app/services/decision_engine.py",
             "لا تمييزَ بين وضع المالك والنشر العامّ")
    else:
        # الافتراضُ خاصّ: تحوّلُ الأداة إلى منشورٍ عامّ لا يقع بالسهو
        m = re.search(r"def is_public_mode.*?return (.*?)\n", s, re.S)
        if m and "SP_PUBLIC" not in m.group(0):
            note("S-ADVICE", "backend/app/services/decision_engine.py",
                 "وضعُ النشر لا يُضبط بمفتاحٍ صريح")
    a = ROOT / "backend/app/services/analysis.py"
    if a.exists() and "public_label(gov.decision)" not in a.read_text(encoding="utf-8"):
        note("S-ADVICE", "backend/app/services/analysis.py",
             "المفردةُ تصل الشاشةَ بلا ترجمةِ وضع النشر")
    # وتعريفُ الأداة موجودٌ في موضعٍ ثابت
    g = ROOT / "frontend/src/pages/SettingsPage.tsx"
    if g.exists():
        t = g.read_text(encoding="utf-8")
        if "طبيعةُ الأداة" not in t or "لا استشارةً استثمارية" not in t:
            note("S-ADVICE", "frontend/src/pages/SettingsPage.tsx",
                 "لا تعريفَ بطبيعة الأداة — يُنشر للعموم بلا بيانِ ما هو")



# ── S-STALE9 — قِدَمُ البيانات وسمٌ لا مانع (D107) ────────────────────────
def check_nine_month_gate() -> None:
    """نصُّ الإطار المهنيّ: فجوةٌ فوق تسعةِ أشهر ⇒ لا قرارَ موثوق.

    كان عندنا وسمُ «قديم» فوق خمسةٍ وأربعين يوماً في القيمة العادلة
    وحدها — وسمٌ يُقرأ ويُنسى ولا أثرَ له في القرار. والقِدَمُ في إطارٍ
    مؤسسيّ مانعٌ لا ملاحظة.
    """
    f = ROOT / "backend/app/services/decision_engine.py"
    if not f.exists():
        return
    s = f.read_text(encoding="utf-8")
    if "stale_data" not in s or not re.search(r"stale_months\s*>\s*9", s):
        note("S-STALE9", "backend/app/services/decision_engine.py",
             "فجوةُ تسعةِ أشهر لا تمنع الحكم — القِدَمُ وسمٌ لا مانع")
    g = ROOT / "backend/app/services/four_scores.py"
    if g.exists() and '"_asof"' not in g.read_text(encoding="utf-8"):
        note("S-STALE9", "backend/app/services/four_scores.py",
             "تاريخُ آخر قائمةٍ لا يصل بوّابةَ القرار — القاعدةُ بلا مُدخَل")



# ── S-DIRECTION — اتّجاهٌ يخالف تعريفَ مقياسه (D115) ──────────────────────
def check_metric_direction() -> None:
    """أخطرُ عطبٍ يمرّ صامتاً: الأسوأُ يُصنَّف الأفضل.

    كان `earnings_stability` و`margin_stability` مُعلَنين `higher` في
    أحدَ عشرَ موضعاً، وهما **معاملُ اختلافٍ** ينصّ تعريفُه في
    `financial_features` على أن «أقلَّ = أكثرُ استقراراً». فكانت أثبتُ
    شركتين في السوق تُعاقَبان (جرير «أعلى من ‎0٪») ويُكافأ الأشدُّ
    تذبذباً (الرياض ريت «أعلى من ‎100٪»).

    والقاعدةُ المحروسة: كلُّ مقياسٍ وُصف في مصدره بأن «أقلَّه أفضل» لا
    يجوز أن يُعلَن `higher` في أيّ بطاقة.
    """
    src = ROOT / "backend/app/services/financial_features.py"
    spec = ROOT / "backend/app/data/archetype_spec.py"
    if not (src.exists() and spec.exists()):
        return
    t = src.read_text(encoding="utf-8")
    # المطابقةُ على السطر كلِّه: وصفُ السمة يقع بعد قوسٍ مغلقٍ من
    # نداءٍ داخليّ (`_stability_pct(...)`)، فمطابقةُ «ما ليس قوساً»
    # تتوقّف قبله ولا تبلغ الوصف — وهو ما جعل الحارسَ بلا مُدخَل.
    lower_is_better = set(re.findall(
        r'feats\["([a-z_0-9]+)"\]\s*=\s*Feature\([^\n]*?أقل\s*=', t))
    if not lower_is_better:
        note("S-DIRECTION", "backend/app/services/financial_features.py",
             "تعذّر استخراجُ اتّجاهات المقاييس من وصفها — الحارسُ بلا مُدخَل")
        return
    body = spec.read_text(encoding="utf-8")
    for key in sorted(lower_is_better):
        for m in re.finditer(rf'\("{key}",\s*"[^"]+",\s*\d+,[^)]*?"(\w+)"\)', body):
            if m.group(1) in ("higher", "higher_abs"):
                note("S-DIRECTION", "backend/app/data/archetype_spec.py",
                     f"«{key}» مُعلَنٌ {m.group(1)} ومصدرُه يقول «أقلُّ أفضل» — "
                     f"فالأسوأُ يُرتَّب في القمّة")



# ── S-ESSENTIAL — درجةٌ بلا ركنٍ يُعرَّف به العمل (D119) ───────────────────
def check_essential_pillar() -> None:
    """«بوبا» بدرجة ‎86.2 والنسبةُ المجمّعة غائبة.

    الشاشةُ تقول «ممتازة» عن شركة تأمينٍ ينقصها المقياسُ الذي يُعرَّف به
    التأمين، ومحرّكُ القيمة العادلة في الشاشة نفسها يمتنع لهذا السبب —
    فيتناقض شطرا الشاشة الواحدة. وليس نقصَ تغطيةٍ يُعوَّض: انضباطُ
    الاكتتاب هو الميزةُ الدائمة الوحيدة في التأمين.
    """
    f = ROOT / "backend/app/services/spec_score.py"
    spec = ROOT / "backend/app/data/archetype_spec.py"
    if f.exists():
        t = f.read_text(encoding="utf-8")
        if 'card.get("essential")' not in t:
            note("S-ESSENTIAL", "backend/app/services/spec_score.py",
                 "الأركانُ التي لا تقوم الدرجةُ بدونها لا تُفحص — تخرج "
                 "درجةٌ عالية والمقياسُ المعرِّف للعمل غائب")
    if spec.exists():
        t2 = spec.read_text(encoding="utf-8")
        m = re.search(r'"insurance":\s*\{.*?\n    \},', t2, re.S)
        if m and '"essential"' not in m.group(0):
            note("S-ESSENTIAL", "backend/app/data/archetype_spec.py",
                 "بطاقةُ التأمين بلا ركنٍ جوهريّ — والنسبةُ المجمّعة "
                 "يمتنع عندها محرّكُ القيمة العادلة فيتناقض الشطران")



# ── S-SCALEDRIFT — عتبةٌ مطلقة على مقياسٍ نسبيّ (D121) ────────────────────
def check_threshold_scale() -> None:
    """معنى الرقم تبدّل، والعتباتُ بقيت على معناه القديم.

    صارت الدرجةُ **رتبةً مئوية في القطاع** — وسيطُها ‎50 بالبناء نفسه —
    وبقيت عتباتُ القرار مكتوبةً لمقياسٍ مطلق. فقِيس على السوق: ‎52٪ من
    الشركات «تجنّب». وذلك عطبٌ رياضيّ لا نتيجةُ تقييم.

    والمحروسُ: أن تُسمّي كلُّ عتبةٍ شريحةً معلومة من التوزيع — شراءٌ قويّ
    في العُشر الأعلى، وشراءٌ في الثلث الأعلى، وتجنّبٌ في الشريحة الدنيا
    وحدها.
    """
    y = ROOT / "backend/app/data/governance_rules.yaml"
    p = ROOT / "backend/app/services/peer_distribution.py"
    if not (y.exists() and p.exists()):
        return
    t = y.read_text(encoding="utf-8")

    def _cut(rule: str) -> int | None:
        m = re.search(rf"id: {rule}\n(?:\s*#[^\n]*\n)*\s*conditions:\n"
                      rf"\s*-\s*\{{[^}}]*metric: quality[^}}]*value:\s*(\d+)", t)
        return int(m.group(1)) if m else None

    sb, bu, av = _cut("strong_buy"), _cut("buy"), _cut("avoid_weak_quality")
    if sb is not None and sb < 75:
        note("S-SCALEDRIFT", "backend/app/data/governance_rules.yaml",
             f"«شراء قوي» عند مئينِ {sb} — أي أعلى من رُبع السوق فأكثر، "
             f"وهي درجةُ تميّزٍ لا توسّط")
    if bu is not None and bu < 60:
        note("S-SCALEDRIFT", "backend/app/data/governance_rules.yaml",
             f"«شراء» عند مئينِ {bu} — قريبٌ من الوسيط")
    if av is not None and sb is not None and av >= sb:
        note("S-SCALEDRIFT", "backend/app/data/governance_rules.yaml",
             "عتبةُ التجنّب تساوي عتبةَ الشراء أو تفوقها")



# ── S-ABSTAINBYPASS — نُسخ بقرار المالك (D123 → D149) ────────────────────
# كان يشترط أن يُسكِت امتناعُ المواصفة ركنَ الجودة. وقد رُفع الاستبدالُ
# كلُّه حين صار منطقُ بطاقة السلامة هو المنطقَ العامّ، فلم يبقَ محرّكان
# يلتفّ أحدُهما على الآخر. والتطابقُ يفحصه `gov_one_engine.py` سلوكياً.
def check_abstain_respected() -> None:
    return



# ── S-MOU — مذكّرةُ التفاهم زينةٌ لا تُلزِم (D125) ────────────────────────
def check_mou_enforced() -> None:
    """شرطٌ لا يُقاس ليس شرطاً.

    عقد المجلسُ واللجنةُ المالية مذكّرةَ تفاهمٍ تُعرّف جاهزيةَ القرار
    بأرقام. ومذكّرةٌ نصّيةٌ وحدها تُقرأ مرّةً ثم يختلف الطرفان في
    تفسيرها — وهو ما وقع مراراً: يُسأل «أجاهزٌ القرار؟» فيُجاب بتقدير.
    فيُشترط أن تكون الشروطُ بياناتٍ يقرؤها البرنامج، وأن يقيسها المسبار
    ويعود بإخفاقٍ إن لم تُستوفَ.
    """
    r = ROOT / "backend/app/data/readiness.py"
    d = ROOT / "docs/GOVERNANCE.md"
    p = ROOT / "scripts/audit/probe_real.py"
    if not r.exists():
        note("S-MOU", "backend/app/data/readiness.py",
             "شروطُ الجاهزية غيرُ معرَّفة أرقاماً — فالجاهزيةُ رأيٌ يُتنازع فيه")
        return
    t = r.read_text(encoding="utf-8")
    for key in ("verdict_share", "avoid_share", "strong_buy_count",
                "contradictions"):
        if f'"{key}"' not in t:
            note("S-MOU", "backend/app/data/readiness.py",
                 f"شرطُ «{key}» مفقودٌ من مذكّرة التفاهم")
    if d.exists() and "مذكّرة تفاهم" not in d.read_text(encoding="utf-8"):
        note("S-MOU", "docs/GOVERNANCE.md",
             "المذكّرةُ غيرُ مثبتة في الميثاق — والميثاقُ مرجعُها الأعلى")
    if p.exists():
        tp = p.read_text(encoding="utf-8")
        if "from app.data.readiness import" not in tp:
            note("S-MOU", "scripts/audit/probe_real.py",
                 "المسبارُ لا يقيس شروطَ المذكّرة — فهي نصٌّ لا يُلزِم")
        if "return 0 if ok else 1" not in tp:
            note("S-MOU", "scripts/audit/probe_real.py",
                 "المسبارُ لا يعود بإخفاقٍ عند عدم استيفاء الشروط")



# ── S-MARKETRANK — الخلاصةُ لا تُرتَّب فتفقد العتباتُ معناها (D126) ───────
def check_market_rank() -> None:
    """عتبةٌ تُسمّي شريحةً لا تصحّ إلا على مقياسٍ منتظم.

    كلُّ مؤشّرٍ يُرتَّب في قطاعه فيصير مئيناً منتظماً، لكنّ متوسّطها
    المرجَّح يتكدّس حول الوسط — فخرج «شراء قوي» شركتين من ‎268 و«تجنّب»
    ‎43٪. فتُرتَّب الخلاصةُ بين شركات السوق فتعود إلى الانتظام.
    """
    f = ROOT / "backend/app/services/spec_score.py"
    p = ROOT / "backend/app/services/peer_distribution.py"
    if f.exists():
        s = f.read_text(encoding="utf-8")
        if "def raw_composite" not in s:
            note("S-MARKETRANK", "backend/app/services/spec_score.py",
                 "لا خلاصةَ خام تُبنى عليها توزيعُ السوق")
        if 'dist.get("composite")' not in s:
            note("S-MARKETRANK", "backend/app/services/spec_score.py",
                 "الخلاصةُ لا تُرتَّب بين شركات السوق — فعتباتُ القرار "
                 "تُسمّي شرائحَ لا وجودَ لها")
    if p.exists() and '"composite"' not in p.read_text(encoding="utf-8"):
        note("S-MARKETRANK", "backend/app/services/peer_distribution.py",
             "توزيعُ الخلاصة لا يُبنى — فلا مرجعَ للترتيب السوقيّ")


CHECKS = {
    "S-MARKETRANK": check_market_rank,
    "S-MOU": check_mou_enforced,
    "S-ABSTAINBYPASS": check_abstain_respected,
    "S-SCALEDRIFT": check_threshold_scale,
    "S-ESSENTIAL": check_essential_pillar,
    "S-DIRECTION": check_metric_direction,
    "S-STALE9": check_nine_month_gate,
    "S-ADVICE": check_public_voice,
    "S-BANDRANK": check_band_not_ranked,
    "S-REDLINE": check_red_lines,
    "S-TIERANK": check_tie_rank,
    "S-GOVNAME": check_governance_naming,
    "S-ONEARCH": check_one_archetype_resolver,
    "S-BLENDCOV": check_score_not_blended,
    "S-RANKBASIS": check_rank_basis,
    "S-SHADOWENGINE": check_shadow_engine,
    "S-PHASESHAPE": check_phase_shape,
    "S-LIQBARS": check_liquidity_bars,
    "S-COVSERIAL": check_coverage_serialized,
    "S-SANEBAND": check_sane_band,
    "S-SINGLEPATH": check_single_path_gate,
    "S-NOFVABSTAIN": check_no_fv_abstains,
    "S-NOMU": check_nomu_discount,
    "S-ARCHLENS": check_archetype_lens,
    "S-ARCHFALLBACK": check_archetype_fallback,
    "S-GENERICPANEL": check_generic_panel,
    "S-ABSTAINBUY": check_abstain_is_not_license,
    "S-UNFALSIFIABLE": check_falsifiable,
    "S-EVERLASTING": check_everlasting_roe,
    "S-CHEAPRISK": check_cheap_risk,
    "S-UNGATED": check_ungated_ddm,
    "S-BLAMESYMBOL": check_blame_symbol,
    "S-FUNDGRADE": check_fund_archetype,
    "S-BLINDMEDIAN": check_blind_median,
    "S-UNEXPLAINED": check_unexplained_score,
    "S-ELIGIBILITY": check_eligibility_tag,
    "S-DIVGRID": check_div_grid,
    "S-FVCEIL": check_fair_value_ceiling,
    "S-FINARCH": check_financial_archetypes,
    "S-TWOENGINES": check_two_engines,
    "S-EVTAG": check_event_tags,
    "S-VANISH": check_vanishing_company,
    "S-TIERSTACK": check_tier_stacking,
    "S-SYMBOL": check_symbol_consistency,
    "S-FLATPAGE": check_flat_page,
    "S-TWOFAIR": check_two_fair_values,
    "S-PEAKVALUE": check_peak_value,
    "S-SCOPEGAP": check_scope_gap,
    "S-DECLAREDONLY": check_declared_only,
    "S-DEADBTN": check_dead_buttons,
    "S-AIFACT": check_ai_fabricates_facts,
    "S-UNSTABLEKEY": check_unstable_key,
    "S-DUPTOKEN": check_duplicate_tokens,
    "S-OVERDARK": check_overdark_ink,
    "S-GHOSTFILTER": check_ghost_filter,
    "S-FREETAG": check_free_tag,
    "S-FALLBACKCHAIN": check_fallback_chain,
    "S-NAMEDVALUE": check_named_value,
    "S-FOOTNOTE": check_footnote,
    "S-NOSTANDARD": check_no_standard,
    "S-STALEGUARD": check_stale_guard,
    "S-AICONTEXT": check_ai_context,
    "S-THINPEER": check_thin_peer,
    "S-NOAUDIT": check_no_audit,
    "S-AUDITSCOPE": check_audit_scope,
    "S-FABRICATED": check_fabricated,
    "S-MERGE": check_merge_save,
    "S-SECRETS": check_secrets,
    "S-HARDCOLOR": check_hardcoded_colors,
    "S-VARLEAK": check_var_leak,
    "S-BOTSCOPE": check_bot_scope,
}


def main() -> int:
    reg = json.loads((pathlib.Path(__file__).parent / "registry.json").read_text(encoding="utf-8"))
    print(f"لجنة كشف الأعطال — الطبقة الساكنة ({len(CHECKS)} فحوص، "
          f"{len(reg['defects'])} عطباً في الذاكرة)\n")
    for name, fn in CHECKS.items():
        before = len(findings)
        fn()
        got = len(findings) - before
        print(f"  {'✖' if got else '✔'} {name:<14} {got if got else 'نظيف'}")
    if findings:
        print(f"\n{len(findings)} ملاحظة:")
        for c, w, d in findings[:40]:
            print(f"  • [{c}] {w}\n      {d}")
    else:
        print("\n✔ لا ملاحظات.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
