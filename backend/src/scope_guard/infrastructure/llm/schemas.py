"""Provider schemas frozen from the existing TypeScript runtime."""

ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "verdict",
        "confidence",
        "summary",
        "reasoning",
        "citations",
        "suggestion",
        "replies",
        "changeOrder",
        "hasAdditionalWork",
        "clientLanguage",
        "changeOrderLabels",
    ],
    "properties": {
        "hasAdditionalWork": {"type": "boolean"},
        "clientLanguage": {
            "type": "string",
            "description": "Final resolved BCP 47 language for all client materials.",
        },
        "changeOrderLabels": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "title",
                "draft",
                "documentNumber",
                "created",
                "project",
                "provider",
                "client",
                "clientEmail",
                "requestedChange",
                "commercialTerms",
                "estimatedEffort",
                "additionalFee",
                "noAdditionalCharge",
                "scheduleImpact",
                "additionalTerms",
                "approval",
                "approvedBy",
                "date",
                "draftFooter",
                "introduction",
                "outsideScopeFree",
                "endDate",
                "rationale",
                "terms",
                "note",
                "page",
                "hours",
            ],
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "draft": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "documentNumber": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "created": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "project": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "provider": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "client": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "clientEmail": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "requestedChange": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "commercialTerms": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "estimatedEffort": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "additionalFee": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "noAdditionalCharge": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "scheduleImpact": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "additionalTerms": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "approval": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "approvedBy": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "date": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "draftFooter": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "introduction": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "outsideScopeFree": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "endDate": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "rationale": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "terms": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "note": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "page": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
                "hours": {
                    "type": "string",
                    "description": "Formal, neutral, non-empty, exclusively in clientLanguage.",
                },
            },
        },
        "verdict": {"type": "string", "enum": ["in_scope", "borderline", "out_of_scope"]},
        "confidence": {
            "type": "integer",
            "description": "Certainty as a percentage from 0 to 100, not a 0-1 fraction.",
            "minimum": 0,
            "maximum": 100,
        },
        "summary": {
            "type": "string",
            "description": "Non-empty. One-sentence verdict in the output language.",
        },
        "reasoning": {
            "type": "string",
            "description": "Non-empty. Explain the verdict from the provided scope only.",
        },
        "citations": {"type": "array", "items": {"type": "string"}},
        "suggestion": {"type": "string"},
        "replies": {
            "type": "object",
            "additionalProperties": False,
            "required": ["warm", "neutral", "firm"],
            "properties": {
                "warm": {"type": "string", "description": "Non-empty client reply."},
                "neutral": {"type": "string", "description": "Non-empty client reply."},
                "firm": {"type": "string", "description": "Non-empty client reply."},
            },
        },
        "changeOrder": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "description",
                "timelineImpact",
                "additionalCost",
                "note",
                "estimatedHours",
                "currency",
                "rationale",
            ],
            "properties": {
                "estimatedHours": {"type": "number"},
                "currency": {"type": "string", "enum": ["", "RUB", "USD", "EUR"]},
                "rationale": {"type": "string"},
                "description": {
                    "type": "string",
                    "description": "Non-empty in every verdict. For in_scope, name the included work.",  # noqa: E501 - frozen compatibility literal
                },
                "timelineImpact": {
                    "type": "string",
                    "description": "Non-empty in every verdict. For in_scope, say none / no extra time.",  # noqa: E501 - frozen compatibility literal
                },
                "additionalCost": {
                    "type": "string",
                    "description": "Decimal amount without currency symbol, for example 2400.00. For in_scope use 0.",  # noqa: E501 - frozen compatibility literal
                },
                "note": {
                    "type": "string",
                    "description": "Non-empty draft disclaimer, not legal advice.",
                },
            },
        },
    },
}

MATERIALS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["clientLanguage", "replies", "changeOrder", "changeOrderLabels"],
    "properties": {
        "clientLanguage": {"type": "string"},
        "replies": {
            "type": "object",
            "additionalProperties": False,
            "required": ["warm", "neutral", "firm"],
            "properties": {
                "warm": {"type": "string"},
                "neutral": {"type": "string"},
                "firm": {"type": "string"},
            },
        },
        "changeOrder": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["description", "timelineImpact", "rationale", "note"],
                    "properties": {
                        "description": {"type": "string"},
                        "timelineImpact": {"type": "string"},
                        "rationale": {"type": "string"},
                        "note": {"type": "string"},
                    },
                },
            ]
        },
        "changeOrderLabels": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "title",
                "draft",
                "documentNumber",
                "created",
                "project",
                "provider",
                "client",
                "clientEmail",
                "requestedChange",
                "commercialTerms",
                "estimatedEffort",
                "additionalFee",
                "noAdditionalCharge",
                "scheduleImpact",
                "additionalTerms",
                "approval",
                "approvedBy",
                "date",
                "draftFooter",
                "introduction",
                "outsideScopeFree",
                "endDate",
                "rationale",
                "terms",
                "note",
                "page",
                "hours",
            ],
            "properties": {
                "title": {"type": "string"},
                "draft": {"type": "string"},
                "documentNumber": {"type": "string"},
                "created": {"type": "string"},
                "project": {"type": "string"},
                "provider": {"type": "string"},
                "client": {"type": "string"},
                "clientEmail": {"type": "string"},
                "requestedChange": {"type": "string"},
                "commercialTerms": {"type": "string"},
                "estimatedEffort": {"type": "string"},
                "additionalFee": {"type": "string"},
                "noAdditionalCharge": {"type": "string"},
                "scheduleImpact": {"type": "string"},
                "additionalTerms": {"type": "string"},
                "approval": {"type": "string"},
                "approvedBy": {"type": "string"},
                "date": {"type": "string"},
                "draftFooter": {"type": "string"},
                "introduction": {"type": "string"},
                "outsideScopeFree": {"type": "string"},
                "endDate": {"type": "string"},
                "rationale": {"type": "string"},
                "terms": {"type": "string"},
                "note": {"type": "string"},
                "page": {"type": "string"},
                "hours": {"type": "string"},
            },
        },
    },
}
