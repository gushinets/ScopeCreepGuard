import { createChangeOrderDocument, type EditableDraft } from '@/lib/change-order/document'

export function ChangeOrderDocumentPreview({ draft }: { draft: EditableDraft }) {
  const document = createChangeOrderDocument(draft)
  const { labels: t } = document

  return (
    <article data-testid="change-order-document-preview" className="mx-auto w-full max-w-[760px] overflow-hidden rounded-sm border border-slate-300 bg-white text-slate-900 shadow-[0_16px_45px_rgba(15,23,42,0.12)]">
      <header className="border-b-4 border-amber-500 bg-slate-950 px-6 py-6 text-white sm:px-9">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-amber-300">{document.status}</p>
            <h2 className="mt-2 max-w-xl text-2xl font-extrabold leading-tight tracking-tight sm:text-3xl">{document.title}</h2>
          </div>
          <dl className="shrink-0 text-xs leading-5 text-slate-300 sm:text-right">
            <div><dt className="inline font-semibold text-white">{t.documentNumber}: </dt><dd className="inline">{document.reference}</dd></div>
            <div><dt className="inline font-semibold text-white">{t.created}: </dt><dd className="inline">{document.createdDate}</dd></div>
          </dl>
        </div>
      </header>

      <div className="px-6 py-7 sm:px-9 sm:py-9">
        <dl className="grid gap-x-8 gap-y-2 border-y border-slate-200 bg-slate-50 px-4 py-4 text-sm sm:grid-cols-2">
          {document.metadata.map(({ label, value }) => <div key={label} className="grid grid-cols-[7rem_1fr] gap-2"><dt className="font-bold text-slate-600">{label}</dt><dd className="font-medium">{value}</dd></div>)}
        </dl>

        <p className="mt-6 text-sm leading-6 text-slate-600">{document.introduction}</p>

        <DocumentSection heading={document.sections[0].heading}>
          {document.description && <p className="whitespace-pre-wrap text-sm leading-6">{document.description}</p>}
        </DocumentSection>

        <DocumentSection heading={document.sections[1].heading}>
          <div className="overflow-hidden rounded border border-slate-300">
            {document.commercialTerms.map(({ label, value }, index) => <div key={label} className={`grid grid-cols-[1fr_auto] gap-5 px-4 py-3 text-sm ${index > 0 ? 'border-t border-slate-200' : ''}`}><span className="font-semibold text-slate-600">{label}</span><strong className={index === document.commercialTerms.length - 1 ? 'text-base text-slate-950' : ''}>{value}</strong></div>)}
          </div>
        </DocumentSection>

        <DocumentSection heading={document.sections[2].heading}>
          {document.scheduleImpact && <p className="whitespace-pre-wrap text-sm leading-6">{document.scheduleImpact}</p>}
        </DocumentSection>

        <DocumentSection heading={document.sections[3].heading}>
          <dl className="space-y-3">{document.additionalItems.map(({ label, value }) => <div key={label}><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</dt><dd className="mt-1 whitespace-pre-wrap text-sm leading-6">{value}</dd></div>)}</dl>
        </DocumentSection>

        <section className="mt-8 border-t-2 border-slate-950 pt-4">
          <h3 className="text-sm font-extrabold uppercase tracking-wide">{document.approvalHeading}</h3>
          <div className="mt-6 grid gap-8 sm:grid-cols-2">
            {document.signatures.map((signature) => <div key={signature.label}><p className="text-sm font-bold">{signature.label}</p><div className="mt-10 border-b border-slate-700" /><p className="mt-1 text-xs text-slate-500">{t.signature}</p><div className="mt-7 border-b border-slate-700" /><p className="mt-1 text-xs text-slate-500">{t.date}</p></div>)}
          </div>
        </section>
      </div>

      <footer className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-6 py-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500 sm:px-9"><span>{t.draftFooter}</span><span>{document.reference}</span></footer>
    </article>
  )
}

function DocumentSection({ heading, children }: { heading: string; children: React.ReactNode }) {
  return <section className="mt-7"><h3 className="border-b border-slate-300 pb-2 text-sm font-extrabold uppercase tracking-wide text-slate-950">{heading}</h3><div className="mt-3">{children}</div></section>
}
