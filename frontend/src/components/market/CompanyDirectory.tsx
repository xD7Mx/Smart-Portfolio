import React from "react";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, X, ExternalLink } from "lucide-react";
import { marketApi } from "../../services/api";
import CompanyLogo from "../common/CompanyLogo";

/* ══ دليلُ الشركات ══ (بأمر المالك · D256)

   «أضف ميزة دليل الشركات كزرٍّ بجانب علامة البحث في نبض السوق».

   والفرقُ بينه وبين البحث فرقُ غرض: البحثُ يعرف ما يريده قبل أن يكتب،
   والدليلُ **يتصفّح** — يرى السوقَ كلَّه مرتّباً بقطاعاته. فلا يُبنى
   بحقلٍ ثانٍ بل بلوحةٍ تُفتح وتُغلق، وفيها القطاعُ عنواناً والشركاتُ
   تحته بشعارِها ورمزِها.

   ولا سعرَ فيه: دليلُ هويّةٍ لا شاشةُ تداول — وخلطُهما يُثقل الفتحةَ
   بلا حاجة. ولمن له معرِّفٌ في «أرقام» رابطٌ إليها، ومن لا معرِّفَ له
   **لا يُختلق له رابط**: وعدٌ لا يُوفى أسوأُ من زرٍّ غائب. */

type Row = {
  symbol: string; name: string; sector?: string | null;
  logo?: string | null; argaam_url?: string | null;
  suspended?: boolean; suspended_since?: string | null;
  nomu?: boolean;
};

