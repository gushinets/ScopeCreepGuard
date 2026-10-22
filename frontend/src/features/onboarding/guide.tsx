import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { useLayoutEffect, useRef, useState } from 'react'
import { useTranslations } from 'use-intl'
import { useOnboarding } from './context'
import { guideConnector, placeGuide, type Box, type Point } from './placement'

const targets: Record<number, string> = { 0: '[data-onboarding="create-project"]', 1: '#project-scope', 2: '#request-input', 4: '[data-onboarding="assessment"]' }
type Anchor = { target: HTMLElement; slot: HTMLElement }
type Layout = { mode: 'measuring' | 'inline' | 'floating'; point?: Point; inView: boolean; line?: ReturnType<typeof guideConnector> }

/** An empty destination, never another guide instance. */
export function OnboardingSlot({ step }: { step: number }) {
  return <div className="onboarding-slot" data-onboarding-slot={step} />
}

function textAndControlBounds(card: HTMLElement, target: HTMLElement): Box[] {
  return [...document.querySelectorAll<HTMLElement>('input,textarea,select,button,label,h1,h2,h3,p,blockquote,li,dt,dd,th,td,summary,[role=alert]')]
    .filter(element => element !== target && !card.contains(element) && element.getClientRects().length)
    .flatMap(element => {
      if (element.matches('h1,h2,h3,p,blockquote,li,dt,dd,th,td') && !element.matches('[role=alert]')) {
        const range = document.createRange()
        range.selectNodeContents(element)
        if (typeof range.getClientRects === 'function') return [...range.getClientRects()]
      }
      return [element.getBoundingClientRect()]
    })
}

/** The workspace mounts exactly one guide; pages expose only targets and slots. */
export function OnboardingGuide() {
  const { state, finishTip, skip, dismissFinal } = useOnboarding()
  const t = useTranslations()
  const active = state?.status === 'not_started' || state?.status === 'in_progress'
  const step = finishTip ? 4 : active && state.step !== 3 ? state.step : null
  const [anchor, setAnchor] = useState<Anchor | null>(null)
  const [layout, setLayout] = useState<Layout>({ mode: 'measuring', inView: false })
  const card = useRef<HTMLElement>(null)

  useLayoutEffect(() => {
    if (step === null) { setAnchor(null); return }
    const find = () => {
      const target = document.querySelector<HTMLElement>(targets[step])
      const slot = document.querySelector<HTMLElement>(`[data-onboarding-slot="${step}"]`)
      setAnchor(current => target && slot ? current?.target === target && current.slot === slot ? current : { target, slot } : null)
      if (target && slot) {
        const id = 'onboarding-description'
        const descriptions = target.getAttribute('aria-describedby')?.split(' ').filter(Boolean) ?? []
        if (!descriptions.includes(id)) target.setAttribute('aria-describedby', [...descriptions, id].join(' '))
      }
    }
    find()
    const observer = new MutationObserver(find)
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-describedby'] })
    return () => observer.disconnect()
  }, [step])

  useLayoutEffect(() => {
    if (!anchor || step === null) return
    const { target, slot } = anchor
    target.setAttribute('data-onboarding-current', 'true')
    let frame = 0, inlineSettled = false
    const measure = (reconsider = false) => {
      if (!card.current || !target.isConnected) return
      const element = card.current
      const originalCardStyle = element.style.cssText
      const originalSlotStyle = slot.style.cssText
      // Check a resize against normal page geometry, not the space occupied by
      // the inline card. Restore synchronously, before the browser can paint.
      if (reconsider && inlineSettled && window.innerWidth > 1100) {
        slot.style.display = 'contents'
        element.style.position = 'fixed'
        element.style.width = '304px'
      }
      const rect = target.getBoundingClientRect()
      const height = element.offsetHeight || 206
      const inView = rect.bottom > 16 && rect.top < window.innerHeight - 16
      const chosen = window.innerWidth > 1100 && (!inlineSettled || reconsider)
        ? placeGuide(rect, { width: 304, height }, { width: window.innerWidth, height: window.innerHeight }, textAndControlBounds(element, target)) : null
      element.style.cssText = originalCardStyle
      slot.style.cssText = originalSlotStyle
      inlineSettled = !chosen
      const cardRect = chosen ? { ...chosen, width: 304, height, right: chosen.left + 304, bottom: chosen.top + height } : element.getBoundingClientRect()
      const line = guideConnector(target.getBoundingClientRect(), cardRect)
      const next: Layout = { mode: chosen ? 'floating' : 'inline', ...(chosen ? { point: chosen } : {}), inView, line }
      setLayout(current => JSON.stringify(current) === JSON.stringify(next) ? current : next)
    }
    const update = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(() => measure()) }
    const resize = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(() => measure(true)) }
    setLayout({ mode: 'measuring', inView: false })
    measure()
    window.addEventListener('resize', resize)
    window.addEventListener('scroll', update, true)
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(update)
    observer?.observe(target)
    if (card.current) observer?.observe(card.current)
    return () => {
      cancelAnimationFrame(frame); observer?.disconnect()
      window.removeEventListener('resize', resize); window.removeEventListener('scroll', update, true)
      target.removeAttribute('data-onboarding-current')
      const descriptions = target.getAttribute('aria-describedby')?.split(' ').filter(id => id && id !== 'onboarding-description') ?? []
      if (descriptions.length) target.setAttribute('aria-describedby', descriptions.join(' ')); else target.removeAttribute('aria-describedby')
    }
  }, [anchor, step, t])

  if (step === null || !anchor) return null
  const current = step === 4 ? 4 : step + 1
  const floating = layout.mode === 'floating'
  const content = <aside ref={card} className="coachmark" role="dialog" aria-modal="false" aria-labelledby="onboarding-title" aria-describedby="onboarding-description" data-onboarding-card data-floating={floating} data-measuring={layout.mode === 'measuring'} style={floating ? { ...layout.point, visibility: layout.inView ? 'visible' : 'hidden' } : undefined}>
    <div className="coachmark-header"><span>{t('onboarding.progress', { current, total: 4 })}</span><button type="button" className="coachmark-close" onClick={step === 4 ? dismissFinal : skip} aria-label={t(step === 4 ? 'design.closeGuide' : 'onboarding.skip')}><X size={17} aria-hidden="true" /></button></div>
    <h2 id="onboarding-title">{t(`onboarding.step${step}Title` as 'onboarding.step0Title')}</h2>
    <p id="onboarding-description">{t(`onboarding.step${step}Body` as 'onboarding.step0Body')}</p>
    <div className="coachmark-footer"><div className="coachmark-progress" aria-hidden="true">{[1, 2, 3, 4].map(index => <span key={index} data-complete={index < current} data-current={index === current} />)}</div>{step === 4 && <button type="button" onClick={dismissFinal} className="coachmark-done">{t('onboarding.done')}</button>}</div>
  </aside>
  return <>{createPortal(content, layout.mode === 'inline' ? anchor.slot : document.body)}{layout.line && floating && layout.inView && createPortal(<svg className="guide-connector" aria-hidden="true"><path d={layout.line.path} /><circle cx={layout.line.x} cy={layout.line.y} r="4" /></svg>, document.body)}</>
}
