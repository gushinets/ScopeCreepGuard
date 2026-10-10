"""Synthetic stdin-only cross-runtime proof test driver, never a production entrypoint."""

import json
import sys

from scope_guard.infrastructure.auth.draft_proofs import DraftProofs
from scope_guard.modules.analysis.domain import DraftProofBinding, DraftProofClaims, freeze, thaw
from scope_guard.modules.analysis.normalization import parse_snapshot
from scope_guard.modules.analysis.serialization import analysis_to_wire

data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
adapter = DraftProofs(data["secret"], lambda: data["now"])
claims = data["claims"]
binding = DraftProofBinding(*(claims[key] for key in ("userId", "projectId", "request", "locale")))
if data["action"] == "issue":
    print(
        adapter.issue(
            DraftProofClaims(
                binding,
                parse_snapshot(claims["analysisSnapshot"], binding.locale),
                freeze(claims["projectSnapshot"]),
            )
        )
    )
else:
    verified = adapter.verify(data["proof"], binding)
    print(
        json.dumps(
            {
                "analysisSnapshot": analysis_to_wire(verified.analysis_snapshot),
                "projectSnapshot": thaw(verified.project_snapshot),
            }
        )
    )
