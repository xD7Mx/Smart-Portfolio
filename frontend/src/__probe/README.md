مِنصّةُ قياسٍ للجنة — لا تدخل الحزمة.

`vite` يبني `index.html` وحدَها، و`probe.html` ليست مُدخَلاً — فهذا
المجلّد لا يظهر في `build/` (مُتحقَّقٌ منه). الغرضُ منه تركيبُ مكوّنٍ
واحدٍ بمعزلٍ عن التطبيق ليُقاس من الـDOM: `scripts/audit/tabs_row.mjs`.

    cd frontend && npx vite --port 5199 --strictPort &
    node scripts/audit/tabs_row.mjs
