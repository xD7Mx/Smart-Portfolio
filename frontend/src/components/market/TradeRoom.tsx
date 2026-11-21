/* ══ غرفة التداول — رسمٌ وقوائمُ مراقبة في شاشةٍ واحدة ══ (بأمر المالك 2026-11-14 · D732)
   «أضيف شركات في القائمة المفضّلة، وأضع قوائم — للسوق الأمريكي وللسوق السعودي… وإذا ضغطتُ على الشركة يظهر الشارت
   بخصائصه: ستوكاستيك، RSI، الماكد، CVD… والمؤشّر حقّي». فالرسمُ في الصدر والقوائمُ بجانبه (تحته على الجوال):
   «محفظتي» و«المؤشرات» قائمتان ثابتتان، وقوائمُ المالك تُنشأ وتُحذف ويُضاف إليها من السوقين بحقل بحثٍ واحد،
   والضغطُ على سطرٍ يفتح رسمَه. والقوائمُ من خادم «المراقبة» نفسِه.
   ‏D736 (المالك 2026-11-15): «المستخدم عربيّ — الشركاتُ في اليمين والرسمُ البيانيُّ على اليسار»، والرسمُ هو الاحترافيُّ الجديد
   (‏chart/ProChart) يبقى قائماً حين يتبدّل الرمز — لا يُهدم ويُبنى.
   ‏D782 (المالك 2026-11-21): «المؤشّراتُ لا يظهر أمامها آخرُ سعر مثل قائمتي والسوق الأمريكي… وخلّها قابلةً للتعديل — كلُّ شيءٍ لازم يكون قابلاً
   للتعديل»: فصارت «المؤشرات» قائمةَ مراقبةٍ على الخادم تُزرع مرّةً بالسبعة وتُعرض بأسعارها، يُضاف إليها ويُحذف منها. و«إخفاءُ القوائم كتريدنق
   فيو — جرسُ إعداداتٍ في القائمة نفسِها: أخلّي قائمتين، وأقسمها قسمين»: فترسٌ في صفّ القوائم يُظهر كلَّ قائمةٍ ويُخفيها، ويقسم اللوحةَ قسمين لكلٍّ
   قائمتُه. و«ملتي سكرين كتريدنق فيو — أربعُ شاشات: ربعُ ساعة، ساعة، أربعُ ساعات… بكيفنا»: فشاشةٌ أو اثنتان أو أربع، لكلٍّ إطارُها، والرمزُ
   واحد، و«تحليلُ الرسم» فوقها يقرأ الأطرَ كلَّها معاً. */
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, X, Pencil, Check, Trash2, Layers, Settings2, ChevronUp, ChevronDown, ArrowUpDown } from "lucide-react";
import ProChart from "../chart/ProChart";
import ChartRead, { type ReadFrame } from "../chart/ChartRead";
import CompanyLogo from "../common/CompanyLogo";
import CheckBox from "../common/CheckBox";
import InlineStockSearch from "./InlineStockSearch";
import OptionChain from "./OptionChain";
import EconEvents from "./EconEvents";
import LiveQuote, { SessionDot, useLive, useSessions } from "../chart/LiveQuote";
import { isOption, optionSub, optionTitle, parseOption } from "../../lib/options";
import { holdingsApi, marketApi } from "../../services/api";
import { invalidateWatchlist } from "../../services/watchlistCache";
import { useAppStore } from "../../store/appStore";
import { useAuthStore } from "../../store/authStore";

/* ‏D782: أسماءُ المؤشّرات للعنوان وحده — والقائمةُ نفسُها على الخادم («المؤشرات») بأسعارها وقابلةٌ للتعديل */
const INDEX_NAMES: Record<string, string> = { "^TASI.SR": "تاسي", "^GSPC": "S&P 500", "^IXIC": "ناسداك", "^DJI": "داو جونز", "BZ=F": "برنت", "GC=F": "الذهب",
  "BTC-USD": "بتكوين" };
