#!/usr/bin/env python3
"""حارسُ D827 · D829 · D830 — ملاحظاتُ المالك على التقرير (2026-11-25).

  ‏D827 «عند التنزيل يظهر قصٌّ في الصفحة الثانية — آخرُ إجراءات الشركات يختفي، وفي التطبيق على الكمبيوتر واضحٌ وتحته فراغ»: قِيس أنّ الطابعَ
        يفتح الورقةَ بنافذةٍ عرضُها 780 فتخرج دالّةُ الملاءمة قبل أن تعمل (كانت تشترط 820) — الصفحاتُ كلُّها بلا تصغيرٍ فيُقصّ ما زاد؛ ثمّ أنّ
        التصغيرَ بالتكبير (‏zoom) يعيد لفَّ الأسطر فيبقى فراغ (0.806)، والتكرارُ البسيطُ يتأرجح.
  ‏D829 «لا تكتب بجانب قسم الأبحاث المحفظةَ الاستثمارية أو المضاربية أو كلَّ المحافظ — اكتفِ بقسم الأبحاث».
  ‏D830 «عند التحميل يصلني تحذيرٌ من كروم» — كروم يحذّر من تنزيلٍ عبر http؛ والعرضُ في قارئ المتصفّح ليس تنزيلاً.

  ١ الطباعةُ الحقيقية (المتصفّحُ بلا واجهةٍ كالخادم): بعرض الحاسوب، والملاءمةُ تعمل — صفحةُ الإجراءات بأسماءٍ طويلةٍ تُصغَّر حتى يسعها، وآخرُ
    صفّ فوق التذييل، والمحتوى بعرض الصفحة كلِّه (لا فراغَ جانبيّ)، وبلا فراغٍ تحته يزيد عن سطرين.
  ٢ الترويسة: «المحفظة الذكية» وتحتها «قسم الأبحاث» وحدَه في كلّ صفحة؛ واسمُ المحفظة المختارة تحت عنوان صفحتها وحدها — ولا «كلّ المحافظ» أبداً.
  ٣ رابطُ العرض: موقَّعٌ قصيرُ العمر بالتقرير المحسوم، والقارئُ يعرض الملفَّ (‏inline) بلا جلسة؛ والمعدَّلُ والمنتهي مرفوضان.

    python3 scripts/audit/report_d827_d830.py
"""
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp_d827_")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import research_paper as RP  # noqa: E402
from app.services import saqr_report as SR  # noqa: E402

# ── ١ الطباعةُ الحقيقية ──
for c in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome",):
    if not _os.environ.get("CHROME_BIN") and _os.path.exists(c):
        _os.environ["CHROME_BIN"] = c
src = (ROOT / "backend/app/services/saqr_report.py").read_text(encoding="utf-8")
out = _os.path.join(_SANDBOX, "paper.html")
subprocess.run([sys.executable, str(ROOT / "scripts/audit/research_desk_d816.py")], env={**_os.environ, "SP_PAPER_OUT": out},
               capture_output=True, timeout=300)
if not (SR.chrome_path() and _os.path.exists(out) and shutil.which("pdftotext")):
    print("… تعذّرت الطباعةُ الحقيقية هنا (لا متصفّحَ أو لا ورقة) — يُكتفى بالساكن")
    check('"--window-size=860,1200"' in src and "gridTemplateColumns.split(' ').length<2" in RP.FIT and "innerWidth<820" not in RP.FIT,
          "١ (ساكن) الطابعُ بعرض الحاسوب، والملاءمةُ بتخطيط الورقة لا برقم العرض")
else:
    html = open(out, encoding="utf-8").read().replace("للصناعة</td>", "للصناعة والتجارة والاستثمار والتطوير العقاري المحدودة</td>")
    probe = ('<script>window.addEventListener("load",function(){setTimeout(function(){var p=document.querySelectorAll(".page")[1],pg=p.getBoundingClientRect(),'
             'lim=p.querySelector(".pf").getBoundingClientRect().top,b=0,L=1e9,R=0;p.querySelectorAll(".pb tr,.pb li,.pb p").forEach(function(r){var q=r.getBoundingClientRect();'
             'b=Math.max(b,q.bottom);L=Math.min(L,q.left);R=Math.max(R,q.right)});var d=document.createElement("div");d.style.cssText="position:fixed;top:0;left:0;font-size:9px;background:#fff";'
             'd.textContent="PROBE fit="+(p.getAttribute("data-fit")||"1")+" gap="+Math.round(lim-b)+" w="+((R-L)/pg.width).toFixed(3)+" iw="+innerWidth;document.body.appendChild(d)},300)})</script>')
    pdf = asyncio.run(SR.to_pdf(html.replace("</body>", probe + "</body>")))
    pf = _os.path.join(_SANDBOX, "p.pdf")
    open(pf, "wb").write(pdf or b"")
    txt = subprocess.run(["pdftotext", "-raw", "-f", "1", "-l", "1", pf, "-"], capture_output=True, text=True).stdout
    line = next((ln for ln in txt.splitlines() if "PROBE" in ln), "")
    kv = dict(x.split("=") for x in line.split()[1:] if "=" in x)
    fit, gap, w, iw = float(kv.get("fit", 1)), int(kv.get("gap", -999)), float(kv.get("w", 0)), int(kv.get("iw", 0))
    check(iw == 860 and fit < 1 and 0 <= gap <= 40 and w >= 0.9 and '"--window-size=860,1200"' in src,
          "١ الطباعةُ الحقيقية: بعرض الحاسوب (860)، وصفحةُ الإجراءات بأسماءٍ طويلةٍ تُصغَّر حتى يسعها — آخرُ صفٍّ فوق التذييل بلا قصٍّ ولا فراغٍ يزيد عن سطرين، "
          "والمحتوى بعرض الصفحة كلِّه", line.strip())

