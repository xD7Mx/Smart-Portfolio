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
  // قفل تمرير الصفحة خلف النافذة.
  React.useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = prev; window.removeEventListener("keydown", onKey); };
  }, [onClose]);

  return (
    <div className="stock-sheet-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="stock-sheet fade-in">
        <div className="stock-sheet-body">
          <StockView symbol={symbol} onClose={onClose} />
        </div>
      </div>
    </div>
  );
}
