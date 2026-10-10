from dataclasses import replace

from scope_guard.core.js_compat import trim
from scope_guard.modules.analysis.context import historical_context
from scope_guard.modules.analysis.domain import AnalysisInput, EstimateOutcome, GenerationError
from scope_guard.modules.analysis.use_cases import interface_locale, size_guard
from scope_guard.modules.change_orders.estimation import commercial_signature


class EstimateChangeOrder:
    def __init__(self, generation):
        self.generation = generation

    async def execute(self, owner, command, resolved):
        service = self.generation
        async with service.reads() as work:
            context = await service.owned(work, owner, command.project_id)
            locale = interface_locale(resolved)
            context = await historical_context(
                work, service.proofs, owner, context, command.request, command.selector, locale
            )
        if command.end_date and context.start_date and command.end_date < context.start_date:
            raise GenerationError("requestBodyInvalid")
        if not (
            context.start_date
            and context.pricing_model
            and context.currency
            and (context.hourly_rate or context.fixed_price)
        ):
            raise GenerationError("pricingModelInvalid")
        size_guard(context.scope, command.request)
        service.allowance(owner)
        timestamp = service.timestamp()
        result = await service.generator.analyze(
            AnalysisInput(
                context,
                trim(command.request),
                locale,
                command.end_date,
                timestamp,
                command.document_language,
            )
        )
        if result.verdict == "in_scope" or result.has_additional_work is not True:
            raise GenerationError("analysisInvalid", 409)
        if result.estimate_valid is not True or result.change_order.currency != context.currency:
            raise GenerationError("analysisInvalid", 502)
        return EstimateOutcome(
            replace(
                result,
                draft_created_at=timestamp,
                commercial_signature=commercial_signature(context, command.end_date),
            )
        )
