export const ACME_SCOPE = `Project: Acme website redesign

Deliverables:
- Visual design for 5 key pages: Home, About, Services, Pricing, Contact.
- Desktop layouts delivered as Figma files.
- One (1) round of revisions across the delivered pages.

Explicitly excluded:
- Front-end or back-end development / implementation.
- Copywriting and content creation.
- Additional pages beyond the 5 listed above.
- Mobile / responsive layouts (desktop only).
- More than one round of revisions.

Timeline: 3 weeks from kickoff. Fixed price for the scope above.`

export const NORTHWIND_SCOPE = `Project: Northwind marketing retainer

Deliverables:
- 8 social posts per month (copy + static image) across LinkedIn and Instagram.
- 1 monthly email newsletter (up to 500 words).
- Monthly performance report.

Included:
- Minor edits and captions for provided brand assets.

Excluded:
- Paid ad management and ad spend.
- Video production and editing.
- Landing page or website work.

Term: rolling monthly. Billed at the start of each month.`

/** Preset client requests reviewers can load to see each verdict. */
export const EXAMPLE_REQUESTS = [
  { key: 'in' },
  { key: 'borderline' },
  { key: 'out' },
] as const
