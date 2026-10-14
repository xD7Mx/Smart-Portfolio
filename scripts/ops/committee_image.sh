#!/usr/bin/env bash
# ══ لجنةُ كشف الأعطال على الخادم — في صورة الخادم نفسِها ══ (D714)
# المضيفُ بلا تبعيّات بايثون (‏loguru · fastapi · sqlalchemy …) ولا node، والحاويةُ العاملةُ تربط ‎backend‎ و‎scripts‎ وحدهما
# فلا تجد الحرّاسُ ملفّاتِ الواجهة. فتُشغَّل اللجنةُ في حاويةٍ عابرةٍ من صورة الخادم نفسِها، والمستودعُ كلُّه مربوطٌ **للقراءة
# فقط** في ‎/repo‎: تبعيّاتُ الإنتاج نفسُها على الشجرة المنشورة نفسِها، ولا يُكتب في المستودع شيء. وما لا يُقاس فيها (فحوصُ
# المتصفّح) يُقال «لم يُقَس» لا «سقط». وإن غابت الصورةُ فعلى المضيف كما كان.
#     bash scripts/ops/committee_image.sh [--live]
set -u
IMG="$(docker inspect -f '{{.Config.Image}}' sp_backend 2>/dev/null || true)"
if [ -z "${IMG}" ]; then
  echo "… لا صورةَ للخادم (‏sp_backend) — تُشغَّل اللجنةُ على المضيف"
  exec bash scripts/audit/run.sh "$@"
fi
echo "• اللجنةُ في صورة الخادم ${IMG} — المستودعُ للقراءة فقط"
exec docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -e TZ=Asia/Riyadh -v "$PWD":/repo:ro -w /repo \
  --entrypoint bash "${IMG}" scripts/audit/run.sh "$@"
