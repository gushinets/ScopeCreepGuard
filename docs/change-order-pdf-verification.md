# Change Order PDF visual verification

Run `corepack pnpm verify:change-order-pdf` from `frontend/`. The command creates normal Russian, long multi-page Russian, English, Spanish, and German PDFs and renders every page to PNG in a fresh `frontend/output/pdf/verification-any-635-<timestamp>/` directory. Existing artifacts are preserved.

Inspect the PNG files for readable text and commercial terms, visible approval lines, page-bounded signatures, and unobstructed footers and page numbers. The explicit verification command requires Poppler's `pdftoppm`; normal unit tests do not generate these artifacts or require Poppler.

German fixtures verify supplied document labels, localized dates, hours, and accented characters. PDF glyph coverage remains limited to the bundled Noto Sans fonts; arbitrary scripts and shaping are not covered by these fixtures.
