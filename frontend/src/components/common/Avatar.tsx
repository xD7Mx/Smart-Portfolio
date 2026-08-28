import React, { useEffect, useState } from "react";
import { Briefcase } from "lucide-react";
import { api } from "../../services/api";

/**
 * الصورة الرمزية — تُجلب كـblob عبر axios (نفس الطريقة المثبتة في المكتبة
 * لأغلفة الكتب) ثم تُعرض كـObject URL. الجلب المباشر بـ<img src> كان يفشل
 * أحيانًا بسبب تخزين المتصفح للـ404 القديم؛ هذه الطريقة تتجنّبه تمامًا.
 * الرمز الافتراضي حين لا توجد صورة: أيقونة المحفظة (كنمط ماك).
 */
export function AvatarImg({ refreshKey = 0, className = "", iconSize = 30 }: {
  refreshKey?: number | string;
  className?: string;
  iconSize?: number;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    let obj: string | null = null;
    setFailed(false);
    api.get("/settings/avatar", { responseType: "blob" })
      .then((r) => {
        if (!alive) return;
        obj = URL.createObjectURL(r.data as Blob);
        setUrl(obj);
      })
      .catch(() => { if (alive) { setFailed(true); setUrl(null); } });
    return () => { alive = false; if (obj) URL.revokeObjectURL(obj); };
  }, [refreshKey]);

  if (url && !failed) {
    return <img src={url} alt="" className={"w-full h-full object-cover " + className} />;
  }
  return <Briefcase size={iconSize} className="text-[var(--brand)]" />;
}

/** الشخصيات الجاهزة — صور المستخدم نفسها (انظر presetAvatars.ts). */
export { PRESET_AVATARS } from "./presetAvatars";
export type { Preset } from "./presetAvatars";

/** يحوّل شخصية (SVG data-URI) إلى PNG blob عبر canvas، لرفعها كصورة عادية
 * (المخزَّن يجب أن يكون صورة نقطية كي يخدمها الخادم ويعرضها المتصفح). */
export function presetToPngBlob(url: string, size = 640): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const c = document.createElement("canvas");
      c.width = size; c.height = size;
      const ctx = c.getContext("2d");
      if (!ctx) { reject(new Error("no ctx")); return; }
      ctx.drawImage(img, 0, 0, size, size);
      c.toBlob((b) => b ? resolve(b) : reject(new Error("toBlob failed")), "image/png");
    };
    img.onerror = () => reject(new Error("svg load failed"));
    img.src = url;
  });
}
