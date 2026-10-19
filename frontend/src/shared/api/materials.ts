import type { AnalysisResult } from './models'
import type { ChangeOrderLabels } from './labels'
export type ClientChangeOrderText = Record<'description' | 'timelineImpact' | 'rationale' | 'note', string>
export interface ClientMaterials {
  clientLanguage: string
  replies: AnalysisResult['replies']
  changeOrder: ClientChangeOrderText | null
  changeOrderLabels?: ChangeOrderLabels
}
