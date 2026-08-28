import React, { useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import { Calculator, Layers, Coins, Target, TrendingUp, Plus, X } from "lucide-react";

const money = (n: number) => (isFinite(n) ? Math.round(n) : 0).toLocaleString("en-US");
const money2 = (n: number) => (isFinite(n) ? n : 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="label">{label}</label>{children}</div>;
}
function Result({ label, value, color, big = false }: { label: string; value: string; color?: string; big?: boolean }) {
  return (
    <div className="kpi">
      <div className="kpi-lbl">{label}</div>
      <div className="kpi-val" style={{ color: color || undefined, fontSize: big ? 22 : undefined }}>{value}</div>
    </div>
  );
}
function Card({ icon: Icon, title, tint, children }: any) {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <div className="mc-icon" style={{ background: tint + "1e" }}><Icon size={15} style={{ color: tint }} /></div>
        <h2 className="card-title">{title}</h2>
      </div>
      {children}
    </div>
  );
}

/* 1) Average cost calculator — multiple buy lots → avg cost + break-even */
function AverageCostCalc() {
  const [lots, setLots] = useState([{ shares: "", price: "" }, { shares: "", price: "" }]);
  const [fees, setFees] = useState("");
  const set = (i: number, k: "shares" | "price") => (e: any) =>
    setLots(ls => ls.map((l, j) => j === i ? { ...l, [k]: e.target.value } : l));
  const totShares = lots.reduce((a, l) => a + (Number(l.shares) || 0), 0);
  const totCost = lots.reduce((a, l) => a + (Number(l.shares) || 0) * (Number(l.price) || 0), 0) + (Number(fees) || 0);
  const avg = totShares > 0 ? totCost / totShares : 0;
  return (
    <Card icon={Layers} title="حاسبة متوسط التكلفة" tint="var(--chart-1)">
      <div className="space-y-2">
        {lots.map((l, i) => (
          <div key={i} className="flex gap-2 items-end">
            <Field label={i === 0 ? "عدد الأسهم" : ""}><input className="input" type="text" inputMode="decimal" lang="en" placeholder="0" value={l.shares} onChange={set(i, "shares")} /></Field>
            <Field label={i === 0 ? "سعر الشراء" : ""}><input className="input" type="text" inputMode="decimal" lang="en" placeholder="0.00" value={l.price} onChange={set(i, "price")} /></Field>
            {lots.length > 1 && <button className="text-[var(--ink-muted)] hover:text-[var(--neg-ink)] pb-2.5" onClick={() => setLots(ls => ls.filter((_, j) => j !== i))}><X size={15} /></button>}
          </div>
        ))}
        <button className="btn-ghost text-xs" onClick={() => setLots(ls => [...ls, { shares: "", price: "" }])}><Plus size={13} /> إضافة عملية شراء</button>
        <Field label="العمولات (اختياري)"><input className="input" type="text" inputMode="decimal" lang="en" placeholder="0.00" value={fees} onChange={e => setFees(e.target.value)} /></Field>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-4">
        <Result label="إجمالي الأسهم" value={money(totShares)} />
        <Result label="إجمالي التكلفة" value={money(totCost) + ""} />
        <Result label="متوسط التكلفة للسهم" value={money2(avg) + ""} color="var(--chart-2)" big />
      </div>
    </Card>
  );
}

