/* ══ شعارُ صقر — الصقرُ الآليّ من تصميم المالك ══ (‏D764 بأمر المالك 2026-11-18)
   «اعتمد هذا العملَ الاحترافيّ الآليّ حتى يُبرز ملامحَ صقر… فيه هيبةٌ ونظراتٌ حادّة ودقّة»، ثمّ: «هذا المرفقُ أجملُ من شكل صقر الحاليّ».
   فالشعارُ صورةُ المالك نفسُها — صقرٌ معدنيٌّ باسطٌ جناحيه بدوائرَ زرقاء وقلبٍ برتقاليّ — مقصوصةً حول الصقر ومضغوطةً (‏webp: 512 للمركز
   و160 للترويسة)، في قرصٍ داكنٍ بلون أرضيتها نفسِها فلا حدَّ يُرى. وحين يعمل صقر يتنفّس توهّجُه — ويسكن مع تفضيل تقليل الحركة. */
import big from "../../assets/saqr/saqr-emblem-512.webp";
import small from "../../assets/saqr/saqr-emblem-160.webp";

export default function SaqrEmblem({ size = 64, live = false, className = "" }: { size?: number; live?: boolean; className?: string }) {
  return (
    <span className={"sqe" + (live ? " live" : "") + (className ? " " + className : "")} style={{ width: size, height: size }} data-role="sq-emblem">
      <img src={size > 80 ? big : small} srcSet={`${small} 160w, ${big} 512w`} sizes={`${size}px`} width={size} height={size}
        alt="صقر" decoding="async" draggable={false} />
    </span>
  );
}
