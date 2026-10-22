// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { IntlProvider } from 'use-intl'
import en from '@/shared/i18n/messages/en.json'
import { OnboardingProvider, OnboardingGuide, OnboardingSlot, SkipOnboarding, useOnboarding } from './index'

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks() })

function Actions() {
  const { send } = useOnboarding()
  return <><button data-onboarding="create-project" onClick={() => { void send('form_opened') }}>Open form</button><button onClick={() => { void send('project_saved') }}>Saved</button><SkipOnboarding /><OnboardingSlot step={0} /><textarea id="project-scope" /><OnboardingSlot step={1} /><textarea id="request-input" /><OnboardingSlot step={2} /><OnboardingGuide /></>
}
function mount() {
  return render(<IntlProvider locale="en" messages={en}><OnboardingProvider><Actions /></OnboardingProvider></IntlProvider>)
}

it.each([0, 1, 2, 3])('dismisses immediately and saves skip at step %s', async step => {
  const fetcher = vi.fn(async (_path, init?: RequestInit) => Response.json(init?.method === 'POST' ? { status: 'skipped', step } : { status: step ? 'in_progress' : 'not_started', step }))
  vi.stubGlobal('fetch', fetcher)
  mount()
  fireEvent.click(await screen.findByText('Skip onboarding'))
  expect(screen.queryByText('Skip onboarding')).toBeNull()
  await waitFor(() => expect(fetcher).toHaveBeenCalledWith('/api/v2/profile/onboarding', expect.objectContaining({ body: JSON.stringify({ event: 'skip' }) })))
})

it('keeps ordinary actions available when onboarding cannot load', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('offline') }))
  mount()
  fireEvent.click(screen.getByText('Open form'))
  expect(screen.getByText('Saved')).toBeTruthy()
  expect(screen.queryByText('Skip onboarding')).toBeNull()
})

it.each(['completed', 'skipped'])('respects persisted %s state on remount', async status => {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({ status, step: 4 })))
  const first = mount()
  await act(async () => {})
  first.unmount()
  mount()
  await act(async () => {})
  expect(screen.queryByText('Skip onboarding')).toBeNull()
})

it('uses one shared card across action steps, with progress inside that card', async () => {
  let step = 0
  vi.stubGlobal('fetch', vi.fn(async (_path, init?: RequestInit) => {
    if (init?.method === 'POST') step++
    return Response.json({ status: step ? 'in_progress' : 'not_started', step })
  }))
  mount()
  await screen.findByText('Step 1 of 4')
  expect(screen.getAllByRole('dialog')).toHaveLength(1)
  expect(screen.queryByText('Getting started')).toBeNull()
  fireEvent.click(screen.getByText('Open form'))
  await screen.findByText('Step 2 of 4')
  expect(screen.getAllByRole('dialog')).toHaveLength(1)
  expect(screen.queryByText('Create a project')).toBeNull()
  fireEvent.click(screen.getByText('Saved'))
  await screen.findByText('Step 3 of 4')
  expect(screen.getAllByRole('dialog')).toHaveLength(1)
  expect(screen.queryByRole('button', { name: 'Next' })).toBeNull()
})

it('does not advance after a failed state save and retries on reconnect', async () => {
  let fail = true
  vi.stubGlobal('fetch', vi.fn(async (_path, init?: RequestInit) => {
    if (init?.method !== 'POST') return Response.json({ status: 'not_started', step: 0 })
    if (fail) throw new Error('offline')
    return Response.json({ status: 'in_progress', step: 1 })
  }))
  mount()
  await screen.findByText('Create a project')
  await act(async () => { fireEvent.click(screen.getByText('Open form')) })
  expect(screen.getByText('Create a project')).toBeTruthy()
  fail = false
  await act(async () => { window.dispatchEvent(new Event('online')) })
  expect(await screen.findByText('What’s included?')).toBeTruthy()
})

it('keeps the inline guide in flow after late target measurements, until the viewport changes', async () => {
  let blocked = true
  let remeasure = () => {}
  vi.stubGlobal('innerWidth', 1280)
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({ status: 'not_started', step: 0 })))
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => { callback(0); return 1 })
  vi.stubGlobal('cancelAnimationFrame', vi.fn())
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback: ResizeObserverCallback) { remeasure = () => callback([], this as unknown as ResizeObserver) }
    observe() {}
    disconnect() {}
  })
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
    if (this.dataset.onboarding === 'create-project') return new DOMRect(1050, 100, 150, 40)
    if (this.dataset.testid === 'obstacle' && blocked) return new DOMRect(770, 90, 270, 180)
    return new DOMRect()
  })
  vi.spyOn(HTMLElement.prototype, 'getClientRects').mockImplementation(function (this: HTMLElement) {
    return (this.dataset.testid === 'obstacle' ? [this.getBoundingClientRect()] : []) as unknown as DOMRectList
  })
  render(<IntlProvider locale="en" messages={en}><OnboardingProvider>
    <button data-onboarding="create-project">New project</button><p data-testid="obstacle">Nearby content</p>
    <OnboardingSlot step={0} /><OnboardingGuide /><p>Project collection</p>
  </OnboardingProvider></IntlProvider>)
  const tip = await screen.findByRole('dialog')
  expect(tip.getAttribute('data-floating')).toBe('false')
  blocked = false
  await act(async () => { remeasure(); window.dispatchEvent(new Event('scroll')) })
  expect(screen.getByRole('dialog').closest('.onboarding-slot')).toBeTruthy()
  expect(screen.getByRole('dialog').getAttribute('data-floating')).toBe('false')
  await act(async () => { window.dispatchEvent(new Event('resize')) })
  expect(screen.getByRole('dialog').getAttribute('data-floating')).toBe('true')
  vi.stubGlobal('innerWidth', 1100)
  await act(async () => { window.dispatchEvent(new Event('resize')) })
  expect(screen.getByRole('dialog').getAttribute('data-floating')).toBe('false')
})

it('places the guide beside visible text without treating unused block width as an obstacle', async () => {
  vi.stubGlobal('innerWidth', 1280)
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({ status: 'not_started', step: 0 })))
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
    if (this.dataset.onboarding === 'create-project') return new DOMRect(1050, 100, 150, 40)
    return new DOMRect(0, 90, 1280, 180)
  })
  vi.spyOn(HTMLElement.prototype, 'getClientRects').mockImplementation(function (this: HTMLElement) {
    return (this.tagName === 'H2' ? [this.getBoundingClientRect()] : []) as unknown as DOMRectList
  })
  const createRange = document.createRange.bind(document)
  vi.spyOn(document, 'createRange').mockImplementation(() => {
    const range = createRange()
    range.getClientRects = () => [new DOMRect(20, 100, 200, 24)] as unknown as DOMRectList
    return range
  })
  render(<IntlProvider locale="en" messages={en}><OnboardingProvider>
    <button data-onboarding="create-project">New project</button><OnboardingSlot step={0} /><OnboardingGuide />
    <h2>Project collection</h2>
  </OnboardingProvider></IntlProvider>)
  expect((await screen.findByRole('dialog')).getAttribute('data-floating')).toBe('true')
})
