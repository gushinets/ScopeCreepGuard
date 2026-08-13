import type { AnalysisResult, Tone, Verdict } from './types'

const OUT_SIGNALS = [
  'more page',
  'more pages',
  'additional page',
  'extra page',
  'new page',
  'another page',
  'mobile',
  'responsive',
  'second round',
  '2nd round',
  'another round',
  'extra round',
  'develop',
  'development',
  'implementation',
  'implement',
  'code',
  'build the site',
  'video',
  'copywriting',
  'landing page',
  'checkout flow',
  'paid ad',
]

const BORDERLINE_SIGNALS = [
  'add a',
  'add an',
  'new section',
  'a section',
  'sign-up',
  'signup',
  'newsletter',
  'new element',
  'small feature',
  'slightly',
  'not sure',
]

const IN_SIGNALS = [
  'typo',
  'fix',
  'color',
  'colour',
  'headline',
  'spacing',
  'revision',
  'small edit',
  'minor edit',
  'caption',
  'tweak',
  'wording',
]

function countMatches(haystack: string, signals: string[]): string[] {
  return signals.filter((s) => haystack.includes(s))
}

/** Pick scope lines that share topical keywords with the request. */
function extractCitations(scope: string, request: string): string[] {
  const req = request.toLowerCase()
  const topics = [
    'page',
    'pages',
    'mobile',
    'responsive',
    'revision',
    'round',
    'develop',
    'video',
    'copywriting',
    'ad',
    'newsletter',
    'section',
  ]
  const relevant = topics.filter((t) => req.includes(t))
  const lines = scope
    .split('\n')
    .map((l) => l.trim().replace(/^-\s*/, ''))
    .filter((l) => l.length > 0)

  const matched = lines.filter((line) => {
    const low = line.toLowerCase()
    return relevant.some((t) => low.includes(t))
  })

  const unique = Array.from(new Set(matched)).slice(0, 3)
  if (unique.length > 0) return unique

  // Fallback: surface the excluded / included section headers.
  return lines
    .filter((l) => /exclud|included|deliverable|revision/i.test(l))
    .slice(0, 2)
}

function buildReplies(verdict: Verdict): Record<Tone, string> {
  if (verdict === 'in_scope') {
    return {
      warm: `Hi there,

Thanks for the note — happy to take care of this! The change you described fits within our agreed scope and the included revision round, so there is no extra cost or timeline impact.

I'll get it done and share an updated version shortly.

Best,`,
      neutral: `Hi,

Thanks for the request. This falls within our agreed scope and the included revision round, so I can proceed at no additional cost.

I'll implement the change and send an updated version for your review.

Best regards,`,
      firm: `Hello,

Confirming that this request is covered by our current scope and the included revision round. I'll proceed and deliver the updated version.

Please note this counts toward the single revision round agreed for the project.

Regards,`,
    }
  }

  if (verdict === 'borderline') {
    return {
      warm: `Hi there,

Thanks for sending this over! It's close to our agreed scope but not a clear match, so I'd like to confirm the details before I start.

Could you clarify exactly what you have in mind? Depending on the effort, this may fit within the current scope, or it may need a small add-on — either way I'll be transparent about it before doing any work.

Best,`,
      neutral: `Hi,

Thanks for the request. This sits on the edge of our agreed scope, so I'd like to align before proceeding.

Could you confirm the exact requirements? If it's a minor adjustment I can likely include it; if it's more involved I'll share a short add-on estimate first.

Best regards,`,
      firm: `Hello,

This request is not clearly covered by our current scope, so I'd like to confirm the specifics before starting any work.

Please share the exact requirements and I'll let you know whether it's included or needs a separate change order.

Regards,`,
    }
  }

  return {
    warm: `Hi there,

Thanks so much for sharing these ideas — I can see how they'd strengthen the project. A quick heads-up: they go beyond what we agreed in the original scope, so I'd love to set them up properly as an add-on.

I've put together a short change order with the extra work, timeline, and cost. Once you approve it, I'll get started right away.

Best,`,
    neutral: `Hi,

Thanks for the request. These items fall outside our agreed scope (specifically the additional pages, mobile layouts, and the second revision round).

I'm glad to take them on as additional work. I've prepared a change order covering the extra scope, timeline, and cost — just let me know if you'd like to proceed.

Best regards,`,
    firm: `Hello,

The requested items are outside the scope we agreed for this project. The original agreement covers a fixed set of deliverables, and these additions go beyond it.

I've prepared a change order with the additional cost and timeline. I'll begin once it's approved.

Regards,`,
  }
}