/* 2) Investment calculator — amount + expected return + dividend → income + projection */
function InvestmentCalc() {
  const [amount, setAmount] = useState("100000");
  const [ret, setRet] = useState("8");
  const [dy, setDy] = useState("4");
  const [years, setYears] = useState("5");
  const P = Number(amount) || 0, r = (Number(ret) || 0) / 100, d = (Number(dy) || 0) / 100, n = Number(years) || 0;
  const annualDiv = P * d;
  const future = P * Math.pow(1 + r, n);
  const totalReturn = future - P;
  return (
    <Card icon={Coins} title="حاسبة الاستثمار — العائد والدخل الشهري" tint="var(--warn-ink)">
      <div className="grid grid-cols-2 gap-3">
        <Field label="مبلغ الاستثمار"><input className="input" type="text" inputMode="decimal" lang="en" value={amount} onChange={e => setAmount(e.target.value)} /></Field>
        {/* «نمو السعر» لا «العائد السنوي»: البطاقة تعرض التوزيعات في خانة
            مستقلّة، فلو فُهم هذا الحقل عائداً كلياً (وهو ما يفهمه أكثر الناس
            من العبارة السابقة) لعُدّت التوزيعات مرّتين — مرّة داخل النسبة
            ومرّة بجانبها. التسمية الصريحة تمنع الازدواج بلا تغيير أي حساب. */}
        <Field label="نمو السعر السنوي المتوقع %"><input className="input" type="text" inputMode="decimal" lang="en" value={ret} onChange={e => setRet(e.target.value)} /></Field>
        <Field label="عائد التوزيعات السنوي %"><input className="input" type="text" inputMode="decimal" lang="en" value={dy} onChange={e => setDy(e.target.value)} /></Field>
        <Field label="عدد السنوات"><input className="input" type="text" inputMode="decimal" lang="en" value={years} onChange={e => setYears(e.target.value)} /></Field>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-4">
        <Result label="الدخل السنوي (توزيعات)" value={money(annualDiv) + ""} color="var(--pos-ink)" />
        <Result label="الدخل الشهري المتوقع" value={money(annualDiv / 12) + ""} color="var(--pos-ink)" big />
        <Result label={`القيمة بعد ${n} سنة`} value={money(future) + ""} color="var(--chart-2)" />
        <Result label="إجمالي النمو الرأسمالي" value={"+" + money(totalReturn) + ""} color="var(--chart-4)" />
      </div>
      <p className="text-[11px] text-[var(--ink-muted)] mt-3">
        التوزيعات محسوبة على المبلغ الأصلي ومنفصلة عن نمو السعر، فلا يُعدّ أيٌّ منهما مرّتين —
        تقديرات افتراضية بناءً على مدخلاتك، والعوائد الفعلية تتغير مع السوق.
      </p>
    </Card>
  );
}

