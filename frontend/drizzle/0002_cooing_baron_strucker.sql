CREATE TYPE "public"."currency" AS ENUM('RUB', 'USD', 'EUR');--> statement-breakpoint
CREATE TYPE "public"."pricing_model" AS ENUM('hourly', 'fixed');--> statement-breakpoint
ALTER TABLE "projects" ADD COLUMN "start_date" date;--> statement-breakpoint
ALTER TABLE "projects" ADD COLUMN "pricing_model" "pricing_model";--> statement-breakpoint
ALTER TABLE "projects" ADD COLUMN "currency" "currency";--> statement-breakpoint
ALTER TABLE "projects" ADD COLUMN "hourly_rate" numeric(14, 2);--> statement-breakpoint
ALTER TABLE "projects" ADD COLUMN "fixed_price" numeric(14, 2);