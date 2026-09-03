import React from "react";
import clsx from "clsx";
import { TrendingUp, TrendingDown, Minus, MoonStar, Circle } from "lucide-react";

// ── Sharia badge — green (pure) / orange (mixed) / red (non-compliant) crescent ──
export function ShariaBadge({ status, size = 13 }: { status?: string | null; size?: number }) {
  if (status === "COMPLIANT") {
    return <span className="shrink-0 inline-flex" title="نقية — متوافقة شرعياً"><MoonStar size={size} className="text-[var(--pos-ink)]" /></span>;
  }
  if (status === "MIXED") {
    /* الرمزُ نفسُه الذي تستعمله البطاقةُ الكبرى — فلا يختلف لونُ الحكم
       الشرعيّ باختلاف موضعه في التطبيق. */
    return <span className="shrink-0 inline-flex" title="مختلطة — متوافقة بشرط التطهير"><MoonStar size={size} className="text-[var(--sharia-mixed)]" /></span>;
  }
  if (status === "NON_COMPLIANT") {
    return <span className="shrink-0 inline-flex" title="غير متوافقة شرعياً"><MoonStar size={size} className="text-[var(--neg-ink)]" /></span>;
  }
  return null;
}

// ── Sharia indicator — green (نقية) / orange (مختلطة) / red (non) / gray (unknown) ──
export function ShariaStatusIndicator({ status, loading, purification, source }:
  { status?: string | null; loading?: boolean; purification?: number | null; source?: string | null }) {
  /* ══ ثلاثةُ ألوانٍ لثلاث حالات ══ (بأمر المالك)
     شرعيٌّ أخضر · مختلطٌ برتقاليّ · غيرُ شرعيٍّ أحمر. والألوانُ رموزٌ
     من `globals.css` تُعرَّف في المظهرين معاً، فلا قيمةَ مكتوبةً هنا.
     و«مختلط» كان بلا نصّ — أيقونةٌ ملوّنةٌ بلا كلمة، فيُقرأ اللونُ ولا
     يُعرف معناه. فصار له اسمُه كأختَيه. */
  const map: Record<string, { icon: any; color: string; bg: string; label: string }> = {
    COMPLIANT:     { icon: MoonStar, color: "var(--pos-ink)", bg: "transparent", label: "متوافق شرعياً (نقي)" },
    MIXED:         { icon: MoonStar, color: "var(--sharia-mixed)", bg: "transparent", label: "مختلط" },
    NON_COMPLIANT: { icon: MoonStar, color: "var(--neg-ink)", bg: "transparent",  label: "غير متوافق شرعياً" },
  };
  const s = status && map[status] ? map[status]
    : { icon: Circle, color: "var(--ink-muted)", bg: "transparent", label: loading ? "جارٍ التحقق…" : "التوافق الشرعي غير محدد" };
  const Icon = s.icon;
  const showPurif = (status === "COMPLIANT" || status === "MIXED") && purification != null;
  return (
    <div className="flex items-center gap-2.5 rounded-xl px-3 py-2 flex-wrap" style={{ background: s.bg }}>
      <Icon size={18} style={{ color: s.color }} className={loading ? "animate-pulse" : ""} />
      {s.label && <span className="text-sm font-bold" style={{ color: s.color }}>{s.label}</span>}
      {showPurif && (
        <span className="text-xs font-semibold px-2 py-0.5 rounded-lg mr-1" style={{ color: s.color, background: "transparent" }}>
          تطهير {purification!.toFixed(2)} ريال/سهم
        </span>
      )}
      {source && <span className="text-[11px] text-[var(--ink-muted)] ms-auto">المصدر: {source}</span>}
    </div>
  );
}

// ── Card ────────────────────────────────────────────────────
interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  action?: React.ReactNode;
}

