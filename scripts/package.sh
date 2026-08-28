#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# بناء حزمة التحديث — **الطريق الوحيد المعتمَد**.
#
# ولماذا سكربتٌ لا أمرٌ يدويّ: كانت الحزمة تُبنى بسطرٍ يُكتب في كل مرّة
# (`git ls-files | tar`)، وفحصُ اللجنة يُشغَّل **إن تذكّرتُه**. وما يعتمد على
# التذكّر يسقط يوم يكثر العمل — وهو بالضبط اليوم الذي تُسلَّم فيه حزمةٌ
# معطوبة. فصار الفحص **شرطاً في الطريق** لا خطوةً بجانبه: لا تُبنى حزمةٌ
# لم تجتز اللجنة، ولا يُتجاوَز ذلك إلا بإذنٍ صريحٍ مكتوب من المالك
# (`--force`) — ويُطبع في المخرَج أن الحزمة خرجت بلا فحص.
#
#   bash scripts/package.sh                    فحصٌ ساكن ثمّ بناء
#   SP_TOKEN=… bash scripts/package.sh --live  مع الطبقة الحيّة (أوثق)
#   bash scripts/package.sh --force            تجاوزٌ بإذن المالك وحده
# ─────────────────────────────────────────────────────────────────────────────
set -u
cd "$(dirname "$0")/.." || exit 2

NAME="spupdatechanged.tar.gz"     # الاسم ثابتٌ بأمر المالك، لا يُغيَّر
LIVE=0; FORCE=0
for a in "$@"; do
  case "$a" in
    --live)  LIVE=1 ;;
    --force) FORCE=1 ;;
    *) echo "وسيطٌ غير معروف: $a"; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }
rule() { printf '%s\n' "──────────────────────────────────────────────"; }

rule; say "بناء حزمة التحديث — بوّابة لجنة كشف الأعطال"; rule

# ── ١) اللجنة أوّلاً ─────────────────────────────────────────────────────────
if [ "$FORCE" = "1" ]; then
  say "⚠ تجاوزٌ صريح (--force): الحزمة تُبنى **بلا فحص**."
  say "  لا يُستعمل هذا إلا بإذن المالك، ويُذكر في التسليم."
else
  if [ "$LIVE" = "1" ]; then
    bash scripts/audit/run.sh --live || { say ""; say "✖ لم تجتز اللجنة — لا حزمة."; exit 1; }
  else
    bash scripts/audit/run.sh || { say ""; say "✖ لم تجتز اللجنة — لا حزمة."; exit 1; }
  fi
fi

# ── ٢) شجرةٌ نظيفة: ما لم يُلتزَم لا يدخل الحزمة ─────────────────────────────
# الحزمة تُبنى من `git ls-files`، فالتعديل غير الملتزَم يدخلها من القرص بلا
# أن يظهر في التاريخ — نسخةٌ لا يمكن إعادة إنتاجها ولا معرفة ما فيها.
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  say ""
  say "⚠ في الشجرة تغييراتٌ غير ملتزَمة — ستدخل الحزمة بلا أثرٍ في التاريخ:"
  git status --short | sed 's/^/    /'
  say "  التزِمها أوّلاً كي تكون الحزمة قابلةً لإعادة الإنتاج."
  [ "$FORCE" = "1" ] || exit 1
fi

# ── ٣) لا سرّ يخرج ──────────────────────────────────────────────────────────
say ""
say "فحصُ الأسرار في الملفّات المتتبَّعة…"
if git ls-files -z | xargs -0 grep -lIE '[0-9]{8,12}:AA[A-Za-z0-9_-]{30,}|sk-[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{30,}' 2>/dev/null | grep -q .; then
  say "✖ رمزٌ سرّيٌّ حيّ في ملفٍّ متتبَّع — أُوقف البناء."
  exit 1
fi
if git ls-files | grep -qE '(^|/)\.env$'; then
  say "✖ ملفّ .env متتبَّع — أُوقف البناء."
  exit 1
fi
say "  ✔ لا سرّ."

# ── ٤) البناء ───────────────────────────────────────────────────────────────
rm -f "$NAME"
git ls-files -z | tar --null -czf "$NAME" -T - || { say "✖ تعذّر البناء."; exit 1; }

COUNT=$(tar -tzf "$NAME" | wc -l | tr -d ' ')
SIZE=$(du -h "$NAME" | cut -f1)
HEAD_SHA=$(git rev-parse --short HEAD)

say ""
rule
say "✔ $NAME — $SIZE · $COUNT ملفاً · من الالتزام $HEAD_SHA"
rule

# ── ٥) أمر التركيب يُطبع مع الحزمة دائماً (شرطُ المالك) ──────────────────────
cat <<'INSTALL'

أمر التركيب:

cd /home/ubuntu/Smart-Portfolio && \
cp -a .env /home/ubuntu/.env.safe.$(date +%s) && \
tar -xzf /home/ubuntu/spupdatechanged.tar.gz -C /home/ubuntu/Smart-Portfolio && \
rm -f backend/app/services/telegram.py && \
docker compose up -d --build && \
echo "⏳ انتظر الإقلاع…" && sleep 60 && \
docker logs sp_backend 2>&1 | grep -a '🦅' | tail -5
INSTALL
