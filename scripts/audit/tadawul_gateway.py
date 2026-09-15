#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D250 — مَعبرٌ واحدٌ إلى «تداول»، والحجبُ يُعبَر لا يُلتفّ حولَه.
#
# كان مكتوباً في ثلاثة ملفّاتٍ أن «تداول» تردّ ‎403 على بيانات السوق،
# فبُني بديلٌ من «أرقام» للدليل وبقي المعدَّلُ الخالي من المخاطر بلا
# مصدر. وقِيس أن الحجبَ **ببصمة TLS** لا بالرؤوس، فعُبر بانتحال بصمة
# كروم — فردّت الصفحاتُ المحجوبةُ ‎200.
#
# وخطرُ ذلك أن تتناثر الجلساتُ: كلُّ ملفٍّ ينتحل بطريقته فتختلف الرؤوسُ
# والتسخينُ ويصير للمعنى الواحد مصدران. فيُقاس السلوك:
#   ٠· الجلبُ يمرّ بالمَعبر ويعيد (الحالة، النصّ)
#   ١· والمُحيلُ (‏Referer) والمعاملاتُ تصل كما أُرسلت
#   ٢· وغيابُ المكتبة لا يُسقط التطبيق بل يُعيده إلى العميل القديم
#   ٣· ولا ملفَّ يطلب «تداول» بعميلٍ خاصٍّ به خارج المَعبر
#   ٤· ومزامنةُ الدليل تمرّ به فعلاً (كانت تُردّ ‎403)
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.services import tadawul_http as th  # noqa: E402

seen: dict = {}


def _stub(url, params, referer, timeout):
    seen.update({"url": url, "params": params, "referer": referer, "timeout": timeout})
    return 200, "صفحةٌ مموَّهة"


_real_blocking = th._blocking_fetch          # يُعاد بعد فحوص التمويه
th._blocking_fetch = _stub
th._have_curl = lambda: True

st, body = asyncio.run(th.fetch("https://www.saudiexchange.sa/x"))
check(st == 200 and body == "صفحةٌ مموَّهة",
      "٠ الجلبُ يمرّ بالمَعبر ويعيد (الحالة، النصّ)", f"{st} · {body}")

asyncio.run(th.fetch("https://www.saudiexchange.sa/y",
                     params={"sectorParameter": "All"}, referer="https://ref"))
check(seen.get("params") == {"sectorParameter": "All"} and seen.get("referer") == "https://ref",
      "١ المُحيلُ والمعاملاتُ يصلان كما أُرسلا", f"{seen.get('params')} · {seen.get('referer')}")

# ── ٢ · غيابُ المكتبة: سقوطٌ إلى العميل القديم لا انهيار ──────────────────
th._have_curl = lambda: False


class _Resp:
    status_code = 403
    text = "محجوب"


class _Client:
    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, *a, **k):
        return _Resp()


import httpx  # noqa: E402

_real = httpx.AsyncClient
httpx.AsyncClient = _Client
try:
    st2, b2 = asyncio.run(th.fetch("https://www.saudiexchange.sa/z"))
    ok = (st2 == 403 and b2 == "محجوب")
    detail = f"{st2} · {b2}"
except Exception as e:                                            # noqa: BLE001
    ok, detail = False, f"{type(e).__name__}: {e}"
finally:
    httpx.AsyncClient = _real
    th._have_curl = lambda: True
check(ok, "٢ بلا المكتبة يعود إلى العميل القديم بلا انهيار", detail)

# ── ٣ · لا عميلَ خاصّاً بـ«تداول» خارج المَعبر ───────────────────────────
SRC = ROOT / "backend" / "app" / "services"
stray = []
for p in sorted(SRC.glob("*.py")):
    if p.name == "tadawul_http.py":
        continue                      # المَعبرُ نفسُه — وهو وحدَه
    # ══ استثناءٌ رُفع ══ (D312)
    # كان `tadawul_announcements.py` مستثنًى بحجّة «عميلُها القديمُ مُحال»،
    # وبقيت تنادي «تداول» بـ`httpx` فتردّ 403 في كلّ نداءٍ صامتاً. فرُحّلت
    # إلى المَعبر ورُفع الاستثناء — فلا حارسَ يحمي ما يجب أن يُقاس.
    t = p.read_text(encoding="utf-8")
    # ══ الجوارُ يُقاس لا الملفّ ══ (بعد أوّل تشغيل)
    # كان الفحصُ يرفض أيَّ عميلٍ في ملفٍّ **يذكر** «تداول» — فأسقط
    # `_argaam_listed` وهي تطلب «أرقام» لا «تداول»: مصدرٌ آخرُ مشروع.
    # فيُقاس القربُ: عميلٌ يُنشأ في جوار عنوانِ «تداول» نفسِه.
    for m in re.finditer(r"saudiexchange\.sa", t):
        win = t[max(0, m.start() - 400): m.end() + 400]
        for c in re.finditer(r"(httpx\.AsyncClient|requests\.get|urlopen)", win):
            stray.append(f"{p.name}: {c.group(0)}")
