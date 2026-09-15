/* تبويبُ «صفقات خاصة» — مصدرُه «تداول» الرسميّ (D318 · D321).
 *
 * الصفقةُ الخاصة متفاوَضٌ عليها خارجَ دفتر الأوامر، بحجمٍ كبيرٍ وسعرٍ قد
 * يخالف سعرَ السوق — ولا تُقرأ من شريط الأسعار.
 *
 * ══ الاسمُ ══ «الصفقات المتفاوض عليها» هو المسمّى الرسميُّ في «تداول»
 * (وهو جدولُ `getNegotiatedDetails` الذي تُقرأ منه الأرقام)، و«صفقة
 * خاصة» هو لفظُ السوق نفسِه — حدثٌ واحدٌ باسمين. فاختار المالكُ لفظَ
 * السوق: أوضحُ لمن يقرأ.
 *
 * ══ ولا عمودَ وقت ══ الوقتُ يميّز صفقتين متشابهتين في اليوم نفسِه،
 * فأُخِذ في **هويّة** الصفقة (منعُ التكرار · D319) ولم يُعرَض: لا يضيف
 * قراراً. والذي يُقرأ للقرار معروضٌ كلُّه: القيمةُ كما نشرها المصدرُ
 * (`turnOver`) لا محتسَبةً، والسعرُ، والكمّية، والتاريخ، والأكبرُ مُعلَم.
 *
 * ══ ولا عمودَ «مقابل السوق» ══ الخصمُ أو العلاوةُ يُقاسان على إغلاقِ
 * **يومِ الصفقة**، وهو ما لا نملكه لكلّ يومٍ في مدى الثلاثين. وقياسُها
 * على سعر اليوم يُنتج رقماً كاذباً لصفقةٍ عمرُها أسابيع — فتُترك.
 *
 * ══ لا وسمَ مصدرٍ في الترويسة ══
 * أُزيل بأمر المالك: «لا فوت نوت ولا هيد نوت». والمصدرُ محفوظٌ في
 * الاستجابة لمن يقرأ السجلَّ، ولا يُكتب على الشاشة.
 *
 * والغيابُ يبقى مُعلَناً بجملةٍ واحدة: يومٌ بلا صفقاتٍ **وارد**، ولا
 * يُطوى التبويبُ فيُظنّ أنه لم يُبنَ، ولا يُعرض صفرٌ مختلَق.
 */
