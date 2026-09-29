"""D534 — صفحةُ البداية من الإعدادات تُعتمد: الدخولُ يمرّ بها، والاستئنافُ لإعادة التحميل وحدها.

    python3 scripts/audit/start_page_d534.py
"""
import pathlib
import re
import sys

SRC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src"
app = (SRC / "App.tsx").read_text(encoding="utf-8")
login = (SRC / "pages" / "LoginPage.tsx").read_text(encoding="utf-8")
m = re.search(r"const PLACE_TTL = ([^;]+);", app)
ttl_ms = eval(m.group(1)) if m else None          # noqa: S307 — تعبيرٌ حسابيٌّ من ملفٍّ متتبَّع
ok1 = ttl_ms is not None and ttl_ms <= 10 * 60 * 1000
ok2 = '"/portfolio", { replace: true }' not in login and 'loc.state?.from || "/"' in login
print(("PASS" if ok1 else "FAIL"), "١ الاستئنافُ لإعادة التحميل وحدها —", ttl_ms)
print(("PASS" if ok2 else "FAIL"), "٢ الدخولُ يمرّ بصفحة البداية لا بالمحفظة")
print(("PASS" if ok1 and ok2 else "FAIL") + " D534 — صفحةُ البداية تُعتمد")
sys.exit(0 if ok1 and ok2 else 1)