const PRESETS = ["السوق السعودي", "السوق الأمريكي"];
type Row = { symbol: string; name: string; price?: number | null; change_pct?: number | null };
const isSaudi = (s: string) => /^\d{4}(\.SR)?$/.test(s);
/** مؤشّرٌ أو عقدٌ آجلٌ أو عملةٌ مشفّرة — يُعرض باسمه أوّلاً ورمزُه تحته */
const isIdx = (s: string) => /^\^|=F$|-USD$/.test(s);
const lsGet = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };
const lsSet = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* وضعُ التصفّح الخاصّ */ } };
/* ‏D783: رفعُ العنصر وإنزالُه ينزلق إلى مكانه (‏FLIP) لا يقفز — والحركةُ المخفّضةُ تُحترم */
function useFlip(ref: React.RefObject<HTMLDivElement>) {
  const last = useRef(new Map<string, number>());
  useLayoutEffect(() => {
    const box = ref.current;
    if (!box) return;
    const els = [...box.querySelectorAll<HTMLElement>("[data-sym]")];
    const now = new Map(els.map(el => [el.dataset.sym as string, el.offsetTop]));
    const calm = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!calm) for (const el of els) {
      const was = last.current.get(el.dataset.sym as string), is = now.get(el.dataset.sym as string);
      if (was != null && is != null && Math.abs(was - is) > 1 && typeof el.animate === "function")
        el.animate([{ transform: `translateY(${was - is}px)` }, { transform: "none" }], { duration: 240, easing: "cubic-bezier(.2,.7,.2,1)" });
    }
    last.current = now;
  });
}
const lsList = (k: string): string[] => { try { const v = JSON.parse(lsGet(k) || "[]"); return Array.isArray(v) ? v.map(String) : []; } catch { return []; } };
const pct = (v?: number | null) => v == null || !isFinite(Number(v)) ? null : Number(v);
/* ‏D747: لأيّ سهمٍ أو صندوقٍ أمريكيّ سلسلةُ خيارات — والمؤشّرُ إلى مؤشّر خياراته (‏S&P 500 ⇐ SPX · ناسداك ⇐ NDX) */
const OPT_INDEX: Record<string, string> = { "^GSPC": "^SPX", "^SPX": "^SPX", "^IXIC": "^NDX", "^NDX": "^NDX", "^RUT": "^RUT", "^VIX": "^VIX" };
const chainOf = (s: string): string | null => {
  const o = parseOption(s);
  if (o) return o.root;
  if (OPT_INDEX[s]) return OPT_INDEX[s];
  return /^[A-Z][A-Z.\-]{0,6}$/.test(s) && !isSaudi(s) && !/-USD$/.test(s) ? s : null;
};

