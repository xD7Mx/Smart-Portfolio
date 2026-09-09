import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Layers, Users, Pencil, Check, X, Globe } from "lucide-react";
import { companiesApi } from "../../services/api";
import { useAuthStore } from "../../store/authStore";

/* ══ نبذةُ الشركة وإدارتها — بطاقتان بلغةٍ واحدة ══ (بأمر المالك · D209)
   كانتا داخل صفحة الشركة المملوكة وحدَها، فتُعرّف الشاشةُ بالشركة هناك
   وتصمت عنها في السوق. ونسخُهما كان سيُنتج تصميمين يتباعدان مع أوّل
   تعديل — وهي علّةُ هذا التطبيق المتكرّرة. فنُقلتا كما هما.

   وتقبلان **مُعرِّفَ صفٍّ أو رمزاً**: بالمعرِّف يكتب المالكُ نبذتَه،
   وبالرمز تُقرأ نبذةُ ياهو لورقةٍ لا يملكها. */

const DESC_SOURCE_LABEL: Record<string, { label: string; tone: string }> = {
  manual: { label: "نصّك المحفوظ", tone: "var(--pos-ink)" },
};

export default function CompanyProfileCards(
  { companyId, symbol }: { companyId?: number; symbol?: string },
) {
  const canEdit = companyId != null;
  const qc = useQueryClient();
  const { canWrite: owner } = useAuthStore();
  const { data, isLoading } = useQuery({
    queryKey: ["company-profile", companyId ?? symbol],
    queryFn: () => (companyId != null
      ? companiesApi.profile(companyId)
      : companiesApi.profileBySymbol(String(symbol))).then(r => r.data.data).catch(() => null),
    enabled: companyId != null || !!symbol,
  });

  const [editDesc, setEditDesc] = useState(false);
  const [descDraft, setDescDraft] = useState("");

  const save = useMutation({
    mutationFn: (payload: any) => companiesApi.saveProfile(companyId!, payload).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["company-profile", companyId ?? symbol] });
      setEditDesc(false);
    },
  });

  const src = data?.description_source ? DESC_SOURCE_LABEL[data.description_source] : null;
  const execs: { name: string; title: string }[] = data?.executives ?? [];
  const isEnglish = data?.description_source === "yahoo";
  const hasDesc = !!data?.description;

  /* لا شيء من Yahoo ولا نصٌّ محفوظ ⇒ لا بطاقة إطلاقاً. عنوانٌ فوق فراغٍ يبدو
     خللاً، وإخفاؤه أنظف من رسالة «لا بيانات» في صفحةٍ مزدحمة أصلاً. الاستثناء
     الوحيد: المالك يرى البطاقة كي يستطيع كتابة النبذة بنفسه. */
  if (!isLoading && !hasDesc && execs.length === 0 && !canWrite) return null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* ① نبذة النشاط */}
      {(hasDesc || isLoading || canWrite) && (
      <div className="card">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 min-w-0">
            <Layers size={15} className="text-[var(--brand-ink)] shrink-0" />
            <p className="card-title">نبذة عن نشاط الشركة</p>
            {src && (
              <span className="text-[10px] px-1.5 py-0.5 rounded shrink-0"
                style={{ background: `color-mix(in srgb, ${src.tone} 12%, transparent)`, color: src.tone }}>{src.label}</span>
            )}
          </div>
          {canWrite && !editDesc && (
            <button className="p-1 rounded-lg text-[var(--ink-muted)] hover:text-[var(--warn-ink)] transition-all shrink-0"
              title="تحرير النبذة"
              onClick={() => { setDescDraft(data?.description || ""); setEditDesc(true); }}>
              <Pencil size={13} />
            </button>
          )}
        </div>

        {editDesc ? (
          <div className="space-y-2">
            <textarea className="input" rows={7} value={descDraft} onChange={e => setDescDraft(e.target.value)}
              placeholder="اكتب نبذة عن نشاط الشركة…" autoFocus />
            <p className="text-[10px] text-[var(--ink-muted)]">
              نصّك يتقدّم على المصدر ولا يُستبدَل. وإفراغ الحقل يُعيد الجلب من Yahoo.
            </p>
            <div className="flex gap-2">
              <button className="btn-primary flex-1" disabled={save.isPending}
                onClick={() => save.mutate({ description: descDraft })}>
                {save.isPending ? "جارٍ الحفظ…" : "حفظ"}
              </button>
              <button className="btn-ghost" onClick={() => setEditDesc(false)}>إلغاء</button>
            </div>
          </div>
        ) : isLoading ? (
          <div className="h-20 skeleton" />
        ) : hasDesc ? (
          <>
            <p className="text-[13px] text-[var(--ink)] leading-relaxed" dir={isEnglish ? "ltr" : undefined}
              style={isEnglish ? { textAlign: "left" } : undefined}>
              {data.description}
            </p>
            {(data.website || data.employees) && (
              <div className="flex items-center gap-4 mt-3 pt-3 border-t border-[var(--hairline)] text-[11px]">
                {data.employees ? (
                  <span className="text-[var(--ink-muted)]">الموظفون: <span className="text-[var(--ink)] tabular-nums">{fmt0(data.employees)}</span></span>
                ) : null}
                {data.website && (
                  <a href={data.website} target="_blank" rel="noopener noreferrer"
                    className="text-[var(--brand-ink)] hover:text-[var(--brand-ink)] truncate" dir="ltr">{data.website}</a>
                )}
              </div>
            )}
          </>
        ) : (
          <Empty label="لا نبذة متاحة من المصدر — اكتبها بنفسك من زر التحرير" />
        )}
      </div>
      )}

      {/* ② الإدارة التنفيذية — تظهر فقط إن وفّرها Yahoo فعلاً */}
      {execs.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Star size={15} className="text-[var(--brand-ink)] shrink-0" />
            <p className="card-title">الإدارة التنفيذية</p>
          </div>
          {/* تمريرٌ أفقيّ بأمر المالك. وكانت قائمةً رأسية يُقصّ فيها الاسم
              الطويل بـ`truncate` — أي أن العلاج القديم للضيق كان **إخفاء
              الاسم**. والصفّ الأفقيّ يُعطي كلّ اسمٍ عرضه كاملاً ويُبقي
              الزائد وراء التمرير بدل أن يبتره.
              و`snap` يُوقف الصفّ عند بطاقةٍ كاملة لا عند نصفها على الجوال. */}
          <div className="overflow-x-auto -mx-1 px-1 pb-1 snap-x snap-mandatory">
            <div className="flex gap-2 w-max">
              {execs.slice(0, 10).map((o, i) => (
                <div key={i}
                  className="snap-start shrink-0 w-[190px] rounded-xl border border-[var(--hairline)] bg-[var(--field)] px-3 py-2.5"
                  /* الاسم اللاتينيّ الأصل يبقى متاحاً عند المرور — فالنقل
                     الصوتيّ لا يُلغي ما يُبحث به. */
                  title={(o as any).name_en || undefined}>
                  {/* الاسم صار عربياً من الخادم، فيتبع اتجاه الصفحة.
                      و`auto` تحمي ما تعذّر نقله فبقي لاتينياً. */}
                  <p className="text-[12.5px] text-[var(--ink)] leading-snug" dir="auto">{o.name}</p>
                  {o.title && (
                    <p className="text-[10.5px] text-[var(--ink-muted)] mt-1 leading-snug" dir="auto">{o.title}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
