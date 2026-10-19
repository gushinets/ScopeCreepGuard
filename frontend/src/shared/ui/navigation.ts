import { featureContext } from './feature-context'
import type { View } from '../config/navigation'

export const [NavigationContext, useWorkspaceNavigation] = featureContext<{
  view: View
  setView: (view: View) => void
  beforeLeave: () => Promise<void>
  registerForm: (guard: (() => boolean) | null) => void
}>('Workspace navigation')
