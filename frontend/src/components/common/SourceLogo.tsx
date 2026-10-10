import React, { useState } from "react";
import Logo from "./Logo";
import { matchSource } from "../../data/newsSources";

/**
 * Outlet (newspaper/agency) logo for the approved news-sources registry —
 * the unified news design language's second identity tier: a headline shows
 * its company's logo when tied to one, else its outlet's logo from here.
 *
 * Fallback chain (same convention as CompanyLogo, real domains only):
 *  1. Clearbit logo for the outlet's registered domain.
 *  2. Google favicon service for the same domain.
 *  3. The app's own mark — never a broken image, never an empty slot.
 *
 * ‏D667 (بأمر المالك: «شعارُ الشركة أوّلاً، وإن لم يوجد — بدلاً من أن يكون فراغاً — ضع شعارَ التطبيق»): كان المصدرُ
 * غيرُ المسجَّل يُرجع لا شيء فيبقى مكانُ الشعار فارغاً، والمتعذّرُ أيقونةَ صحيفةٍ رمادية.
 */
export default function SourceLogo({ source, size = 30 }: { source?: string | null; size?: number }) {
  const entry = matchSource(source);
  const [stage, setStage] = useState<number>(0);
  if (!entry) return <Logo size={size} flat />;
  // Candidate chain: an explicit `logo` URL first (when set), then the
  // domain-derived Clearbit logo, then the domain favicon, then a neutral tile.
  const candidates = [
    entry.logo,
    `https://logo.clearbit.com/${entry.domain}`,
    `https://www.google.com/s2/favicons?domain=${entry.domain}&sz=64`,
  ].filter(Boolean) as string[];
  const url = candidates[stage];
  if (stage < candidates.length) {
    return (
      <img
        src={url}
        alt={entry.name_ar}
        width={size}
        height={size}
        onError={() => setStage(s => s + 1)}
        onLoad={e => {
          const img = e.currentTarget;
          if (img.naturalWidth <= 2 || img.naturalHeight <= 2) setStage(s => s + 1);
        }}
        className="rounded-lg object-contain bg-white/90 p-0.5 shrink-0"
        style={{ width: size, height: size }}
        loading="lazy"
      />
    );
  }
  return <Logo size={size} flat />;
}

/** True when this source label belongs to the approved outlets registry. */
export function hasSourceLogo(source?: string | null): boolean {
  return !!matchSource(source);
}