export default function CompanyDirectory({ onPick }: { onPick: (symbol: string) => void }) {
  const [open, setOpen] = React.useState(false);
  const [q, setQ] = React.useState("");
  /* ══ «نمو» اختياريّ والقطاعُ بلمسة (بأمر المالك · D486) ══
     الجميعُ يظهر افتراضاً، ومفتاحٌ يُخفي السوقَ الموازية لمن شاء؛ وقائمةُ
     القطاعات بجانب البحث تنقل إلى قطاعٍ بعينه مباشرةً. */
  const [showNomu, setShowNomu] = React.useState(true);
  const [sector, setSector] = React.useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["market-directory"],
    queryFn: () => marketApi.directory().then(r => r.data.data),
    enabled: open,
    staleTime: 12 * 60 * 60 * 1000,
    retry: 0,
  });

  const rows: Row[] = data?.companies || [];
  const term = q.trim();
  const sectors = React.useMemo(
    () => [...new Set(rows.map(r => r.sector || "غير مصنّف"))].sort((a, b) => a.localeCompare(b, "ar")),
    [rows]);
  const shown = rows.filter(r =>
    (showNomu || !r.nomu)
    && (!sector || (r.sector || "غير مصنّف") === sector)
    && (!term || r.symbol.includes(term) || (r.name || "").includes(term)));

  const bySector = React.useMemo(() => {
    const m = new Map<string, Row[]>();
    for (const r of shown) {
      const k = r.sector || "غير مصنّف";
      (m.get(k) || m.set(k, []).get(k)!).push(r);
    }
    return [...m.entries()].sort((a, b) => b[1].length - a[1].length);
  }, [shown]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="دليل الشركات"
        title="دليل الشركات"
        className="shrink-0 grid place-items-center rounded-lg"
        style={{ width: 32, height: 32, background: "var(--field)", color: "var(--ink)" }}>
        <BookOpen size={15} />
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
             style={{ background: "rgb(0 0 0 / .45)" }}
             onClick={() => setOpen(false)}>
          <div className="w-full sm:max-w-2xl rounded-t-2xl sm:rounded-2xl overflow-hidden"
               style={{ background: "var(--surface)", maxHeight: "82vh" }}
               onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-3 py-2.5"
                 style={{ borderBottom: "1px solid var(--hairline)" }}>
              <BookOpen size={15} className="text-[var(--ink)]" />
              <h3 className="text-[13px] font-bold text-[var(--ink)]">دليل الشركات</h3>
              {rows.length > 0 && (
                <span className="text-[10.5px] tabular-nums text-[var(--ink-muted)]">
                  {shown.length}
                </span>
              )}
              <button type="button" aria-label="إغلاق" onClick={() => setOpen(false)}
                      className="mr-auto grid place-items-center rounded-lg"
                      style={{ width: 30, height: 30, color: "var(--ink-muted)" }}>
                <X size={15} />
              </button>
            </div>

            <div className="px-3 py-2 space-y-2" style={{ borderBottom: "1px solid var(--hairline)" }}>
              <div className="flex items-center gap-2">
                <input
                  value={q}
                  onChange={e => setQ(e.target.value)}
                  placeholder="اسم الشركة أو رمزها"
                  className="flex-1 min-w-0 rounded-lg px-2.5 py-1.5 text-[12px] text-[var(--ink)]"
                  style={{ background: "var(--field)", border: "1px solid var(--hairline)", minHeight: 32 }}
                />
                <select value={sector} onChange={e => setSector(e.target.value)} aria-label="القطاع"
                  className="shrink-0 max-w-[45%] rounded-lg px-2 py-1.5 text-[12px] text-[var(--ink)]"
                  style={{ background: "var(--field)", border: "1px solid var(--hairline)", minHeight: 32 }}>
                  <option value="">كل القطاعات</option>
                  {sectors.map(x => <option key={x} value={x}>{x}</option>)}
                </select>
              </div>
              <label className="flex items-center gap-2 text-[12px] text-[var(--ink)] cursor-pointer select-none" style={{ minHeight: 32 }}>
                <input type="checkbox" checked={showNomu} onChange={e => setShowNomu(e.target.checked)}
                       className="w-4 h-4 accent-[var(--brand)]" />
                إظهار السوق الموازية «نمو»
              </label>
            </div>

            <div className="overflow-y-auto" style={{ maxHeight: "62vh" }}>
              {isLoading && (
                <p className="px-3 py-4 text-[11.5px] text-[var(--ink-muted)]">…يُحمَّل الدليل</p>
              )}
              {!isLoading && shown.length === 0 && (
                <p className="px-3 py-4 text-[11.5px] text-[var(--ink-muted)]">
                  لا شركةَ بهذا الاسم أو الرمز
                </p>
              )}
              {bySector.map(([sector, list]) => (
                <div key={sector}>
                  <div className="px-3 py-1.5 text-[10.5px] font-bold text-[var(--ink-muted)]"
                       style={{ background: "var(--field)" }}>
                    {sector} <span className="tabular-nums">({list.length})</span>
                  </div>
                  {list.map(r => (
                    <div key={r.symbol}
                         className="flex items-center gap-2 px-3 py-2"
                         style={{ borderBottom: "1px solid var(--hairline)" }}>
                      <button type="button"
                              onClick={() => { setOpen(false); onPick(r.symbol); }}
                              className="flex items-center gap-2 min-w-0 flex-1 text-right">
                        <CompanyLogo symbol={r.symbol} size={22} />
                        <span className="min-w-0">
                          <span className="block text-[12px] font-semibold text-[var(--ink)] truncate">
                            {r.name}
                          </span>
                          <span className="block text-[10px] tabular-nums text-[var(--ink-muted)]" dir="ltr">
                            {r.symbol}
                          </span>
                        </span>
                      </button>
                      {r.nomu && (
                        <span className="shrink-0 text-[9.5px] font-bold px-1.5 py-0.5 rounded-md"
                              style={{ background: "var(--field)", color: "var(--ink-muted)" }}>
                          نمو
                        </span>
                      )}
                      {r.suspended && (
                        <span className="shrink-0 text-[9.5px] font-bold px-1.5 py-0.5 rounded-md"
                              style={{ background: "var(--tag-sell)", color: "var(--tag-ink)" }}>
                          موقوفة
                        </span>
                      )}
                      {r.argaam_url && (
                        <a href={r.argaam_url} target="_blank" rel="noreferrer"
                           aria-label={`${r.name} في أرقام`}
                           className="shrink-0 grid place-items-center rounded-lg"
                           style={{ width: 30, height: 30, color: "var(--ink-muted)" }}>
                          <ExternalLink size={13} />
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
