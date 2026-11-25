"""رقيبُ حلقة الأحداث (‏D843 — المالك 2026-11-25: «لاحظتُ بطئاً عند تحميل التطبيق للمحتوى والصفحات»).

قيس على الخادم: طلباتُ الصفحة الواحدة تنتهي معاً بعد ثوانٍ (المحفظةُ 7–13 ث، و«الإشعارات» 17 ث خلف طلبٍ واحد)، وهي وحدَها في عمليةٍ
مستقلّةٍ أقلُّ من نصف ثانية — فشيءٌ متزامنٌ في العملية الحيّة يحبس الحلقةَ فينتظره كلُّ طلب. والرقيبُ يسمّيه: خيطٌ خفيفٌ يراقب نبضاً تكتبه
الحلقةُ كلَّ 50ms؛ فإن تأخّر النبضُ فوق 400ms أخذ لقطةً من مكدّس خيط الحلقة نفسِه (أين هي الآن — في أيّ دالّةٍ من التطبيق)، وحين تعود
الحلقةُ يكتب الحبسَ بمدّته ومكانه في ملفٍّ صغير (آخرُ مئةٍ وعشرين) يقرؤه كاشفُ الخادم. لا يغيّر شيئاً في عمل التطبيق، وكلفتُه نبضٌ ولقطة.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
import traceback
from collections import deque
from datetime import datetime, timezone

_HB = {"t": time.monotonic()}
_STALLS: deque = deque(maxlen=120)
_ON = {"on": False}
THRESH = 0.4


def path() -> str:
    d = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "perf")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "loop_stalls.json")


def _where(frame) -> list[str]:
    """أسطرُ المكدّس من شيفرة التطبيق (والمكتبةُ الأخيرةُ التي استُدعيت منها) — من الأعمق."""
    out = []
    for fs in traceback.extract_stack(frame)[::-1]:
        f = fs.filename
        if "/app/" in f and "loop_watch" not in f:
            out.append(f"{f.split('/app/')[-1]}:{fs.lineno} {fs.name}")
        elif not out and "site-packages" in f:
            out.append(f"{f.split('site-packages/')[-1]}:{fs.lineno} {fs.name}")
        if len(out) >= 8:
            break
    if not out:                                                   # لا شيفرةَ من التطبيق في المكدّس: أعمقُ ثلاثة أسطرٍ كما هي
        out = [f"{fs.filename.split('/')[-1]}:{fs.lineno} {fs.name}" for fs in traceback.extract_stack(frame)[::-1][:3]]
    return out


def _save() -> None:
    try:
        tmp = path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(list(_STALLS), fh, ensure_ascii=False)
        os.replace(tmp, path())
    except Exception:                                             # noqa: BLE001
        pass


def _watch(loop_tid: int) -> None:
    cur = None
    while _ON["on"]:
        time.sleep(0.1)
        late = time.monotonic() - _HB["t"]
        if late > THRESH and cur is None:
            fr = sys._current_frames().get(loop_tid)
            cur = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "where": _where(fr) if fr else [], "t0": _HB["t"]}
        elif late > THRESH and cur is not None and late > 2.0 and not cur.get("where2"):
            fr = sys._current_frames().get(loop_tid)        # لقطةٌ ثانيةٌ في الحبس الطويل — أيبقى في المكان نفسِه؟
            cur["where2"] = _where(fr) if fr else []
        elif late <= THRESH and cur is not None:
            cur["ms"] = round((_HB["t"] - cur.pop("t0")) * 1000)
            _STALLS.append(cur)
            cur = None
            _save()


async def _beat() -> None:
    while _ON["on"]:
        _HB["t"] = time.monotonic()
        await asyncio.sleep(0.05)


def start() -> None:
    if _ON["on"]:
        return
    _ON["on"] = True
    _HB["t"] = time.monotonic()
    asyncio.get_running_loop().create_task(_beat())
    threading.Thread(target=_watch, args=(threading.get_ident(),), name="loop-watch", daemon=True).start()


def stop() -> None:
    _ON["on"] = False