export interface AnalyzeOptions {
  forceError?: boolean
}

export class AnalysisError extends Error {}

export function analyzeRequest(
  scope: string,
  request: string,
  options: AnalyzeOptions = {},
): AnalysisResult {
  if (options.forceError) {
    throw new AnalysisError('The analysis service did not respond.')
  }

  const hay = request.toLowerCase()
  const out = countMatches(hay, OUT_SIGNALS)
  const border = countMatches(hay, BORDERLINE_SIGNALS)
  const inside = countMatches(hay, IN_SIGNALS)

  let verdict: Verdict
  if (out.length > 0) verdict = 'out_of_scope'
  else if (border.length > 0) verdict = 'borderline'
  else if (inside.length > 0) verdict = 'in_scope'
  else verdict = 'borderline'

  const citations = extractCitations(scope, request)

  if (verdict === 'in_scope') {
    return {
      verdict,
      confidence: 82,
      summary:
        'This request appears to fall within your agreed scope and the included revision round.',
      reasoning:
        'The request describes small adjustments to pages and elements that are part of the agreed deliverables, and it fits within the single revision round included in the scope. No new deliverables are introduced.',
      citations,
      replies: buildReplies(verdict),
      changeOrder: {
        description: 'No additional work required — request is covered by the current scope.',
        timelineImpact: 'None.',
        additionalCost: '$0 (included).',
        note: 'This is a draft summary, not a legal document. Review before sending.',
      },
    }
  }

  if (verdict === 'borderline') {
    return {
      verdict,
      confidence: 54,
      summary:
        'This request is close to your scope but not a clear match. Confirm the details before you commit.',
      reasoning:
        'The request introduces something adjacent to the agreed deliverables — it touches an in-scope area but may add new work whose effort is unclear from the wording. The scope neither clearly includes nor clearly excludes it.',
      citations,
      suggestion:
        'Ask the client for the exact requirements, or clarify in your scope whether this type of change is included. Avoid starting work until it is agreed.',
      replies: buildReplies(verdict),
      changeOrder: {
        description:
          'Optional add-on (pending clarification): the newly requested element beyond the agreed deliverables.',
        timelineImpact: 'To be confirmed once requirements are clear.',
        additionalCost: 'To be estimated after scope is confirmed.',
        note: 'This is a draft summary, not a legal document. Review before sending.',
      },
    }
  }

  return {
    verdict,
    confidence: 88,
    summary:
      'This request goes beyond your agreed scope. It is likely additional, billable work.',
    reasoning:
      'The request adds deliverables that the scope either does not list or explicitly excludes — such as extra pages, mobile/responsive layouts, or a further revision round. Delivering it without a change order would be unpaid extra work.',
    citations,
    suggestion:
      'Send a change order so the extra pages, mobile layouts, and additional revision round are agreed and paid before you begin.',
    replies: buildReplies(verdict),
    changeOrder: {
      description:
        '3 additional page designs, mobile/responsive layouts for all pages, and a second round of revisions.',
      timelineImpact: '+1.5 weeks added to the current timeline.',
      additionalCost: '$2,400 (fixed, billed on approval).',
      note: 'This is a draft summary, not a legal document. Review before sending.',
    },
  }
}