export function Card({ children, className, title, action }: CardProps) {
  return (
    <div className={clsx("card fade-in", className)}>
      {(title || action) && (
        <div className="flex items-center justify-between mb-4">
          {title && <h3 className="font-semibold text-sm text-[var(--ink-muted)] uppercase tracking-wider">{title}</h3>}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

// ── MetricCard ───────────────────────────────────────────────
interface MetricCardProps {
  label: string;
  value: string | number;
  sub?: string;
  change?: number;
  icon?: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export function MetricCard({ label, value, sub, change, icon, className, onClick }: MetricCardProps) {
  const isPositive = change !== undefined && change > 0;
  const isNegative = change !== undefined && change < 0;

  return (
    <div
      className={clsx("card cursor-pointer hover:border-[var(--brand)] transition-colors", className)}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-[var(--ink-muted)] uppercase tracking-wider mb-1">{label}</p>
          <p className="text-2xl font-bold truncate">{value}</p>
          {sub && <p className="text-xs text-[var(--ink-muted)] mt-1">{sub}</p>}
        </div>
        {icon && (
          <div className="ml-3 p-2 rounded-lg text-[var(--brand-ink)] shrink-0">
            {icon}
          </div>
        )}
      </div>

      {change !== undefined && (
        <div className={clsx(
          "flex items-center gap-1 mt-3 text-sm font-medium",
          isPositive ? "text-[var(--pos-ink)]" : isNegative ? "text-[var(--neg-ink)]" : "text-[var(--ink-muted)]"
        )}>
          {isPositive ? <TrendingUp size={14} /> : isNegative ? <TrendingDown size={14} /> : <Minus size={14} />}
          <span>{change > 0 ? "+" : ""}{change.toFixed(2)}%</span>
        </div>
      )}
    </div>
  );
}

// ── Badge ────────────────────────────────────────────────────
type BadgeVariant = "default" | "success" | "danger" | "warning" | "info" | "neutral";

const BADGE_STYLES: Record<BadgeVariant, string> = {
  default: "bg-[var(--surface)] text-[var(--ink)]",
  success: " text-[var(--pos-ink)]",
  danger:  " text-[var(--neg-ink)]",
  warning: " text-[var(--warn-ink)]",
  info:    " text-[var(--brand-ink)]",
  neutral: "bg-[var(--surface)] text-[var(--ink-muted)]",
};

export function Badge({ label, variant = "default" }: { label: string; variant?: BadgeVariant }) {
  return (
    <span className={clsx("inline-flex items-center px-2 py-0.5 rounded text-xs font-medium", BADGE_STYLES[variant])}>
      {label}
    </span>
  );
}

// ── SkeletonCard ─────────────────────────────────────────────
export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card space-y-3">
      <div className="skeleton h-4 w-24" />
      <div className="skeleton h-8 w-32" />
      {Array.from({ length: lines - 2 }).map((_, i) => (
        <div key={i} className="skeleton h-3 w-full" />
      ))}
    </div>
  );
}

// ── EmptyState ───────────────────────────────────────────────
export function EmptyState({ icon, title, description, action }: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <div className="mb-4 text-[var(--ink-muted)]">{icon}</div>}
      <h3 className="text-base font-semibold text-[var(--ink)] mb-1">{title}</h3>
      {description && <p className="text-sm text-[var(--ink-muted)] mb-4 max-w-xs">{description}</p>}
      {action}
    </div>
  );
}

// ── Button ───────────────────────────────────────────────────
type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

const BTN_STYLES: Record<ButtonVariant, string> = {
  primary:   "bg-[var(--brand)] hover:bg-[var(--brand)] text-[var(--ink)]",
  secondary: "bg-[var(--surface)] hover:bg-[var(--ink-muted)] text-[var(--ink)]",
  danger:    "bg-[var(--neg-ink)] hover:bg-[var(--neg-ink)] text-[var(--ink)]",
  ghost:     "text-[var(--ink-muted)] hover:text-[var(--ink)] hover:bg-[var(--surface)]",
};

export function Button({ children, variant = "primary", className, size = "md", ...props }: {
  children: React.ReactNode;
  variant?: ButtonVariant;
  className?: string;
  size?: "sm" | "md" | "lg";
  [key: string]: any;
}) {
  const sizes = { sm: "px-3 py-1.5 text-xs", md: "px-4 py-2 text-sm", lg: "px-6 py-2.5 text-base" };
  return (
    <button
      className={clsx(
        "inline-flex items-center gap-2 rounded-lg font-medium transition-colors disabled:opacity-50",
        BTN_STYLES[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

// ── Progress Bar ─────────────────────────────────────────────
export function ProgressBar({ value, max = 100, color = "blue", label }: {
  value: number;
  max?: number;
  color?: "blue" | "green" | "amber" | "red";
  label?: string;
}) {
  const pct = Math.min((value / max) * 100, 100);
  const colors = { blue: "bg-[var(--brand)]", green: "bg-[var(--pos-ink)]", amber: "bg-[var(--warn-ink)]", red: "bg-[var(--neg-ink)]" };

  return (
    <div>
      {label && (
        <div className="flex justify-between text-xs text-[var(--ink-muted)] mb-1">
          <span>{label}</span>
          <span>{pct.toFixed(1)}%</span>
        </div>
      )}
      <div className="h-2 rounded-full bg-[var(--surface)] overflow-hidden">
        <div
          className={clsx("h-full rounded-full transition-all duration-500", colors[color])}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/* ── حقل رقمي — مصدرٌ واحد لكل إدخال رقمي في التطبيق ────────────────────
   يحلّ عِلّتين كانتا متفرّقتين:

   ① الأرقام الهندية: `type="number"` يفرض على أجهزة اللغة العربية لوحةً
      بأرقام ٠-٩ الهندية، والمتصفّح يرفضها كقيمة رقمية فيُفرَّغ الحقل — فيبدو
      أن الكتابة «توقّفت فجأة». والعلاج المُجرَّب في هذا التطبيق (بطاقة التوزيع
      النسبي والحاسبات) هو text + inputMode=decimal مع تحويل أي رقم هندي إلى
      لاتيني فور كتابته. كان مطبَّقاً في ٢١ حقلاً وغائباً عن ١٩ — فنفس الإدخال
      يسلك سلوكين حسب الشاشة التي أنت فيها.

   ② تعريف المكوّن داخل دالة العرض: كل إعادة رسمٍ تُنشئ نوعاً جديداً، فيُفكّك
      React الحقل ويُعيد بناءه ويضيع التركيز بعد كل حرف. ولهذا يجب أن يبقى
      هذا المكوّن هنا في المستوى الأعلى، لا داخل أي دالة.

   يقبل النقطة والفاصلة العربية (٫) كفاصلٍ عشري، ويمنع ما عدا الأرقام. */
const AR_INDIC = /[٠-٩]/g, EXT_INDIC = /[۰-۹]/g;

export function toLatinDigits(v: string): string {
  return (v || "")
    .replace(AR_INDIC, d => String(d.charCodeAt(0) - 0x0660))
    .replace(EXT_INDIC, d => String(d.charCodeAt(0) - 0x06F0))
    .replace(/[٫،]/g, ".");
}

export function NumInput({
  value, onChange, allowDecimal = true, className = "input", ...rest
}: {
  value: string;
  onChange: (v: string) => void;
  allowDecimal?: boolean;
  className?: string;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "type">) {
  return (
    <input
      {...rest}
      className={className}
      type="text"
      inputMode={allowDecimal ? "decimal" : "numeric"}
      lang="en"
      dir="ltr"
      value={value}
      onChange={e => {
        let v = toLatinDigits(e.target.value).replace(allowDecimal ? /[^\d.]/g : /[^\d]/g, "");
        if (allowDecimal) {
          const i = v.indexOf(".");                    // نقطة عشرية واحدة فقط
          if (i !== -1) v = v.slice(0, i + 1) + v.slice(i + 1).replace(/\./g, "");
        }
        onChange(v);
      }}
    />
  );
}