# ── ٢ الترويسة ──
one = RP.render({"date": "2026-11-25", "market": {}, "portfolio_id": 2, "portfolio_name": "المحفظة الاستثمارية"}, "all")
allp = RP.render({"date": "2026-11-25", "market": {}, "portfolio_id": "all", "portfolio_name": "كلّ المحافظ"}, "all")
smalls = [s.split("</small>")[0] for s in one.split("<small>")[1:]]
ps = one.count('data-k="pf-name"')
last = one.rsplit('<section class="page">', 1)[-1]
check(smalls and all(s == "قسم الأبحاث" for s in smalls) and ps == 1 and 'data-k="pf-name">المحفظة الاستثمارية<' in last
      and "كلّ المحافظ" not in allp and 'data-k="pf-name"' not in allp and "<small>قسم الأبحاث · " not in one,
      "٢ الترويسة: «المحفظة الذكية» وتحتها «قسم الأبحاث» وحدَه في كلّ صفحة؛ واسمُ المحفظة المختارة تحت عنوان صفحتها وحدها — ولا «كلّ المحافظ» أبداً",
      f"{set(smalls)} · اسمٌ {ps}")

# ── ٣ رابطُ العرض ──
from app.api.v1.endpoints import market as MK  # noqa: E402
REP = {"date": "2026-11-25", "market": {}, "portfolio_id": 3, "portfolio_name": "المضاربية"}
MK._report_for = lambda pf, day: (3, REP, False)
from app.services import research_desk as RD  # noqa: E402
RD.load_report = lambda key, day=None: REP if (key == 3 and day == "2026-11-25") else None
got_pdf: list = []


async def fake_pdf(r, part="all"):
    got_pdf.append((r.get("portfolio_id"), part))
    return b"%PDF-1.4 view"

RP.pdf = fake_pdf
RP.pdf_warm = lambda r, part="all": False


async def run3():
    from urllib.parse import parse_qs, urlparse
    from fastapi import HTTPException
    link = (await MK.research_desk_pdf_link(None, "3"))["data"]
    q = {k: v[0] for k, v in parse_qs(urlparse(link["path"]).query).items()}
    ok = await MK.research_desk_pdf_view(q["k"], q["day"], q["mo"], int(q["exp"]), q["sig"])
    bad = []
    for mut in ({"sig": "0" * 32}, {"day": "2026-11-24"}, {"exp": int(time.time()) - 5}):
        a = {**q, "exp": int(q["exp"]), **mut}
        try:
            await MK.research_desk_pdf_view(a["k"], a["day"], a["mo"], a["exp"], a["sig"])
            bad.append("قُبل")
        except HTTPException as e:
            bad.append(e.status_code)
    return link, q, ok, bad

link, q, ok, bad = asyncio.run(run3())
disp = ok.headers.get("content-disposition", "")
check(link["path"].startswith("/market/research-desk/pdf-view?") and q["k"] == "3" and q["day"] == "2026-11-25" and ok.body.startswith(b"%PDF")
      and disp.startswith("inline;") and bad == [403, 403, 403] and got_pdf == [(3, "all")]
      and "MK.public_router" not in "" and any(getattr(r, "path", "") == "/research-desk/pdf-view" for r in MK.public_router.routes),
      "٣ رابطُ العرض موقَّعٌ قصيرُ العمر بالتقرير المحسوم، والقارئُ يعرض الملفَّ (‏inline) بلا جلسة — والتوقيعُ المعدَّلُ واليومُ المبدَّلُ والمنتهي مرفوضة",
      f"{disp} · {bad}")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
