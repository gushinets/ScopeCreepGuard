import type { Industry } from '@/lib/types'

export function buildAnalysisMessages(input: {
  scope: string
  request: string
  industry: Industry
}) {
  const system = `You are Scope Creep Guard for freelancers.
Compare the client request ONLY against the provided project scope.
Industry context: ${input.industry}.
Return one verdict:
- in_scope: clearly covered by scope / included revisions
- out_of_scope: new deliverables or explicitly excluded work
- borderline: adjacent or unclear; do not pretend certainty
Rules:
- Cite short verbatim phrases from the scope in citations (0-3 items).
- Write replies.warm / replies.neutral / replies.firm in professional English the freelancer can send.
- Fill changeOrder for out_of_scope and borderline; for in_scope set cost to included / $0 style text.
- changeOrder.note must say this is a draft, not legal advice.
- Never invent scope clauses that are not in the provided scope.
- suggestion may be empty string when not needed.`

  const user = `PROJECT SCOPE:
${input.scope}

CLIENT REQUEST:
${input.request}`

  return [
    { role: 'system' as const, content: system },
    { role: 'user' as const, content: user },
  ]
}
