import { createContext, useContext, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

const Surface = createContext<HTMLDivElement | null>(null)

/** The agreement has its own full-width working surface below the scope comparison. */
export function AgreementHost({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<HTMLDivElement | null>(null)
  return <Surface value={target}>{children}<div id="agreement-workspace" className="agreement-surface" ref={setTarget} /></Surface>
}

export function AgreementSurface({ children }: { children: ReactNode }) {
  const target = useContext(Surface)
  return target ? createPortal(children, target) : children
}
