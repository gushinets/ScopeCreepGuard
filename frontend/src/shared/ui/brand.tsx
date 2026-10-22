export function Brand({ compact = false }: { compact?: boolean }) {
  return <span className="brand-lockup" aria-label="Scope Creep Guard">
    <svg className="brand-mark" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path d="M16 3 27 8v9c0 6-5 10-11 13C10 27 5 23 5 17V8L16 3Z" stroke="currentColor" strokeWidth="1.8" />
      <path d="M11 12h10M11 17h6M20 16v7m-3-3h6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
    {!compact && <span>Scope Creep <br />Guard</span>}
  </span>
}
