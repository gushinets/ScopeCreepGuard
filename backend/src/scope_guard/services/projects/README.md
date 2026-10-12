# Projects services

Use cases depend on domain values, explicit UoW/read ports and integration
interfaces. Every write commits explicitly; failure rolls back. HTTP composition
lives in apps/api and concrete adapters live in database/integrations.
