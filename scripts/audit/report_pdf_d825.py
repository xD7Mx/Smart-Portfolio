#!/usr/bin/env python3
"""حارسُ D825 — «هناك تأخيرٌ في تحميل ملفّ التقرير اليوميّ» (المالك 2026-11-24).

قِيس على الخادم (‏report_speed_door_d825.py): رأسُ التقرير 2ms، والورقةُ تُبنى في 6–19ms، أمّا الملفُّ فـ7–10 ثوانٍ في كلّ ضغطةٍ على «PDF»:
يُشغَّل متصفّحٌ بلا واجهةٍ من جديد ليطبع الورقةَ نفسَها التي لم تتغيّر.

  ١ الورقةُ حتميّة (لا ساعةَ فيها) فمحتواها مفتاحُ ملفّها، والملفُّ يُطبع مرّةً ويُعاد بعدها فوراً بلا متصفّح.
  ٢ فتحُ الورقة يُعِدّ ملفَّها في الخلفية، والضغطُ على «PDF» أثناءها ينتظر الطبعَ الجاري لا يبدأ ثانياً — وطابعٌ واحدٌ في آن.
  ٣ ولا تحضيرَ في الخلفية إن ضاقت ذاكرةُ الخادم، والمحفوظُ محدود (الأحدثُ استعمالاً يبقى).
  ٤ الطلبان يمرّان من دالّةٍ واحدة (‏_pdf_args): ما يُعَدّ عند الفتح هو ما يُطلب عند الحفظ — وتلغرامُ يمرّ من الملفّ المحفوظ نفسِه.

    python3 scripts/audit/report_pdf_d825.py
"""
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp_d825_")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
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

prints: list = []
live = {"n": 0, "max": 0}


async def fake_to_pdf(html):
    prints.append(len(html))
    live["n"] += 1
    live["max"] = max(live["max"], live["n"])
    await asyncio.sleep(0.4)
    live["n"] -= 1
    return b"%PDF-1.4 " + RP.pdf_key(html).encode() * 60


SR.to_pdf = fake_to_pdf
R1 = {"date": "2026-11-25", "market": {}, "headline": "عنوانٌ أوّل"}
R2 = {"date": "2026-11-25", "market": {}, "headline": "عنوانٌ ثانٍ"}
R3 = {"date": "2026-11-24", "market": {}, "headline": "عنوانُ الأمس"}


async def run():
    out = {}
    det = RP.render(R1, "all") == RP.render(R1, "all")
    t0 = time.monotonic()
    a = await RP.pdf(R1)
    out["first"] = time.monotonic() - t0
    t0 = time.monotonic()
    b = await RP.pdf(R1)
    out["second"] = time.monotonic() - t0
    out["same"] = a == b and a.startswith(b"%PDF")
    out["p1"] = len(prints)
    # ٢ التحضيرُ عند الفتح ثمّ الضغطُ أثناءه
    w = RP.pdf_warm(R2)
    await asyncio.sleep(0.05)
    t0 = time.monotonic()
    c = await RP.pdf(R2)
    out["during"] = time.monotonic() - t0
    out["p2"] = len(prints)
    out["warm_again"] = RP.pdf_warm(R2)                           # محفوظٌ الآن ⇐ لا شيء
    # طابعٌ واحدٌ في آن: ورقتان مختلفتان معاً
    live["max"] = 0
    await asyncio.gather(RP.pdf(R3), RP.pdf({**R3, "headline": "رابعة"}))
    out["conc"] = live["max"]
    # ٣ الذاكرة الضيّقة، والحدّ
    o_mem = RP._mem_ok
    RP._mem_ok = lambda need_mb=350: False
    out["tight"] = RP.pdf_warm({**R1, "headline": "ذاكرةٌ ضيّقة"})
    RP._mem_ok = o_mem
    o_keep = RP.PDF_KEEP
    RP.PDF_KEEP = 2
    await RP.pdf({**R1, "headline": "خامسة"})
    out["files"] = len([n for n in _os.listdir(RP._pdf_dir()) if n.endswith(".pdf")])
    RP.PDF_KEEP = o_keep
    return det, w, c, out

det, w, c, o = asyncio.run(run())
check(det and o["same"] and o["p1"] == 1 and o["first"] >= 0.35 and o["second"] < 0.05,
      "١ الورقةُ حتميّةٌ فمحتواها مفتاحُ ملفّها: الطبعةُ الأولى بالمتصفّح والثانيةُ من المحفوظ فوراً بلا متصفّح",
      f"الأولى {o['first']:.2f}ث · الثانية {o['second'] * 1000:.0f}ms · طبعات {o['p1']}")
check(w is True and c and o["p2"] == 2 and o["during"] < 0.4 and o["warm_again"] is False and o["conc"] == 1,
      "٢ فتحُ الورقة يُعِدّ ملفَّها في الخلفية، والحفظُ أثناءه ينتظر الطبعَ الجاري (لا طبعةَ ثانية)، والمحفوظُ لا يُعاد — وطابعٌ واحدٌ في آن",
      f"انتظر {o['during']:.2f}ث · طبعات {o['p2']} · معاً {o['conc']}")
check(o["tight"] is False and o["files"] == 2,
      "٣ لا تحضيرَ في الخلفية إن ضاقت ذاكرةُ الخادم، والمحفوظُ محدودٌ يبقى منه الأحدثُ استعمالاً", f"ملفّات {o['files']}")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
paper = mk[mk.index("async def research_desk_paper("):mk.index("def _pdf_args(")]
pdfe = mk[mk.index("async def research_desk_pdf("):]
pdfe = pdfe[:pdfe.index("@router.")]
rd = (ROOT / "backend/app/services/research_desk.py").read_text(encoding="utf-8")
check("pdf_warm(rp, pp)" in paper and "_pdf_args(pf, day)" in paper and "r, part = _pdf_args(pf, day)" in pdfe and "await pdf(r, part)" in pdfe
      and "await RP.pdf(r)" in rd,
      "٤ الفتحُ والحفظُ من دالّةٍ واحدة (ما يُعَدّ عند الفتح هو ما يُطلب عند الحفظ)، وإرسالُ تلغرام يمرّ من الملفّ المحفوظ نفسِه")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
