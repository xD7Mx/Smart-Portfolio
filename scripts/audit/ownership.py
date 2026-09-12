#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D270 — هيكلُ الملكية بالمتصفّح: اكتشافٌ لا مسارٌ محفوظ، وجهلٌ لا يُملأ.
#
# أربعةُ بنودٍ قِيست مرسومةً بجافاسكربت (‏200 وصفرُ صفوف) فلا يبلغها انتحالُ
# البصمة. والمتصفّحُ يبلغها، ويجلب معه ثلاثةَ أخطار:
#
#   ٠· **مسارٌ محفوظٌ يصمت يومَ يدور** — فتُقرأ الروابطُ بأسمائها العربية
#   ١· **رقمٌ بلا علامة نسبةٍ يُقرأ نسبةً** — فلا يُقرأ إلا ما فُهم
#   ٢· **صفٌّ لم يُفهَم يُصفَّر** — بل يُترك، والبندُ الفارغُ يغيب
#   ٣· وغيابُ المتصفّح **يُقال باسمه** لا يُخلَط بغياب البيانات
#   ٤· وقراءةٌ شائخةٌ لا تُقرأ حاضراً
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import datetime as _dt  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.services import lastgood, ownership as ow  # noqa: E402

BASE = "https://www.argaam.com"

HOME = """<html><body>
 <a href="/ar/company/x/1">نظرة عامة</a>
 <a href="/ar/company/shareholders/marketid/3/companyid/1010"> كبار المساهمين </a>
 <a href="/ar/company/insider/marketid/3/companyid/1010">صفقات كبار المساهمين</a>
 <a href="/ar/company/foreign/marketid/3/companyid/1010">الملكية الأجنبية</a>
 <a href="/ar/company/est/marketid/3/companyid/1010">تقديرات المحللين</a>
</body></html>"""

# ── ٠ · الروابطُ تُكتشَف بأسمائها ────────────────────────────────────────
links = ow.tab_links(HOME, BASE)
check(set(links) == set(ow.TABS)
      and links["major_holders"].endswith("/shareholders/marketid/3/companyid/1010")
      and links["major_holders"].startswith(BASE),
      "٠ الروابطُ تُقرأ من الصفحة بأسمائها العربية ويُكمَّل أصلُها",
      str(sorted(links)))

# ويومَ يدور المسار: الاسمُ باقٍ فيُكتشَف الرابطُ الجديدُ بلا تعديل شيفرة.
moved = HOME.replace("/ar/company/shareholders/marketid/3/companyid/1010",
                     "/ar/co/v2/holders/9/1010")
check(ow.tab_links(moved, BASE)["major_holders"].endswith("/ar/co/v2/holders/9/1010"),
      "٠ب ومسارٌ دار يُكتشَف باسمه — لا يصمت الصفُّ بلا سبب")
check(not ow.tab_links("<a href='/x'>أخبار الشركة</a>", BASE),
      "٠ج وتبويبٌ ليس منها لا يُلتقَط بالتقريب")

# ── ١ · ٢ · لا يُقرأ إلا ما فُهم ────────────────────────────────────────
PAGE = """<table>
 <tr><th>المساهم</th><th>النسبة</th></tr>
 <tr><td>صندوق الاستثمارات العامة</td><td>70.00%</td></tr>
 <tr><td>المؤسسة العامة للتأمينات</td><td>9.5 %</td></tr>
 <tr><td>مساهمٌ بلا نسبة</td><td>—</td></tr>
 <tr><td>سطرٌ برقمٍ لا نسبة</td><td>1,240,000</td></tr>
</table>"""
rows = ow.parse(PAGE)
check([r["name"] for r in rows] == ["صندوق الاستثمارات العامة",
                                    "المؤسسة العامة للتأمينات"]
      and rows[0]["percent"] == 70.0 and rows[1]["percent"] == 9.5,
      "١ النسبةُ تُقرأ بعلامتها، ورقمٌ بلا علامةٍ ليس نسبة", str(rows))
