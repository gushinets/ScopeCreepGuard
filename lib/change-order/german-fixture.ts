import type { ChangeOrderLabels } from './labels'

/** Shared verification fixture for the full document path. */
export const germanLabels: ChangeOrderLabels = {
  title: 'ÄNDERUNGSAUFTRAG', draft: 'ENTWURF', documentNumber: 'Dokumentnummer', created: 'Erstellt',
  project: 'Projekt', provider: 'Auftragnehmer', client: 'Auftraggeber', clientEmail: 'E-Mail des Auftraggebers',
  requestedChange: '1. Angeforderte Änderung', commercialTerms: '2. Vergütungsbedingungen',
  estimatedEffort: 'Geschätzter Aufwand', additionalFee: 'Zusätzliche Vergütung', noAdditionalCharge: 'Ohne zusätzliche Vergütung',
  scheduleImpact: '3. Auswirkungen auf den Zeitplan', additionalTerms: '4. Zusätzliche Bedingungen',
  approval: '5. Zustimmung des Auftraggebers', approvedBy: 'Genehmigt von', date: 'Datum', draftFooter: 'Entwurf zur Prüfung und Genehmigung',
  introduction: 'Dieser Entwurf dokumentiert zusätzliche Arbeiten. Er wird erst mit Zustimmung des Auftraggebers wirksam.',
  outsideScopeFree: 'Diese zusätzlichen Arbeiten werden ohne zusätzliche Vergütung ausgeführt.', endDate: 'Neues Projektabschlussdatum',
  rationale: 'Grundlage der Schätzung', terms: 'Besondere Bedingungen', note: 'Anmerkung', page: 'Seite', hours: 'Stunden',
}
