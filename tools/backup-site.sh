#!/usr/bin/env bash
# نسخة الكود بلا بيانات وبلا أسرار.
#
# سبب وجوده: النمط `--exclude='./.env'` لا يطابق `.env.save` ولا `.env.swp`
# ولا `.env.bak` — وهي ملفات يُنشئها المحرّر تلقائياً وتحمل الأسرار كاملةً.
# وقعت الحادثة فعلاً: أرشيفٌ ضمّهما فتسرّبت كلمة قاعدة البيانات ومفاتيح
# الذكاء وتوكن تيليجرام وسرّ الجلسات. هذا السكربت يقفل النمط كلّه.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-$HOME/current-site-$(date +%F).tar.gz}"

tar czf "$OUT" \
  --exclude='./.env' --exclude='./.env.*' --exclude='*/.env' --exclude='*/.env.*' \
  --exclude='*.swp' --exclude='*.swo' --exclude='*.save' --exclude='*.bak' --exclude='*~' \
  --exclude='./.git' --exclude='*/node_modules' --exclude='*/__pycache__' \
  --exclude='*/.vault' --exclude='./docker/ssl' \
  --exclude='./data' --exclude='./backups' --exclude='./storage' --exclude='./logs' \
  --exclude='*/frontend/build' \
  .

echo "الحجم: $(du -h "$OUT" | cut -f1)"
echo "— تحقّق أنّ الأرشيف نظيف:"
if tar tzf "$OUT" | grep -Ei '\.env|\.vault|ssl/|\.swp$|\.save$' ; then
  echo "!! تحذير: الأرشيف يحتوي ملفات حسّاسة — لا ترفعه." >&2
  exit 1
fi
echo "نظيف: لا أسرار داخل الأرشيف."
