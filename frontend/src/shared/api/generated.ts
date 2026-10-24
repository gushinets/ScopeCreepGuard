export interface paths {
    "/health/live": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Live */
        get: operations["live_health_live_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ready */
        get: operations["ready_health_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/register": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Register */
        post: operations["register_api_auth_register_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login_api_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["logout_api_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Me */
        get: operations["me_api_auth_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Projects */
        get: operations["list_projects_api_projects_get"];
        put?: never;
        /** Create Project */
        post: operations["create_project_api_projects_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/projects/{project_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Project */
        get: operations["get_project_api_projects__project_id__get"];
        put?: never;
        post?: never;
        /** Delete Project */
        delete: operations["delete_project_api_projects__project_id__delete"];
        options?: never;
        head?: never;
        /** Update Project */
        patch: operations["update_project_api_projects__project_id__patch"];
        trace?: never;
    };
    "/api/projects/{project_id}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create History */
        post: operations["create_history_api_projects__project_id__history_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/analyze": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Analyze
         * @description Generation requires the durable LLM workflow (otherwise 503 workflowUnavailable), an owned working draftId, expectedRevision, and a stable UUID operationId or Idempotency-Key. Returns 202 for pending work; poll statusUrl until terminal. Client snapshots are not authoritative.
         */
        post: operations["analyze_api_analyze_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/replies/regenerate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reply
         * @description Generation requires the durable LLM workflow (otherwise 503 workflowUnavailable), an owned working draftId, expectedRevision, and a stable UUID operationId or Idempotency-Key. Returns 202 for pending work; poll statusUrl until terminal. Client snapshots are not authoritative.
         */
        post: operations["reply_api_replies_regenerate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/client-materials/language": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Materials
         * @description Generation requires the durable LLM workflow (otherwise 503 workflowUnavailable), an owned working draftId, expectedRevision, and a stable UUID operationId or Idempotency-Key. Returns 202 for pending work; poll statusUrl until terminal. Client snapshots are not authoritative.
         */
        post: operations["materials_api_client_materials_language_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/change-orders/estimate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Estimate
         * @description Generation requires the durable LLM workflow (otherwise 503 workflowUnavailable), an owned working draftId, expectedRevision, and a stable UUID operationId or Idempotency-Key. Returns 202 for pending work; poll statusUrl until terminal. Client snapshots are not authoritative.
         */
        post: operations["estimate_api_change_orders_estimate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/drafts/{draftId}/pdf": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Saved Pdf */
        get: operations["saved_pdf_api_drafts__draftId__pdf_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/change-orders/pdf": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Preview Pdf */
        post: operations["preview_pdf_api_change_orders_pdf_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/change-orders/pdf": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Preview Pdf */
        post: operations["preview_pdf_api_v2_change_orders_pdf_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/scope/extract": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Scope Extract */
        post: operations["scope_extract_api_scope_extract_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/drafts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Drafts */
        get: operations["list_drafts_api_drafts_get"];
        put?: never;
        /** Create Draft */
        post: operations["create_draft_api_drafts_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/drafts/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Draft */
        get: operations["get_draft_api_drafts__id__get"];
        /** Update Draft */
        put: operations["update_draft_api_drafts__id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/locale": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Set Locale */
        post: operations["set_locale_api_locale_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/evaluations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Evaluation */
        post: operations["create_evaluation_api_evaluations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/evaluations/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Evaluations */
        get: operations["export_evaluations_api_evaluations_export_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/legacy-drafts/{identifier}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Legacy Revision */
        get: operations["legacy_revision_api_v2_legacy_drafts__identifier__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Projects */
        get: operations["projects_api_v2_projects_get"];
        put?: never;
        /** Create Project */
        post: operations["create_project_api_v2_projects_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/projects/{identifier}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Project */
        get: operations["project_api_v2_projects__identifier__get"];
        put?: never;
        post?: never;
        /** Archive Project */
        delete: operations["archive_project_api_v2_projects__identifier__delete"];
        options?: never;
        head?: never;
        /** Update Project */
        patch: operations["update_project_api_v2_projects__identifier__patch"];
        trace?: never;
    };
    "/api/v2/projects/{identifier}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restore Project */
        post: operations["restore_project_api_v2_projects__identifier__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/projects/{identifier}/draft": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Project Draft */
        get: operations["project_draft_api_v2_projects__identifier__draft_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Draft Collection */
        get: operations["draft_collection_api_v2_drafts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts/export.csv": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Drafts Csv */
        get: operations["export_drafts_csv_api_v2_drafts_export_csv_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts/{identifier}/export.csv": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Draft Csv */
        get: operations["export_draft_csv_api_v2_drafts__identifier__export_csv_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts/{identifier}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Draft */
        get: operations["draft_api_v2_drafts__identifier__get"];
        /** Save Draft */
        put: operations["save_draft_api_v2_drafts__identifier__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts/{identifier}/clear": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Clear Draft */
        post: operations["clear_draft_api_v2_drafts__identifier__clear_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts/{identifier}/revisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Revisions */
        get: operations["revisions_api_v2_drafts__identifier__revisions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts/{identifier}/revisions/{number}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restore */
        post: operations["restore_api_v2_drafts__identifier__revisions__number__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts/{identifier}/analyses": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Analyze */
        post: operations["analyze_api_v2_drafts__identifier__analyses_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/analyses/{identifier}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Run */
        get: operations["run_api_v2_analyses__identifier__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts/{identifier}/agreement": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Prepare Agreement */
        post: operations["prepare_agreement_api_v2_drafts__identifier__agreement_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts/{identifier}/estimate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Estimate */
        post: operations["estimate_api_v2_drafts__identifier__estimate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/analyses/{identifier}/apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Apply */
        post: operations["apply_api_v2_analyses__identifier__apply_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts/{identifier}/regenerate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Regenerate */
        post: operations["regenerate_api_v2_drafts__identifier__regenerate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts/{identifier}/translate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Translate */
        post: operations["translate_api_v2_drafts__identifier__translate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/llm-operations/{identifier}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Llm Status */
        get: operations["llm_status_api_v2_llm_operations__identifier__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/drafts/{identifier}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete */
        post: operations["complete_api_v2_drafts__identifier__history_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/projects/{identifier}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Histories */
        get: operations["histories_api_v2_projects__identifier__history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/history/{identifier}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** History */
        get: operations["history_api_v2_history__identifier__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/history/{identifier}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reopen History */
        post: operations["reopen_history_api_v2_history__identifier__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/history/{identifier}/change-orders": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Agreements */
        get: operations["agreements_api_v2_history__identifier__change_orders_get"];
        put?: never;
        /** Finalize */
        post: operations["finalize_api_v2_history__identifier__change_orders_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/change-orders/{identifier}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Agreement */
        get: operations["agreement_api_v2_change_orders__identifier__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/change-orders/{identifier}/void": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Void */
        post: operations["void_api_v2_change_orders__identifier__void_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/change-orders/{identifier}/exports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Exports */
        get: operations["exports_api_v2_change_orders__identifier__exports_get"];
        put?: never;
        /** Create Export */
        post: operations["create_export_api_v2_change_orders__identifier__exports_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/exports/{identifier}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export */
        get: operations["export_api_v2_exports__identifier__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/exports/{identifier}/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Retry */
        post: operations["retry_api_v2_exports__identifier__retry_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/exports/{identifier}/download": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Download */
        get: operations["download_api_v2_exports__identifier__download_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/analyses/{identifier}/evaluation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Evaluate */
        post: operations["evaluate_api_v2_analyses__identifier__evaluation_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/profile/onboarding": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Onboarding */
        get: operations["onboarding_api_v2_profile_onboarding_get"];
        put?: never;
        /** Advance Onboarding */
        post: operations["advance_onboarding_api_v2_profile_onboarding_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v2/profile": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Profile */
        get: operations["profile_api_v2_profile_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Profile */
        patch: operations["update_profile_api_v2_profile_patch"];
        trace?: never;
    };
    "/api/v2/session/interaction": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Interaction */
        post: operations["interaction_api_v2_session_interaction_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AgreementDTO */
        AgreementDTO: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Projectid
             * Format: uuid
             */
            projectId: string;
            /**
             * Historyentryid
             * Format: uuid
             */
            historyEntryId: string;
            /** Reference */
            reference: string;
            /** Contentsnapshot */
            contentSnapshot: {
                [key: string]: unknown;
            };
            /** Schemaversion */
            schemaVersion: number;
            /**
             * Status
             * @enum {string}
             */
            status: "finalized" | "voided";
            /** Revision */
            revision: string;
            /**
             * Finalizedbyuserid
             * Format: uuid
             */
            finalizedByUserId: string;
            /**
             * Finalizedat
             * Format: date-time
             */
            finalizedAt: string;
            /** Voidedat */
            voidedAt: string | null;
            /**
             * Updatedat
             * Format: date-time
             */
            updatedAt: string;
        };
        /** AgreementResponse */
        AgreementResponse: {
            changeOrder: components["schemas"]["AgreementDTO"];
        };
        /** AgreementsResponse */
        AgreementsResponse: {
            /** Changeorders */
            changeOrders: components["schemas"]["AgreementDTO"][];
        };
        /** AnalysisChangeOrder */
        AnalysisChangeOrder: {
            /** Description */
            description: string;
            /** Timelineimpact */
            timelineImpact: string;
            /** Additionalcost */
            additionalCost: string;
            /** Note */
            note: string;
            /** Estimatedhours */
            estimatedHours?: number | null;
            /** Currency */
            currency?: components["schemas"]["Currency"] | "" | null;
            /** Rationale */
            rationale?: string | null;
        };
        /** AnalysisReplies */
        AnalysisReplies: {
            /** Warm */
            warm: string;
            /** Neutral */
            neutral: string;
            /** Firm */
            firm: string;
        };
        /** AnalysisResponse */
        AnalysisResponse: {
            analysisRun: components["schemas"]["AnalysisRunDTO"];
            draft: components["schemas"]["WorkingDraftDTO"] | null;
            /** Applied */
            applied: boolean;
            /**
             * Conflict
             * @default false
             */
            conflict: boolean;
            /** Historyentryid */
            historyEntryId?: string | null;
        };
        /** AnalysisRunDTO */
        AnalysisRunDTO: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Projectid
             * Format: uuid
             */
            projectId: string;
            /**
             * Sourcedraftid
             * Format: uuid
             */
            sourceDraftId: string;
            /** Sourcedraftrevision */
            sourceDraftRevision: string;
            /** Requesttext */
            requestText: string;
            /** Projectsnapshot */
            projectSnapshot: {
                [key: string]: unknown;
            };
            /** Interfacelocale */
            interfaceLocale: string;
            /** Requesteddocumentlanguage */
            requestedDocumentLanguage?: string | null;
            /** Requestlanguage */
            requestLanguage?: string | null;
            resultSnapshot?: components["schemas"]["AnalysisSnapshot"] | null;
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "running" | "succeeded" | "failed" | "cancelled";
            /**
             * Purpose
             * @default analysis
             * @enum {string}
             */
            purpose: "analysis" | "estimate";
            /** Model */
            model?: string | null;
            /** Promptversion */
            promptVersion?: string | null;
            /** Errorcode */
            errorCode?: string | null;
            /**
             * Createdat
             * Format: date-time
             */
            createdAt: string;
            /** Startedat */
            startedAt?: string | null;
            /** Finishedat */
            finishedAt?: string | null;
        };
        /** AnalysisSnapshot */
        AnalysisSnapshot: {
            verdict: components["schemas"]["Verdict"];
            /** Confidence */
            confidence: number;
            /** Summary */
            summary: string;
            /** Reasoning */
            reasoning: string;
            /** Citations */
            citations: string[];
            /** Suggestion */
            suggestion?: string | null;
            replies: components["schemas"]["AnalysisReplies"];
            changeOrder: components["schemas"]["AnalysisChangeOrder"] | null;
            estimate?: components["schemas"]["PreliminaryEstimate"] | null;
            /** Hasadditionalwork */
            hasAdditionalWork?: boolean | null;
            /** Requestlanguage */
            requestLanguage?: ("ru" | "en" | "es" | "other") | null;
            /** Clientlanguage */
            clientLanguage?: string | null;
            changeOrderLabels?: components["schemas"]["ChangeOrderLabels"] | null;
            /** Draftcreatedat */
            draftCreatedAt?: string | null;
            /** Commercialsignature */
            commercialSignature?: string | null;
            /** Estimatevalid */
            estimateValid?: boolean | null;
        };
        /** AnalyzeResponse */
        AnalyzeResponse: {
            result: components["schemas"]["AnalysisSnapshot"];
            projectSnapshot: components["schemas"]["ProjectSnapshot"];
            /** Proof */
            proof: string;
        };
        /** AuthResponse */
        AuthResponse: {
            user: components["schemas"]["UserResponse"];
        };
        /** ChangeOrderLabels */
        ChangeOrderLabels: {
            /** Title */
            title: string;
            /** Draft */
            draft: string;
            /** Documentnumber */
            documentNumber: string;
            /** Created */
            created: string;
            /** Project */
            project: string;
            /** Provider */
            provider: string;
            /** Client */
            client: string;
            /** Clientemail */
            clientEmail: string;
            /** Requestedchange */
            requestedChange: string;
            /** Commercialterms */
            commercialTerms: string;
            /** Estimatedeffort */
            estimatedEffort: string;
            /** Additionalfee */
            additionalFee: string;
            /** Noadditionalcharge */
            noAdditionalCharge: string;
            /** Scheduleimpact */
            scheduleImpact: string;
            /** Additionalterms */
            additionalTerms: string;
            /** Approval */
            approval: string;
            /** Approvedby */
            approvedBy: string;
            /** Date */
            date: string;
            /** Draftfooter */
            draftFooter: string;
            /** Introduction */
            introduction: string;
            /** Outsidescopefree */
            outsideScopeFree: string;
            /** Enddate */
            endDate: string;
            /** Rationale */
            rationale: string;
            /** Terms */
            terms: string;
            /** Note */
            note: string;
            /** Page */
            page: string;
            /** Hours */
            hours: string;
        };
        /** ClientChangeOrderText */
        ClientChangeOrderText: {
            /** Description */
            description: string;
            /** Timelineimpact */
            timelineImpact: string;
            /** Rationale */
            rationale: string;
            /** Note */
            note: string;
        };
        /** ClientMaterials */
        ClientMaterials: {
            /** Clientlanguage */
            clientLanguage: string;
            replies: components["schemas"]["Replies"];
            changeOrder?: components["schemas"]["ClientChangeOrderText"] | null;
            changeOrderLabels?: components["schemas"]["ChangeOrderLabels"] | null;
        };
        /** CreatedDraftResponse */
        CreatedDraftResponse: {
            draft: components["schemas"]["scope_guard_api__schemas__drafts__DraftResponse"];
            entry: components["schemas"]["CreatedHistoryEntry"];
        };
        /** CreatedHistoryEntry */
        CreatedHistoryEntry: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Draftid */
            draftId?: string | null;
            /**
             * Date
             * Format: date
             */
            date: string;
            /** Request */
            request: string;
            verdict: components["schemas"]["Verdict"];
            /** Summary */
            summary: string;
            /**
             * Projectid
             * Format: uuid
             */
            projectId: string;
        };
        /**
         * Currency
         * @enum {string}
         */
        Currency: "RUB" | "USD" | "EUR";
        /** DraftCollectionItem */
        DraftCollectionItem: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Projectid
             * Format: uuid
             */
            projectId: string;
            /** Projectname */
            projectName: string;
            /** Requestpreview */
            requestPreview: string;
            /** Verdict */
            verdict: ("in_scope" | "borderline" | "out_of_scope") | null;
            /**
             * Createdat
             * Format: date-time
             */
            createdAt: string;
            /**
             * Updatedat
             * Format: date-time
             */
            updatedAt: string;
        };
        /** DraftCollectionResponse */
        DraftCollectionResponse: {
            /** Drafts */
            drafts: components["schemas"]["DraftCollectionItem"][];
            /** Total */
            total: number;
            /** Hasdrafts */
            hasDrafts: boolean;
        };
        /** DraftEditableChangeOrder */
        DraftEditableChangeOrder: {
            /** Createdat */
            createdAt: string;
            /** Language */
            language: string;
            /** Projectname */
            projectName: string;
            /** Description */
            description: string;
            /** Estimatedhours */
            estimatedHours: string;
            /** Additionalcost */
            additionalCost: string;
            /** Timelineimpact */
            timelineImpact: string;
            /** Rationale */
            rationale: string;
            /** Note */
            note: string;
            /** Providername */
            providerName: string;
            /** Clientname */
            clientName: string;
            /** Clientemail */
            clientEmail: string;
            /** Enddate */
            endDate: string;
            /** Additionalterms */
            additionalTerms: string;
            /** Clientapprovername */
            clientApproverName: string;
            /** Approvaldate */
            approvalDate: string;
            /** Noadditionalcharge */
            noAdditionalCharge: boolean;
            /** Reference */
            reference?: string;
            changeOrderLabels?: components["schemas"]["ChangeOrderLabels"];
            /** Aivalues */
            aiValues?: {
                [key: string]: string;
            };
            /** Currency */
            currency: components["schemas"]["Currency"] | "" | unknown[];
        };
        /** DraftEnvelope */
        DraftEnvelope: {
            draft: components["schemas"]["scope_guard_api__schemas__drafts__DraftResponse"];
        };
        /** DraftListItem */
        DraftListItem: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Requestpreview */
            requestPreview: string;
            /** Projectname */
            projectName: string;
            verdict: components["schemas"]["Verdict"];
            /**
             * Createdat
             * Format: date-time
             */
            createdAt: string;
            /**
             * Updatedat
             * Format: date-time
             */
            updatedAt: string;
        };
        /** DraftsResponse */
        DraftsResponse: {
            /** Drafts */
            drafts: components["schemas"]["DraftListItem"][];
        };
        /**
         * ErrorCode
         * @enum {string}
         */
        ErrorCode: "errors.providerBudgetUnavailable" | "errors.operationBudgetExceeded" | "errors.operationDeadlineExceeded" | "errors.semanticAttemptsExhausted" | "errors.transportAttemptsExhausted" | "errors.providerOutcomeUnknown" | "errors.providerTransportFailed" | "errors.providerOutputIncomplete" | "errors.operationLeaseLost" | "errors.workflowVersionUnavailable" | "errors.providerModelMismatch" | "errors.attemptSequenceInvalid" | "errors.requestBodyInvalid" | "errors.requestFailed" | "errors.authRequired" | "errors.emailRequired" | "errors.passwordRequired" | "errors.invalidEmail" | "errors.passwordTooShort" | "errors.duplicateEmail" | "errors.invalidCredentials" | "errors.projectNotFound" | "errors.projectNameRequired" | "errors.scopeRequired" | "errors.industryInvalid" | "errors.clientInvalid" | "errors.startDateInvalid" | "errors.pricingModelInvalid" | "errors.currencyInvalid" | "errors.hourlyRateInvalid" | "errors.fixedPriceInvalid" | "errors.historyDateInvalid" | "errors.requestRequired" | "errors.verdictInvalid" | "errors.summaryRequired" | "errors.localeInvalid" | "errors.clientLanguageUnsupported" | "errors.analysisUnavailable" | "errors.analysisFailed" | "errors.analysisInvalid" | "errors.analysisInputTooLarge" | "errors.analysisRateLimited" | "errors.draftProofInvalid" | "errors.draftNotFound" | "errors.draftSaveFailed" | "errors.draftLoadFailed" | "errors.evaluationReasoningRequired" | "errors.evaluationLabelInvalid" | "errors.evaluationHistoryNotFound" | "errors.pdfDocumentMissing" | "errors.pdfDocumentInvalid" | "errors.pdfLanguageUnsupported" | "errors.pdfGlyphUnsupported" | "errors.pdfLabelsMissing" | "errors.pdfExportFailed" | "errors.pdfExportTimeout" | "errors.pdfInputTooLarge" | "errors.pdfResourceLimit" | "errors.scopeFileTooLarge" | "errors.scopeFileUnsupported" | "errors.scopeFileEmpty" | "errors.scopeFileEncoding" | "errors.scopePdfInvalid" | "errors.scopePdfEncrypted" | "errors.scopePdfNoText" | "errors.scopePdfTooManyPages" | "errors.scopeTextTooLarge" | "errors.scopeResourceLimit" | "errors.scopeExtractTimeout" | "errors.scopeExtractFailed" | "errors.technicalBusy";
        /** ErrorResponse */
        ErrorResponse: {
            error: components["schemas"]["ErrorCode"];
            /** Fields */
            fields?: {
                [key: string]: "required" | "positive";
            } | null;
        };
        /** EstimateProvenance */
        EstimateProvenance: {
            /**
             * Analysisrunid
             * Format: uuid
             */
            analysisRunId: string;
            /** Sourcedraftrevision */
            sourceDraftRevision: string;
            /** Effectiveenddate */
            effectiveEndDate: string | null;
            /** Commercialsignature */
            commercialSignature: string;
            /** Estimatevalid */
            estimateValid: boolean;
        };
        /** EstimateResponse */
        EstimateResponse: {
            result: components["schemas"]["AnalysisSnapshot"];
        };
        /**
         * EvaluationAccuracy
         * @enum {string}
         */
        EvaluationAccuracy: "correct" | "wrong" | "debatable";
        /** EvaluationEnvelope */
        EvaluationEnvelope: {
            evaluation: components["schemas"]["EvaluationResponse"];
        };
        /** EvaluationResponse */
        EvaluationResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            accuracy: components["schemas"]["EvaluationAccuracy"];
            humanVerdict: components["schemas"]["Verdict"] | null;
        };
        /** ExportDTO */
        ExportDTO: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Changeorderid
             * Format: uuid
             */
            changeOrderId: string;
            /**
             * Format
             * @constant
             */
            format: "pdf";
            /** Language */
            language: string;
            /** Rendererversion */
            rendererVersion: string;
            /** Templateversion */
            templateVersion: string;
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "processing" | "ready" | "failed" | "expired";
            /** Checksum */
            checksum: string | null;
            /** Mimetype */
            mimeType: string | null;
            /** Sizebytes */
            sizeBytes: number | null;
            /** Errorcode */
            errorCode: string | null;
            /** Attemptcount */
            attemptCount: number;
            /**
             * Createdat
             * Format: date-time
             */
            createdAt: string;
            /** Finishedat */
            finishedAt: string | null;
        };
        /** ExportRequest */
        ExportRequest: {
            /**
             * Operationid
             * Format: uuid
             */
            operationId: string;
            /** Language */
            language?: string | null;
        };
        /** ExportResponse */
        ExportResponse: {
            export: components["schemas"]["ExportDTO"];
        };
        /** ExportsResponse */
        ExportsResponse: {
            /** Exports */
            exports: components["schemas"]["ExportDTO"][];
        };
        /** ExtractionResponse */
        ExtractionResponse: {
            /** Text */
            text: string;
            /** Warnings */
            warnings: (components["schemas"]["PagesWithoutText"] | components["schemas"]["NulRemoved"])[];
        };
        /** Feedback */
        Feedback: {
            /**
             * Accuracy
             * @enum {string}
             */
            accuracy: "correct" | "wrong" | "debatable";
            /** Humanverdict */
            humanVerdict?: ("in_scope" | "borderline" | "out_of_scope") | null;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HistoriesResponse */
        HistoriesResponse: {
            /** Entries */
            entries: components["schemas"]["HistoryEntryDTO"][];
        };
        /** HistoryEntryDTO */
        HistoryEntryDTO: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Projectid
             * Format: uuid
             */
            projectId: string;
            /** Sourcedraftid */
            sourceDraftId: string | null;
            /** Sourcedraftrevision */
            sourceDraftRevision: string | null;
            /** Analysisrunid */
            analysisRunId: string | null;
            /** Checksnapshot */
            checkSnapshot: {
                [key: string]: unknown;
            };
            /** Schemaversion */
            schemaVersion: number;
            /**
             * Verdict
             * @enum {string}
             */
            verdict: "in_scope" | "borderline" | "out_of_scope";
            /** Summary */
            summary: string;
            /** Request */
            request: string;
            /** Date */
            date: string;
            /** Completedat */
            completedAt: string | null;
            /** Savedbyuserid */
            savedByUserId: string | null;
            /**
             * Sourcekind
             * @enum {string}
             */
            sourceKind: "explicit" | "legacy_unverified";
        };
        /** HistoryEntryResponse */
        HistoryEntryResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Draftid */
            draftId?: string | null;
            /**
             * Date
             * Format: date
             */
            date: string;
            /** Request */
            request: string;
            verdict: components["schemas"]["Verdict"];
            /** Summary */
            summary: string;
        };
        /**
         * Industry
         * @enum {string}
         */
        Industry: "Development" | "Design" | "Marketing";
        /** LivenessResponse */
        LivenessResponse: {
            /**
             * Status
             * @default ok
             * @constant
             */
            status: "ok";
        };
        /** LlmOperationStatus */
        LlmOperationStatus: {
            /**
             * Operationid
             * Format: uuid
             */
            operationId: string;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "succeeded" | "failed";
            /** Statusurl */
            statusUrl: string;
            /**
             * Deadlineat
             * Format: date-time
             */
            deadlineAt: string;
            /** Stages */
            stages: {
                [key: string]: string;
            };
            /** Responseformat */
            responseFormat: string;
            /** Result */
            result: {
                [key: string]: unknown;
            } | null;
            /** Error */
            error: {
                [key: string]: unknown;
            } | null;
        };
        /** MaterialsResponse */
        MaterialsResponse: {
            materials: components["schemas"]["ClientMaterials"];
        };
        /** NulRemoved */
        NulRemoved: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            code: "nul_removed";
        };
        /** OkResponse */
        OkResponse: {
            /**
             * Ok
             * @constant
             */
            ok: true;
        };
        /** OnboardingEvent */
        OnboardingEvent: {
            /**
             * Event
             * @enum {string}
             */
            event: "form_opened" | "project_saved" | "check_submitted" | "result_viewed" | "skip";
        };
        /** OnboardingState */
        OnboardingState: {
            /**
             * Status
             * @enum {string}
             */
            status: "not_started" | "in_progress" | "completed" | "skipped";
            /** Step */
            step: number;
        };
        /** Operation */
        Operation: {
            /**
             * Operationid
             * Format: uuid
             */
            operationId: string;
        };
        /** PagesWithoutText */
        PagesWithoutText: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            code: "pages_without_text";
            /** Pagenumbers */
            pageNumbers: number[];
        };
        /** PendingLlmOperation */
        PendingLlmOperation: {
            /**
             * Operationid
             * Format: uuid
             */
            operationId: string;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "succeeded" | "failed";
            /** Statusurl */
            statusUrl: string;
            /**
             * Deadlineat
             * Format: date-time
             */
            deadlineAt: string;
        };
        /** PreliminaryEstimate */
        PreliminaryEstimate: {
            /** Estimatedhours */
            estimatedHours: number;
            /** Additionalcost */
            additionalCost: string;
            /** Currency */
            currency: components["schemas"]["Currency"] | "";
        };
        /**
         * PricingModel
         * @enum {string}
         */
        PricingModel: "hourly" | "fixed";
        /** ProfileChanges */
        ProfileChanges: {
            /** Displayname */
            displayName?: string | null;
            /** Businessname */
            businessName?: string | null;
            /** Providername */
            providerName?: string | null;
            /** Profession */
            profession?: string | null;
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "inactive";
            preferences?: components["schemas"]["ProfilePreferences"];
        };
        /** ProfilePreferences */
        ProfilePreferences: {
            /** Locale */
            locale?: ("ru" | "en") | null;
            /** Timezone */
            timezone?: string | null;
            /** Preferredtone */
            preferredTone?: ("warm" | "neutral" | "firm") | null;
            /** Defaultcurrency */
            defaultCurrency?: ("RUB" | "USD" | "EUR") | null;
        };
        /** ProfileResponse */
        ProfileResponse: {
            profile: components["schemas"]["ProfileView"];
        };
        /** ProfileUpdate */
        ProfileUpdate: {
            /**
             * Operationid
             * Format: uuid
             */
            operationId: string;
            /** Expectedrevision */
            expectedRevision: string;
            changes: components["schemas"]["ProfileChanges"];
        };
        /** ProfileView */
        ProfileView: {
            /** Displayname */
            displayName?: string | null;
            /** Businessname */
            businessName?: string | null;
            /** Providername */
            providerName?: string | null;
            /** Profession */
            profession?: string | null;
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "inactive";
            preferences?: components["schemas"]["ProfilePreferences"];
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Revision */
            revision: string;
            /** Createdat */
            createdAt: string;
            /** Updatedat */
            updatedAt: string;
        };
        /** ProjectEnvelope */
        ProjectEnvelope: {
            project: components["schemas"]["scope_guard_api__schemas__projects__ProjectResponse"];
        };
        /** ProjectSnapshot */
        ProjectSnapshot: {
            /**
             * Version
             * @constant
             */
            version: 1;
            /** Name */
            name: string;
            /** Clientname */
            clientName?: string | null;
            industry: components["schemas"]["Industry"];
            /** Scope */
            scope: string;
            /** Startdate */
            startDate: string | null;
            /** Enddate */
            endDate: string | null;
            pricingModel: components["schemas"]["PricingModel"] | null;
            currency: components["schemas"]["Currency"] | null;
            /** Hourlyrate */
            hourlyRate: string | null;
            /** Fixedprice */
            fixedPrice: string | null;
            /** Documentlanguage */
            documentLanguage: string | null;
        };
        /** ProjectUpdate */
        ProjectUpdate: {
            /**
             * Operationid
             * Format: uuid
             */
            operationId: string;
            /** Name */
            name: string;
            /** Clientname */
            clientName?: string | null;
            /** Clientemail */
            clientEmail?: string | null;
            /**
             * Industry
             * @enum {string}
             */
            industry: "Development" | "Design" | "Marketing";
            /** Scope */
            scope: string;
            /** Startdate */
            startDate: string;
            /** Enddate */
            endDate?: string | null;
            /**
             * Pricingmodel
             * @enum {string}
             */
            pricingModel: "hourly" | "fixed";
            /**
             * Currency
             * @enum {string}
             */
            currency: "RUB" | "USD" | "EUR";
            /** Hourlyrate */
            hourlyRate?: string | number | null;
            /** Fixedprice */
            fixedPrice?: string | number | null;
            /** Expectedrevision */
            expectedRevision: string;
        };
        /** ProjectWrite */
        ProjectWrite: {
            /**
             * Operationid
             * Format: uuid
             */
            operationId: string;
            /** Name */
            name: string;
            /** Clientname */
            clientName?: string | null;
            /** Clientemail */
            clientEmail?: string | null;
            /**
             * Industry
             * @enum {string}
             */
            industry: "Development" | "Design" | "Marketing";
            /** Scope */
            scope: string;
            /** Startdate */
            startDate: string;
            /** Enddate */
            endDate?: string | null;
            /**
             * Pricingmodel
             * @enum {string}
             */
            pricingModel: "hourly" | "fixed";
            /**
             * Currency
             * @enum {string}
             */
            currency: "RUB" | "USD" | "EUR";
            /** Hourlyrate */
            hourlyRate?: string | number | null;
            /** Fixedprice */
            fixedPrice?: string | number | null;
        };
        /** ReadinessResponse */
        ReadinessResponse: {
            /**
             * Status
             * @enum {string}
             */
            status: "ok" | "unavailable";
            /**
             * Database
             * @enum {string}
             */
            database: "ok" | "unavailable";
        };
        /** Replies */
        Replies: {
            /** Warm */
            warm: string;
            /** Neutral */
            neutral: string;
            /** Firm */
            firm: string;
        };
        /** ReplyAlternatives */
        ReplyAlternatives: {
            /** Warm */
            warm: string;
            /** Neutral */
            neutral: string;
            /** Firm */
            firm: string;
        };
        /** ReplyResponse */
        ReplyResponse: {
            /** Reply */
            reply: string;
        };
        /** RevisionDTO */
        RevisionDTO: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Draftid
             * Format: uuid
             */
            draftId: string;
            /** Revision */
            revision: string;
            /** Statesnapshot */
            stateSnapshot: {
                [key: string]: unknown;
            };
            /** Schemaversion */
            schemaVersion: number;
            /** Reason */
            reason: string;
            /** Actortype */
            actorType: string;
            /** Actoruserid */
            actorUserId: string | null;
            /**
             * Createdat
             * Format: date-time
             */
            createdAt: string;
            /** Projectid */
            projectId?: string | null;
        };
        /** RevisionResponse */
        RevisionResponse: {
            revision: components["schemas"]["RevisionDTO"];
        };
        /** RevisionsResponse */
        RevisionsResponse: {
            /** Revisions */
            revisions: components["schemas"]["RevisionDTO"][];
        };
        /** RunAnalysis */
        RunAnalysis: {
            /**
             * Operationid
             * Format: uuid
             */
            operationId: string;
            /** Expectedrevision */
            expectedRevision: string;
            /**
             * Locale
             * @enum {string}
             */
            locale: "en" | "ru";
            /** Documentlanguage */
            documentLanguage?: string | null;
        };
        /** SaveWorkingDraft */
        SaveWorkingDraft: {
            /**
             * Operationid
             * Format: uuid
             */
            operationId: string;
            /** Expectedrevision */
            expectedRevision: string;
            changes?: components["schemas"]["WorkingChanges"] | null;
            /** Patch */
            patch?: {
                [key: string]: string | boolean;
            } | null;
            /**
             * Reason
             * @default autosave
             * @enum {string}
             */
            reason: "autosave" | "manual_save" | "tone_change" | "language_change" | "change_order_edit";
        };
        /** TranslateWorkingDraft */
        TranslateWorkingDraft: {
            /**
             * Operationid
             * Format: uuid
             */
            operationId: string;
            /** Expectedrevision */
            expectedRevision: string;
            /** Language */
            language: string;
        };
        /** UserResponse */
        UserResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Email */
            email: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /**
         * Verdict
         * @enum {string}
         */
        Verdict: "in_scope" | "borderline" | "out_of_scope";
        /** VersionedOperation */
        VersionedOperation: {
            /**
             * Operationid
             * Format: uuid
             */
            operationId: string;
            /** Expectedrevision */
            expectedRevision: string;
        };
        /** WorkflowProject */
        WorkflowProject: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Clientname */
            clientName?: string | null;
            /** Clientemail */
            clientEmail?: string | null;
            /** Industry */
            industry: string;
            /** Scope */
            scope: string;
            /** Startdate */
            startDate?: string | null;
            /** Enddate */
            endDate?: string | null;
            /** Pricingmodel */
            pricingModel?: string | null;
            /** Currency */
            currency?: string | null;
            /** Hourlyrate */
            hourlyRate?: string | null;
            /** Fixedprice */
            fixedPrice?: string | null;
            /**
             * Createdat
             * Format: date-time
             */
            createdAt: string;
            /**
             * Updatedat
             * Format: date-time
             */
            updatedAt: string;
            /** Archivedat */
            archivedAt?: string | null;
            /** Lastchecked */
            lastChecked?: string | null;
            /**
             * History
             * @default []
             */
            history: {
                [key: string]: unknown;
            }[];
        };
        /** WorkingChanges */
        WorkingChanges: {
            /** Requesttext */
            requestText?: string | null;
            draftDocument?: components["schemas"]["WorkingDocument"] | null;
        };
        /** WorkingDocument */
        WorkingDocument: {
            /**
             * Version
             * @constant
             */
            version: 2;
            reply: components["schemas"]["WorkingReply"];
            changeOrder: components["schemas"]["DraftEditableChangeOrder"] | null;
            estimate?: components["schemas"]["EstimateProvenance"] | null;
            /** Languageselection */
            languageSelection?: {
                [key: string]: unknown;
            } | null;
        };
        /** WorkingDraftDTO */
        WorkingDraftDTO: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Projectid
             * Format: uuid
             */
            projectId: string;
            /** Requesttext */
            requestText: string;
            /** Lastanalysisrunid */
            lastAnalysisRunId: string | null;
            /** Analysisisstale */
            analysisIsStale: boolean;
            draftDocument: components["schemas"]["WorkingDocument"];
            /** Revision */
            revision: string;
            /**
             * Createdat
             * Format: date-time
             */
            createdAt: string;
            /**
             * Updatedat
             * Format: date-time
             */
            updatedAt: string;
            analysisRun?: components["schemas"]["AnalysisRunDTO"] | null;
        };
        /** WorkingReply */
        WorkingReply: {
            /** Text */
            text: string;
            /**
             * Tone
             * @enum {string}
             */
            tone: "warm" | "neutral" | "firm";
            /** Language */
            language: string;
            generated: components["schemas"]["ReplyAlternatives"];
        };
        /** HistoryResponse */
        scope_guard_api__contracts__HistoryResponse: {
            entry: components["schemas"]["HistoryEntryResponse"];
        };
        /** ProjectsResponse */
        scope_guard_api__contracts__ProjectsResponse: {
            /** Projects */
            projects: components["schemas"]["scope_guard_api__schemas__projects__ProjectResponse"][];
        };
        /** DraftResponse */
        scope_guard_api__schemas__drafts__DraftResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Projectid
             * Format: uuid
             */
            projectId: string;
            /**
             * Historyentryid
             * Format: uuid
             */
            historyEntryId: string;
            /** Request */
            request: string;
            /**
             * Createdat
             * Format: date-time
             */
            createdAt: string;
            /**
             * Updatedat
             * Format: date-time
             */
            updatedAt: string;
            /**
             * Status
             * @constant
             */
            status: "draft";
            /**
             * Locale
             * @enum {string}
             */
            locale: "en" | "ru";
            /** Requestlanguage */
            requestLanguage: ("ru" | "en" | "es" | "other") | null;
            /** Clientmateriallanguage */
            clientMaterialLanguage: string;
            /** Projectsnapshot */
            projectSnapshot: {
                [key: string]: unknown;
            } | null;
            /** Analysissnapshot */
            analysisSnapshot: {
                [key: string]: unknown;
            };
            /** Draftdocument */
            draftDocument: {
                [key: string]: unknown;
            };
        };
        /** ProjectResponse */
        scope_guard_api__schemas__projects__ProjectResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Clientname */
            clientName?: string | null;
            industry: components["schemas"]["Industry"];
            /** Scope */
            scope: string;
            /** Startdate */
            startDate: string | null;
            pricingModel: components["schemas"]["PricingModel"] | null;
            currency: components["schemas"]["Currency"] | null;
            /** Hourlyrate */
            hourlyRate: string | null;
            /** Fixedprice */
            fixedPrice: string | null;
            /** Lastchecked */
            lastChecked?: string | null;
            /** History */
            history: components["schemas"]["HistoryEntryResponse"][];
        };
        /** DraftResponse */
        scope_guard_api__schemas__workflow__DraftResponse: {
            draft: components["schemas"]["WorkingDraftDTO"];
        };
        /** HistoryResponse */
        scope_guard_api__schemas__workflow__HistoryResponse: {
            entry: components["schemas"]["HistoryEntryDTO"];
        };
        /** ProjectResponse */
        scope_guard_api__schemas__workflow__ProjectResponse: {
            project: components["schemas"]["WorkflowProject"];
        };
        /** ProjectsResponse */
        scope_guard_api__schemas__workflow__ProjectsResponse: {
            /** Projects */
            projects: components["schemas"]["WorkflowProject"][];
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    live_health_live_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LivenessResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    ready_health_ready_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadinessResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadinessResponse"];
                };
            };
        };
    };
    register_api_auth_register_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    email: string;
                    password: string;
                };
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    login_api_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    email: string;
                    password: string;
                };
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    logout_api_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OkResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    me_api_auth_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_projects_api_projects_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__contracts__ProjectsResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_project_api_projects_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    name: string;
                    scope: string;
                    clientName?: string | null;
                    /** @enum {string} */
                    industry: "Development" | "Design" | "Marketing";
                    /** Format: date */
                    startDate: string;
                    /** @enum {string} */
                    pricingModel: "hourly" | "fixed";
                    /** @enum {string} */
                    currency: "RUB" | "USD" | "EUR";
                    hourlyRate?: string | number | null;
                    fixedPrice?: string | number | null;
                };
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectEnvelope"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_project_api_projects__project_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectEnvelope"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_project_api_projects__project_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OkResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_project_api_projects__project_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    name: string;
                    scope: string;
                    clientName?: string | null;
                    /** @enum {string} */
                    industry: "Development" | "Design" | "Marketing";
                    /** Format: date */
                    startDate: string;
                    /** @enum {string} */
                    pricingModel: "hourly" | "fixed";
                    /** @enum {string} */
                    currency: "RUB" | "USD" | "EUR";
                    hourlyRate?: string | number | null;
                    fixedPrice?: string | number | null;
                };
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectEnvelope"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_history_api_projects__project_id__history_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    date: string;
                    request: string;
                    /** @enum {string} */
                    verdict: "in_scope" | "borderline" | "out_of_scope";
                    summary: string;
                };
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__contracts__HistoryResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    analyze_api_analyze_post: {
        parameters: {
            query?: never;
            header?: {
                "Idempotency-Key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    projectId: string;
                    request: string;
                    documentLanguage?: string;
                    endDate?: string;
                    /** Format: uuid */
                    draftId?: string;
                    /** Format: uuid */
                    operationId?: string;
                    expectedRevision?: string;
                };
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalyzeResponse"];
                };
            };
            /** @description Accepted */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PendingLlmOperation"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Upgrade Required */
            426: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Bad Gateway */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    reply_api_replies_regenerate_post: {
        parameters: {
            query?: never;
            header?: {
                "Idempotency-Key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    projectId: string;
                    request: string;
                    documentLanguage?: string;
                    endDate?: string;
                    /** @enum {string} */
                    tone: "warm" | "neutral" | "firm";
                    previousReply: string;
                    /** Format: uuid */
                    draftId?: string;
                    /** Format: uuid */
                    operationId?: string;
                    expectedRevision?: string;
                };
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReplyResponse"];
                };
            };
            /** @description Accepted */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PendingLlmOperation"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Upgrade Required */
            426: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Bad Gateway */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    materials_api_client_materials_language_post: {
        parameters: {
            query?: never;
            header?: {
                "Idempotency-Key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    projectId: string;
                    request: string;
                    documentLanguage?: string;
                    endDate?: string;
                    /** Format: uuid */
                    draftId?: string;
                    proof?: string;
                    locale?: string;
                    historyId?: string;
                    clientLanguage: string;
                    analysis: Record<string, never>;
                    /** Format: uuid */
                    operationId?: string;
                    expectedRevision?: string;
                };
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MaterialsResponse"];
                };
            };
            /** @description Accepted */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PendingLlmOperation"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Upgrade Required */
            426: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Bad Gateway */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    estimate_api_change_orders_estimate_post: {
        parameters: {
            query?: never;
            header?: {
                "Idempotency-Key"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    projectId: string;
                    request: string;
                    documentLanguage?: string;
                    endDate?: string;
                    /** Format: uuid */
                    draftId?: string;
                    proof?: string;
                    locale?: string;
                    /** Format: uuid */
                    operationId?: string;
                    expectedRevision?: string;
                };
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EstimateResponse"];
                };
            };
            /** @description Accepted */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PendingLlmOperation"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Upgrade Required */
            426: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Precondition Required */
            428: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Bad Gateway */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    saved_pdf_api_drafts__draftId__pdf_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                draftId: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Change Order PDF */
            200: {
                headers: {
                    "Content-Disposition"?: string;
                    "Cache-Control"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/pdf": string;
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Gateway Timeout */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    preview_pdf_api_change_orders_pdf_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    /**
                     * Projectid
                     * Format: uuid
                     */
                    projectId: string;
                    /** Draftid */
                    draftId?: string | null;
                    /** DraftEditableChangeOrder */
                    changeOrder: {
                        /** Createdat */
                        createdAt: string;
                        /** Language */
                        language: string;
                        /** Projectname */
                        projectName: string;
                        /** Description */
                        description: string;
                        /** Estimatedhours */
                        estimatedHours: string;
                        /** Additionalcost */
                        additionalCost: string;
                        /** Timelineimpact */
                        timelineImpact: string;
                        /** Rationale */
                        rationale: string;
                        /** Note */
                        note: string;
                        /** Providername */
                        providerName: string;
                        /** Clientname */
                        clientName: string;
                        /** Clientemail */
                        clientEmail: string;
                        /** Enddate */
                        endDate: string;
                        /** Additionalterms */
                        additionalTerms: string;
                        /** Clientapprovername */
                        clientApproverName: string;
                        /** Approvaldate */
                        approvalDate: string;
                        /** Noadditionalcharge */
                        noAdditionalCharge: boolean;
                        /** Reference */
                        reference?: string;
                        changeOrderLabels?: {
                            /** Title */
                            title: string;
                            /** Draft */
                            draft: string;
                            /** Documentnumber */
                            documentNumber: string;
                            /** Created */
                            created: string;
                            /** Project */
                            project: string;
                            /** Provider */
                            provider: string;
                            /** Client */
                            client: string;
                            /** Clientemail */
                            clientEmail: string;
                            /** Requestedchange */
                            requestedChange: string;
                            /** Commercialterms */
                            commercialTerms: string;
                            /** Estimatedeffort */
                            estimatedEffort: string;
                            /** Additionalfee */
                            additionalFee: string;
                            /** Noadditionalcharge */
                            noAdditionalCharge: string;
                            /** Scheduleimpact */
                            scheduleImpact: string;
                            /** Additionalterms */
                            additionalTerms: string;
                            /** Approval */
                            approval: string;
                            /** Approvedby */
                            approvedBy: string;
                            /** Date */
                            date: string;
                            /** Draftfooter */
                            draftFooter: string;
                            /** Introduction */
                            introduction: string;
                            /** Outsidescopefree */
                            outsideScopeFree: string;
                            /** Enddate */
                            endDate: string;
                            /** Rationale */
                            rationale: string;
                            /** Terms */
                            terms: string;
                            /** Note */
                            note: string;
                            /** Page */
                            page: string;
                            /** Hours */
                            hours: string;
                        };
                        /** Aivalues */
                        aiValues?: {
                            [key: string]: string;
                        };
                        /** Currency */
                        currency: ("RUB" | "USD" | "EUR") | "" | unknown[];
                    };
                };
            };
        };
        responses: {
            /** @description Change Order PDF */
            200: {
                headers: {
                    "Content-Disposition"?: string;
                    "Cache-Control"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/pdf": string;
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Gateway Timeout */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    preview_pdf_api_v2_change_orders_pdf_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    /**
                     * Projectid
                     * Format: uuid
                     */
                    projectId: string;
                    /** Draftid */
                    draftId?: string | null;
                    /** DraftEditableChangeOrder */
                    changeOrder: {
                        /** Createdat */
                        createdAt: string;
                        /** Language */
                        language: string;
                        /** Projectname */
                        projectName: string;
                        /** Description */
                        description: string;
                        /** Estimatedhours */
                        estimatedHours: string;
                        /** Additionalcost */
                        additionalCost: string;
                        /** Timelineimpact */
                        timelineImpact: string;
                        /** Rationale */
                        rationale: string;
                        /** Note */
                        note: string;
                        /** Providername */
                        providerName: string;
                        /** Clientname */
                        clientName: string;
                        /** Clientemail */
                        clientEmail: string;
                        /** Enddate */
                        endDate: string;
                        /** Additionalterms */
                        additionalTerms: string;
                        /** Clientapprovername */
                        clientApproverName: string;
                        /** Approvaldate */
                        approvalDate: string;
                        /** Noadditionalcharge */
                        noAdditionalCharge: boolean;
                        /** Reference */
                        reference?: string;
                        changeOrderLabels?: {
                            /** Title */
                            title: string;
                            /** Draft */
                            draft: string;
                            /** Documentnumber */
                            documentNumber: string;
                            /** Created */
                            created: string;
                            /** Project */
                            project: string;
                            /** Provider */
                            provider: string;
                            /** Client */
                            client: string;
                            /** Clientemail */
                            clientEmail: string;
                            /** Requestedchange */
                            requestedChange: string;
                            /** Commercialterms */
                            commercialTerms: string;
                            /** Estimatedeffort */
                            estimatedEffort: string;
                            /** Additionalfee */
                            additionalFee: string;
                            /** Noadditionalcharge */
                            noAdditionalCharge: string;
                            /** Scheduleimpact */
                            scheduleImpact: string;
                            /** Additionalterms */
                            additionalTerms: string;
                            /** Approval */
                            approval: string;
                            /** Approvedby */
                            approvedBy: string;
                            /** Date */
                            date: string;
                            /** Draftfooter */
                            draftFooter: string;
                            /** Introduction */
                            introduction: string;
                            /** Outsidescopefree */
                            outsideScopeFree: string;
                            /** Enddate */
                            endDate: string;
                            /** Rationale */
                            rationale: string;
                            /** Terms */
                            terms: string;
                            /** Note */
                            note: string;
                            /** Page */
                            page: string;
                            /** Hours */
                            hours: string;
                        };
                        /** Aivalues */
                        aiValues?: {
                            [key: string]: string;
                        };
                        /** Currency */
                        currency: ("RUB" | "USD" | "EUR") | "" | unknown[];
                    };
                };
            };
        };
        responses: {
            /** @description Change Order PDF */
            200: {
                headers: {
                    "Content-Disposition"?: string;
                    "Cache-Control"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/pdf": string;
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Gateway Timeout */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    scope_extract_api_scope_extract_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": {
                    /** Format: binary */
                    file: string;
                };
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExtractionResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Too Many Requests */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Gateway Timeout */
            504: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_drafts_api_drafts_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "private, no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DraftsResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    "Cache-Control"?: "private, no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "private, no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "private, no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "private, no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "private, no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    create_draft_api_drafts_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    /**
                     * Projectid
                     * Format: uuid
                     */
                    projectId: string;
                    /** Request */
                    request: string;
                    /**
                     * Locale
                     * @enum {string}
                     */
                    locale: "en" | "ru";
                    /**
                     * Idempotencykey
                     * Format: uuid
                     */
                    idempotencyKey: string;
                    /** Proof */
                    proof: string;
                    /** DraftDocument */
                    draftDocument: {
                        /**
                         * Version
                         * @constant
                         */
                        version: 1;
                        /** AnalysisSnapshot */
                        result: {
                            /**
                             * Verdict
                             * @enum {string}
                             */
                            verdict: "in_scope" | "borderline" | "out_of_scope";
                            /** Confidence */
                            confidence: number;
                            /** Summary */
                            summary: string;
                            /** Reasoning */
                            reasoning: string;
                            /** Citations */
                            citations: string[];
                            /** Suggestion */
                            suggestion?: string | null;
                            /** AnalysisReplies */
                            replies: {
                                /** Warm */
                                warm: string;
                                /** Neutral */
                                neutral: string;
                                /** Firm */
                                firm: string;
                            };
                            changeOrder: {
                                /** Description */
                                description: string;
                                /** Timelineimpact */
                                timelineImpact: string;
                                /** Additionalcost */
                                additionalCost: string;
                                /** Note */
                                note: string;
                                /** Estimatedhours */
                                estimatedHours?: number | null;
                                /** Currency */
                                currency?: ("RUB" | "USD" | "EUR") | "" | null;
                                /** Rationale */
                                rationale?: string | null;
                            } | null;
                            estimate?: {
                                /** Estimatedhours */
                                estimatedHours: number;
                                /** Additionalcost */
                                additionalCost: string;
                                /** Currency */
                                currency: ("RUB" | "USD" | "EUR") | "";
                            } | null;
                            /** Hasadditionalwork */
                            hasAdditionalWork?: boolean | null;
                            /** Requestlanguage */
                            requestLanguage?: ("ru" | "en" | "es" | "other") | null;
                            /** Clientlanguage */
                            clientLanguage?: string | null;
                            changeOrderLabels?: {
                                /** Title */
                                title: string;
                                /** Draft */
                                draft: string;
                                /** Documentnumber */
                                documentNumber: string;
                                /** Created */
                                created: string;
                                /** Project */
                                project: string;
                                /** Provider */
                                provider: string;
                                /** Client */
                                client: string;
                                /** Clientemail */
                                clientEmail: string;
                                /** Requestedchange */
                                requestedChange: string;
                                /** Commercialterms */
                                commercialTerms: string;
                                /** Estimatedeffort */
                                estimatedEffort: string;
                                /** Additionalfee */
                                additionalFee: string;
                                /** Noadditionalcharge */
                                noAdditionalCharge: string;
                                /** Scheduleimpact */
                                scheduleImpact: string;
                                /** Additionalterms */
                                additionalTerms: string;
                                /** Approval */
                                approval: string;
                                /** Approvedby */
                                approvedBy: string;
                                /** Date */
                                date: string;
                                /** Draftfooter */
                                draftFooter: string;
                                /** Introduction */
                                introduction: string;
                                /** Outsidescopefree */
                                outsideScopeFree: string;
                                /** Enddate */
                                endDate: string;
                                /** Rationale */
                                rationale: string;
                                /** Terms */
                                terms: string;
                                /** Note */
                                note: string;
                                /** Page */
                                page: string;
                                /** Hours */
                                hours: string;
                            } | null;
                            /** Draftcreatedat */
                            draftCreatedAt?: string | null;
                            /** Commercialsignature */
                            commercialSignature?: string | null;
                            /** Estimatevalid */
                            estimateValid?: boolean | null;
                        };
                        clientMaterials: {
                            /** Clientlanguage */
                            clientLanguage: string;
                            /** Replies */
                            replies: {
                                /** Warm */
                                warm: string;
                                /** Neutral */
                                neutral: string;
                                /** Firm */
                                firm: string;
                            };
                            changeOrder?: {
                                /** Description */
                                description: string;
                                /** Timelineimpact */
                                timelineImpact: string;
                                /** Rationale */
                                rationale: string;
                                /** Note */
                                note: string;
                            } | null;
                            changeOrderLabels?: {
                                /** Title */
                                title: string;
                                /** Draft */
                                draft: string;
                                /** Documentnumber */
                                documentNumber: string;
                                /** Created */
                                created: string;
                                /** Project */
                                project: string;
                                /** Provider */
                                provider: string;
                                /** Client */
                                client: string;
                                /** Clientemail */
                                clientEmail: string;
                                /** Requestedchange */
                                requestedChange: string;
                                /** Commercialterms */
                                commercialTerms: string;
                                /** Estimatedeffort */
                                estimatedEffort: string;
                                /** Additionalfee */
                                additionalFee: string;
                                /** Noadditionalcharge */
                                noAdditionalCharge: string;
                                /** Scheduleimpact */
                                scheduleImpact: string;
                                /** Additionalterms */
                                additionalTerms: string;
                                /** Approval */
                                approval: string;
                                /** Approvedby */
                                approvedBy: string;
                                /** Date */
                                date: string;
                                /** Draftfooter */
                                draftFooter: string;
                                /** Introduction */
                                introduction: string;
                                /** Outsidescopefree */
                                outsideScopeFree: string;
                                /** Enddate */
                                endDate: string;
                                /** Rationale */
                                rationale: string;
                                /** Terms */
                                terms: string;
                                /** Note */
                                note: string;
                                /** Page */
                                page: string;
                                /** Hours */
                                hours: string;
                            } | null;
                        } | null;
                        changeOrder: {
                            /** Createdat */
                            createdAt: string;
                            /** Language */
                            language: string;
                            /** Projectname */
                            projectName: string;
                            /** Description */
                            description: string;
                            /** Estimatedhours */
                            estimatedHours: string;
                            /** Additionalcost */
                            additionalCost: string;
                            /** Timelineimpact */
                            timelineImpact: string;
                            /** Rationale */
                            rationale: string;
                            /** Note */
                            note: string;
                            /** Providername */
                            providerName: string;
                            /** Clientname */
                            clientName: string;
                            /** Clientemail */
                            clientEmail: string;
                            /** Enddate */
                            endDate: string;
                            /** Additionalterms */
                            additionalTerms: string;
                            /** Clientapprovername */
                            clientApproverName: string;
                            /** Approvaldate */
                            approvalDate: string;
                            /** Noadditionalcharge */
                            noAdditionalCharge: boolean;
                            /** Reference */
                            reference?: string;
                            changeOrderLabels?: {
                                /** Title */
                                title: string;
                                /** Draft */
                                draft: string;
                                /** Documentnumber */
                                documentNumber: string;
                                /** Created */
                                created: string;
                                /** Project */
                                project: string;
                                /** Provider */
                                provider: string;
                                /** Client */
                                client: string;
                                /** Clientemail */
                                clientEmail: string;
                                /** Requestedchange */
                                requestedChange: string;
                                /** Commercialterms */
                                commercialTerms: string;
                                /** Estimatedeffort */
                                estimatedEffort: string;
                                /** Additionalfee */
                                additionalFee: string;
                                /** Noadditionalcharge */
                                noAdditionalCharge: string;
                                /** Scheduleimpact */
                                scheduleImpact: string;
                                /** Additionalterms */
                                additionalTerms: string;
                                /** Approval */
                                approval: string;
                                /** Approvedby */
                                approvedBy: string;
                                /** Date */
                                date: string;
                                /** Draftfooter */
                                draftFooter: string;
                                /** Introduction */
                                introduction: string;
                                /** Outsidescopefree */
                                outsideScopeFree: string;
                                /** Enddate */
                                endDate: string;
                                /** Rationale */
                                rationale: string;
                                /** Terms */
                                terms: string;
                                /** Note */
                                note: string;
                                /** Page */
                                page: string;
                                /** Hours */
                                hours: string;
                            };
                            /** Aivalues */
                            aiValues?: {
                                [key: string]: string;
                            };
                            /** Currency */
                            currency: ("RUB" | "USD" | "EUR") | "" | unknown[];
                        } | null;
                        /** ReplyDocument */
                        reply: {
                            /** Tone */
                            tone: ("warm" | "neutral" | "firm") | unknown[];
                            /** Text */
                            text: string;
                            /** Replies */
                            generated: {
                                /** Warm */
                                warm: string;
                                /** Neutral */
                                neutral: string;
                                /** Firm */
                                firm: string;
                            };
                        };
                        /** ProjectDetails */
                        projectDetails: {
                            /** Clientname */
                            clientName: string;
                            /** Clientemail */
                            clientEmail: string;
                            /** Enddate */
                            endDate: string;
                        };
                    };
                };
            };
        };
        responses: {
            /** @description OK */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CreatedDraftResponse"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CreatedDraftResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_draft_api_drafts__id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Cache-Control"?: "private, no-store";
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DraftEnvelope"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    "Cache-Control"?: "private, no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    "Cache-Control"?: "private, no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Forbidden */
            403: {
                headers: {
                    "Cache-Control"?: "private, no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not Found */
            404: {
                headers: {
                    "Cache-Control"?: "private, no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    "Cache-Control"?: "private, no-store";
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    update_draft_api_drafts__id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    /** DraftDocument */
                    draftDocument: {
                        /**
                         * Version
                         * @constant
                         */
                        version: 1;
                        /** AnalysisSnapshot */
                        result: {
                            /**
                             * Verdict
                             * @enum {string}
                             */
                            verdict: "in_scope" | "borderline" | "out_of_scope";
                            /** Confidence */
                            confidence: number;
                            /** Summary */
                            summary: string;
                            /** Reasoning */
                            reasoning: string;
                            /** Citations */
                            citations: string[];
                            /** Suggestion */
                            suggestion?: string | null;
                            /** AnalysisReplies */
                            replies: {
                                /** Warm */
                                warm: string;
                                /** Neutral */
                                neutral: string;
                                /** Firm */
                                firm: string;
                            };
                            changeOrder: {
                                /** Description */
                                description: string;
                                /** Timelineimpact */
                                timelineImpact: string;
                                /** Additionalcost */
                                additionalCost: string;
                                /** Note */
                                note: string;
                                /** Estimatedhours */
                                estimatedHours?: number | null;
                                /** Currency */
                                currency?: ("RUB" | "USD" | "EUR") | "" | null;
                                /** Rationale */
                                rationale?: string | null;
                            } | null;
                            estimate?: {
                                /** Estimatedhours */
                                estimatedHours: number;
                                /** Additionalcost */
                                additionalCost: string;
                                /** Currency */
                                currency: ("RUB" | "USD" | "EUR") | "";
                            } | null;
                            /** Hasadditionalwork */
                            hasAdditionalWork?: boolean | null;
                            /** Requestlanguage */
                            requestLanguage?: ("ru" | "en" | "es" | "other") | null;
                            /** Clientlanguage */
                            clientLanguage?: string | null;
                            changeOrderLabels?: {
                                /** Title */
                                title: string;
                                /** Draft */
                                draft: string;
                                /** Documentnumber */
                                documentNumber: string;
                                /** Created */
                                created: string;
                                /** Project */
                                project: string;
                                /** Provider */
                                provider: string;
                                /** Client */
                                client: string;
                                /** Clientemail */
                                clientEmail: string;
                                /** Requestedchange */
                                requestedChange: string;
                                /** Commercialterms */
                                commercialTerms: string;
                                /** Estimatedeffort */
                                estimatedEffort: string;
                                /** Additionalfee */
                                additionalFee: string;
                                /** Noadditionalcharge */
                                noAdditionalCharge: string;
                                /** Scheduleimpact */
                                scheduleImpact: string;
                                /** Additionalterms */
                                additionalTerms: string;
                                /** Approval */
                                approval: string;
                                /** Approvedby */
                                approvedBy: string;
                                /** Date */
                                date: string;
                                /** Draftfooter */
                                draftFooter: string;
                                /** Introduction */
                                introduction: string;
                                /** Outsidescopefree */
                                outsideScopeFree: string;
                                /** Enddate */
                                endDate: string;
                                /** Rationale */
                                rationale: string;
                                /** Terms */
                                terms: string;
                                /** Note */
                                note: string;
                                /** Page */
                                page: string;
                                /** Hours */
                                hours: string;
                            } | null;
                            /** Draftcreatedat */
                            draftCreatedAt?: string | null;
                            /** Commercialsignature */
                            commercialSignature?: string | null;
                            /** Estimatevalid */
                            estimateValid?: boolean | null;
                        };
                        clientMaterials: {
                            /** Clientlanguage */
                            clientLanguage: string;
                            /** Replies */
                            replies: {
                                /** Warm */
                                warm: string;
                                /** Neutral */
                                neutral: string;
                                /** Firm */
                                firm: string;
                            };
                            changeOrder?: {
                                /** Description */
                                description: string;
                                /** Timelineimpact */
                                timelineImpact: string;
                                /** Rationale */
                                rationale: string;
                                /** Note */
                                note: string;
                            } | null;
                            changeOrderLabels?: {
                                /** Title */
                                title: string;
                                /** Draft */
                                draft: string;
                                /** Documentnumber */
                                documentNumber: string;
                                /** Created */
                                created: string;
                                /** Project */
                                project: string;
                                /** Provider */
                                provider: string;
                                /** Client */
                                client: string;
                                /** Clientemail */
                                clientEmail: string;
                                /** Requestedchange */
                                requestedChange: string;
                                /** Commercialterms */
                                commercialTerms: string;
                                /** Estimatedeffort */
                                estimatedEffort: string;
                                /** Additionalfee */
                                additionalFee: string;
                                /** Noadditionalcharge */
                                noAdditionalCharge: string;
                                /** Scheduleimpact */
                                scheduleImpact: string;
                                /** Additionalterms */
                                additionalTerms: string;
                                /** Approval */
                                approval: string;
                                /** Approvedby */
                                approvedBy: string;
                                /** Date */
                                date: string;
                                /** Draftfooter */
                                draftFooter: string;
                                /** Introduction */
                                introduction: string;
                                /** Outsidescopefree */
                                outsideScopeFree: string;
                                /** Enddate */
                                endDate: string;
                                /** Rationale */
                                rationale: string;
                                /** Terms */
                                terms: string;
                                /** Note */
                                note: string;
                                /** Page */
                                page: string;
                                /** Hours */
                                hours: string;
                            } | null;
                        } | null;
                        changeOrder: {
                            /** Createdat */
                            createdAt: string;
                            /** Language */
                            language: string;
                            /** Projectname */
                            projectName: string;
                            /** Description */
                            description: string;
                            /** Estimatedhours */
                            estimatedHours: string;
                            /** Additionalcost */
                            additionalCost: string;
                            /** Timelineimpact */
                            timelineImpact: string;
                            /** Rationale */
                            rationale: string;
                            /** Note */
                            note: string;
                            /** Providername */
                            providerName: string;
                            /** Clientname */
                            clientName: string;
                            /** Clientemail */
                            clientEmail: string;
                            /** Enddate */
                            endDate: string;
                            /** Additionalterms */
                            additionalTerms: string;
                            /** Clientapprovername */
                            clientApproverName: string;
                            /** Approvaldate */
                            approvalDate: string;
                            /** Noadditionalcharge */
                            noAdditionalCharge: boolean;
                            /** Reference */
                            reference?: string;
                            changeOrderLabels?: {
                                /** Title */
                                title: string;
                                /** Draft */
                                draft: string;
                                /** Documentnumber */
                                documentNumber: string;
                                /** Created */
                                created: string;
                                /** Project */
                                project: string;
                                /** Provider */
                                provider: string;
                                /** Client */
                                client: string;
                                /** Clientemail */
                                clientEmail: string;
                                /** Requestedchange */
                                requestedChange: string;
                                /** Commercialterms */
                                commercialTerms: string;
                                /** Estimatedeffort */
                                estimatedEffort: string;
                                /** Additionalfee */
                                additionalFee: string;
                                /** Noadditionalcharge */
                                noAdditionalCharge: string;
                                /** Scheduleimpact */
                                scheduleImpact: string;
                                /** Additionalterms */
                                additionalTerms: string;
                                /** Approval */
                                approval: string;
                                /** Approvedby */
                                approvedBy: string;
                                /** Date */
                                date: string;
                                /** Draftfooter */
                                draftFooter: string;
                                /** Introduction */
                                introduction: string;
                                /** Outsidescopefree */
                                outsideScopeFree: string;
                                /** Enddate */
                                endDate: string;
                                /** Rationale */
                                rationale: string;
                                /** Terms */
                                terms: string;
                                /** Note */
                                note: string;
                                /** Page */
                                page: string;
                                /** Hours */
                                hours: string;
                            };
                            /** Aivalues */
                            aiValues?: {
                                [key: string]: string;
                            };
                            /** Currency */
                            currency: ("RUB" | "USD" | "EUR") | "" | unknown[];
                        } | null;
                        /** ReplyDocument */
                        reply: {
                            /** Tone */
                            tone: ("warm" | "neutral" | "firm") | unknown[];
                            /** Text */
                            text: string;
                            /** Replies */
                            generated: {
                                /** Warm */
                                warm: string;
                                /** Neutral */
                                neutral: string;
                                /** Firm */
                                firm: string;
                            };
                        };
                        /** ProjectDetails */
                        projectDetails: {
                            /** Clientname */
                            clientName: string;
                            /** Clientemail */
                            clientEmail: string;
                            /** Enddate */
                            endDate: string;
                        };
                    };
                };
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DraftEnvelope"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    set_locale_api_locale_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    /** @enum {string} */
                    locale: "en" | "ru";
                };
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OkResponse"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_evaluation_api_evaluations_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    /** Format: uuid */
                    historyEntryId: string;
                    /** @constant */
                    accuracy: "correct";
                    aiReasoning: string;
                    humanVerdict?: never;
                } | {
                    /** Format: uuid */
                    historyEntryId: string;
                    /** @constant */
                    accuracy: "debatable";
                    aiReasoning: string;
                    humanVerdict?: never;
                } | {
                    /** Format: uuid */
                    historyEntryId: string;
                    /** @constant */
                    accuracy: "wrong";
                    aiReasoning: string;
                    /** @enum {string} */
                    humanVerdict: "in_scope" | "borderline" | "out_of_scope";
                };
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EvaluationEnvelope"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    export_evaluations_api_evaluations_export_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Content-Disposition"?: "attachment; filename=\"scope-creep-evaluations.jsonl\"";
                    [name: string]: unknown;
                };
                content: {
                    "application/x-ndjson": string;
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    legacy_revision_api_v2_legacy_drafts__identifier__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevisionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    projects_api_v2_projects_get: {
        parameters: {
            query?: {
                archived?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__ProjectsResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_project_api_v2_projects_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectWrite"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__ProjectResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    project_api_v2_projects__identifier__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__ProjectResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    archive_project_api_v2_projects__identifier__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_project_api_v2_projects__identifier__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__ProjectResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    restore_project_api_v2_projects__identifier__restore_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__ProjectResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    project_draft_api_v2_projects__identifier__draft_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__DraftResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    draft_collection_api_v2_drafts_get: {
        parameters: {
            query?: {
                projectId?: string | null;
                createdFrom?: string | null;
                createdTo?: string | null;
                sort?: "newest" | "oldest";
                limit?: number;
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DraftCollectionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    export_drafts_csv_api_v2_drafts_export_csv_get: {
        parameters: {
            query?: {
                projectId?: string | null;
                createdFrom?: string | null;
                createdTo?: string | null;
                sort?: "newest" | "oldest";
                locale?: "en" | "ru";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Content-Disposition"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/csv": string;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    export_draft_csv_api_v2_drafts__identifier__export_csv_get: {
        parameters: {
            query?: {
                locale?: "en" | "ru";
                expectedRevision?: string | null;
            };
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    "Content-Disposition"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/csv": string;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    draft_api_v2_drafts__identifier__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__DraftResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    save_draft_api_v2_drafts__identifier__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SaveWorkingDraft"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__DraftResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    clear_draft_api_v2_drafts__identifier__clear_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VersionedOperation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__DraftResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    revisions_api_v2_drafts__identifier__revisions_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevisionsResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    restore_api_v2_drafts__identifier__revisions__number__restore_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
                number: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VersionedOperation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__DraftResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    analyze_api_v2_drafts__identifier__analyses_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RunAnalysis"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalysisResponse"];
                };
            };
            /** @description Accepted */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PendingLlmOperation"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    run_api_v2_analyses__identifier__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    prepare_agreement_api_v2_drafts__identifier__agreement_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VersionedOperation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__DraftResponse"];
                };
            };
            /** @description Accepted */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PendingLlmOperation"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    estimate_api_v2_drafts__identifier__estimate_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VersionedOperation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalysisResponse"];
                };
            };
            /** @description Accepted */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PendingLlmOperation"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    apply_api_v2_analyses__identifier__apply_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalysisResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    regenerate_api_v2_drafts__identifier__regenerate_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VersionedOperation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__DraftResponse"];
                };
            };
            /** @description Accepted */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PendingLlmOperation"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    translate_api_v2_drafts__identifier__translate_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TranslateWorkingDraft"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__DraftResponse"];
                };
            };
            /** @description Accepted */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PendingLlmOperation"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    llm_status_api_v2_llm_operations__identifier__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LlmOperationStatus"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    complete_api_v2_drafts__identifier__history_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VersionedOperation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__HistoryResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    histories_api_v2_projects__identifier__history_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HistoriesResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    history_api_v2_history__identifier__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__HistoryResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    reopen_history_api_v2_history__identifier__restore_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VersionedOperation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["scope_guard_api__schemas__workflow__DraftResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    agreements_api_v2_history__identifier__change_orders_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgreementsResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    finalize_api_v2_history__identifier__change_orders_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Operation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgreementResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    agreement_api_v2_change_orders__identifier__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgreementResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    void_api_v2_change_orders__identifier__void_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VersionedOperation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgreementResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    exports_api_v2_change_orders__identifier__exports_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExportsResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_export_api_v2_change_orders__identifier__exports_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ExportRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExportResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    export_api_v2_exports__identifier__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExportResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    retry_api_v2_exports__identifier__retry_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Operation"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExportResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    download_api_v2_exports__identifier__download_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    evaluate_api_v2_analyses__identifier__evaluation_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                identifier: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Feedback"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    onboarding_api_v2_profile_onboarding_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OnboardingState"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    advance_onboarding_api_v2_profile_onboarding_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OnboardingEvent"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OnboardingState"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    profile_api_v2_profile_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileResponse"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_profile_api_v2_profile_patch: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProfileUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    interaction_api_v2_session_interaction_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Unexpected request failure */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
}