import { useQuery } from "@tanstack/react-query";
import { Handshake, Search, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import CompanyLogo from "../common/CompanyLogo";
import { norm, searchCompanies } from "../../data/saudiCompanies";
import { marketApi } from "../../services/api";

type Deal = {
  symbol: string; price: number; quantity: number; value: number;
  name?: string; at?: string;
};

const num = (n: number, d = 0) =>
  n.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

/** الرياالاتُ الكبيرةُ تُقرأ بوحدتها: ‎57 مليوناً أسهلُ من ‎57,000,000. */
function money(v: number): string {
  if (v >= 1e9) return `${num(v / 1e9, 2)} مليار`;
  if (v >= 1e6) return `${num(v / 1e6, 1)} مليون`;
  return num(v);
}

const RANGES = [
  { days: 7, label: "أسبوعي" },
  { days: 30, label: "شهري" },
] as const;

export default function SpecialDeals({ onOpen }: { onOpen?: (s: string) => void }) {
  /* مدًى كالمفكرة بأمر المالك: سجلُّ عملياتٍ بالتاريخ لا لقطةٌ لحظية. */
  const [days, setDays] = useState<number>(30);
  const { data, isLoading } = useQuery({
    queryKey: ["special-deals", days],
    queryFn: () => marketApi.specialDeals(days).then(r => r.data.data),
    refetchInterval: 10 * 60 * 1000,
    staleTime: 2 * 60 * 1000,
  });

  /* ══ بحثٌ يتمدّد في محلّه — النمطُ نفسُه لا ثانٍ ══ (بأمر المالك)
     زرٌّ يستطيل حقلاً ويعود بالعرض والشفافية، بأصنافِ `inline-search`
     التي أُقرّت في D210 — فلا لغةَ حركةٍ ثانيةٌ في التطبيق. وهو **فرزٌ
     لما وصل** لا نداءٌ للخادم: السجلُّ في اليد، فالبحثُ لحظيٌّ بلا طلب.
     والمطابقةُ بالرمز وباسم الصفقة وبالاسم الدارج (معادن ← التعدين) عبر
     دليل الشركات نفسِه. */
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const close = () => { setOpen(false); setQ(""); };
  useEffect(() => { if (open) inputRef.current?.focus(); }, [open]);
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)
          && !q) close();
    };
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open, q]);

  const all: Deal[] = data?.deals ?? [];
  const deals = useMemo(() => {
    const n = norm(q);
    if (!n) return all;
    const byName = new Set(
      searchCompanies(q, 400).map(c => c.symbol.replace(".SR", "")));
    return all.filter(d => d.symbol.startsWith(n)
      || norm(d.name || "").includes(n) || byName.has(d.symbol));
  }, [all, q]);
  const biggest = deals.reduce((a, d) => Math.max(a, d.value || 0), 0);

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Handshake size={16} className="text-[var(--brand-ink)]" />
        <h2 className="card-title">صفقات خاصة</h2>
        <div ref={wrapRef} className="relative inline-flex items-center">
          <div className="inline-search" data-open={open ? "1" : "0"}>
            <button type="button"
                    aria-label={open ? "إغلاق البحث" : "ابحث في الصفقات"}
                    title={open ? "إغلاق البحث" : "ابحث في الصفقات"}
                    onClick={() => (open ? close() : setOpen(true))}
                    className="inline-search-btn">
              {open ? <X size={14} /> : <Search size={14} />}
            </button>
            <input ref={inputRef} className="inline-search-input" value={q}
                   placeholder="بالرمز أو الاسم…"
                   tabIndex={open ? 0 : -1}
                   onChange={e => setQ(e.target.value)}
                   onKeyDown={e => { if (e.key === "Escape") close(); }} />
          </div>
        </div>
        <div className="ms-auto flex rounded-lg border border-[var(--line)] overflow-hidden">
          {RANGES.map(r => (
            <button key={r.days} onClick={() => setDays(r.days)}
                    aria-pressed={days === r.days}
                    className="px-2.5 py-1 text-[11px] font-bold min-h-[32px]"
                    style={days === r.days
                      ? { background: "var(--brand-ink)", color: "var(--on-brand)" }
                      : { color: "var(--ink-muted)" }}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <p className="py-8 text-center text-[13px] text-[var(--ink-muted)]">…</p>
      ) : !deals.length ? (
        /* غيابُ الصفقة وغيابُ نتيجةِ البحث حالتان لا واحدة: الأولى خبرٌ
           عن السوق، والثانية عن كلمةٍ كتبها القارئ. */
        <p className="py-8 text-center text-[13px] text-[var(--ink-muted)]">
          {q ? `لا صفقة تطابق «${q}» في هذه المدة.`
             : "لا صفقات خاصة في هذه المدة."}
        </p>
      ) : (
        <>
          {/* الجوّال بطاقات، واللوحيُّ فما فوق جدول — النمطُ نفسُه في
              «القوائم المالية»: جدولٌ بعرض 520px لا يُقرأ في 390px. */}
          <div className="md:hidden space-y-2">
            {deals.map((d, i) => (
              <button key={`${d.symbol}-${i}`} onClick={() => onOpen?.(d.symbol)}
                      className="w-full text-right rounded-xl border border-[var(--line)] p-2.5">
                <div className="flex items-center gap-2">
                  {/* الشعارُ هويّةُ الصفّ: يُقرأ الصفُّ قبل قراءة حرفه. */}
                  <CompanyLogo symbol={d.symbol} size={28} />
                  <span className="font-bold text-[13px] text-[var(--ink)]">
                    {d.name || d.symbol}
                  </span>
                  <span className="text-[11px] text-[var(--ink-muted)] tabular-nums">
                    {d.symbol}
                  </span>
                  <span className="ms-auto font-bold tabular-nums text-[13px] text-[var(--ink)]">
                    {money(d.value)} ﷼
                  </span>
                </div>
                <div className="mt-1 flex items-baseline gap-3 text-[11px] text-[var(--ink-muted)] tabular-nums">
                  <span>{num(d.price, 2)} ﷼</span>
                  <span>{num(d.quantity)} سهم</span>
                  {d.at && <span className="ms-auto">{d.at}</span>}
                </div>
              </button>
            ))}
          </div>

          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-right text-[12.5px]">
              <thead>
                <tr className="text-[var(--ink-muted)] text-[11px]">
                  <th className="py-1.5 font-normal">الشركة</th>
                  <th className="py-1.5 font-normal">الرمز</th>
                  <th className="py-1.5 font-normal">السعر</th>
                  <th className="py-1.5 font-normal">الكمية</th>
                  <th className="py-1.5 font-normal">القيمة</th>
                  <th className="py-1.5 font-normal">التاريخ</th>
                </tr>
              </thead>
              <tbody>
                {deals.map((d, i) => (
                  <tr key={`${d.symbol}-${i}`}
                      onClick={() => onOpen?.(d.symbol)}
                      className="border-t border-[var(--line)] cursor-pointer">
                    <td className="py-1.5 text-[var(--ink)]">
                      <span className="flex items-center gap-2">
                        <CompanyLogo symbol={d.symbol} size={24} />
                        <span>{d.name || "—"}</span>
                      </span>
                    </td>
                    <td className="py-1.5 tabular-nums text-[var(--ink-muted)]">{d.symbol}</td>
                    <td className="py-1.5 tabular-nums text-[var(--ink)]">{num(d.price, 2)}</td>
                    <td className="py-1.5 tabular-nums text-[var(--ink)]">{num(d.quantity)}</td>
                    <td className="py-1.5 tabular-nums font-bold text-[var(--ink)]">
                      {money(d.value)}
                      {/* الأكبرُ يُعلَم: حجمُ الصفقة هو معناها. */}
                      {d.value === biggest && biggest > 0 && (
                        <span className="ms-1.5 text-[10px] font-bold text-[var(--brand-ink)]">
                          الأكبر
                        </span>
                      )}
                    </td>
                    <td className="py-1.5 tabular-nums text-[var(--ink-muted)]">{d.at || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex items-center gap-3 text-[11px] text-[var(--ink-muted)] tabular-nums">
            {/* المجموعُ يتبع المعروضَ لا المخزَّن: من بحث عن سهمٍ يقرأ
                عددَ صفقاته وإجماليَّها، ويُقال إنّ هذا فرزٌ من كلٍّ. */}
            <span>{deals.length} صفقة{q && all.length !== deals.length
              ? ` من ${all.length}` : ""}</span>
            <span>
              إجمالي {money(deals.reduce((a, d) => a + (d.value || 0), 0))} ﷼
            </span>
            {data?.as_of && <span className="ms-auto">{String(data.as_of).slice(0, 16)}</span>}
          </div>
        </>
      )}
    </div>
  );
}
