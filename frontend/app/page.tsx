import { AppShell } from '@/components/scope-guard/app-shell'

export default function Page() {
  return <AppShell persistent={process.env.SCOPE_GUARD_WORKFLOW_V2 === 'true'} />
}
