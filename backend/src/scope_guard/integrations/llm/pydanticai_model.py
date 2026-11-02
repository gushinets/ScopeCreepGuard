"""NativeOutput model bridge. It has no independent provider client or retry policy."""

from dataclasses import replace

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    RetryFeedbackPart,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.profiles import ModelProfile
from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
from pydantic_ai.usage import RequestUsage

from scope_guard.integrations.llm.gateway import GatewayFailure, ProviderRequest


class GatewayResponsesModel(Model):
    def __init__(self, gateway, binding, prepared_request=None):
        super().__init__(
            profile=ModelProfile(
                supports_json_schema_output=True,
                json_schema_transformer=OpenAIJsonSchemaTransformer,
            )
        )
        self.gateway, self.binding = gateway, binding
        self.semantic = binding.semantic_start
        self.prepared_request = prepared_request
        self.retry_feedback = []

    def prepare_messages(self, messages, model_request_parameters=None):
        # The SDK renders RetryFeedbackPart as user text before request(). Keep
        # typed feedback for the ledger, while retaining its safe wire rendering.
        self.retry_feedback = []
        for message in reversed(messages):
            if isinstance(message, ModelResponse):
                break
            if isinstance(message, ModelRequest):
                self.retry_feedback.extend(
                    part for part in message.parts if isinstance(part, RetryFeedbackPart)
                )
        return super().prepare_messages(messages, model_request_parameters)

    async def record_feedback(self, part):
        if isinstance(part.content, list):
            message = "output.structure: " + "; ".join(
                ".".join(map(str, e["loc"])) + ": " + e["type"] for e in part.content
            )
        else:
            message = part.content
        await self.gateway.validation_feedback(self.binding, message)

    @property
    def model_name(self):
        return self.binding.model

    @property
    def system(self):
        return "openai"

    async def request(self, messages, model_settings, model_request_parameters):
        _, parameters = self.prepare_request(model_settings, model_request_parameters)
        if (
            parameters.output_mode != "native"
            or parameters.output_object is None
            or (parameters.function_tools or parameters.native_tools)
        ):
            raise ValueError("nativeStructuredOutputRequired")
        serialized = []
        for message in messages:
            if isinstance(message, ModelRequest):
                if message.instructions:
                    serialized.append({"role": "system", "content": message.instructions})
                for part in message.parts:
                    if isinstance(part, (SystemPromptPart, UserPromptPart)):
                        serialized.append(
                            {
                                "role": "system" if isinstance(part, SystemPromptPart) else "user",
                                "content": part.content,
                            }
                        )
                    elif isinstance(part, RetryPromptPart):
                        serialized.append({"role": "user", "content": part.model_response()})
                        await self.record_feedback(part)
            elif isinstance(message, ModelResponse):
                for part in message.parts:
                    if isinstance(part, TextPart):
                        serialized.append({"role": "assistant", "content": part.content})
        feedback, self.retry_feedback = self.retry_feedback, []
        for part in feedback:
            await self.record_feedback(part)
        self.semantic += 1
        output = parameters.output_object
        if self.binding.transport_start and self.semantic == self.binding.semantic_start + 1:
            if not self.prepared_request or self.prepared_request["schema"] != output.json_schema:
                raise GatewayFailure("workflowVersionUnavailable")
            serialized = self.prepared_request["messages"]
        observed = await self.gateway.request(
            ProviderRequest(
                replace(
                    self.binding,
                    transport_start=self.binding.transport_start
                    if self.semantic == self.binding.semantic_start + 1
                    else 0,
                ),
                self.semantic,
                serialized,
                output.json_schema,
                output.name or "stage_output",
                60,
            )
        )
        if observed.status != "completed" or not observed.text.strip():
            raise GatewayFailure("providerOutputIncomplete")
        return ModelResponse(
            parts=[TextPart(observed.text)],
            model_name=observed.model,
            provider_name=observed.provider,
            provider_response_id=observed.response_id,
            provider_details={
                "request_id": observed.request_id,
                "usage_status": "reported"
                if observed.input_tokens is not None and observed.output_tokens is not None
                else "unknown",
            },
            usage=RequestUsage(
                input_tokens=observed.input_tokens or 0,
                output_tokens=observed.output_tokens or 0,
                cache_read_tokens=observed.cached_tokens or 0,
            ),
        )