check(all(r["percent"] is not None for r in rows),
      "٢ وصفٌّ لم يُفهَم يُترك — لا يُصفَّر ولا يُملأ بشبيهه")
check(ow.parse("<html>لا جدول</html>") == [],
      "٢ب وصفحةٌ بلا جدولٍ تعود فارغةً لا مختلَقة")
check(ow._pct("120%") is None and ow._pct("-3.2%") == -3.2,
      "٢ج ونسبةٌ خارج المعقول ليست نسبة", str(ow._pct("120%")))

# وأوسعُ جدولٍ يفوز: صفحةٌ فيها جدولُ تنقّلٍ صغيرٌ لا يُقرأ بدل الجدول.
NAV = "<table><tr><td>القطاع</td><td>50%</td></tr></table>" + PAGE
check(len(ow.parse(NAV)) == 2, "٢د وجدولُ الزينة لا يُقرأ بدل جدول المحتوى")

# ── ٣ · غيابُ المتصفّح يُقال باسمه ───────────────────────────────────────
import app.services.browser_fetch as bf  # noqa: E402
import app.services.argaam_calendar as ac  # noqa: E402


async def _cid(sym, *a, **k):
    return "1010"


ac._company_id = _cid                                            # type: ignore[assignment]


async def _boom(*a, **k):
    raise bf.BrowserUnavailable("playwright غير مركَّبة")


bf.render = _boom                                                # type: ignore[assignment]
res = asyncio.run(ow.refresh("1010"))
check("المتصفّح" in str(res.get("error") or ""),
      "٣ غيابُ المتصفّح حالةٌ باسمها لا «لا بيانات»", str(res)[:70])
check(ow.reading("1010") is None,
      "٣ب ولا يُكتب شيءٌ حين لا يُقرأ شيء")

# ── ٤ · المسارُ الكامل، ثمّ الشيخوخة ─────────────────────────────────────
async def _render(urls, **k):
    return {u: (HOME if "companyoverview" in u else PAGE) for u in urls}


bf.render = _render                                              # type: ignore[assignment]
res = asyncio.run(ow.refresh("1010"))
rec = ow.reading("1010") or {}
check(res.get("ok") and len(rec.get("major_holders") or []) == 2
      and rec.get("urls", {}).get("foreign", "").startswith(BASE),
      "٤ والمسارُ الكامل يحفظ ما قُرئ برابطه وتاريخه", str(res)[:80])

empty = {"error": None}


async def _render_blank(urls, **k):
    return {u: (HOME if "companyoverview" in u else "<html></html>") for u in urls}


bf.render = _render_blank                                        # type: ignore[assignment]
res2 = asyncio.run(ow.refresh("2010"))
check(not res2.get("ok") and ow.reading("2010") is None,
      "٤ب وتبويباتٌ فُتحت بلا صفٍّ مفهومٍ ليست نجاحاً", str(res2)[:70])

rec["as_of"] = (_dt.date.today()
                - _dt.timedelta(days=ow.MAX_AGE_DAYS + 2)).isoformat()
lastgood.save(ow.STORE_KEY.format(sym="1010"), rec)
check(ow.reading("1010") is None,
      f"٤ج وقراءةٌ أقدمُ من {ow.MAX_AGE_DAYS} يوماً لا تُقرأ حاضراً")

# ── ٥ · متصفّحٌ واحدٌ في الصورة لا اثنان ─────────────────────────────────
kw = bf._launch_kwargs()
check("--no-sandbox" in kw["args"],
      "٥ الإقلاعُ بلا صندوقٍ رمليّ — شرطُ كروميوم داخل حاوية")
dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
check("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1" in dockerfile
      and "chromium" in dockerfile,
      "٥ب ولا يُنزَّل متصفّحٌ ثانٍ لمعنًى واحد — كروميومُ الصورة نفسُه")

print(("FAIL" if fail else "PASS") + " D270 — هيكلُ الملكية بالمتصفّح")
raise SystemExit(fail)
