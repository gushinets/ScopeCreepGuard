// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import ru from '@/messages/ru.json'
import { PersistentHistoryView } from './persistent-history'
const state = vi.hoisted(() => ({ complete: vi.fn() }))
vi.mock('./store', () => ({ useStore: () => ({ selectedProject: { history: [] }, draftDocument: { changeOrder: {} }, workflow: { complete: state.complete } }) }))
beforeEach(() => { state.complete.mockReset().mockResolvedValue(undefined) })
afterEach(cleanup)
it.each([{ locale: 'en', messages: en, label: 'Archive current document edits' }, { locale: 'ru', messages: ru, label: 'Сохранить правки документа в Историю' }] as const)('archives edited material through the existing durable action in $locale', async ({ locale, messages, label }) => {
 let finish!: () => void
 state.complete.mockImplementation(() => new Promise<void>(resolve => { finish = resolve }))
 render(<NextIntlClientProvider locale={locale} messages={messages}><PersistentHistoryView /></NextIntlClientProvider>)
 const action = screen.getByRole('button', { name: label }) as HTMLButtonElement
 fireEvent.click(action)
 expect(action.disabled).toBe(true)
 expect(state.complete).toHaveBeenCalledTimes(1)
 finish()
 await waitFor(() => expect(action.disabled).toBe(false))
})
