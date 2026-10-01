export const REPLY_TONE_SKILLS = {
  warm: `Write exactly one complete client-facing reply.

Use a warm, calm, professional, and confidently helpful tone. Adapt the level of formality to the client’s message. Keep simple cases concise; provide enough context when the scope, constraints, or decision may be unclear.

The reply must:
- acknowledge the client’s request directly and respectfully;
- state the scope position unambiguously: confirm what is included, distinguish what is outside the agreed scope, or explain what information is needed to determine this;
- avoid defensiveness, blame, legalistic wording, empty reassurance, and vague promises;
- if the request is in scope, confirm the concrete next action and, where known, the expected outcome or timing;
- if it is partly or fully out of scope, explain the boundary in practical terms and offer a realistic path forward, such as a separate estimate, prioritization, a phased option, an alternative solution, or a clarifying question;
- if the request cannot be completed now, say why plainly and identify the specific condition or information required to proceed;
- close with one constructive next step the client can understand and act on.

Do not invent facts, deadlines, pricing, approvals, or commitments. Do not repeat the client’s wording unnecessarily. Do not use placeholders, headings, bullet points, or meta-commentary. Return only the final reply.`,

  neutral: `Write exactly one complete, concise client-facing business reply.

Use a neutral, calm, factual, and professional tone. Be courteous without sounding cold, apologetic, overly familiar, defensive, or promotional.

The reply must:
- state the scope position clearly: confirm what is included, identify what is outside the agreed scope, or explain what information is needed to determine the scope;
- briefly explain the practical implication when necessary;
- name one specific next action: proceed with the included work, request clarification, prepare a separate estimate, propose an alternative, or ask for confirmation;
- avoid vague wording, blame, unnecessary background, and unverified promises;
- never invent dates, prices, approvals, requirements, or commitments.

Do not use headings, bullet points, placeholders, or meta-commentary. Return only the final reply.`,

  firm: `Write exactly one complete client-facing reply.

Use a respectful, firm, and professional tone. Be direct about boundaries and decisions without sounding aggressive, accusatory, dismissive, defensive, or apologetic.

The reply must:
- acknowledge the request briefly and accurately;
- state the scope position clearly: confirm whether the requested work is included, partially included, outside the agreed scope, or cannot yet be assessed without more information;
- when work is outside the agreed scope, say so plainly and distinguish it from the currently agreed deliverables;
- avoid vague language, blame, unnecessary justification, pressure tactics, and unverified commitments;
- state the required next step unambiguously: confirm the scope, approve an estimate, issue or approve a Change Order, provide the missing clarification, or decline the additional work;
- explain what will happen after that step is completed, without inventing dates, pricing, approvals, requirements, or commitments;
- make clear that additional work will not begin until the required scope decision or authorization is in place.

Do not use headings, bullet points, placeholders, or meta-commentary. Return only the final reply.`,
} as const

export function formatReplyToneSkills() {
  return `REPLY TONE SKILLS:

Apply each skill only to its corresponding reply string. The overall response must still be structured JSON.

replies.warm:
${REPLY_TONE_SKILLS.warm}

replies.neutral:
${REPLY_TONE_SKILLS.neutral}

replies.firm:
${REPLY_TONE_SKILLS.firm}`
}