check(not stray, "٣ لا ملفَّ يطلب «تداول» بعميلٍ خاصٍّ به", "؛ ".join(stray[:3]))

# ── ٤ · مزامنةُ الدليل تمرّ بالمَعبر ──────────────────────────────────────
sync_src = (SRC / "tadawul_sync.py").read_text(encoding="utf-8")
check("from app.services.tadawul_http import fetch" in sync_src,
      "٤ مزامنةُ الدليل تجلب من المَعبر لا من العميل المحجوب")

# ── ٥ · والمعدَّلُ الخالي من المخاطر كذلك ────────────────────────────────
rf_src = (SRC / "risk_free.py").read_text(encoding="utf-8")
check("from app.services.tadawul_http import fetch" in rf_src,
      "٥ وقارئُ الصكوك يجلب من المَعبر نفسِه")

# ── ٦ · والإفصاحاتُ: قشرةٌ تُسمّي خدمتَها فتُنادى ──────────────────────
# قِيس على خادم المالك: بعد المَعبر صارت صفحةُ الإفصاحات ٢٠٠ بـ٥٧٢ ألفَ
# حرفٍ و**صفرَ جداول**، وخدمتُها المسمّاةُ فيها (`getNewsListData`) تردّ
# `{"announcementList":[{"PR_DATE":"Sep 14, 2026","TITLE":…}]}` — ومفتاحُ
# القائمة وأسماءُ الحقول وصيغةُ التاريخ **كلُّها** خارج قارئي (D313).
th._blocking_fetch = _real_blocking          # قياسٌ حقيقيٌّ يحتاج جالباً حقيقياً


def _ann_from_service() -> tuple[int, str, str]:
    import asyncio as _aio
    import http.server
    import json as _j
    import socketserver
    import threading

    import app.services.tadawul_announcements as A

    page = ('<!DOCTYPE html><html lang="en"><head><base href='
            '"http://127.0.0.1:{p}/wps/portal/x/!ut/p/z1/ABC/"></head><body>'
            '<a href="/wps/portal/x/p0/z1=NJgetNewsListData=/">x</a>'
            '</body></html>')
    svc = {"announcementList": [
        {"PR_DATE": "Sep 14, 2026", "SYMBOL": "1120",
         "TITLE": "إعلان شركة الراجحي عن تنفيذ صفقة خاصة على أسهمها",
         "PR_URL": "/ar/news/1"}]}

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):                                # noqa: D102
            pass

        def do_GET(self):                                         # noqa: N802
            port = self.server.server_address[1]
            b = (_j.dumps(svc, ensure_ascii=False).encode()
                 if "=NJ" in self.path else page.format(p=port).encode())
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url, js = A.DEFAULT_TADAWUL_URL, A.TADAWUL_JSON_URL
    A.DEFAULT_TADAWUL_URL, A.TADAWUL_JSON_URL = f"http://127.0.0.1:{port}/p", ""
    try:
        items = _aio.run(A.fetch_tadawul_announcements(force=True))
        first = items[0] if items else {}
        return len(items), str(first.get("date")), str(first.get("symbol"))
    finally:
        A.DEFAULT_TADAWUL_URL, A.TADAWUL_JSON_URL = url, js
        srv.shutdown()


_n, _d, _s = _ann_from_service()
check(_n == 1, "٦ خدمةُ صفحة الإفصاحات تُكتشَف وتُنادى فتُقرأ عناصرُها",
      f"{_n} عنصراً")
check(_d == "2026-09-14",
      "٦ب و«Sep 14, 2026» تاريخٌ يُقرأ — وكان يعود None فيُسقطه الفلتر", _d)
check(_s == "1120", "٦ج ورمزُ الشركة يُقرأ من الحقل الكبير (`SYMBOL`)", _s)

print(("FAIL" if fail else "PASS") + " D250 — مَعبرٌ واحدٌ إلى «تداول»")
raise SystemExit(fail)
