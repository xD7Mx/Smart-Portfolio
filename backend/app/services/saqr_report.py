"""ورقةُ تقرير صقر — **نفس تقرير التطبيق**، لا ورقةٌ أخرى تشبهه.

## خطأٌ وقعتُ فيه، وهذا تصحيحه

أوّل نسخةٍ من هذا الملف بنت ورقةً **من عندي**: خلفيةٌ بيضاء وجدولُ صفوفٍ
بسيط، اقترضت من التطبيق تدرّجَه ورموزَه اللونية وظننتُ ذلك كافياً. وسأل
المالك: «لماذا لا يظهر بنفس تصميم تقرير التطبيق؟» — والجواب أنه فعلاً لم
يكن كذلك. التطبيق له تقريرٌ مصمَّمٌ قائم (`ReportDocument.tsx`): ورقٌ
كريميّ، وخطٌّ **رِقعيّ عريض** لا خطّ المتن، وشريطٌ ذهبيّ تحت الترويسة،
وشبكةُ ستّ بطاقات، وجدولُ مراكز بترويسةٍ كحلية وصفوفٍ متناوبة، وحاصرةُ
تقييمٍ ذهبية. فما بنيتُه كان **تصميماً ثانياً** لا نقلاً للأول — وهو
بالضبط العيب الذي أُحاسِب عليه في هذا التطبيق: مصدران لشيءٍ واحد.

فهذا الملف الآن **نقلٌ حرفيّ** لذلك المكوّن: كل لونٍ ومقاسٍ وحاشيةٍ مأخوذٌ
من سطره هناك. ومصدر أرقامه محرّك التقارير نفسه (`generate_report`) لا
حسابٌ موازٍ — فالورقة التي تصل تلغرام هي التي تُرى في «التقارير».

## ولماذا متصفّحٌ لا مكتبة PDF

العربية. وصلُ الحروف واتّجاه السطر عملُ مُصفِّف نصوصٍ حقيقيّ، ومكتبات PDF
العامّة تكتبها منفصلةً مقلوبة ما لم تُبنَ طبقات تشكيلٍ واتّجاه تُخطئ في
الأسماء المركّبة ولا يُكتشف خطؤها إلا بالعين. والمتصفّح يفعلها كما يفعلها
في الشاشة تماماً.

وإن غاب المتصفّح أُرسلت الصفحة HTML وقيل ذلك صراحةً: صفحةٌ تفتح خيرٌ من
حروفٍ مقطّعة، ومن صمتٍ بلا تفسير.
"""

import asyncio
import base64
import html as _html
import os
import shutil
import tempfile

from loguru import logger

# ── الخطوط ────────────────────────────────────────────────────────────────
# نسخةٌ داخل `backend/` لأن سياق بناء الحاوية هو `./backend` وحده — ومجلّد
# الواجهة غير موجودٍ في الصورة أصلاً. ولو تُرك المسار مشيراً إليه لسقط
# الخطّ صامتاً وطُبعت الورقة بخطٍّ نظاميّ، فتختلف عن الشاشة بلا خطأٍ يظهر.
_FONT_DIRS = [
    os.path.join(os.path.dirname(__file__), "../assets/fonts"),
    "/app/app/assets/fonts",
    "/app/frontend/src/assets/fonts",
    os.path.join(os.getcwd(), "frontend/src/assets/fonts"),
]


