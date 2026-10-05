# Change Order PDF visual verification

Run `pnpm verify:change-order-pdf` from the repository root. The command creates normal Russian, long multi-page Russian, English, and Spanish PDFs and renders every page to PNG under `output/pdf/verification/`.

Inspect the PNG files for readable text and commercial terms, visible approval lines, page-bounded signatures, and unobstructed footers and page numbers. The explicit verification command requires Poppler's `pdftoppm`; normal unit tests do not generate these artifacts or require Poppler.
