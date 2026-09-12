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
    if p.name in ("tadawul_http.py", "tadawul_announcements.py"):
        continue                      # المَعبرُ نفسُه، والإعلاناتُ عميلُها القديمُ مُحال
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

print(("FAIL" if fail else "PASS") + " D250 — مَعبرٌ واحدٌ إلى «تداول»")
raise SystemExit(fail)
