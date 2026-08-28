#!/usr/bin/env bash
# تنظيف دوري آمن لكاش/نفايات Docker — يمنع تراكم كاش البناء الذي التهم القرص.
# آمن تماماً: يحذف كاش البناء غير المستخدَم والصور المعلّقة (بلا وسم) فقط —
# لا يمسّ الحاويات العاملة ولا الصور المستخدَمة ولا أي بيانات (قواعد/مكتبة/نسخ).
#
# كاش البناء لا يتراكم إلا عند البناء (build)، فالتنظيف اليومي يكفي لتغطية أي
# بناء خلال 24 ساعة — التشغيل الأكثر تواتراً بلا فائدة (لا جديد ليُنظَّف).
# التركيب مرّة واحدة (كرون يومي، 04:00):
#   chmod +x ~/Smart-Portfolio/scripts/docker-cleanup.sh
#   ( crontab -l 2>/dev/null | grep -v docker-cleanup.sh ; \
#     echo "0 4 * * * $HOME/Smart-Portfolio/scripts/docker-cleanup.sh" ) | crontab -
#
# فحص السجل لاحقاً:  tail -n 40 ~/docker-cleanup.log

set -euo pipefail
LOG="${DOCKER_CLEANUP_LOG:-$HOME/docker-cleanup.log}"

{
  echo "==== $(date '+%Y-%m-%d %H:%M:%S') — بدء التنظيف ===="
  echo "-- قبل --"
  df -h / | awk 'NR==1 || /\/$/'
  docker system df 2>/dev/null || true

  # كاش البناء غير المستخدَم (السبب الرئيسي للتضخّم) + الصور المعلّقة فقط.
  docker builder prune -f
  docker image prune -f

  echo "-- بعد --"
  df -h / | awk 'NR==1 || /\/$/'
  echo "==== انتهى ===="
  echo
} >> "$LOG" 2>&1

# إبقاء آخر ~500 سطر فقط من السجل كي لا يكبر.
if [ -f "$LOG" ]; then
  tail -n 500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
