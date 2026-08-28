#!/usr/bin/env bash
# نسخة قاعدة البيانات **خارج الخادم**.
#
# الخطر الذي يعالجه: قاعدة البيانات في فوليوم Docker على قرص الخادم،
# والنسخ الاحتياطية في ./data/backups على **القرص نفسه**. فموتُ الخادم أو
# تلفُ القرص أو حذفُ الـinstance بالخطأ يُفقد الاثنين معاً — نسخةٌ احتياطية
# تموت مع أصلها ليست نسخةً احتياطية.
#
# الاستعمال:
#   bash tools/backup-offsite.sh                 # يكتب في ~/offsite/
#   bash tools/backup-offsite.sh s3://bucket/x   # ثم يرفعها (يتطلب aws cli)
set -euo pipefail
cd "$(dirname "$0")/.."

DEST="${1:-}"
STAMP=$(date +%F-%H%M)
OUT_DIR="$HOME/offsite"
mkdir -p "$OUT_DIR"
DUMP="$OUT_DIR/db-$STAMP.sql.gz"

# pg_dump من داخل الحاوية بمتغيّراتها — فلا يُكتب اسم مستخدم ولا قاعدة هنا.
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$DUMP"

SIZE=$(stat -c%s "$DUMP")
if [ "$SIZE" -lt 10240 ]; then
  echo "!! النسخة أصغر من ١٠ كيلوبايت ($SIZE) — الأرجح أنها فشلت. لم تُعتمد." >&2
  rm -f "$DUMP"; exit 1
fi

# تحقّق أنّ الملف مفكوكٌ سليم — نسخةٌ لا تُفكّ ليست نسخة.
gzip -t "$DUMP"
echo "تمّت: $DUMP ($(du -h "$DUMP" | cut -f1))"

# الإبقاء على آخر ١٤ نسخة محليّاً.
ls -1t "$OUT_DIR"/db-*.sql.gz | tail -n +15 | xargs -r rm -f

if [ -n "$DEST" ]; then
  aws s3 cp "$DUMP" "$DEST/" --only-show-errors
  echo "رُفعت إلى $DEST"
else
  echo "لم تُرفع خارج الخادم. مرّر وجهةً (s3://…) أو نزّلها بنفسك — "
  echo "النسخة على قرص الخادم وحده لا تحميك من تلف القرص."
fi
