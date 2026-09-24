import { D7M_COLORS, D7M_DEFAULTS, FIB_LEVELS, type D7MSettings } from "./d7m";

/** لونُ الرمز الحاليّ بصيغة #rrggbb ليظهر في منتقي اللون. */
function tokenHex(name: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  if (/^#[0-9a-f]{6}$/i.test(v)) return v;
  if (/^#[0-9a-f]{3}$/i.test(v)) return "#" + v.slice(1).split("").map(c => c + c).join("");
  const m = v.match(/\d+(\.\d+)?/g);
  if (m && m.length >= 3) return "#" + m.slice(0, 3).map(n => Math.round(+n).toString(16).padStart(2, "0")).join("");
  return "#000000";
}

type K = keyof D7MSettings;
type Props = { cfg: D7MSettings; onChange: (c: D7MSettings) => void; onClose: () => void };

/** إعداداتُ مؤشّر D7M — كلُّ مدخلٍ في السكربت له مفتاحٌ هنا. */
export default function D7MPanel({ cfg, onChange, onClose }: Props) {
  const set = (k: K, v: unknown) => onChange({ ...cfg, [k]: v } as D7MSettings);
  const Check = ({ k, label }: { k: K; label: string }) => (
    <label className="d7m-row">
      <input type="checkbox" checked={!!cfg[k]} onChange={e => set(k, e.target.checked)} />
      <span>{label}</span>
    </label>
  );
  const Num = ({ k, label, step = 1 }: { k: K; label: string; step?: number }) => (
    <label className="d7m-row">
      <span>{label}</span>
      <input type="number" step={step} value={Number(cfg[k])} dir="ltr"
        onChange={e => { const n = Number(e.target.value); if (Number.isFinite(n)) set(k, n); }} />
    </label>
  );
  return (
    <div className="d7m-modal" role="dialog" aria-label="إعدادات D7M" onClick={onClose}>
      <div className="d7m-sheet" onClick={e => e.stopPropagation()}>
        <div className="d7m-head">
          <strong>إعدادات D7M</strong>
          <button type="button" className="d7m-btn" onClick={() => onChange({ ...D7M_DEFAULTS })}>الافتراضي</button>
          <button type="button" className="d7m-btn" onClick={onClose} aria-label="إغلاق">✕</button>
        </div>

        <fieldset><legend>الألوان</legend>
          <div className="d7m-colors">
            {D7M_COLORS.map(([k, label, token]) => (
              <label key={k} className="d7m-row">
                <span>{label}</span>
                <span className="flex items-center gap-1">
                  <input type="color" aria-label={`لون ${label}`} value={cfg.colors[k] || tokenHex(token)}
                    onChange={e => set("colors", { ...cfg.colors, [k]: e.target.value })} />
                  {cfg.colors[k] && (
                    <button type="button" className="d7m-reset" title="لونُ المظهر" aria-label={`إرجاع لون ${label}`}
                      onClick={() => { const c = { ...cfg.colors }; delete c[k]; set("colors", c); }}>↺</button>
                  )}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset><legend>فيبوناتشي تلقائي</legend>
          <Check k="fib" label="إظهار" />
          <Num k="fibDev" label="مضاعف الانحراف" step={0.5} />
          <Num k="fibDepth" label="العمق" />
          <Check k="fibReverse" label="عكس الاتجاه" />
          <Check k="fibZones" label="مناطق الدعم والمقاومة" />
          <div className="d7m-levels">
            {FIB_LEVELS.map(([lv]) => (
              <label key={lv} className="d7m-row">
                <input type="checkbox" checked={cfg.fibLevels[String(lv)] !== false}
                  onChange={e => set("fibLevels", { ...cfg.fibLevels, [String(lv)]: e.target.checked })} />
                <span dir="ltr">{lv}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset><legend>الاتجاه التلقائي</legend>
          <Check k="trend" label="إظهار" />
          <Num k="trendPP" label="فترة المحور" />
          <Check k="trendShapes" label="علامات الاختراق" />
        </fieldset>

        <fieldset><legend>القناة التلقائية</legend>
          <Check k="channel" label="إظهار" />
          <Num k="chDev" label="مضاعف الانحراف" step={0.5} />
          <Num k="chDepth" label="العمق" />
        </fieldset>

        <fieldset><legend>VWAP</legend>
          <Check k="vwap" label="إظهار" />
          <label className="d7m-row"><span>المرساة</span>
            <select value={cfg.vwapAnchor} onChange={e => set("vwapAnchor", e.target.value)}>
              <option value="Session">جلسة</option><option value="Week">أسبوع</option>
              <option value="Month">شهر</option><option value="Year">سنة</option>
            </select>
          </label>
          <Check k="vwapBand" label="النطاقات" />
          <Num k="vwapMult" label="مضاعف النطاق" step={0.5} />
        </fieldset>

        <fieldset><legend>المتوسطات الأُسّية</legend>
          <Check k="ema20" label="EMA 20" /><Check k="ema50" label="EMA 50" />
          <Check k="ema100" label="EMA 100" /><Check k="ema200" label="EMA 200" />
          <Check k="ema400" label="EMA 400" />
        </fieldset>

        <fieldset><legend>مستويات اليوم السابق</legend>
          <Check k="pdh" label="أعلى أمس" /><Check k="pdl" label="أدنى أمس" />
          <Check k="pdc" label="إغلاق أمس" /><Check k="dOpen" label="افتتاح اليوم" />
        </fieldset>

        <fieldset><legend>اللوحات</legend>
          <Check k="dashboard" label="لوحة الاتجاه" />
          <label className="d7m-row"><span>مكان اللوحة</span>
            <select value={cfg.dashPos} onChange={e => set("dashPos", e.target.value)}>
              <option value="tr">أعلى اليمين</option><option value="tl">أعلى اليسار</option>
              <option value="br">أسفل اليمين</option><option value="bl">أسفل اليسار</option>
            </select>
          </label>
          <Num k="bull" label="حدّ الصعود" /><Num k="bear" label="حدّ الهبوط" />
          <Check k="macdDash" label="المحلّل الذكي" />
          <Check k="alertsDash" label="التنبيهات" />
          <Check k="tradeTool" label="أداة الصفقة" />
        </fieldset>

        <fieldset><legend>VIX والأخبار</legend>
          <Num k="vixWarn" label="تحذير VIX" /><Num k="vixBlock" label="منع VIX" />
          <Check k="news" label="تواريخ الأخبار" />
          <label className="d7m-row d7m-col"><span>التواريخ</span>
            <textarea dir="ltr" rows={3} value={cfg.newsDates} onChange={e => set("newsDates", e.target.value)} />
          </label>
        </fieldset>
      </div>
    </div>
  );
}
