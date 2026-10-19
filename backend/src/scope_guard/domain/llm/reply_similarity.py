"""Deterministic textual similarity, not a measure of semantic equivalence."""

import unicodedata
from difflib import SequenceMatcher

REPLY_SIMILARITY_THRESHOLD = 0.72
# The gateway already refuses inputs over 32768 UTF-8 bytes, including framing.
# Bound normalized comparison too (NFKC/casefold can expand characters). Never
# truncate: an oversized value must use the existing validation/error path.
MAX_REPLY_COMPARISON_LENGTH = 32768


def normalize_reply(text: str) -> str:
    if len(text) > MAX_REPLY_COMPARISON_LENGTH:
        raise ValueError("text.length: reply exceeds comparison limit")
    folded = unicodedata.normalize("NFKC", text).casefold()
    normalized = " ".join(
        "".join(" " if unicodedata.category(c).startswith("P") else c for c in folded).split()
    )
    if len(normalized) > MAX_REPLY_COMPARISON_LENGTH:
        raise ValueError("text.length: normalized reply exceeds comparison limit")
    return normalized


def reply_similarity(previous: str, candidate: str) -> float | None:
    """Return the exact normalized character ratio; no reference means no check."""
    original = normalize_reply(previous)
    if not original:
        return None
    revised = normalize_reply(candidate)
    if original == revised:
        return 1.0
    return SequenceMatcher(None, original, revised, autojunk=False).ratio()


def previous_reply(facts: dict) -> str:
    reply = facts["document"]["reply"]
    return reply.get("text") or reply["generated"].get(reply["tone"], "")
