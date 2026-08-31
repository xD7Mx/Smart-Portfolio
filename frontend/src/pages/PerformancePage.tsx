/* قياس الأداء — عدّادٌ واحد وبطاقاتُ إنتاج.

   القاعدة الحاكمة: **رقمٌ واحد للربح** (نموّ رأس المال) هو نفسه المعروض في
   باند الثروة والأهداف — رقمٌ في ثلاثة مواضع لا ثلاثة أرقام متقاربة يتنازعها
   القارئ. وكل بطاقةٍ أخرى تُعلن إنتاجها هي بمبلغٍ صريح، بلا نسبةٍ ولا اسمٍ
   يوهم بأنها «عائد»، فلا تُجمع ولا تُقارن بالعدّاد.

   وحُذفت DPI وTVPI والمحصول واسترداد رأس المال: بسطُها يحوي **رأس المال
   العائد** لا الربح، فتظهر أكبر من الربح دائماً وتُقرأ إنجازاً وهي ليست كذلك
   — وهو ما جعل مالكاً يتوقّع أرباحاً كبيرة ثم يجدها عُشر ما ظنّ.

   وحُذف TWR وأقصى التراجع: يحتاجان تسجيلاً يومياً متّصلاً وتفسيراً في كل
   مرّة، ولا يغيّران قراراً في محفظةٍ تُدار بالضخّ الشهري.

   وفحص السلامة لم يُلغَ بل صار صامتاً: يعمل في الخلفية ولا يظهر إلا حين
   ينكسر شيءٌ فعلاً — المعيار لا يُطلَب من المالك أن يضغط زرّه.
*/
import { useQuery } from "@tanstack/react-query";
import { Coins, Scissors, Gift, PieChart, Target } from "lucide-react";
import { portfolioApi } from "../services/api";

const fmt = (n: number | null | undefined, d = 0) =>
  n == null ? "—" : Number(n).toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d });

function Card({ icon: Icon, title, children }: any) {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-2.5">
        <Icon size={15} className="text-cyan-400" />
        <h2 className="card-title">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function Big({ value, color, suffix = "" }: { value: string; color?: string; suffix?: string }) {
  return (
    <div className="text-3xl font-extrabold tabular-nums" dir="ltr" style={{ color: color || "var(--fg-strong)" }}>
      {value}<span className="text-lg">{suffix}</span>
    </div>
  );
}

/* المقام — السطر الذي يمنع الرقم من أن يكون ادّعاءً. */
function Denom({ children }: any) {
  return <p className="text-[11px] text-slate-500 mt-1.5 leading-relaxed">{children}</p>;
}

/* `embedded` حين يُعرض القسم داخل لوحة التحكم: تُسقَط حاشية الصفحة وعنوانها
   لأن التبويب نفسه صار هو العنوان. والمحتوى واحدٌ لا نسختان. */
export default function PerformancePage({ embedded = false }: { embedded?: boolean }) {
  const { data: p } = useQuery({
    queryKey: ["portfolio-performance"],
    queryFn: () => portfolioApi.performance().then((r: any) => r.data.data),
    retry: 0,
  });
  const { data: s, isLoading } = useQuery({
    queryKey: ["portfolio-summary"],
    queryFn: () => portfolioApi.summary().then((r: any) => r.data.data),
    retry: 0,
  });

  if (isLoading) return <div className="p-4 text-slate-400 text-sm">جارٍ الحساب…</div>;
  if (!s) return <div className="p-4 text-slate-400 text-sm">تعذّر حساب مقاييس الأداء.</div>;

  const growth: number | null = s.capital_growth_pct ?? null;
  const netProfit: number | null = s.net_profit ?? null;
  const costBasis: number = s.total_cost ?? 0;
  const dividends: number = s.dividends_received ?? 0;
  const saleGains: number = s.sale_gains ?? 0;
  const con = p?.concentration || {};
  const bonus = p?.bonus || {};

  return (
    <div className={embedded ? "space-y-3" : "space-y-3 p-3 md:p-4"}>
      {!embedded && <h1 className="text-lg font-bold text-white">قياس الأداء</h1>}

      {growth != null && (
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Target size={15} className="text-emerald-400" />
            <h2 className="card-title">نموّ رأس المال</h2>
            <span className="mr-auto text-lg font-extrabold tabular-nums" dir="ltr"
              style={{ color: growth >= 0 ? "var(--pos-ink)" : "var(--neg-ink)" }}>
              {(growth >= 0 ? "+" : "") + fmt(growth, 2)}%
            </span>
          </div>
          {/* الشريط يمتلئ نحو ١٠٠٪ — مضاعفة رأس المال. والقصّ عند الطرفين
              يمنع شريطاً يفيض أو يختفي، والرقم فوقه يبقى غير مقصوص. */}
          <div className="h-2.5 rounded-full overflow-hidden" style={{ background: "rgba(148,163,184,.15)" }}>
            <div className="h-full rounded-full transition-all"
              style={{ width: `${Math.min(100, Math.max(0, growth))}%`,
                       background: "linear-gradient(90deg,var(--pos-fill),var(--pos-ink))" }} />
          </div>
          <Denom>صافي الربح {fmt(netProfit)} ÷ إجمالي المدفوع {fmt(costBasis)}</Denom>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Card icon={Coins} title="التوزيعات">
          <Big value={fmt(dividends)} color="var(--pos-ink)" />
          <Denom>نقدٌ دخل حسابك من الشركات</Denom>
        </Card>

        {/* ربح التصفية وحده لا حصيلتها: الحصيلة تحوي رأس مالك العائد، وعرضها
            هنا يُعيد الخطأ الذي حُذف من أجله DPI. */}
        <Card icon={Scissors} title="التصفية">
          <Big value={fmt(saleGains)} color={saleGains >= 0 ? "var(--pos-ink)" : "var(--neg-ink)"} />
          <Denom>ربح عمليات البيع — دون رأس المال العائد</Denom>
        </Card>

        {bonus?.shares > 0 && (
          <Card icon={Gift} title="أسهم المنحة">
            <Big value={fmt(bonus.shares)} />
            <Denom>قيمتها السوقية {fmt(bonus.market_value)} — ضمن قيمة مراكزك</Denom>
          </Card>
        )}

        {con?.top3_pct != null && (
          <Card icon={PieChart} title="التركّز">
            <Big value={fmt(con.top3_pct, 1)} suffix="%"
              color={con.top3_pct > 60 ? "var(--warn-ink)" : "var(--fg-strong)"} />
            <Denom>
              نصيب أكبر ثلاثة مراكز
              {con.top1_name && <> · الأكبر {con.top1_name} {fmt(con.top1_pct, 1)}%</>}
            </Denom>
          </Card>
        )}
      </div>
    </div>
  );
}
