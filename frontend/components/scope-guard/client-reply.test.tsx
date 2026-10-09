// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { AnalysisResult } from '@/lib/types'
import { ClientReply } from './client-reply'

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => {
    const messages: Record<string, string> = {
      'reply.heading': 'Suggested reply to client',
      'reply.toneAria': 'Reply tone',
      'reply.editableLabel': 'Editable reply to client',
      'reply.warm': 'Warm',
      'reply.neutral': 'Neutral',
      'reply.firm': 'Firm',
      'reply.copied': 'Copied',
      'reply.copy': 'Copy reply',
      'reply.regenerate': 'Regenerate',
      'reply.regenerating': 'Generating a new variant…',
      'reply.regenerateError':
        'Couldn’t generate a new variant. Your reply was not changed. Try again.',
      'reply.sendYourself': 'Nothing is sent automatically.',
      'reply.copiedStatus': 'Reply copied to clipboard.',
      'reply.confirmReplace': 'Replace your edits?',
    }
    return messages[key] ?? key
  },
}))

const result: AnalysisResult = {
  verdict: 'out_of_scope',
  confidence: 90,
  summary: 'A blog is additional work.',
  reasoning: 'The scope only includes a landing page.',
  citations: ['landing page'],
  replies: {
    warm: 'Warm original reply.',
    neutral: 'Neutral original reply.',
    firm: 'Firm original reply.',
  },
  changeOrder: {
    description: 'Add a blog.',
    timelineImpact: 'To be estimated.',
    additionalCost: 'To be estimated.',
    note: 'Draft only.',
  },
}

function renderReply() {
  return render(
    <ClientReply
      result={result}
      projectId="project-1"
      request="Please add a blog."
    />,
  )
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
  vi.spyOn(window, 'confirm').mockReturnValue(true)
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('ClientReply regeneration', () => {
  it('shows loading and disables regeneration and tone controls', async () => {
    let resolveFetch!: (value: Response) => void
    vi.mocked(fetch).mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveFetch = resolve
      }),
    )
    renderReply()

    fireEvent.click(screen.getByRole('button', { name: 'Regenerate' }))

    expect(
      (screen.getByRole('button', {
        name: 'Generating a new variant…',
      }) as HTMLButtonElement).disabled,
    ).toBe(true)
    for (const radio of screen.getAllByRole('radio')) {
      expect((radio as HTMLButtonElement).disabled).toBe(true)
    }

    resolveFetch({
      ok: true,
      json: async () => ({ reply: 'New neutral reply.' }),
    } as Response)
    await waitFor(() => {
      expect(
        (screen.getByLabelText('Editable reply to client') as HTMLTextAreaElement)
          .value,
      ).toBe('New neutral reply.')
    })
  })

  it('sends the original request and current visible reply, then replaces it', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ reply: 'Substantively different reply.' }),
    } as Response)
    renderReply()
    const textarea = screen.getByLabelText('Editable reply to client')
    fireEvent.change(textarea, { target: { value: 'My edited visible reply.' } })

    fireEvent.click(screen.getByRole('button', { name: 'Regenerate' }))

    expect(window.confirm).toHaveBeenCalledWith('Replace your edits?')
    await waitFor(() => {
      expect((textarea as HTMLTextAreaElement).value).toBe(
        'Substantively different reply.',
      )
    })
    expect(fetch).toHaveBeenCalledWith('/api/replies/regenerate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        projectId: 'project-1',
        request: 'Please add a blog.',
        tone: 'neutral',
        previousReply: 'My edited visible reply.',
      }),
    })
  })

  it('preserves the reply after failure and succeeds when retried', async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce({ ok: false, status: 502 } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ reply: 'Reply returned by retry.' }),
      } as Response)
    renderReply()
    const textarea = screen.getByLabelText('Editable reply to client')

    fireEvent.click(screen.getByRole('button', { name: 'Regenerate' }))

    expect((await screen.findByRole('alert')).textContent).toContain(
      'Couldn’t generate a new variant. Your reply was not changed. Try again.',
    )
    expect((textarea as HTMLTextAreaElement).value).toBe(
      'Neutral original reply.',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Regenerate' }))

    await waitFor(() => {
      expect((textarea as HTMLTextAreaElement).value).toBe(
        'Reply returned by retry.',
      )
    })
    expect(screen.queryByRole('alert')).toBeNull()
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})
