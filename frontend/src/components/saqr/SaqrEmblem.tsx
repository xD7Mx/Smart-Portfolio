/* ══ شعارُ صقر — الصقرُ الآليّ من تصميم المالك ══ (‏D764 بأمر المالك 2026-11-18)
   «اعتمد هذا العملَ الاحترافيّ الآليّ حتى يُبرز ملامحَ صقر… فيه هيبةٌ ونظراتٌ حادّة ودقّة»، ثمّ: «هذا المرفقُ أجمل»، ثمّ: «هكذا أجملُ بدون
   خلفية». فالشعارُ صورةُ المالك نفسُها — صقرٌ معدنيٌّ باسطٌ جناحيه بدوائرَ زرقاء وقلبٍ برتقاليّ — بشفافيتها، بلا قرصٍ ولا أرضية، مضغوطةً
   (‏webp: 512 للمركز و160 للترويسة) وبنسبتها (1014×961). وحين يعمل صقر يتنفّس توهّجُه الأزرق — ويسكن مع تفضيل تقليل الحركة.

   ‏D837 (المالك 2026-11-25): «الفونيكس أكبر… والإضاءةُ الداخليةُ الصفراءُ تتوهّج وتتفاعل مع الرسم، والأجنحةُ تنزل من الأسفل إلى الأعلى —
   الأيقونةُ تفاعلية… أبغى أشعر من النظرة الأولى أنّ أمامي تداولاً آليّاً». فالشعارُ الكبير (‏rich) طبقاتٌ من الصورة نفسِها: الجسدُ وجناحان
   مقصوصان عند الكتفين — يرتفع الجناحان من الأسفل إلى مكانهما عند الظهور، ويرفرفان رفرفةً هادئةً حين يعمل صقر؛ وقلبُه وأضواءُ جناحيه وذيله
   تتوهّج وتنبض (والنبضُ يسري في أسلاك أنظمته من تحت قلبه)؛ ويميل مع المؤشّر، ولمسُه يرفرفه. وكلُّ ذلك يسكن مع تقليل الحركة. */
import { useRef, useState, type CSSProperties, type KeyboardEvent, type PointerEvent } from "react";
import big from "../../assets/saqr/saqr-emblem-512.webp";
import small from "../../assets/saqr/saqr-emblem-160.webp";

const RATIO = 961 / 1014;

/* القصُّ عند الكتفين بإحداثيات الصورة (‏512×485) نسبةً مئوية — الجناحُ يتجاوز حدَّ الجسد قليلاً عند الكتف فلا يظهر شقٌّ حين يتحرّك */
const pc = (pts: [number, number][]) => `polygon(${pts.map(([x, y]) => `${(x / 512 * 100).toFixed(2)}% ${(y / 485 * 100).toFixed(2)}%`).join(", ")})`;
const L: [number, number][] = [[0, 0], [206, 0], [206, 140], [210, 195], [221, 214], [221, 262], [204, 300], [166, 320], [130, 332], [0, 348]];
const R: [number, number][] = L.map(([x, y]) => [512 - x, y] as [number, number]).reverse();
const BODY: [number, number][] = [[206, 0], [306, 0], [306, 140], [302, 195], [291, 214], [291, 262], [308, 300], [346, 320], [382, 332], [512, 348], [512, 485],
  [0, 485], [0, 348], [130, 332], [166, 320], [204, 300], [221, 262], [221, 214], [210, 195], [206, 140]];
const CLIP_L = pc(L), CLIP_R = pc(R), CLIP_B = pc(BODY);
/* الأضواءُ البرتقاليةُ في الصورة: القلب، وضوءُ كلّ جناح، وأضواءُ الذيل */
const at = (x: number, y: number, s: number): CSSProperties => ({ left: `${x / 512 * 100}%`, top: `${y / 485 * 100}%`, width: `${s}%`, height: `${s * 512 / 485}%` });

export default function SaqrEmblem({ size = 64, live = false, className = "", rich = false }: { size?: number; live?: boolean; className?: string; rich?: boolean }) {
  const box = useRef<HTMLSpanElement | null>(null);
  const [beat, setBeat] = useState(0);
  if (!rich) {
    return (
      <span className={"sqe" + (live ? " live" : "") + (className ? " " + className : "")} style={{ width: size, height: Math.round(size * RATIO) }} data-role="sq-emblem">
        <img src={size > 80 ? big : small} srcSet={`${small} 160w, ${big} 512w`} sizes={`${size}px`} width={size} height={Math.round(size * RATIO)}
          alt="صقر" decoding="async" draggable={false} />
      </span>
    );
  }
  const still = () => { try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; } };
  const tilt = (e: PointerEvent<HTMLSpanElement>) => {
    const el = box.current;
    if (!el || e.pointerType !== "mouse" || still()) return;
    const r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
    el.style.setProperty("--ry", `${(x * 12).toFixed(2)}deg`);
    el.style.setProperty("--rx", `${(-y * 9).toFixed(2)}deg`);
  };
  const rest = () => { const el = box.current; if (el) { el.style.setProperty("--ry", "0deg"); el.style.setProperty("--rx", "0deg"); } };
  const flap = () => { if (!still()) setBeat(b => b + 1); };
  const key = (e: KeyboardEvent<HTMLSpanElement>) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); flap(); } };
  const img = (cls: string, clip: string, alt: string) => (
    <img className={cls} src={big} alt={alt} aria-hidden={alt ? undefined : true} decoding="async" draggable={false} style={{ clipPath: clip }} />
  );
  return (
    <span ref={box} className={"sqe rich" + (live ? " live" : "") + (className ? " " + className : "")} data-role="sq-emblem" data-beat={beat % 2 ? "a" : beat ? "b" : undefined}
      role="button" tabIndex={0} aria-label="صقر — المسه ليرفرف" onPointerMove={tilt} onPointerLeave={rest} onClick={flap} onKeyDown={key}>
      <span className="sqe-tilt">
        <i className="sqe-aura" aria-hidden />
        {img("sqe-img sqe-body", CLIP_B, "صقر")}
        {/* الجناحُ طبقتان حول الكتف نفسِه: الخارجيةُ للارتفاع عند الظهور والرفرفةِ الهادئة، والداخليةُ لرفرفة اللمس — فتجتمعان ولا تُعاد إحداهما */}
        <span className="sqe-wing l" aria-hidden><span className="sqe-flap">{img("sqe-img", CLIP_L, "")}<i className="sqe-lt" style={at(115, 146, 7)} /></span></span>
        <span className="sqe-wing r" aria-hidden><span className="sqe-flap">{img("sqe-img", CLIP_R, "")}<i className="sqe-lt" style={at(397, 146, 7)} /></span></span>
        <i className="sqe-heart" aria-hidden style={at(256, 252, 13)} />
        <i className="sqe-lt t" aria-hidden style={at(255, 420, 6)} />
        <i className="sqe-lt t" aria-hidden style={at(209, 393, 5)} />
        <i className="sqe-lt t" aria-hidden style={at(303, 393, 5)} />
      </span>
    </span>
  );
}
