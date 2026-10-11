# Change Order PDF visual verification

Run `uv run python scripts/verify_any641_pdf.py --output ../output/pdf/verification-<unique-name>` from `backend/`. The command creates English, Russian, Spanish and German PDFs, long documents, missing commercial values and oversized metadata/approval rows, then renders every page to PNG. Use a fresh output directory for each inspection.

Inspect the PNG files for readable text and commercial terms, visible approval lines, page-bounded signatures, and unobstructed footers and page numbers. The explicit verification command requires Poppler's `pdftoppm`; normal unit tests do not generate these artifacts or require Poppler.

German fixtures verify supplied document labels, localized dates, hours, and accented characters. PDF glyph coverage remains limited to the bundled Noto Sans fonts; arbitrary scripts and shaping are not covered by these fixtures.
