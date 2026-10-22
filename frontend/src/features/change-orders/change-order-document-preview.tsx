import { createChangeOrderDocument, type EditableDraft } from '@/features/change-orders/model/document'

export function ChangeOrderDocumentPreview({ draft }: { draft: EditableDraft }) {
  const document = createChangeOrderDocument(draft)
  const { labels: t } = document

  return (
    <article data-testid="change-order-document-preview" className="agreement-paper">
      <header className="agreement-paper-header">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
          <div>
            <p className="text-xs text-muted-foreground">{document.status}</p>
            <h2 className="mt-2 text-xl font-medium leading-tight">{document.title}</h2>
          </div>
          <dl className="text-xs leading-5 text-muted-foreground">
            <div><dt className="inline font-medium text-foreground">{t.documentNumber}: </dt><dd className="inline">{document.reference}</dd></div>
            <div><dt className="inline font-medium text-foreground">{t.created}: </dt><dd className="inline">{document.createdDate}</dd></div>
          </dl>
        </div>
      </header>

      <div className="agreement-paper-body">
        {document.readinessWarning && <p role="note" className="mb-4 border border-amber-600 bg-amber-50 p-3 text-sm font-semibold">{document.readinessWarning}</p>}
        <dl className="document-metadata">
          {document.metadata.map(({ label, value }) => <div key={label} className="grid grid-cols-[7rem_1fr] gap-2"><dt className="font-medium text-muted-foreground">{label}</dt><dd className="font-medium">{value}</dd></div>)}
        </dl>

        <p className="mt-6 text-sm leading-6 text-muted-foreground">{document.introduction}</p>

        <DocumentSection heading={document.sections[0].heading}>
          {document.description && <p className="whitespace-pre-wrap text-sm leading-6">{document.description}</p>}
        </DocumentSection>

        <DocumentSection heading={document.sections[1].heading}>
          <div className="overflow-hidden rounded border border-border">
            {document.commercialTerms.map(({ label, value }, index) => <div key={label} className={`grid grid-cols-[1fr_auto] gap-5 px-4 py-3 text-sm ${index > 0 ? 'border-t border-border' : ''}`}><span className="font-semibold text-muted-foreground">{label}</span><strong className={index === document.commercialTerms.length - 1 ? 'text-base text-foreground' : ''}>{value}</strong></div>)}
          </div>
        </DocumentSection>

        <DocumentSection heading={document.sections[2].heading}>
          {document.scheduleImpact && <p className="whitespace-pre-wrap text-sm leading-6">{document.scheduleImpact}</p>}
        </DocumentSection>

        <DocumentSection heading={document.sections[3].heading}>
          <dl className="space-y-3">{document.additionalItems.map(({ label, value }) => <div key={label}><dt className="text-xs font-medium text-muted-foreground">{label}</dt><dd className="mt-1 whitespace-pre-wrap text-sm leading-6">{value}</dd></div>)}</dl>
        </DocumentSection>

        <section className="mt-8 border-t border-border pt-4">
          <h3 className="text-sm font-medium">{document.approvalHeading}</h3>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div><dt className="font-medium text-muted-foreground">{t.approvedBy}</dt><dd className="mt-5 min-h-5 border-b border-slate-400">{document.approval.approverName}</dd></div>
            <div><dt className="font-medium text-muted-foreground">{t.date}</dt><dd className="mt-5 min-h-5 border-b border-slate-400">{document.approval.approvalDate}</dd></div>
          </dl>
        </section>
      </div>

      <footer className="agreement-paper-footer"><span>{t.draftFooter}</span><span>{document.reference}</span></footer>
    </article>
  )
}

function DocumentSection({ heading, children }: { heading: string; children: React.ReactNode }) {
  return <section className="mt-7"><h3 className="pb-2 text-sm font-medium text-foreground">{heading}</h3><div className="mt-3">{children}</div></section>
}
