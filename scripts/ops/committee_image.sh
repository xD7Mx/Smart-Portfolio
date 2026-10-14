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
# ‏D714: وملفُّ ‎.env‎ مُقنَّعٌ بملفٍّ فارغ — قِيس (run 38604710923): الإعداداتُ تقرأ ‎.env‎ من مجلّد العمل فرفضت مفاتيحَه الزائدة
# وطبعت **قيمَها** في السجلّ (ومنها كلمةُ مرور قاعدة البيانات) — فحُذف السجلّ، ولا يرى الحرّاسُ أسرارَ الخادم بعدها.
# و‎/app‎ هي ‎backend‎ المستودع كما في الحاوية العاملة (‏./backend:/app) — لا نسخةُ الصورة المخبوزة القديمة.
MASK=()
for f in .env backend/.env; do [ -f "$f" ] && MASK+=(-v "/dev/null:/repo/$f:ro"); done
# ‏D714: والصورةُ بلا ‎git‎ — فقِيس «تعذّر سرد الملفّات المتتبَّعة» في حارس الأسرار. فيُعدّ المضيفُ جردَ الملفّات المتتبَّعة
# (‏git ls-files) ويُربط للقراءة، ويقرؤه الحارسُ حين لا ‎git‎ — فيُفحص كلُّ ملفٍّ متتبَّعٍ كما على المضيف.
TRK="$(mktemp)"
git ls-files > "$TRK" 2>/dev/null || true
echo "• اللجنةُ في صورة الخادم ${IMG} — المستودعُ للقراءة فقط، وأسرارُ الخادم مُقنَّعة"
docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -e TZ=Asia/Riyadh -v "$PWD":/repo:ro "${MASK[@]}" \
  -v "$TRK":/tmp/sp_tracked:ro -e SP_TRACKED=/tmp/sp_tracked \
  -v "$PWD/backend":/app:ro -w /repo --entrypoint bash "${IMG}" scripts/audit/run.sh "$@"
RC=$?
rm -f "$TRK"
exit $RC
