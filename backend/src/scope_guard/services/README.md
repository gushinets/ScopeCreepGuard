Services own application use cases and explicit transaction boundaries. They use
domain values, repository/UoW contracts, dedicated query ports and integration
interfaces without importing HTTP objects, ORM types or concrete adapters.

Document preparation and scope extraction receive explicit validated inputs and
return detached results. Integrations own rendering, localization/fonts, readers
and bounded isolated execution. Export preserves saved/editor money and currency
without conversion or implicit recalculation. Read transactions close before LLM
calls; failed writes roll back through Unit of Work cleanup.
