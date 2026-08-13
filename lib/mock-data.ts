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
export const EXAMPLE_REQUESTS: {
  key: string
  label: string
  text: string
}[] = [
  {
    key: 'in',
    label: 'In scope',
    text: 'On the Home page, could you fix the typo in the hero headline and adjust the accent color to a slightly darker blue? This would be part of our revision round.',
  },
  {
    key: 'borderline',
    label: 'Borderline',
    text: 'Could you add a small newsletter sign-up section to the bottom of the Home page? It is a new element, but it sits on a page that is already in scope.',
  },
  {
    key: 'out',
    label: 'Out of scope',
    text: 'Can you also add 3 more pages, prepare mobile versions of all the pages, and do a second round of revisions after we review?',
  },
  {
    key: 'error',
    label: 'Connection error',
    text: 'Please review whether this larger set of changes to the checkout flow is covered by our current agreement.',
  },
]
