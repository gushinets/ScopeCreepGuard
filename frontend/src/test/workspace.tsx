/** Test-only compatibility lens for unchanged persistence assertions; no legacy application. */
import { useState, type ReactNode } from 'react'
import { createBrowserRouter, RouterProvider } from 'react-router'
import { WorkspaceProvider } from '@/app/workspace'
import { SessionProvider, useSession, SessionContext } from '@/features/auth'
import { ProjectsContext, useProjects, type ProjectsValue } from '@/features/projects'
import { DraftsContext, useDrafts, type DraftsValue } from '@/features/drafts'
import { AnalysisContext, useAnalysis, type AnalysisValue } from '@/features/analysis'
import { AgreementContext, useAgreements } from '@/features/change-orders'
import { HistoryContext, useHistory } from '@/features/history'
import { NavigationContext, useWorkspaceNavigation } from '@/shared/ui/navigation'
import { adoptHistoryState } from '@/shared/config/navigation'

function Authenticated({ children }: { children: ReactNode }) {
  const { user } = useSession()
  return user ? <WorkspaceProvider key={user.id}>{children}</WorkspaceProvider> : null
}
export function PersistentStoreProvider({ children }: { children: ReactNode }) {
  const [router] = useState(() => { adoptHistoryState(); return createBrowserRouter([{ path: '*', element: <SessionProvider><Authenticated>{children}</Authenticated></SessionProvider> }]) })
  return <RouterProvider router={router} />
}
export function useStore() {
  const session = useSession(), projects = useProjects(), drafts = useDrafts(), analysis = useAnalysis(), agreements = useAgreements(), history = useHistory(), navigation = useWorkspaceNavigation()
  return { ...session, ...projects, ...drafts, ...analysis, ...agreements, ...navigation,
    workflow: { ...drafts.workflow, ...history, ...agreements, regenerate: analysis.regenerate, archivedProjects: projects.archivedProjects, openArchived: projects.openArchived } }
}
export type StoreValue = ReturnType<typeof useStore>

/** UI unit fixtures inject focused contexts instead of constructing a fake legacy provider. */
function TestProviders({ children, value }: { children: ReactNode; value: StoreValue }) {
  const combined = { ...value, ...value.workflow }
  return <SessionContext.Provider value={value}><ProjectsContext.Provider value={value as ProjectsValue}>
    <DraftsContext.Provider value={value as DraftsValue}><AnalysisContext.Provider value={value as AnalysisValue}>
      <AgreementContext.Provider value={combined}><HistoryContext.Provider value={value.workflow ?? {} as StoreValue['workflow']}>
        <NavigationContext.Provider value={{ ...value, beforeLeave: async () => {}, registerForm: () => {} }}>{children}</NavigationContext.Provider>
      </HistoryContext.Provider></AgreementContext.Provider>
    </AnalysisContext.Provider></DraftsContext.Provider>
  </ProjectsContext.Provider></SessionContext.Provider>
}
export const StoreContext = { Provider: TestProviders }