def _face(family: str, file: str, weight: int) -> str:
    for d in _FONT_DIRS:
        p = os.path.abspath(os.path.join(d, file))
        if os.path.exists(p):
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return (f"@font-face{{font-family:'{family}';font-weight:{weight};"
                    f"font-display:block;"
                    f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return ""


def _fonts() -> str:
    # الرِقعيّ العريض هو خطّ الورقة في التطبيق، والوزنان ٣٠٠ و٥٠٠ هما
    # المستعملان في المكوّن — فيُضمَّنان معاً وإلّا زوّر المتصفّح الوزن.
    return "".join([
        _face("Thmanyah Serif Display", "thmanyahserifdisplay-Light.woff2", 300),
        _face("Thmanyah Serif Display", "thmanyahserifdisplay-Regular.woff2", 400),
        _face("Thmanyah Serif Display", "thmanyahserifdisplay-Medium.woff2", 500),
    ])


# ── الألوان: من `ReportDocument.tsx` سطراً بسطر ────────────────────────────
NAVY, NAVY_2 = "#3b1e78", "#6d28d9"
GOLD, GOLD_L = "#d4af37", "#f3d98b"
GREEN, RED = "#0f9d63", "#c0273c"
PAPER, INK = "#faf6ee", "#241f1a"
LINE, ZEBRA = "#e4dcc2", "#f6f2e4"
MUTED = "#6b6459"          # `--ink-muted` على الورق الكريميّ

_CSS = f"""
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:{PAPER}}}
body{{color:{INK};font-family:'Thmanyah Serif Display','Segoe UI',sans-serif;
      direction:rtl;text-align:right}}
.doc{{width:794px;min-height:1123px;background:{PAPER};display:flex;
      flex-direction:column}}
.hd{{background:linear-gradient(135deg,{NAVY},{NAVY_2});padding:28px 44px 22px}}
.hd .row{{display:flex;align-items:center;justify-content:space-between}}
.hd .name{{color:#fff;font-size:22px;font-weight:500}}
.hd .tag{{color:{GOLD_L};font-size:11.5px;font-weight:300;margin-top:2px}}
.hd .meta{{text-align:left;color:{GOLD_L};font-size:11px}}
.hd .meta b{{color:#fff;font-weight:300}}
.gold{{height:4px;background:linear-gradient(90deg,{GOLD},{GOLD_L},{GOLD})}}
.body{{padding:26px 44px 32px;flex:1}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:22px}}
.kpi{{border:1px solid {LINE};border-radius:8px;padding:10px 12px;background:#fff}}
.kpi .l{{font-size:10px;color:{MUTED};font-weight:300}}
.kpi .v{{font-size:16px;font-weight:300;margin-top:2px;font-variant-numeric:tabular-nums;
         direction:ltr;unicode-bidi:isolate;text-align:right}}
.sec{{font-size:13px;font-weight:500;color:{NAVY};margin-bottom:8px;
      border-inline-start:3px solid {GOLD};padding-inline-start:8px}}
table{{width:100%;border-collapse:collapse;font-size:11.5px}}
thead tr{{background:#efe7cf;color:{NAVY};border-bottom:2px solid {GOLD};
          -webkit-print-color-adjust:exact;print-color-adjust:exact}}
th{{padding:7px 10px;text-align:start;font-weight:500}}
td{{padding:6px 10px;border-bottom:1px solid #e9e2cc}}
tbody tr:nth-child(even){{background:{ZEBRA}}}
tbody tr:nth-child(odd){{background:#fff}}
.num{{font-variant-numeric:tabular-nums}}
.mut{{color:{MUTED}}}
.pos{{color:{GREEN}}} .neg{{color:{RED}}} .navy{{color:{NAVY}}}
.anh{{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}}
.pill{{font-size:11px;font-weight:300;color:{NAVY};background:{ZEBRA};
       border:1px solid {GOLD};border-radius:999px;padding:3px 12px}}
.an{{font-size:12px;line-height:1.9;color:#28324a;white-space:pre-wrap;
     background:#fff;border:1px solid {LINE};border-radius:8px;padding:16px}}
.ft{{background:linear-gradient(135deg,{NAVY},{NAVY_2});padding:16px 44px;
     display:flex;align-items:center;justify-content:center;
     color:{GOLD_L};font-size:10.5px;font-weight:300}}
@page{{size:A4;margin:0}}
"""


def _money(n) -> str:
    try:
        return f"{float(n or 0):,.0f}"
    except Exception:
        return "—"


def _e(v) -> str:
    return _html.escape(str(v if v is not None else ""))


def _kpi(label: str, value: str, cls: str = "navy") -> str:
    return (f'<div class="kpi"><div class="l">{_e(label)}</div>'
            f'<div class="v {cls}">{_e(value)}</div></div>')


def build_html(data: dict, *, period: str = "", generated_at: str = "") -> str:
    """يبني الورقة من **مخرَج محرّك التقارير نفسه**.

    المفاتيح هي مفاتيح `generate_report` حرفياً، فلا تحويل ولا إعادة تسمية
    يفتح باب التباعد.
    """
    m = data.get("metrics") or {}
    upnl = m.get("unrealized_pnl") or 0
    roi = m.get("roi_pct") or 0

    wealth = m.get("wealth")
    net = m.get("net_profit")
    growth_pct = m.get("capital_growth_pct")
    cagr = m.get("cagr_pct")
    cash_pct = m.get("cash_pct")

    def _sgn(v, d=2, suf="%"):
        """رقمٌ بإشارته، أو شرطةٌ إن غاب. لا يُختلق صفرٌ لغائب — والفرق
        بين «صفر» و«غير متوفّر» فرقُ معنى لا فرقُ شكل."""
        if v is None:
            return "—"
        return ("+" if v >= 0 else "") + f"{v:.{d}f}{suf}"

    def _cls(v):
        return "navy" if v is None else ("pos" if v >= 0 else "neg")

    # ══ شبكة المالك: ثلاثة صفوفٍ لكلٍّ معنى ══
    # الأول: ما تملك.  الثاني: ما ربحت.  الثالث: كيف أدّت.
    # والترتيب من اليمين لأن الصفحة عربية — أوّل ما يُذكر أوّلُ ما يُرى.
    kpis = "".join([
        _kpi("القيمة السوقية", _money(m.get("market_value"))),
        _kpi("القيمة المدفوعة", _money(m.get("total_invested"))),
        _kpi("إجمالي الثروة", _money(wealth) if wealth is not None else "—"),

        _kpi("الأرباح غير المحققة",
             ("+" if upnl >= 0 else "") + _money(upnl), "pos" if upnl >= 0 else "neg"),
        _kpi("نسبة الأرباح غير المحققة", _sgn(roi), "pos" if roi >= 0 else "neg"),
        _kpi("صافي الربح",
             ("+" if (net or 0) >= 0 else "") + _money(net) if net is not None else "—",
             _cls(net)),

        _kpi("عائد المحفظة", _sgn(growth_pct), _cls(growth_pct)),
        # العائد المركّب يمتنع قبل تسعين يوماً من بداية المشروع (بند
        # الميثاق): ضربُ شهرٍ في اثني عشر يَعِد بما لا يُعرف. والخانة تبقى
        # باسمها وشرطتها فلا يتزحزح الصفّ ولا يُظنّ الاسم ساقطاً.
        _kpi("العائد المركّب", _sgn(cagr), _cls(cagr)),
        _kpi("نسبة السيولة النقدية",
             f"{cash_pct:.2f}%" if cash_pct is not None else "—"),
    ])

    # صناديق النموّ: «السابق › الحالي» — بنفس منطق ألوان المكوّن، واللون
    # بحسب **إشارة الحالي** لا اتجاه التغيّر.
    # ══ صناديق النموّ أُسقطت ══
    # كانت تعرض «عائد المحفظة» و«التفوّق على تاسي» و«نسبة السيولة»، وقد صار
    # اثنان منها في شبكة المقاييس بأمر المالك. وإبقاؤها يعني رقماً واحداً
    # في موضعين من الورقة نفسها — وهو ما نتحاماه في كل شاشة.
    growth_html = ""

    positions = data.get("positions") or []
    pos_html = ""
    if positions:
        rows = []
        for p in positions:
            pnl = p.get("pnl") or 0
            rows.append(
                f'<tr><td style="font-weight:300">{_e(p.get("name"))}</td>'
                f'<td class="mut">{_e(p.get("symbol"))}</td>'
                f'<td class="num">{_money(p.get("shares"))}</td>'
                f'<td class="num">{_money(p.get("market_value"))}</td>'
                f'<td class="num {"pos" if pnl >= 0 else "neg"}">'
                f'<bdi dir="ltr" style="unicode-bidi:isolate">{"+" if pnl >= 0 else ""}{_money(pnl)} '
                f'({"+" if (p.get("pnl_pct") or 0) >= 0 else ""}{(p.get("pnl_pct") or 0):.1f}%)</bdi></td></tr>')
        head = "".join(f"<th>{h}</th>" for h in
                       ("الشركة", "الرمز", "الأسهم", "القيمة", "الربح/الخسارة"))
        pos_html = (f'<div style="margin-bottom:24px"><div class="sec">تفاصيل المراكز</div>'
                    f'<table><thead><tr>{head}</tr></thead>'
                    f'<tbody>{"".join(rows)}</tbody></table></div>')

    score = data.get("overall_score")
    pill = f'<div class="pill">التقييم العام {_e(score)}/100</div>' if score is not None else ""
    content = data.get("content") or "لا تتوفر بيانات تحليلية لهذا التقرير."

    return (
        "<!doctype html><html dir='rtl' lang='ar'><head><meta charset='utf-8'>"
        # العنوان يُسمّي الوثيقة داخل قارئ PDF. وبلا هذا السطر تحمل اسم
        # الملف المؤقّت الذي طُبعت منه — قِيس في القارئ.
        f"<title>تقرير {_e(period)} — المحفظة الذكية</title>"
        f"<style>{_fonts()}{_CSS}</style></head><body><div class='doc'>"
        f"<div class='hd'><div class='row'>"
        f"<div><div class='name'>المحفظة الذكية</div>"
        f"<div class='tag'>تقرير أداء المحفظة الاستثمارية</div></div>"
        f"<div class='meta'><div>الفترة: <b>{_e(period)}</b></div>"
        f"<div style='margin-top:3px'>تاريخ الإصدار: {_e(generated_at)}</div></div>"
        f"</div></div><div class='gold'></div>"
        f"<div class='body'><div class='kpis'>{kpis}</div>{growth_html}{pos_html}"
        f"<div><div class='anh'><div class='sec' style='margin-bottom:0'>التحليل الشامل</div>{pill}</div>"
        f"<div class='an'>{_e(content)}</div></div></div>"
        # ══ لا حاشية ══ (بأمر المالك، مكرَّراً)
        # كانت هنا «قراءةٌ فقط — لا أمرَ بيعٍ ولا شراء»: تبريرٌ يعتذر عمّا
        # لم يُطلب. والتطبيق سجلٌّ رسميّ لا مدوّنة، فلا رأيَ فيه ولا شرحَ
        # ولا تحفّظ — والمالك يعرف أن تقريره تقرير.
        "</div></body></html>")


# ── HTML ← PDF ────────────────────────────────────────────────────────────
_CHROME_NAMES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")


def chrome_path() -> str | None:
    env = os.environ.get("CHROME_BIN")
    if env and os.path.exists(env):
        return env
    for n in _CHROME_NAMES:
        p = shutil.which(n)
        if p:
            return p
    return None


async def to_pdf(html: str) -> bytes | None:
    """يطبع الورقة PDF بمتصفّحٍ بلا واجهة. `None` إن لم يوجد متصفّح.

    ولا يُرمى استثناء: غياب المتصفّح حالةٌ متوقّعة تُعالَج بإرسال HTML،
    لا عطبٌ يُسقط ردّ البوت.
    """
    exe = chrome_path()
    if not exe:
        return None
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "r.html")
        out = os.path.join(d, "r.pdf")
        with open(src, "w", encoding="utf-8") as f:
            f.write(html)
        cmd = [exe, "--headless", "--disable-gpu", "--no-sandbox",
               "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
               "--virtual-time-budget=5000",
               f"--print-to-pdf={out}", f"file://{src}"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
            _, err = await asyncio.wait_for(proc.communicate(), timeout=90)
            if os.path.exists(out) and os.path.getsize(out) > 800:
                with open(out, "rb") as f:
                    return f.read()
            logger.warning(f"🦅 طباعة التقرير أخفقت: {(err or b'')[:200]!r}")
        except Exception as e:
            logger.warning(f"🦅 طباعة التقرير تعذّرت: {e}")
    return None
