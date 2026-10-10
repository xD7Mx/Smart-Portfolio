import React from "react";
import CompanyLogo from "./CompanyLogo";
import Logo from "./Logo";
import { lookupCompany } from "../../data/saudiCompanies";

/* ══ بطاقةُ الحدث الموحّدة (D666) ══ (بأمر المالك: «الشكلُ الجماليّ والتصميمُ الموحّد للتطبيق ميزةٌ لنا»)
   مكوّنٌ واحدٌ لا نسخٌ متطابقةٌ اليومَ تتباعد غداً: المفكرةُ والإفصاحات والأحداثُ الجوهرية والتوقعات كلُّها هذه
   البطاقة — الشعارُ يميناً، ثمّ الوسمُ رقعةً صلبةً بحبرٍ أسود (‏--tag-*)، ثمّ الاسمُ والرمز، ثمّ العنوانُ سطراً رئيسياً
   ينتهي بتاريخه، وسطرُ أرقامٍ صغيرٌ حين يكون للبند رقم. وتعمل في الجوال كما في الحاسوب: لا عرضَ ثابتاً، والنصُّ
   ينكمش (‏min-w-0) ولا يدفع الصفَّ إلى التمرير. */
export type CardTag = { label: string; bg: string; fg?: string };

export const fmtCardDate = (d?: string | null) =>
  d ? new Date(d).toLocaleDateString("ar-SA-u-ca-gregory-nu-latn", { day: "2-digit", month: "2-digit", year: "numeric" }) : "—";

export default function EventCard({ symbol, name, tag, title, date, meta, href, onClick }: {
  symbol?: string | null; name?: string | null; tag: CardTag; title: React.ReactNode; date?: string | null;
  meta?: React.ReactNode; href?: string | null; onClick?: () => void;
}) {
  const nm = name || (symbol ? lookupCompany(symbol)?.name_ar : null);
  const body = (
    <div className="event-item flex items-center gap-3 p-2.5 rounded-xl transition-colors">
      {/* ‏D667: بندٌ لا شركةَ له (تقريرٌ اقتصاديّ · إعلانٌ عامّ) تملأ علامةُ التطبيق مكانَ شعاره — لا فراغَ يكسر المحاذاة */}
      <span className="shrink-0">{symbol ? <CompanyLogo symbol={symbol} size={32} /> : <Logo size={32} flat />}</span>
      <div className="min-w-0 flex-1 space-y-1">
        <span className="ev-tag inline-block" style={{ background: tag.bg, color: tag.fg || "var(--tag-ink)" }}>{tag.label}</span>
        {(nm || symbol) && (
          <div className="flex items-center gap-2 flex-wrap min-w-0">
            {nm && <span className="text-[var(--ink-muted)] text-[12px] font-semibold truncate">{nm}</span>}
            {symbol && <span className="tag-b shrink-0" style={{ fontSize: 10 }}>{symbol}</span>}
          </div>
        )}
        <div className="flex items-baseline gap-2">
          <p className="flex-1 min-w-0 text-[var(--ink)] text-[13px] font-semibold leading-snug">{title}</p>
          <span className="shrink-0 text-[var(--ink-muted)] text-[11px] tabular-nums">{fmtCardDate(date)}</span>
        </div>
        {meta ? <div className="flex items-center gap-x-2 gap-y-0.5 flex-wrap text-[11px] text-[var(--ink-muted)]">{meta}</div> : null}
      </div>
    </div>
  );
  const cls = "w-full text-start block min-h-[32px] active:scale-[.995] transition-transform";
  if (href) return <a href={href} target="_blank" rel="noopener noreferrer" className={cls}>{body}</a>;
  if (onClick) return <button onClick={onClick} className={cls}>{body}</button>;
  return <div className={cls}>{body}</div>;
}
