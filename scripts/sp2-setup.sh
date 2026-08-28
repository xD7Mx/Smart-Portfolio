#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# إنشاء النسخة الثانية المستقلة (Smart-Portfolio-2) دفعة واحدة.
# نسخة معزولة كاملة على نفس السيرفر: حاويات sp2_*، منافذ 8080/8443/8001/3001/5433،
# قاعدة بيانات خاصة، كلمة مرور وسر JWT جديدان. لا تمسّ النسخة الأصل بحرف.
#
# الاستخدام:
#   bash ~/Smart-Portfolio/scripts/sp2-setup.sh 'كلمة_مرور_الشخص_الآخر'
#   (بدون وسيط: تُولَّد كلمة مرور عشوائية وتُطبع في النهاية)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SRC=~/Smart-Portfolio
DST=~/Smart-Portfolio-2
NEW_PASSWORD="${1:-$(openssl rand -hex 8)}"

[ -d "$SRC" ] || { echo "✗ لا يوجد $SRC"; exit 1; }
[ -e "$DST" ] && { echo "✗ $DST موجود مسبقاً — احذفه أولاً إن أردت إعادة الإنشاء:"; echo "  cd $DST && docker compose down -v; cd ~ && rm -rf $DST"; exit 1; }

echo "◆ 1/5 نسخ المشروع (بدون سجلات وبيانات التشغيل)…"
mkdir -p "$DST"
# tar موجود في كل نظام (بخلاف rsync): نستثني ما يخص تشغيل النسخة الأصل —
# النسخة الثانية تبدأ نظيفة، مع الإبقاء على backups/ كي تُستعاد منها المحفظة
# كنقطة بداية إن رغب صاحبها.
(cd "$SRC" && tar cf - \
    --exclude='./logs' --exclude='./storage' --exclude='./data' \
    --exclude='__pycache__' --exclude='node_modules' \
    --exclude='./frontend/build' --exclude='./backend/lastgood.json' \
    .) | (cd "$DST" && tar xf -)

echo "◆ 2/5 تعديل أسماء الحاويات والمنافذ ووسم النسخة (B)…"
# وسم النسخة يُقلب داخل compose نفسه (بنية تحتية، لا .env) ضمن إعادة التسمية
# الجوهرية — فلا يختلف مستقبلاً ولا يعتمد على أمر يدوي.
sed -i 's/sp_/sp2_/g;
        s/- SP_COPY=A/- SP_COPY=B/;
        s/"5432:5432"/"5433:5432"/;
        s/"8000:8000"/"8001:8000"/;
        s/"3000:3000"/"3001:3000"/;
        s/"80:80"/"8080:80"/;
        s/"443:443"/"8443:443"/' "$DST/docker-compose.yml"

echo "◆ 3/5 عزل الاعتماد: كلمة مرور وسرّ JWT جديدان…"
NEW_SECRET=$(openssl rand -hex 32)
NEW_JWT=$(openssl rand -hex 32)
set_env() {  # يستبدل السطر إن وُجد وإلا يضيفه — يعمل مهما كان شكل .env الحالي
  local key="$1" val="$2" file="$DST/.env"
  if grep -q "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$file"
  else
    echo "${key}=${val}" >> "$file"
  fi
}
set_env APP_PASSWORD "$NEW_PASSWORD"
set_env SECRET_KEY  "$NEW_SECRET"
set_env JWT_SECRET  "$NEW_JWT"
# SP_COPY لم يعد في .env — صار في صميم docker-compose.yml (أعلاه) كي لا يختلف.

echo "◆ 3.5/5 شعار النسخة الثانية (نفس الأبراج، الخلفية مقلوبة: بنفسجي فوق وأزرق تحت)…"
# هوية الأبراج ثابتة؛ يتميّز B بقلب تدرّج الخلفية فقط. يُوحَّد على كل الأصعدة:
# أيقونة التطبيق (PWA/أندرويد)، أيقونة آبل (آيفون/آيباد/ماك)، وfavicon المتصفح.
ICO="$DST/frontend/public/icons"
if [ -d "$ICO/b" ]; then
  cp -f "$ICO/b/icon-192.png"        "$ICO/icon-192.png"
  cp -f "$ICO/b/icon-512.png"        "$ICO/icon-512.png"
  cp -f "$ICO/b/apple-touch-icon.png" "$ICO/apple-touch-icon.png"
  [ -f "$ICO/b/source.svg" ] && cp -f "$ICO/b/source.svg" "$ICO/source.svg"
  # favicon: قلب لوني التدرّج (تبديل متبادل عبر قيمة مؤقتة كي لا يتضاعف الاستبدال)
  sed -i "s|stop-color='%232563eb'|stop-color='%23TMPSWAP'|;
          s|stop-color='%239b34e6'|stop-color='%232563eb'|;
          s|stop-color='%23TMPSWAP'|stop-color='%239b34e6'|" \
        "$DST/frontend/index.html"
fi

echo "◆ 4/5 بناء وتشغيل الحزمة الثانية…"
cd "$DST"
docker compose up -d --build

echo "◆ 5/5 التحقق من الإقلاع…"
sleep 8
docker compose ps --format 'table {{.Name}}\t{{.Status}}' | sed 's/^/   /'

IP=$(curl -s --max-time 5 ifconfig.me || hostname -I | awk '{print $1}')
echo ""
echo "════════════════════════════════════════════════════"
echo "✓ النسخة الثانية جاهزة"
echo "  الرابط:        http://${IP}:8080"
echo "  كلمة المرور:   ${NEW_PASSWORD}"
echo "  قاعدة البيانات: مستقلة تماماً (لن تمسّ نسختك الأصل)"
echo "  لاستنساخ محفظتك كنقطة بداية: الإعدادات ← النسخ الاحتياطي ← استعادة"
echo "════════════════════════════════════════════════════"
