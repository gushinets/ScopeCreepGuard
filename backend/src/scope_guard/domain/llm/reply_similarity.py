"""Deterministic textual similarity, not a measure of semantic equivalence."""

import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

REPLY_SIMILARITY_THRESHOLD = 0.72
# The gateway already refuses inputs over 32768 UTF-8 bytes, including framing.
# Keep the existing structural allowance separate from the CPU comparison cap.
MAX_REPLY_LENGTH = 32768
# SequenceMatcher is quadratic in the worst case. Never pass more than 2048
# normalized characters per side (256x smaller pair space than the former cap).
# Long replies remain valid, but novelty is explicitly unchecked; never truncate.
MAX_REPLY_COMPARISON_LENGTH = 2048


@dataclass(frozen=True)
class ReplyComparison:
    score: float | None
    skipped_reason: Literal["empty_previous", "comparison_limit"] | None = None


def normalize_reply(text: str) -> str:
    if len(text) > MAX_REPLY_LENGTH:
        raise ValueError("text.length: reply exceeds comparison limit")
    # Unicode expansion is linear in this bounded raw input. Expanded replies
    # still skip comparison rather than becoming structurally invalid.
    folded = unicodedata.normalize("NFKC", text).casefold()
    normalized = " ".join(
        "".join(" " if unicodedata.category(c).startswith("P") else c for c in folded).split()
    )
    return normalized


def compare_replies(previous: str, candidate: str) -> ReplyComparison:
    """Score whole normalized replies only within the safe CPU bound."""
    original = normalize_reply(previous)
    if not original:
        return ReplyComparison(None, "empty_previous")
    revised = normalize_reply(candidate)
    if max(len(original), len(revised)) > MAX_REPLY_COMPARISON_LENGTH:
        return ReplyComparison(None, "comparison_limit")
    if original == revised:
        return ReplyComparison(1.0)
    return ReplyComparison(SequenceMatcher(None, original, revised, autojunk=False).ratio())


def reply_similarity(previous: str, candidate: str) -> float | None:
    """Exact textual ratio, or None when checking was skipped; never an approximation."""
    return compare_replies(previous, candidate).score


def previous_reply(facts: dict) -> str:
    reply = facts["document"]["reply"]
    return reply.get("text") or reply["generated"].get(reply["tone"], "")