export default function TradeRoom() {
  const qc = useQueryClient();
  const { theme } = useAppStore();
  const owner = useAuthStore((s: any) => s.isOwner);
  const [list, setListState] = useState<string>(() => { try { return localStorage.getItem("sp_room_list") || "mine"; } catch { return "mine"; } });
  const setList = (v: string) => { setListState(v); try { localStorage.setItem("sp_room_list", v); } catch { /* خاصّ */ } };
  const [sym, setSymState] = useState<string | null>(() => { try { return localStorage.getItem("sp_room_symbol"); } catch { return null; } });
  const chartRef = useRef<HTMLDivElement>(null);
  const pick = (s: string) => {
    setSymState(s); try { localStorage.setItem("sp_room_symbol", s); } catch { /* خاصّ */ }
    // على الجوال القائمةُ تحت الرسم — يُعاد إليه بانسياب
    if (window.innerWidth < 1024) chartRef.current?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  };
  const [editing, setEditing] = useState(false);
  const [chainFor, setChainFor] = useState<string | null>(null);
  const [naming, setNaming] = useState<string | null>(null);
  /* ‏D782: القوائمُ المخفيّة، والقسمُ الثاني، وعددُ الشاشات — اختياراتُ عرضٍ تُحفظ في المتصفّح */
  const [hidden, setHiddenState] = useState<string[]>(() => lsList("sp_room_hidden"));
  const setHidden = (v: string[]) => { setHiddenState(v); lsSet("sp_room_hidden", JSON.stringify(v)); };
  const [list2, setList2State] = useState<string>(() => lsGet("sp_room_list2") || "");
  const setList2 = (v: string) => { setList2State(v); lsSet("sp_room_list2", v); };
  const [gear, setGear] = useState(false);
  const gearRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!gear) return;
    const away = (e: Event) => { if (gearRef.current && !gearRef.current.contains(e.target as Node)) setGear(false); };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [gear]);
  const [layoutN, setLayoutState] = useState<number>(() => { const v = Number(lsGet("sp_room_layout")); return v === 2 || v === 4 ? v : 1; });
  const setLayout = (n: number) => { setLayoutState(n); lsSet("sp_room_layout", String(n)); };
  const snaps = useRef(new Map<number, () => ReadFrame | null>());
  const rowsBox = useRef<HTMLDivElement>(null), rowsBox2 = useRef<HTMLDivElement>(null);
  useFlip(rowsBox); useFlip(rowsBox2);

  /* ‏D762: أيقونةُ حالة السوق بجانب كلّ شركةٍ في القائمة — السعوديّةُ بحالة «تداول» والأمريكيّةُ بحالة نيويورك */
  const { data: ses } = useSessions();
  const dotFor = (s: string) => /-USD$/.test(s) ? <SessionDot always /> : isSaudi(s) || /TASI/i.test(s) ? <SessionDot s={ses?.sa} />
    : chainOf(s) || /^\^(GSPC|IXIC|DJI|RUT|VIX)$/.test(s) ? <SessionDot s={ses?.us} /> : null;
  const { data: holdings = [] } = useQuery({
    queryKey: ["holdings"],
    queryFn: () => holdingsApi.list().then(r => (Array.isArray(r.data?.data) ? r.data.data : [])),
  });
  const { data: groups = [] } = useQuery<any[]>({
    queryKey: ["watchlist-groups"],
    queryFn: () => marketApi.watchGroups().then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
  });
  const gid = list.startsWith("g") ? Number(list.slice(1)) : null;
  const group = groups.find((g: any) => g.id === gid);
  useEffect(() => {
    /* ‏D782: «المؤشرات» الثابتةُ القديمة (‏idx) صارت قائمةً على الخادم — فمن كانت مفتوحتَه تُفتح له القائمةُ الجديدة */
    if (list === "idx" && groups.length) { const ig = groups.find((g: any) => g.name === "المؤشرات"); setList(ig ? `g${ig.id}` : "mine"); return; }
    if (gid != null && groups.length && !group) setList("mine");
  }, [list, gid, groups, group]);
  /* ‏D783 (المالك): «أرفع وأنزل وأرتّب — أرامكو تحت، والراجحي فوق»: ترتيبُ «محفظتي» بيد المالك يُحفظ في المتصفّح (شركاتُ المحفظة ليست قائمةً
     على الخادم)، وترتيبُ القوائم الأخرى على الخادم */
  const [mineOrder, setMineOrderState] = useState<string[]>(() => lsList("sp_room_mine_order"));
  const setMineOrder = (v: string[]) => { setMineOrderState(v); lsSet("sp_room_mine_order", JSON.stringify(v)); };
  const mineRows: Row[] = useMemo(() => {
    const base: Row[] = holdings.filter((h: any) => h.company?.symbol).map((h: any) => ({
      symbol: h.company.symbol, name: h.company.name_ar || h.company.name || h.company.company_name,
      price: Number(h.last_price) || null, change_pct: pct(h.change_pct) }));
    if (!mineOrder.length) return base;
    const at = new Map(mineOrder.map((s, i) => [s, i])), was = new Map(base.map((r, i) => [r.symbol, i]));
    const key = (r: Row) => at.has(r.symbol) ? at.get(r.symbol)! : mineOrder.length + was.get(r.symbol)!;
    return [...base].sort((a, b) => key(a) - key(b));
  }, [holdings, mineOrder]);
  const { data: wrows = [], isFetching } = useQuery<Row[]>({
    queryKey: ["watchlist", gid],
    queryFn: () => marketApi.watchlist(gid!).then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
    enabled: gid != null && !!group, refetchInterval: 60_000,
  });
  const rows: Row[] = list === "mine" ? mineRows : wrows;
  /* القسمُ الثاني (‏D782): قائمتُه بأسعارها كالأوّل */
  const gid2 = list2.startsWith("g") ? Number(list2.slice(1)) : null;
  const group2 = groups.find((g: any) => g.id === gid2);
  const { data: wrows2 = [] } = useQuery<Row[]>({
    queryKey: ["watchlist", gid2],
    queryFn: () => marketApi.watchlist(gid2!).then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
    enabled: gid2 != null && !!group2, refetchInterval: 60_000,
  });
  const rows2: Row[] = list2 === "mine" ? mineRows : gid2 != null && group2 ? wrows2 : [];

  const symbol = sym || rows[0]?.symbol || "^TASI.SR";
  const label = INDEX_NAMES[symbol] || (isIdx(symbol) ? [...rows, ...rows2].find(r => r.symbol === symbol)?.name : undefined);
  const nm = isOption(symbol) ? optionTitle(parseOption(symbol)!) : label || [...rows, ...rows2].find(r => r.symbol === symbol)?.name || "";
  const market: "us" | "sa" = isSaudi(symbol) || /TASI/i.test(symbol) ? "sa" : "us";
  /* السعرُ الحيُّ وحالةُ السوق للرمز المفتوح — النداءُ نفسُه الذي يقرؤه الرسم (مفتاحٌ واحد)، فالأيقونةُ بجانب الاسم تتبع الجلسةَ لحظةً بلحظة */
  const { data: live } = useLive(symbol);
  const headDot = /-USD$/.test(symbol) ? <SessionDot always /> : live?.session ? <SessionDot s={live.session} /> : dotFor(symbol);

  const add = useMutation({
    mutationFn: (a: { s: string; name?: string }) => marketApi.watchAdd(a.s, a.name, gid!),
    onSuccess: () => invalidateWatchlist(qc),
  });
  /* ‏D781 (المالك): «علامةُ زائدٍ في الرسم: ما يظهر عليه — سهمٌ أو عقد — يُضاف إلى القائمة المفتوحة الآن» — وإن كانت المفتوحةُ «محفظتي» أو
     «المؤشرات» (لا يُضاف إليهما) فقائمةٌ صغيرةٌ بقوائمك تختار منها */
  const [addMenu, setAddMenu] = useState(false);
  const [addedTo, setAddedTo] = useState<string | null>(null);
  const inList = gid != null && wrows.some(r => r.symbol === symbol);
  const nameOf = (s: string) => (isOption(s) ? optionTitle(parseOption(s)!) : [...rows, ...rows2].find(r => r.symbol === s)?.name || INDEX_NAMES[s] || undefined);
  const addTo = useMutation({
    mutationFn: (g: number) => marketApi.watchAdd(symbol, nameOf(symbol), g),
    onSuccess: (_r, g) => { invalidateWatchlist(qc); setAddMenu(false); setAddedTo(groups.find((x: any) => x.id === g)?.name || "القائمة"); },
  });
  useEffect(() => { setAddMenu(false); setAddedTo(null); }, [symbol]);
  useEffect(() => { if (!addedTo) return; const t = setTimeout(() => setAddedTo(null), 2600); return () => clearTimeout(t); }, [addedTo]);
  const remove = useMutation({
    mutationFn: (s: string) => marketApi.watchRemove(s, gid!),
    onSuccess: () => invalidateWatchlist(qc),
  });
  const create = useMutation({
    mutationFn: (name: string) => marketApi.watchGroupCreate({ name }),
    onSuccess: (r: any) => {
      setNaming(null);
      qc.invalidateQueries({ queryKey: ["watchlist-groups"] }).then(() => {
        const id = r?.data?.data?.id; if (id) setList(`g${id}`);
      });
    },
  });
  const dropGroup = useMutation({
    mutationFn: (id: number) => marketApi.watchGroupRemove(id),
    onSuccess: () => { setList("mine"); setEditing(false); qc.invalidateQueries({ queryKey: ["watchlist-groups"] }); invalidateWatchlist(qc); },
  });
  const missingPresets = PRESETS.filter(p => !groups.some((g: any) => g.name === p));

  const allTabs: [string, string][] = [["mine", "محفظتي"], ...groups.map((g: any) => [`g${g.id}`, g.name] as [string, string])];
  const shownTabs = allTabs.filter(([id]) => !hidden.includes(id));
  const tabs = shownTabs.length ? shownTabs : allTabs;
  /* القائمةُ المفتوحةُ أُخفيت ⇒ أوّلُ الظاهرة؛ والقسمُ الثاني لقائمةٍ حُذفت يُطوى */
  useEffect(() => { if (groups.length && hidden.includes(list) && tabs.length) setList(tabs[0][0]); }, [hidden, list, tabs, groups.length]);
  useEffect(() => { if (list2 && list2 !== "mine" && groups.length && !group2) setList2(""); }, [list2, groups.length, group2]);
  const toggleHidden = (id: string, show: boolean) => {
    const nx = show ? hidden.filter(x => x !== id) : [...hidden, id];
    if (allTabs.filter(([t]) => !nx.includes(t)).length === 0) return;        // قائمةٌ واحدةٌ تبقى ظاهرةً على الأقلّ
    setHidden(nx);
  };

  /* ‏D783: رفعُ عنصرٍ وإنزالُه — «محفظتي» في المتصفّح، والقوائمُ على الخادم (ترتيبُ D683 نفسُه) بانسيابٍ فوريّ ثمّ الحفظ */
  const move = (listId: string, symbol: string, dir: -1 | 1) => {
    const cur = (listId === "mine" ? mineRows : listId === list ? wrows : wrows2).map(r => r.symbol);
    const i = cur.indexOf(symbol), j = i + dir;
    if (i < 0 || j < 0 || j >= cur.length) return;
    const nx = [...cur];
    [nx[i], nx[j]] = [nx[j], nx[i]];
    if (listId === "mine") { setMineOrder(nx); return; }
    const g = Number(listId.slice(1));
    qc.setQueryData<Row[]>(["watchlist", g], old => (old ? nx.map(x => old.find(r => r.symbol === x)).filter(Boolean) as Row[] : old));
    marketApi.watchOrder(nx, g).catch(() => invalidateWatchlist(qc));
  };
  /* ‏D783: ترتيبُ القوائم نفسِها، وتسميتُها، وحذفُها — من ترس القوائم */
  const moveGroup = (id: number, dir: -1 | 1) => {
    const ids = groups.map((g: any) => g.id as number), i = ids.indexOf(id), j = i + dir;
    if (i < 0 || j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    qc.setQueryData<any[]>(["watchlist-groups"], old => (old ? ids.map(x => old.find((g: any) => g.id === x)).filter(Boolean) : old));
    marketApi.watchGroupsOrder(ids).finally(() => qc.invalidateQueries({ queryKey: ["watchlist-groups"] }));
  };
  const [renaming, setRenaming] = useState<{ id: number; v: string } | null>(null);
  const rename = useMutation({
    mutationFn: (a: { id: number; name: string }) => marketApi.watchGroupUpdate(a.id, { name: a.name }),
    onSuccess: () => { setRenaming(null); qc.invalidateQueries({ queryKey: ["watchlist-groups"] }); },
  });

  const renderRow = (r: Row, i: number, edit: boolean, listId: string = list, n: number = rows.length) => {
    const ch = pct(r.change_pct);
    const on = r.symbol === symbol;
    const o = parseOption(r.symbol);
    const byName = isSaudi(r.symbol) || isIdx(r.symbol);
    return (
      <div key={r.symbol} className={"troom-row card-rise" + (on ? " on" : "")} style={{ animationDelay: `${Math.min(i, 14) * 18}ms` }} data-sym={r.symbol}>
        <button type="button" className="troom-pick" onClick={() => pick(r.symbol)} aria-pressed={on} data-role="troom-row" title={r.name}>
          <CompanyLogo symbol={r.symbol} size={24} />
          <span className="min-w-0 flex-1 text-start">
            {o ? (<>
              <span className="troom-nm"><span className="text-[12.5px] font-bold text-[var(--ink)] truncate">{optionTitle(o)}</span>{dotFor(r.symbol)}</span>
              <span className="block text-[10px] text-[var(--ink-muted)] truncate tabular-nums">{optionSub(o)}</span>
            </>) : (<>
              <span className="troom-nm"><span className="text-[12.5px] font-bold text-[var(--ink)] truncate">{byName ? r.name : r.symbol}</span>{dotFor(r.symbol)}</span>
              <span className="block text-[10px] text-[var(--ink-muted)] truncate tabular-nums" dir={isSaudi(r.symbol) ? undefined : "ltr"} style={{ textAlign: "right" }}>
                {isIdx(r.symbol) ? r.symbol : isSaudi(r.symbol) ? r.symbol.replace(".SR", "") : (r.name !== r.symbol ? r.name : "")}
              </span>
            </>)}
          </span>
          {r.price != null && !edit && (
            <span className="text-end shrink-0" data-role="troom-price">
              <span className="block text-[12.5px] font-bold tabular-nums text-[var(--ink)]" dir="ltr">{Number(r.price).toFixed(2)}</span>
              {ch != null && <span className={"block text-[10.5px] font-bold tabular-nums " + (ch >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")} dir="ltr">
                {(ch >= 0 ? "+" : "") + ch.toFixed(2)}%</span>}
            </span>
          )}
        </button>
        {edit && (
          <span className="troom-ord" data-role="troom-ord">
            <button type="button" className="btn-ghost troom-icon" aria-label={`ارفع ${r.name || r.symbol}`} title="ارفع" disabled={i === 0}
              onClick={() => move(listId, r.symbol, -1)} data-role="troom-up"><ChevronUp size={15} /></button>
            <button type="button" className="btn-ghost troom-icon" aria-label={`أنزل ${r.name || r.symbol}`} title="أنزل" disabled={i === n - 1}
              onClick={() => move(listId, r.symbol, 1)} data-role="troom-down"><ChevronDown size={15} /></button>
            {listId !== "mine" && (
              <button type="button" className="btn-ghost troom-icon troom-danger" aria-label={`إزالة ${r.symbol}`} title="إزالة"
                onClick={() => remove.mutate(r.symbol)} data-role="troom-remove"><X size={14} /></button>
            )}
          </span>
        )}
      </div>
    );
  };

  const identityNode = (
          <span className="troom-ident flex items-center gap-1.5 min-w-0" data-role="troom-ident">
            <CompanyLogo symbol={symbol} size={26} />
            {isOption(symbol) ? (() => { const o = parseOption(symbol)!; return (<>
              <span className="text-[14px] font-bold text-[var(--ink)] tabular-nums whitespace-nowrap">{optionTitle(o)}</span>
              <span className="troom-osub tabular-nums">{optionSub(o)}</span>
            </>); })() : (<>
              <span className="text-[14px] font-bold text-[var(--ink)] tabular-nums" dir="ltr">{label || symbol.replace(".SR", "")}</span>
              {!label && <span className="text-[12px] text-[var(--ink-muted)] truncate max-w-[40vw] lg:max-w-[180px]">{nm}</span>}
            </>)}
            {/* ‏D782 (المالك): «حالةُ السوق أيقونةٌ بجانب الشركات» — بجانب الاسم، ومكانُ شارتها لزرّ «تحليل الرسم» */}
            <span className="troom-sdot" data-role="troom-sdot">{headDot}</span>
            {owner && (inList ? (
              <span className="troom-inlist" data-role="troom-inlist" title={`في «${group?.name || "القائمة"}»`} aria-label="في القائمة"><Check size={14} /></span>
            ) : (
              <span className="troom-addw">
                <button type="button" className="btn-ghost troom-plus" data-role="troom-add" disabled={addTo.isPending}
                  title={gid != null ? `أضِفه إلى «${group?.name || "القائمة"}»` : "أضِفه إلى قائمة"} aria-label={gid != null ? `أضِفه إلى «${group?.name || "القائمة"}»` : "أضِفه إلى قائمة"}
                  aria-expanded={gid == null ? addMenu : undefined} onClick={() => (gid != null ? addTo.mutate(gid) : setAddMenu(v => !v))}><Plus size={15} /></button>
                {addMenu && gid == null && (
                  <span className="troom-addmenu" role="menu" data-role="troom-add-menu">
                    {groups.length ? groups.map((g: any) => (
                      <button key={g.id} type="button" role="menuitem" className="troom-additem" onClick={() => addTo.mutate(g.id)}>{g.name}</button>
                    )) : <span className="troom-addnone">لا قوائمَ لك بعد — أنشئ قائمةً من «+» في القوائم</span>}
                  </span>
                )}
                {addedTo && <span className="troom-added" role="status" data-role="troom-added">أُضيف إلى «{addedTo}»</span>}
              </span>
            ))}
            {chainOf(symbol) && (
              <button type="button" className="btn-ghost troom-oc" onClick={() => setChainFor(chainOf(symbol))} data-role="troom-options"
                title="عقود الخيارات" aria-label={`عقود خيارات ${chainOf(symbol)}`}>
                <Layers size={13} className="inline-block align-[-2px] me-1" />عقود الخيارات
              </button>
            )}
            {/* ‏D761 · D782: الأحداثُ وأثرُها — للسهم الأمريكيّ بقراءة السوق الأمريكي، وللسعوديّ بقراءة السوق السعودي وأحداثِ الشركة */}
            {(chainOf(symbol) || market === "sa") && (
              <EconEvents compact market={market} symbol={market === "sa" && isSaudi(symbol) ? symbol : undefined} name={market === "sa" ? nm : undefined} />
            )}
          </span>
  );

  return (
    <div className="troom" data-role="troom">
      <aside className="troom-list card" data-role="troom-list">
        <div className="troom-tabrow">
        <div className="troom-tabs" role="tablist" aria-label="القوائم">
          {tabs.map(([id, name]) => (
            <button key={id} type="button" role="tab" aria-selected={list === id} data-role="troom-tab"
              className={"seg-btn chip" + (list === id ? " on" : "")} onClick={() => { setList(id); setEditing(false); }}>{name}</button>
          ))}
          {owner && (
            <button type="button" className="seg-btn chip troom-new" title="قائمة جديدة" aria-label="قائمة جديدة" data-role="troom-new"
              onClick={() => setNaming(n => n == null ? "" : null)}><Plus size={14} /></button>
          )}
        </div>
          <div ref={gearRef} className="troom-gearw">
            <button type="button" className={"seg-btn chip troom-gear" + (gear ? " on" : "")} title="إعداداتُ القوائم" aria-label="إعداداتُ القوائم"
              aria-expanded={gear} data-role="troom-gear" onClick={() => setGear(g => !g)}><Settings2 size={14} /></button>
            {gear && (
              <div className="troom-gearmenu" role="dialog" aria-label="إعداداتُ القوائم" data-role="troom-gear-menu">
                <span className="troom-gcap">القوائم — إظهارٌ وترتيبٌ وتسميةٌ وحذف</span>
                {allTabs.map(([id, name]) => {
                  const g = id === "mine" ? null : groups.find((x: any) => `g${x.id}` === id);
                  const gi = g ? groups.indexOf(g) : -1;
                  return (
                    <div key={id} className="troom-grow" data-role="troom-glist" data-list={id}>
                      {g && renaming?.id === g.id ? (
                        <span className="troom-rename">
                          <input className="input" autoFocus value={renaming.v} aria-label="الاسمُ الجديد" data-role="troom-rename-input"
                            onChange={e => setRenaming({ id: g.id, v: e.target.value })}
                            onKeyDown={e => { if (e.key === "Enter" && renaming.v.trim()) rename.mutate({ id: g.id, name: renaming.v.trim() }); if (e.key === "Escape") setRenaming(null); }} />
                          <button type="button" className="btn-ghost troom-icon" aria-label="احفظ الاسم" title="احفظ" disabled={!renaming.v.trim() || rename.isPending}
                            onClick={() => rename.mutate({ id: g.id, name: renaming.v.trim() })} data-role="troom-rename-save"><Check size={15} /></button>
                        </span>
                      ) : (
                        <CheckBox checked={!hidden.includes(id)} onChange={v => toggleHidden(id, v)} label={name} className="troom-gitem" />
                      )}
                      {g && owner && renaming?.id !== g.id && (
                        <span className="troom-gacts">
                          <button type="button" className="btn-ghost troom-icon" aria-label={`ارفع قائمة ${name}`} title="ارفع" disabled={gi <= 0}
                            onClick={() => moveGroup(g.id, -1)} data-role="troom-gup"><ChevronUp size={15} /></button>
                          <button type="button" className="btn-ghost troom-icon" aria-label={`أنزل قائمة ${name}`} title="أنزل" disabled={gi >= groups.length - 1}
                            onClick={() => moveGroup(g.id, 1)} data-role="troom-gdown"><ChevronDown size={15} /></button>
                          <button type="button" className="btn-ghost troom-icon" aria-label={`أعِد تسمية ${name}`} title="إعادةُ تسمية"
                            onClick={() => setRenaming({ id: g.id, v: name })} data-role="troom-grename"><Pencil size={13} /></button>
                          <button type="button" className="btn-ghost troom-icon troom-danger" aria-label={`احذف قائمة ${name}`} title="حذفُ القائمة"
                            disabled={groups.length <= 1}
                            onClick={() => { if (window.confirm(`حذفُ قائمة «${name}» وما فيها؟`)) dropGroup.mutate(g.id); }} data-role="troom-gdel"><Trash2 size={13} /></button>
                        </span>
                      )}
                    </div>
                  );
                })}
                {owner && (
                  <button type="button" className="troom-gorder" data-role="troom-gorder" onClick={() => { setEditing(true); setGear(false); }}>
                    <ArrowUpDown size={14} /> رتّب عناصرَ «{allTabs.find(([id]) => id === list)?.[1] || ""}»</button>
                )}
                <span className="troom-gcap">القسمُ الثاني</span>
                <div className="troom-gsplit" data-role="troom-split">
                  <button type="button" className={"seg-btn chip" + (!list2 ? " on" : "")} aria-pressed={!list2} onClick={() => setList2("")}>بلا</button>
                  {allTabs.filter(([id]) => id !== list).map(([id, name]) => (
                    <button key={id} type="button" className={"seg-btn chip" + (list2 === id ? " on" : "")} aria-pressed={list2 === id}
                      onClick={() => setList2(id)} data-list={id}>{name}</button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {naming != null && (
          <div className="troom-naming" data-role="troom-naming">
            <input className="input" autoFocus placeholder="اسمُ القائمة" value={naming} aria-label="اسم القائمة"
              onChange={e => setNaming(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && naming.trim()) create.mutate(naming.trim()); if (e.key === "Escape") setNaming(null); }} />
            <button type="button" className="btn-primary troom-icon" disabled={!naming.trim() || create.isPending}
              onClick={() => create.mutate(naming.trim())} title="إنشاء" aria-label="إنشاء"><Check size={15} /></button>
            {missingPresets.map(p => (
              <button key={p} type="button" className="seg-btn chip" onClick={() => create.mutate(p)} data-role="troom-preset">{p}</button>
            ))}
          </div>
        )}

        {((gid != null && group) || (list === "mine" && owner)) && (
          <div className="troom-bar">
            {/* ‏D761: الاختيارُ يُضيف إلى القائمة ويفتح رسمَه — وعقدُ الخيار المنسوخ من المختبر يُفتح عقداً باسمه */}
            {owner && gid != null && <InlineStockSearch onPick={s => { add.mutate({ s, name: isOption(s) ? optionTitle(parseOption(s)!) : undefined }); pick(s); }} global />}
            <span className="text-[11px] text-[var(--ink-muted)] tabular-nums ms-auto">{rows.length}</span>
            {owner && (
              <button type="button" className={"btn-ghost troom-icon" + (editing ? " on" : "")} title={editing ? "تمّ" : "تحرير القائمة"}
                aria-label="تحرير القائمة" onClick={() => setEditing(e => !e)} data-role="troom-edit">
                {editing ? <Check size={15} /> : <Pencil size={14} />}
              </button>
            )}
            {owner && editing && group && !group.is_default && (
              <button type="button" className="btn-ghost troom-icon troom-danger" title={`حذف قائمة «${group.name}»`} aria-label="حذف القائمة"
                onClick={() => { if (window.confirm(`حذفُ قائمة «${group.name}» وما فيها؟`)) dropGroup.mutate(group.id); }}>
                <Trash2 size={14} />
              </button>
            )}
          </div>
        )}

        <div ref={rowsBox} className="troom-rows" data-role="troom-rows">
          {rows.map((r, i) => renderRow(r, i, editing && owner))}
          {!rows.length && (
            <div className="text-[12px] text-[var(--ink-muted)] text-center py-6">
              {gid != null ? (isFetching ? "…" : "القائمةُ فارغة.") : "لا شركات."}
            </div>
          )}
        </div>
        {list2 && list2 !== list && (
          <div className="troom-sec2" data-role="troom-sec2">
            <div className="troom-sec2-head">
              <b>{allTabs.find(([id]) => id === list2)?.[1] || ""}</b>
              <button type="button" className="btn-ghost troom-icon" title="إغلاقُ القسم الثاني" aria-label="إغلاقُ القسم الثاني" onClick={() => setList2("")}
                data-role="troom-sec2-close"><X size={14} /></button>
            </div>
            <div ref={rowsBox2} className="troom-rows" data-role="troom-rows2">
              {rows2.map((r, i) => renderRow(r, i, false))}
              {!rows2.length && <div className="text-[12px] text-[var(--ink-muted)] text-center py-4">القائمةُ فارغة.</div>}
            </div>
          </div>
        )}
      </aside>

      <section ref={chartRef} className="troom-chart card" data-role="troom-chart">
        {layoutN === 1 ? (
          <ProChart symbol={symbol} theme={theme === "light" ? "light" : "dark"} identity={identityNode}
            layout={{ n: 1, set: setLayout }} read={{ name: nm, market }} snaps={snaps} />
        ) : (<>
          {/* ‏D782: الشاشاتُ المتعدّدة — الرأسُ واحدٌ فوقها: الاسمُ والعقودُ والأحداثُ و«تحليلُ الرسم» للأطر كلِّها معاً والسعرُ الحيّ */}
          <div className="troom-mhead" data-role="troom-mhead">
            {identityNode}
            <ChartRead symbol={symbol} name={nm} market={market}
              frames={() => [...snaps.current.entries()].sort((a, b) => a[0] - b[0]).map(([, f]) => f()).filter(Boolean) as ReadFrame[]} />
            <LiveQuote symbol={symbol} live={live} badge={false} />
          </div>
          <div className={`troom-grid g${layoutN}`} data-role="troom-grid">
            {Array.from({ length: layoutN }, (_, k) => (
              <div key={k} className="troom-pane" data-role="troom-pane">
                <ProChart symbol={symbol} theme={theme === "light" ? "light" : "dark"} slot={k} mini rows={layoutN === 4 ? 2 : 1}
                  layout={k === 0 ? { n: layoutN, set: setLayout } : undefined} snaps={snaps} />
              </div>
            ))}
          </div>
        </>)}
        {chainFor && (
          <OptionChain underlying={chainFor} onClose={() => setChainFor(null)}
            onPick={c => { setChainFor(null); pick(c); }}
            onAdd={owner && gid != null && group ? (c, name) => add.mutate({ s: c, name }) : undefined} />
        )}
      </section>
    </div>
  );
}
