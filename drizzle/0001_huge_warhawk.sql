CREATE TYPE "public"."evaluation_accuracy" AS ENUM('correct', 'wrong', 'debatable');--> statement-breakpoint
CREATE TABLE "evaluation_cases" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid NOT NULL,
	"history_entry_id" uuid,
	"scope" text NOT NULL,
	"request" text NOT NULL,
	"ai_verdict" "verdict" NOT NULL,
	"human_verdict" "verdict",
	"ai_reasoning" text NOT NULL,
	"accuracy" "evaluation_accuracy" NOT NULL,
	"industry" "industry" NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "evaluation_cases_history_entry_id_unique" UNIQUE("history_entry_id"),
	CONSTRAINT "evaluation_cases_accuracy_human_verdict" CHECK ((
        ("evaluation_cases"."accuracy" = 'debatable' AND "evaluation_cases"."human_verdict" IS NULL)
        OR
        ("evaluation_cases"."accuracy" = 'correct' AND "evaluation_cases"."human_verdict" IS NOT NULL AND "evaluation_cases"."human_verdict" = "evaluation_cases"."ai_verdict")
        OR
        ("evaluation_cases"."accuracy" = 'wrong' AND "evaluation_cases"."human_verdict" IS NOT NULL AND "evaluation_cases"."human_verdict" <> "evaluation_cases"."ai_verdict")
      ))
);
--> statement-breakpoint
ALTER TABLE "evaluation_cases" ADD CONSTRAINT "evaluation_cases_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "evaluation_cases" ADD CONSTRAINT "evaluation_cases_history_entry_id_history_entries_id_fk" FOREIGN KEY ("history_entry_id") REFERENCES "public"."history_entries"("id") ON DELETE set null ON UPDATE no action;