/* 3) Reach-a-target calculator — required monthly injection to hit e.g. 1,000,000 */
function GoalCalc() {
  const [target, setTarget] = useState("1000000");
  const [current, setCurrent] = useState("50000");
  const [ret, setRet] = useState("8");
  const [years, setYears] = useState("15");
  const T = Number(target) || 0, P = Number(current) || 0, r = (Number(ret) || 0) / 100, yrs = Number(years) || 0;
  const i = r / 12, n = yrs * 12;
  const grownCurrent = P * Math.pow(1 + i, n);
  let pmt: number;
  if (n <= 0) pmt = 0;
  else if (i === 0) pmt = (T - P) / n;
  else pmt = (T - grownCurrent) * i / (Math.pow(1 + i, n) - 1);
  pmt = Math.max(0, pmt);

  // projection chart
  const data: any[] = [];
  let bal = P;
  for (let m = 0; m <= n; m++) {
    if (m % 12 === 0) data.push({ year: m / 12, value: Math.round(bal) });
    bal = bal * (1 + i) + pmt;
  }
  const totalInjected = P + pmt * n;
  /* القيمة النهائية الفعلية = آخر نقطة في نفس المنحنى المرسوم، لا الهدف.
     كانت «الأرباح المتوقعة من النمو» تُحسب (الهدف − ما ستضخّه)، وهو يصحّ فقط
     حين يلزم ضخٌّ شهري موجب. أما إذا كفى رأس المال الحالي وحده لبلوغ الهدف
     فيُصفَّر الضخّ بـ max(0, pmt)، وتتجاوز القيمة النهائية الهدفَ كثيراً —
     فتعرض البطاقة ربحاً أقلّ بكثير من الحقيقة بينما الرسم البياني فوقها
     ينتهي عند رقمٍ أعلى: رقمان متناقضان في بطاقةٍ واحدة. مثال حقيقي: هدف
     ١٠٠ ألف برأس مال ٥٠ ألفاً و٨٪ و١٥ سنة → المعروض ٥٠ ألفاً والفعلي
     ١١٥٫٣ ألفاً. الآن يُشتقّ الرقم من نفس المنحنى فلا يتناقضان أبداً. */
  const finalValue = data.length ? data[data.length - 1].value : P;
  const growthProfit = Math.max(0, finalValue - totalInjected);
  return (
    <Card icon={Target} title="حاسبة الوصول للهدف — كم أحتاج ضخاً شهرياً؟" tint="var(--chart-3)">
      <div className="grid grid-cols-2 gap-3">
        <Field label="المبلغ المستهدف"><input className="input" type="text" inputMode="decimal" lang="en" value={target} onChange={e => setTarget(e.target.value)} /></Field>
        <Field label="رأس المال الحالي"><input className="input" type="text" inputMode="decimal" lang="en" value={current} onChange={e => setCurrent(e.target.value)} /></Field>
        <Field label="العائد السنوي المتوقع %"><input className="input" type="text" inputMode="decimal" lang="en" value={ret} onChange={e => setRet(e.target.value)} /></Field>
        <Field label="خلال كم سنة"><input className="input" type="text" inputMode="decimal" lang="en" value={years} onChange={e => setYears(e.target.value)} /></Field>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4">
        <Result label="الضخ الشهري المطلوب" value={money(pmt) + ""} color="var(--chart-4)" big />
        <Result label="إجمالي ما ستضخّه" value={money(totalInjected) + ""} />
        {/* القيمة النهائية معروضة صراحةً: كانت مضمرة في الرسم وحده، فيتعذّر
            على القارئ التحقّق من رقم الأرباح بجانبه. */}
        <Result label={`القيمة بعد ${yrs || 0} سنة`} value={money(finalValue) + ""} color="var(--chart-2)" />
        <Result label="الأرباح المتوقعة من النمو" value={"+" + money(growthProfit) + ""} color="var(--pos-ink)" />
      </div>
      {pmt === 0 && finalValue > T && (
        <p className="text-[11px] text-[var(--pos-ink)] mt-2">
          رأس مالك الحالي يكفي وحده لبلوغ الهدف — بل يتجاوزه إلى {money(finalValue)} ﷼ بلا أي ضخّ شهري.
        </p>
      )}
      {data.length > 1 && (
        <div style={{ height: 180 }} dir="ltr" className="mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
              <defs><linearGradient id="goalFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--chart-3)" stopOpacity={0.35} /><stop offset="100%" stopColor="var(--chart-3)" stopOpacity={0} />
              </linearGradient></defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.12)" />
              <XAxis dataKey="year" tick={{ fontSize: 10, fill: "var(--ink-muted)" }} tickFormatter={(y: number) => `${y}س`} />
              <YAxis tick={{ fontSize: 10, fill: "var(--ink-muted)" }} width={52} tickFormatter={(v: number) => money(v)} />
              <Tooltip contentStyle={{ background: "var(--pop)", border: "1px solid var(--line)", color: "var(--tip-text)", borderRadius: 10, fontSize: 12 }}
                labelStyle={{ color: "var(--tip-text)", fontWeight: 300, marginBottom: 4 }}
                itemStyle={{ color: "var(--tip-text)" }}
                formatter={(v: any) => [money(v) + "", "القيمة"]} labelFormatter={(l: any) => `بعد ${l} سنة`} />
              <Area type="monotone" dataKey="value" stroke="var(--chart-3)" strokeWidth={2} fill="url(#goalFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
      <p className="text-[11px] text-[var(--ink-muted)] mt-2">يفترض إعادة استثمار العوائد شهرياً بمعدل ثابت — لتقريب الصورة لا للضمان.</p>
    </Card>
  );
}

/* 4) Compound growth — principal + monthly contribution + return + years */
function CompoundCalc() {
  const [principal, setPrincipal] = useState("20000");
  const [monthly, setMonthly] = useState("2000");
  const [ret, setRet] = useState("8");
  const [years, setYears] = useState("10");
  const P = Number(principal) || 0, PMT = Number(monthly) || 0, r = (Number(ret) || 0) / 100, yrs = Number(years) || 0;
  const i = r / 12, n = yrs * 12;
  const fv = i === 0 ? P + PMT * n : P * Math.pow(1 + i, n) + PMT * ((Math.pow(1 + i, n) - 1) / i);
  const contributed = P + PMT * n;
  const profit = fv - contributed;
  return (
    <Card icon={TrendingUp} title="حاسبة النمو المركّب" tint="var(--pos-ink)">
      <div className="grid grid-cols-2 gap-3">
        <Field label="المبلغ الأولي"><input className="input" type="text" inputMode="decimal" lang="en" value={principal} onChange={e => setPrincipal(e.target.value)} /></Field>
        <Field label="الإضافة الشهرية"><input className="input" type="text" inputMode="decimal" lang="en" value={monthly} onChange={e => setMonthly(e.target.value)} /></Field>
        <Field label="العائد السنوي المتوقع %"><input className="input" type="text" inputMode="decimal" lang="en" value={ret} onChange={e => setRet(e.target.value)} /></Field>
        <Field label="عدد السنوات"><input className="input" type="text" inputMode="decimal" lang="en" value={years} onChange={e => setYears(e.target.value)} /></Field>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-4">
        <Result label="القيمة النهائية" value={money(fv) + ""} color="var(--pos-ink)" big />
        <Result label="إجمالي ما أودعته" value={money(contributed) + ""} />
        <Result label="صافي الأرباح المركّبة" value={"+" + money(profit) + ""} color="var(--chart-4)" />
      </div>
    </Card>
  );
}

export default function CalculatorsPage() {
  return (
    <div className="space-y-5 fade-in">
      <div>
        <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2"><Calculator size={22} className="text-[var(--brand-ink)]" /> الحاسبات</h1>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AverageCostCalc />
        <InvestmentCalc />
        <GoalCalc />
        <CompoundCalc />
      </div>
    </div>
  );
}
