import React from "react";
import StockView from "./StockView";

/**
 * نافذة الشركة — تُفتح **في مكانها** فوق القسم الذي جئت منه، فلا يُقذف بك
 * إلى صفحة السوق كلّما ضغطت اسم شركة. تحتفظ بسياقك: تُغلقها فتجد نفسك حيث
 * كنت، بنفس التمرير ونفس التبويب.
 *
 * التخطيط: على الجوال تملأ الشاشة من الأسفل (ورقة صاعدة) لأن الارتفاع هو
 * المورد الشحيح هناك؛ وعلى الكمبيوتر نافذة مركزية محدودة العرض. المحتوى
 * نفسه في الحالتين — لا نسختين تتباعدان.
 */
export default function StockSheet({ symbol, onClose }: { symbol: string; onClose: () => void }) {
  /* ‏D689: الورقةُ تصعد عند الفتح وتنزل عند الإغلاق — كانت تختفي فجأة. فالإغلاقُ يبدأ الحركةَ ثمّ يُبلغ الأبَ بعدها */
  const [leaving, setLeaving] = React.useState(false);
  const leavingRef = React.useRef(false);
  const close = React.useCallback(() => {
    if (leavingRef.current) return;
    leavingRef.current = true;
    setLeaving(true);
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    setTimeout(onClose, reduce ? 0 : 200);
  }, [onClose]);
  // قفل تمرير الصفحة خلف النافذة.
  React.useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    window.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = prev; window.removeEventListener("keydown", onKey); };
  }, [close]);

  return (
    <div className={"stock-sheet-overlay" + (leaving ? " leaving" : "")} onClick={e => { if (e.target === e.currentTarget) close(); }}>
      <div className="stock-sheet">
        <div className="stock-sheet-body">
          <StockView symbol={symbol} onClose={close} />
        </div>
      </div>
    </div>
  );
}
