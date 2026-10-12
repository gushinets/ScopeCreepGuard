"""Composition for isolated document preparation, with concrete localization."""

from scope_guard.integrations.documents import localization
from scope_guard.services.documents.service import prepare_document as prepare


def prepare_document(draft, project_snapshot=None):
    return prepare(draft, project_snapshot, localization=localization)
