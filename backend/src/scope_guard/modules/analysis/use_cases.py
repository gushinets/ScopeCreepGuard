"""Ordered read-only business workflows; no open read work reaches the generator."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from scope_guard.core.js_compat import trim, utf16_length
from scope_guard.modules.analysis.context import historical_context, project_context
from scope_guard.modules.analysis.domain import (
    ABSENT,
    AnalysisInput,
    AnalyzeCommand,
    AnalyzeOutcome,
    DraftProofBinding,
    DraftProofClaims,
    GenerationError,
    LocaleResolution,
    MaterialInput,
    MaterialsCommand,
    MaterialsOutcome,
    ProjectSnapshotV1,
    RegenerateReplyCommand,
    ReplyInput,
    ReplyOutcome,
    freeze,
    thaw,
)
from scope_guard.modules.analysis.normalization import parse_analysis
from scope_guard.modules.analysis.ports import (
    DraftProofPort,
    GenerationPort,
    LimiterPort,
    ReadWorkFactory,
)
from scope_guard.modules.change_orders.estimation import commercial_signature


def interface_locale(value: LocaleResolution, *, analyze=False) -> str:
    if value.failed or analyze and value.value not in ("en", "ru"):
        raise RuntimeError("locale_resolution_failed")
    if value.value not in ("en", "ru"):
        raise GenerationError("localeInvalid")
    return value.value


def size_guard(*values: str, extra=0):
    if sum(utf16_length(value) for value in values) + extra > 100_000:
        raise GenerationError("analysisInputTooLarge")


class GenerationUseCases:
    def __init__(
        self,
        reads: ReadWorkFactory,
        generator: GenerationPort,
        proofs: DraftProofPort,
        limiter: LimiterPort,
        clock,
    ):
        self.reads, self.generator, self.proofs, self.limiter, self.clock = (
            reads,
            generator,
            proofs,
            limiter,
            clock,
        )

    async def owned(self, work, owner: str, project: str):
        value = await work.projects.get_owned(UUID(owner), UUID(project))
        if value is None:
            raise GenerationError("projectNotFound", 404)
        return project_context(value)

    def allowance(self, owner: str):
        if not self.limiter.allow(owner, int(self.clock() * 1000)):
            raise GenerationError("analysisRateLimited", 429)

    def timestamp(self):
        return (
            datetime.fromtimestamp(self.clock(), UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

    async def analyze(
        self, owner: str, command: AnalyzeCommand, resolved: LocaleResolution
    ) -> AnalyzeOutcome:
        async with self.reads() as work:
            context = await self.owned(work, owner, command.project_id)
        if command.end_date and context.start_date and command.end_date < context.start_date:
            raise GenerationError("requestBodyInvalid")
        if not trim(context.scope):
            raise GenerationError("scopeRequired")
        self.allowance(owner)
        size_guard(context.scope, command.request)
        locale = interface_locale(resolved, analyze=True)
        timestamp = self.timestamp()
        result = await self.generator.analyze(
            AnalysisInput(
                context,
                command.request,
                locale,
                command.end_date,
                timestamp,
                command.document_language,
            )
        )
        if (
            result.has_additional_work is True
            and context.currency
            and result.change_order.currency != context.currency
        ):
            result = replace(result, estimate_valid=False)
        result = replace(
            result,
            draft_created_at=timestamp,
            commercial_signature=commercial_signature(context, command.end_date),
        )
        snapshot = ProjectSnapshotV1(context, command.end_date, command.document_language)
        # Keep construction immutable; serialize only at the token infrastructure boundary.
        from scope_guard.modules.analysis.serialization import snapshot_to_wire

        proof = self.proofs.issue(
            DraftProofClaims(
                DraftProofBinding(owner, context.project_id, command.request, locale),
                result,
                freeze(snapshot_to_wire(snapshot)),
            )
        )
        return AnalyzeOutcome(result, snapshot, proof)

    async def regenerate_reply(
        self, owner: str, command: RegenerateReplyCommand, resolved: LocaleResolution
    ) -> ReplyOutcome:
        async with self.reads() as work:
            context = await self.owned(work, owner, command.project_id)
        if not trim(context.scope):
            raise GenerationError("scopeRequired")
        size_guard(context.scope, command.request, command.previous_reply)
        self.allowance(owner)
        locale = interface_locale(resolved)
        return ReplyOutcome(
            await self.generator.regenerate_reply(
                ReplyInput(
                    context,
                    command.request,
                    locale,
                    command.tone,
                    command.previous_reply,
                    command.document_language,
                )
            )
        )

    async def translate_materials(
        self, owner: str, command: MaterialsCommand, resolved: LocaleResolution
    ) -> MaterialsOutcome:
        async with self.reads() as work:
            context = await self.owned(work, owner, command.project_id)
            history = None
            if command.history_id != ABSENT:
                entries = await work.history.for_project(UUID(context.project_id))
                history = next(
                    (item for item in entries if str(item.id) == command.history_id), None
                )
                if history is None or history.request != command.request:
                    raise GenerationError("requestBodyInvalid")
            locale = interface_locale(resolved)
            context = await historical_context(
                work, self.proofs, owner, context, command.request, command.selector, locale
            )
        try:
            analysis = parse_analysis(thaw(command.analysis), locale)
        except (ValueError, TypeError):
            raise GenerationError("requestBodyInvalid") from None
        if history and (analysis.verdict != history.verdict or analysis.summary != history.summary):
            raise GenerationError("requestBodyInvalid")
        size_guard(context.scope, extra=command.input_length)
        self.allowance(owner)
        return MaterialsOutcome(
            await self.generator.translate_materials(
                MaterialInput(context, command.request, locale, command.client_language, analysis)
            )
        )
