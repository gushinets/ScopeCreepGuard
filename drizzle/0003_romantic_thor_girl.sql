ALTER TABLE "projects" ADD CONSTRAINT "projects_commercial_terms_consistent" CHECK ((
    ("projects"."start_date" IS NULL AND "projects"."pricing_model" IS NULL AND "projects"."currency" IS NULL AND "projects"."hourly_rate" IS NULL AND "projects"."fixed_price" IS NULL)
    OR
    ("projects"."start_date" IS NOT NULL AND "projects"."currency" IS NOT NULL AND (
      ("projects"."pricing_model" = 'hourly' AND "projects"."hourly_rate" > 0 AND "projects"."fixed_price" IS NULL)
      OR ("projects"."pricing_model" = 'fixed' AND "projects"."fixed_price" > 0 AND "projects"."hourly_rate" IS NULL)
    ))
  ));