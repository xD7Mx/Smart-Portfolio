import React from "react";
import { useQuery } from "@tanstack/react-query";
import { marketApi } from "../../services/api";
import clsx from "clsx";

/* تاريخُ الإقفال بصيغة التطبيق نفسها (يوم/شهر/سنة) — هي المستعملة في
   سجلّ العمليات والتوزيعات والمفكرة، فلا تتعدّد الصيغ في تطبيقٍ واحد. */
const closeDate = (a?: string | null) =>
  a && a.length >= 10 ? `${a.slice(8, 10)}/${a.slice(5, 7)}/${a.slice(0, 4)}` : null;

const compact = (n: number) => {
  if (n == null) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
};

/* صيغةٌ قصيرة للبطاقات على الجوّال وحدها. الجدولُ العريض يُبقي الرقم
   كاملاً — فيه متّسع، والدقّةُ الكاملة مقصودةٌ هناك. أمّا ثلثُ عرضِ
   390px فلا يسع «3,600,000,000» مقروءاً، ورقمٌ لا يُقرأ ليس دقّة. */
const brief = (n: number) => {
  if (n == null) return "—";
  const a = Math.abs(n);
  const f = (x: number) => x.toLocaleString("en-US", { maximumFractionDigits: a >= 1e9 ? 2 : 1 });
  if (a >= 1e9) return f(n / 1e9) + " مليار";
  if (a >= 1e6) return f(n / 1e6) + " مليون";
  if (a >= 1e3) return f(n / 1e3) + " ألف";
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
};

/* Traffic-light dot like the reference report: green good, amber caution, red bad */
function Light({ change, invert = false }: { change: number | null; invert?: boolean }) {
  if (change == null) return <span className="text-[var(--ink-muted)] text-xs">—</span>;
  const good = invert ? change <= 0 : change >= 0;
  const strong = Math.abs(change) >= 5;
  const color = good ? (strong ? "var(--pos-ink)" : "var(--pos-ink)") : (strong ? "var(--neg-ink)" : "var(--warn-ink)");
  return (
    <span className="inline-flex items-center gap-1.5 text-xs" style={{ color }}>
      <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
      {(change >= 0 ? "+" : "") + change.toFixed(1)}%
    </span>
  );
}

/**
 * Three-year financial statement table (نمو / ربحية / ملاءة / تدفقات) with a
 * YoY change traffic light and an automatic AI verdict — the governance report.
 * Fully auto-filled from the source; no manual entry.
 */
