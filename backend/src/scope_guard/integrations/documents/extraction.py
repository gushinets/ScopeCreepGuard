"""Composition for isolated extraction, with concrete file readers."""

from scope_guard.integrations.documents.scope_readers.pdf import read_pdf
from scope_guard.integrations.documents.scope_readers.text import read_text
from scope_guard.services.scope_extraction.service import extract as extract_scope


class Readers:
    read_pdf = staticmethod(read_pdf)
    read_text = staticmethod(read_text)


def extract(name: str, content_type: str, data: bytes):
    return extract_scope(name, content_type, data, readers=Readers())
