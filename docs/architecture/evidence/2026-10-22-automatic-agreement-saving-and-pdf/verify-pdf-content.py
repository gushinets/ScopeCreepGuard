from pathlib import Path

from pypdf import PdfReader

root = Path('/workspace/output/local')
expected_text = {
    'en': 'Latest edit included in downloaded PDF',
    'ru': 'Последняя правка включена в скачанный PDF',
}
for locale, description in expected_text.items():
    rendered_texts = []
    for kind in ('agreement', 'archived'):
        path = root / f'automatic-{kind}-{locale}.pdf'
        assert path.read_bytes().startswith(b'%PDF-')
        reader = PdfReader(path)
        text = ' '.join(page.extract_text() for page in reader.pages)
        rendered_texts.append(text)
        for expected in (description, '777.25', 'EUR', '9.5', 'North Studio', 'Example Client', 'Written approval before delivery.'):
            assert expected in text, (path.name, expected)
        print(f'{path.name}: valid PDF, {len(reader.pages)} pages, latest text and all edited commercial terms verified')
    assert rendered_texts[0] == rendered_texts[1]