export default function FinancialsTable({ symbol }: { symbol: string }) {
  /* ══ سنويٌّ وربعيّ — خياران ══ (بأمر المالك · D259)
     كان المُبدِّلُ قد أُزيل لأن الربعيَّ يخرج فارغاً من ياهو: «مُبدِّلٌ
     يقود إلى فراغٍ أسوأُ من غيابه». وقد زال سببُ الإزالة لا القاعدة —
     صار للربعيّ مصدرٌ رسميّ (‏تداول ثمّ أرقام)، فعاد الخياران.
     ومصدرُ ما يُعرض معلَنٌ مع الجدول: لا يُخلط مصدران بلا بيان. */
  const [freq, setFreq] = React.useState<"annual" | "quarterly">("annual");
  const { data, isLoading } = useQuery({
    queryKey: ["financials", symbol, freq],
    queryFn: () => marketApi.financials(symbol, freq).then(r => r.data.data),
    enabled: !!symbol,
    retry: 0,
  });

  const Switch = () => (
    <div className="flex items-center gap-1 shrink-0" role="group" aria-label="دورية القوائم">
      {([["annual", "سنوي"], ["quarterly", "ربع سنوي"]] as const).map(([k, label]) => (
        <button key={k} type="button" onClick={() => setFreq(k)}
                aria-pressed={freq === k}
                className="text-[11px] font-bold rounded-lg px-2.5 py-1"
                style={{
                  background: freq === k ? "var(--tag-agm)" : "var(--field)",
                  color: freq === k ? "var(--tag-ink)" : "var(--ink-muted)",
                }}>
          {label}
        </button>
      ))}
    </div>
  );

  if (isLoading) return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="card-title">البيانات المالية</h3><Switch />
      </div>
      <div className="h-40 skeleton" />
    </div>
  );
  /* ══ الخيارُ يبقى ولو خلا الجدول ══
     شاشةٌ تُبدَّل فتختفي أزرارُها تحبس المستخدمَ في الفرع الفارغ. */
  if (!data || !data.periods || !data.periods.length) return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="card-title">البيانات المالية</h3><Switch />
      </div>
      <div className="py-8 text-center text-[var(--ink-muted)] text-sm">
        {freq === "quarterly"
          ? "لا قوائم ربعية لهذا الرمز بعد"
          : "لا توجد قوائم مالية متاحة لهذا الرمز"}
      </div>
    </div>
  );

  // Newest year first — in the site's RTL layout that puts 2025 rightmost
  // (nearest the indicator name) and older years progressively to its left.
  const years: number[] = [...data.years].reverse();
  const periodsDesc = [...data.periods].reverse();
  const ch = data.changes || {};
  const P = (field: string) => periodsDesc.map((p: any) => p[field]);

  const sectionsAll: { title: string; rows: { label: string; field: string; invert?: boolean; ratio?: boolean }[] }[] = [
    { title: "النمو", rows: [
      { label: "الإيرادات", field: "revenue" },
      { label: "ربحية السهم", field: "eps", ratio: true },
    ]},
    { title: "الربحية", rows: [
      { label: "صافي الربح", field: "net_income" },
    ]},
    { title: "الملاءة المالية", rows: [
      { label: "حقوق الملكية", field: "equity" },
      /* «للسهم» في التسمية ليست زيادةً بل تمييز: حقوق الملكية فوقها هي
         القيمة الدفترية للشركة كلّها، وهذه هي نصيب السهم الواحد منها —
         وهي المعنى المتداول للمصطلح، وهي التي تُقارَن بالسعر مباشرةً. */
      { label: "القيمة الدفترية للسهم", field: "book_value", ratio: true },
      { label: "نسبة المديونية", field: "debt_ratio", invert: true, ratio: true },
      { label: "تغطية الفوائد", field: "interest_coverage", ratio: true },
    ]},
    { title: "التدفقات النقدية", rows: [
      { label: "صافي الأنشطة التشغيلية", field: "operating_cash_flow" },
      { label: "التدفق النقدي الحر", field: "free_cash_flow" },
      { label: "النقد نهاية الفترة", field: "ending_cash" },
    ]},
  ];

  // ══ صفٌّ لا رقمَ فيه لا يُعرض ══ (D177 · بأمر المالك)
  // قال: «إن استطعتَ إظهارَ الأرقام فتبقى القيمة الدفترية، وإن لم تستطع
  // ملأها لجميع السنوات فحذفُها أفضل». والحذفُ الثابت يعاقب الشركاتِ
  // التي تصل بياناتُها، والإبقاءُ الثابت يُبقي صفّاً من الشرطات.
  // فالقرارُ لكلّ شركةٍ على حدة: يُعرض الصفُّ متى حمل رقماً واحداً على
  // الأقلّ، ويُطوى متى خلا من كلّ سنة — فلا شرطاتٌ ولا حذفُ ما يُملأ.
  // (وعددُ أسهم السنة يُشتقّ من قائمتها نفسِها في الخادم — انظر
  //  `_set_book_value`، فامتلأ الصفُّ حيث كان فارغاً.)
  const hasAny = (field: string) =>
    P(field).some((v: any) => v !== null && v !== undefined && v !== "");
  const sections = sectionsAll.map(sec => ({
    ...sec, rows: sec.rows.filter(r => hasAny(r.field)),
  })).filter(sec => sec.rows.length > 0);

  return (
    /* التمرير الأفقي مقصود هنا ولا بديل عنه: مقارنة السنوات جنباً إلى جنب هي
       غرض الجدول، وتحويله بطاقاتٍ يُلغي المقارنة نفسها. لكنه كان يُطبَّق على
       البطاقة كلها فينزلق **عمود اسم المؤشر** مع التمرير، فتقرأ رقماً على
       الجوال ولا تدري أيّ بندٍ هو — والحكم النصّي أسفل الجدول كان يُسحَب معه
       أيضاً. الحلّ: التمرير على غلافٍ للجدول وحده، والعمود الأول مثبَّت
       (sticky) بخلفية البطاقة فلا تمرّ الأرقام من تحته. */
    <div className="card">
    {/* ══ الترويسة: العنوانُ والخياران ══
        وسطرُ «المصدر …» أُزيل بأمر المالك: لم يأذن به، وكتبتُه من عندي.
        والتطبيقُ سجلٌّ رسميٌّ لا مدوّنة — لا حواشيَ ولا تبريرات. */}
    <div className="flex items-center justify-between gap-2 mb-3">
      <h3 className="card-title">البيانات المالية</h3>
      <Switch />
    </div>
    {data.kind === "net_income_only" && (
      /* صدقٌ في التسمية: هذه نتيجةُ ربعٍ لا قائمةٌ كاملة. */
      <p className="mb-2 text-[11px] text-[var(--ink-muted)]">
        نتيجةُ الربع المعلَنة — صافي الربح دون بقيّة بنود القوائم
      </p>
    )}
    {/* ══ الجوّال بطاقات · اللوحيّ فما فوق جدول ══ (بأمر المالك)
        الجدولُ يحتاج 520px عرضاً، وشاشةُ الجوّال 390. فكان يُقرأ بتمريرٍ
        أفقيّ: رقمٌ واحد ظاهر، وبقيّةُ السنوات خارج الشاشة — وهو نقيضُ
        غرض الجدول (المقارنة جنباً إلى جنب).
        فعلى الجوّال يصير كلُّ مؤشّرٍ **بطاقةً**: اسمُه سطراً، وتحته
        فتراتُه الثلاث في صفٍّ واحد يتّسع له العرض، ونسبةُ التغيّر معها.
        فتبقى المقارنة قائمة بلا تمرير. والجدولُ كما هو حيث يتّسع له
        المكان — لا نسختان تتباعدان، بل عرضان لبياناتٍ واحدة. */}
    <div className="md:hidden space-y-3">
      {sections.map(sec => (
        <div key={sec.title}>
          <div className="text-[12px] text-[var(--brand-ink)] mb-1.5">{sec.title}</div>
          <div className="space-y-1.5">
            {sec.rows.map(row => {
              const vals = P(row.field);
              return (
                <div key={row.field} className="rounded-lg px-2.5 py-2"
                  style={{ background: "color-mix(in srgb, var(--brand) 5%, transparent)" }}>
                  {/* المحتوى مُوسَّطٌ كلُّه (بأمر المالك): الاسمُ والفترةُ
                      والرقم على محورٍ واحد، فتُقرأ البطاقةُ عموداً لا
                      سطوراً متفرّقة. وعنوانُ القسم وحده يبقى يميناً.

                      وعلامةُ التغيّر **خارج تدفّق التوسيط**: كانت في الصفّ
                      نفسه، فيُوسَّط الزوجُ (الاسم + العلامة) لا الاسم —
                      فينزاح الاسمُ عن محور البطاقة بنصف عرض العلامة.
                      قِيس الانحراف: ٩px. وهو صغيرٌ بالمسطرة، لكنّه ظاهرٌ
                      للعين لأن الأرقام تحته على المحور الصحيح فيبدو
                      العمودُ مكسوراً. فصارت العلامةُ مُطلَقةً على الحافّة،
                      والاسمُ وحده هو ما يُوسَّط. */}
                  <div className="relative flex items-center justify-center mb-1.5">
                    <span className="text-[11px] text-[var(--ink)] text-center">{row.label}</span>
                    <span className="absolute inset-inline-start-0" style={{ insetInlineStart: 0 }}>
                      <Light change={ch[row.field] ?? null} invert={row.invert} />
                    </span>
                  </div>
                  <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${years.length}, minmax(0,1fr))` }}>
                    {vals.map((v: number, i: number) => {
                      /* السنويُّ سطرٌ واحد: كان «2024» عنواناً و«12/2024»
                         تحته — والسنةُ مكرّرةٌ مرّتين بلا فائدة. فصار
                         تاريخَ الإقفال كاملاً (‏31/12/2024): يقول السنة
                         ومتى أُقفلت معاً. */
                      const a = periodsDesc[i]?.as_of;
                      const full = closeDate(a);
                      const head = full || String(years[i]);
                      return (
                        <div key={i} className="text-center">
                          {/* التوسيط يُكتب صراحةً هنا: `dir="ltr"` على العنصر
                              لا يكفي لأن في التطبيق قاعدةً عامّة تُحاذي
                              إلى اليمين فتغلب الوراثة من الأب المُوسَّط.
                              قِيس الانحراف قبلها: ‏28px في كل خانة —
                              والرقم تحته على المحور، فيبدو العمود مائلاً. */}
                          <div className="text-center text-[9px] text-[var(--ink-muted)] leading-tight tabular-nums"
                            dir="ltr">{head}</div>
                          <div className="text-center text-[12px] tabular-nums text-[var(--ink)] leading-tight mt-0.5">
                            {v == null ? "—" : row.ratio ? v.toFixed(2) : brief(v)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>

    <div className="overflow-x-auto hidden md:block">
      <table className="w-full text-sm min-w-[520px]">
        <thead>
          <tr className="border-b border-[var(--hairline)]">
            <th className="th text-center fin-stick align-middle">المؤشر</th>
            {years.map((y, i) => (
              /* توسيطُ العمود كلِّه لا الرأس وحده (بأمر المالك): `.th`
                 و`.td` كلاهما `text-align: start`، فتوسيطُ الكلمة وحدها
                 كان يُخرجها عن عمود أرقامها — عنوانٌ في الوسط وأرقامٌ إلى
                 يمينه. فالرأس والقيم يُوسَّطان معاً. */
              <th key={y} className="th text-center align-middle">
                {/* ══ الدور عنوانٌ والتاريخ فرعٌ ══ (بأمر المالك)
                    كان الترتيب معكوساً: التاريخ عنواناً والدور تحته. والقارئ
                    هنا يسأل «كم الحالي مقابل المماثل؟» لا «ماذا جرى في
                    2026 ر٢» — فالدور هو المدخل، والتاريخ يُثبته.
                    والتاريخ يُعرض شهراً وسنة (‏06/2026) لا رمزَ ربعٍ: الشهر
                    يقول متى أُقفل الربع فعلاً، ورمزُ الربع يفترض سنةً مالية
                    تبدأ في يناير — وهي لا تبدأ كذلك عند كل شركة. */}
                {(() => {
                  const a = periodsDesc[i]?.as_of;
                  const mmyy = closeDate(a);
                  /* التاريخ الفرعيّ للسنويّ أيضاً: يقول **متى أُقفلت السنة
                     المالية** فعلاً (‏12/2025 عند أكثر شركات تداول)، ولا
                     يُفترض ديسمبر — فبعض الشركات تُقفل في شهرٍ آخر، وسنةٌ
                     مجرّدة تُخفي ذلك. ويُقرأ من المصدر لا يُلفَّق. */
                  /* سطرٌ واحد: تاريخُ الإقفال كاملاً بدل سنةٍ فوق شهرِها. */
                  return <span className="block tabular-nums" dir="ltr">{mmyy || y}</span>;
                })()}
              </th>
            ))}
            {/* نسبةٌ واحدة (بأمر المالك): التغيّر **عن الربع المماثل**.
                وهو الرقم الذي تتصدّر به إفصاحات تداول نفسها، لأنه يُحيّد
                الموسمية: ربعٌ قويٌّ موسمياً يرتفع عن سابقه بلا أن تنمو
                الشركة، والمقارنة بمماثله وحدها تكشف ذلك. والمتتالي كان
                عموداً ثانياً يُثقل الجدول ويُقاس بالنظر متى لزم. */}
            <th className="th text-center align-middle">التغير %</th>
          </tr>
        </thead>
        <tbody>
          {sections.map(sec => (
            <React.Fragment key={sec.title}>
              <tr><td colSpan={years.length + 2} className="py-2 px-3 text-center text-[13px] text-[var(--brand-ink)] bg-[var(--field)]">{sec.title}</td></tr>
              {sec.rows.map(row => {
                const vals = P(row.field);
                return (
                  <tr key={row.field} className="border-b border-[var(--hairline)]/50">
                    <td className="td text-[var(--ink)] fin-stick">{row.label}</td>
                    {vals.map((v: number, i: number) => (
                      <td key={i} className="td tabular-nums text-[var(--ink)] text-center">
                        {v == null ? "—" : row.ratio ? v.toFixed(2) : compact(v)}
                      </td>
                    ))}
                    <td className="td text-center">
                      <Light change={ch[row.field] ?? null} invert={row.invert} />
                    </td>
                  </tr>
                );
              })}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
      {/* ══ خلاصةُ القوائم — سطرُ محلّلٍ واحدٌ لا لوحةُ أرقام ══ (بأمر المالك)
          كان الشريطُ يحمل الدرجةَ `/100` وعددَ السنوات مع الجملة. والدرجةُ
          معروضةٌ أصلاً في بطاقة التقييم — فتكرارُها يجعل الشاشةَ تقول
          الشيءَ مرّتين، وعددُ السنوات ظاهرٌ في ترويسة الجدول فوقه.
          والمصادرُ صارت رسميةً من مُصدِرها، فلا موضعَ لاعتذارٍ ولا لدعوةٍ
          لاكتشاف سبب: تحليلٌ ماليٌّ مختصرٌ في سطرٍ لا يزيد. */}
      <div className="mt-4 rounded-xl px-3 py-2.5 flex items-center gap-2"
           style={{
             color: "var(--tag-ink)",
             background: data.verdict_tone === "green" ? "var(--tag-buy)"
               : data.verdict_tone === "red" ? "var(--tag-sell)"
               : data.verdict_tone === "yellow" ? "var(--tag-hold)"
               : "var(--tag-agm)",
           }}>
        <span className="min-w-0 text-[12.5px] font-bold leading-snug">
          {data.verdict || "بيانات متاحة"}
        </span>
        {data.investment_phase === true && (
          <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-md"
                style={{ background: "rgb(0 0 0 / .18)" }}>
            مرحلة توسّع
          </span>
        )}
      </div>
    </div>
  );
}
