"""Allocate fresh wire JSON from immutable generation outcomes."""

from scope_guard.modules.analysis.domain import (
    ABSENT,
    AnalysisResult,
    ClientMaterials,
    Labels,
    ProjectSnapshotV1,
)


def replies_to_wire(replies):
    return {"warm": replies.warm, "neutral": replies.neutral, "firm": replies.firm}


def analysis_to_wire(result: AnalysisResult) -> dict:
    co = result.change_order
    change_order: dict = {
        "description": co.description,
        "timelineImpact": co.timeline_impact,
        "additionalCost": co.additional_cost,
        "note": co.note,
    }
    for key, optional in (
        ("estimatedHours", co.estimated_hours),
        ("currency", co.currency),
        ("rationale", co.rationale),
    ):
        if optional != ABSENT:
            change_order[key] = optional
    wire = {
        "verdict": result.verdict,
        "confidence": result.confidence,
        "summary": result.summary,
        "reasoning": result.reasoning,
        "citations": list(result.citations),
        "replies": replies_to_wire(result.replies),
        "changeOrder": change_order,
        "clientLanguage": result.client_language,
    }
    for key, extra in (
        (
            "changeOrderLabels",
            dict(result.change_order_labels.values)
            if isinstance(result.change_order_labels, Labels)
            else ABSENT,
        ),
        ("hasAdditionalWork", result.has_additional_work),
        ("requestLanguage", result.request_language),
        ("estimateValid", result.estimate_valid),
        ("suggestion", result.suggestion),
        ("draftCreatedAt", result.draft_created_at),
        ("commercialSignature", result.commercial_signature),
    ):
        if extra != ABSENT:
            wire[key] = extra
    return wire


def materials_to_wire(value: ClientMaterials) -> dict:
    co = value.change_order
    wire = {
        "clientLanguage": value.client_language,
        "replies": replies_to_wire(value.replies),
        "changeOrder": None
        if co is None
        else {
            "description": co.description,
            "timelineImpact": co.timeline_impact,
            "rationale": co.rationale,
            "note": co.note,
        },
    }
    if isinstance(value.change_order_labels, Labels):
        wire["changeOrderLabels"] = dict(value.change_order_labels.values)
    return wire


def snapshot_to_wire(value: ProjectSnapshotV1) -> dict:
    p = value.context
    return {
        **({"clientName": p.client_name} if p.client_name != ABSENT else {}),
        "version": 1,
        "name": p.name,
        "industry": p.industry,
        "scope": p.scope,
        "startDate": p.start_date,
        "endDate": value.end_date,
        "pricingModel": p.pricing_model,
        "currency": p.currency,
        "hourlyRate": p.hourly_rate,
        "fixedPrice": p.fixed_price,
        "documentLanguage": value.document_language,
    }
