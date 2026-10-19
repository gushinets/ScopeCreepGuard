"""In-memory durable-step boundary for the real gateway and native-output runner."""

from uuid import uuid4

from scope_guard.domain.llm.runtime import PROMPT_VERSION, GatewayFailure

APPROVED = {"decision": "accept", "violations": []}


class ReviewLedger:
    def __init__(self):
        self.calls, self.feedbacks, self.records = [], [], {}

    async def steps(self, operation):
        return list(self.records.values())

    def review_slot(self, binding, stage, attempt):
        name = f"{stage}_review_{attempt}"
        return self.records.setdefault(
            name,
            {
                "id": uuid4(),
                "stage_key": name,
                "status": "pending",
                "semantic_attempt": 0,
                "transport_attempt": 0,
                "candidate": None,
                "prepared_request": None,
                "prompt_version": PROMPT_VERSION,
                "schema_version": "stage-v1",
                "accepted_result": None,
                "input_hash": None,
            },
        )

    async def freeze_stage(self, binding, input_hash):
        step = next(r for r in self.records.values() if r["id"] == binding.step_id)
        if step["input_hash"] and step["input_hash"] != input_hash:
            raise GatewayFailure("workflowVersionUnavailable")
        step["input_hash"] = input_hash

    async def reserve(self, request, transport_attempt):
        step = next((r for r in self.records.values() if r["id"] == request.binding.step_id), None)
        if step:
            step.update(
                status="running",
                semantic_attempt=request.semantic_attempt,
                transport_attempt=transport_attempt,
            )
        self.calls.append({"request": request, "transport": transport_attempt})
        return len(self.calls) - 1

    async def complete(self, identifier, response=None, error=None):
        self.calls[identifier].update(response=response, error=error)

    async def checkpoint(self, request, response):
        step = next((r for r in self.records.values() if r["id"] == request.binding.step_id), None)
        if step:
            step.update(
                candidate=response.text, status="running", semantic_attempt=request.semantic_attempt
            )

    async def accept(self, binding, value):
        step = next(r for r in self.records.values() if r["id"] == binding.step_id)
        step.update(status="accepted", accepted_result=value, candidate=None)

    async def feedback(self, binding, error):
        self.feedbacks.append(error)
        call = next(
            c for c in reversed(self.calls) if c["request"].binding.step_id == binding.step_id
        )
        call["rejected"] = True

    async def remember_reply(self, binding, novelty):
        step = next((r for r in self.records.values() if r["id"] == binding.step_id), None)
        if step:
            step["feedback"] = {**(step.get("feedback") or {}), "novelty": novelty}
