#!/usr/bin/env python3
"""كاشفُ D843 (٤) — ذاكرةُ الخادم: حجمُ مخزن «آخر قيمةٍ صالحة» ومفاتيحُه الأكبر، وسجلُّ حالة السوق، وذاكرةُ العمليات والمبادلة. قراءةٌ فقط."""
import json
import os
from collections import Counter

P = os.environ.get("LASTGOOD_PATH") or "/app/data/lastgood.json"
try:
    st = os.stat(P)
    print(f"المخزن {P}: {st.st_size / 1e6:.1f}MB")
    d = json.load(open(P, encoding="utf-8"))
    sizes = Counter()
    pref = Counter()
    for k, v in d.items():
        n = len(json.dumps(v, ensure_ascii=False))
        sizes[k] = n
        pref[k.split(":")[0] + ":" + (k.split(":")[1] if ":" in k else "")] += n
    print(f"مفاتيح {len(d)} · أكبرُ البادئات:")
    for k, n in pref.most_common(12):
        print(f"   {n / 1e6:7.2f}MB  {k}")
    print("أكبرُ المفاتيح:")
    for k, n in sizes.most_common(8):
        print(f"   {n / 1e6:7.2f}MB  {k[:80]}")
except Exception as e:                                            # noqa: BLE001
    print("المخزن:", type(e).__name__, e)
for f in ("/app/data", "/app/storage"):
    try:
        big = []
        for root, _, files in os.walk(f):
            for x in files:
                q = os.path.join(root, x)
                try:
                    big.append((os.path.getsize(q), q))
                except OSError:
                    pass
        big.sort(reverse=True)
        print(f"\nأكبرُ الملفّات في {f}:")
        for n, q in big[:10]:
            print(f"   {n / 1e6:8.1f}MB  {q}")
    except Exception as e:                                        # noqa: BLE001
        print(f, type(e).__name__)
print("\nالعمليات (‏RSS):")
for pid in os.listdir("/proc"):
    if not pid.isdigit():
        continue
    try:
        cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode()[:90]
        rss = next((int(l.split()[1]) for l in open(f"/proc/{pid}/status") if l.startswith("VmRSS")), 0)
        if rss > 20000:
            print(f"   {rss / 1024:7.0f}MB  {pid}  {cmd}")
    except Exception:                                             # noqa: BLE001
        pass
m = {l.split(":")[0]: l.split(":")[1].strip() for l in open("/proc/meminfo")}
print("\nالذاكرة:", {k: m.get(k) for k in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree", "Cached")})
