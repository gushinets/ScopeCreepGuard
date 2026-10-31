import { createBrowserRouter, Navigate, useLocation } from 'react-router'
import { AuthForm } from '@/features/auth'
import { VerifyEmail, ConfirmEmail } from '@/features/auth/email-confirmation'
import { PasswordRecovery } from '@/features/auth/password-recovery'
import { ProtectedWorkspace, PublicAuthLayout } from './layout'
import { CheckPage, ProjectsPage, NewProjectPage, EditProjectPage, HistoryPage, DraftsPage } from '@/pages/screens'
import { adoptHistoryState } from '@/shared/config/navigation'

function CheckAlias() { const location = useLocation(); return <Navigate to={`/${location.search}${location.hash}`} replace /> }
function NotFound() { return <main className="p-10"><h1>404</h1><a href="/">Scope Creep Guard</a></main> }
export const routes = [
  { path: '/forgot-password', element: <PasswordRecovery /> },
  { path: '/reset-password', element: <PasswordRecovery reset /> },
  { path: '/verify-email', element: <VerifyEmail /> },
  { path: '/confirm-email', element: <ConfirmEmail /> },
  { element: <PublicAuthLayout />, children: [{ path: '/login', element: <AuthForm mode="login" /> }, { path: '/register', element: <AuthForm mode="register" /> }] },
  { element: <ProtectedWorkspace />, children: [
    { path: '/', element: <CheckPage /> }, { path: '/check', element: <CheckAlias /> },
    { path: '/projects', element: <ProjectsPage /> }, { path: '/projects/new', element: <NewProjectPage /> },
    { path: '/projects/:projectId/edit', element: <EditProjectPage /> }, { path: '/history', element: <HistoryPage /> },
    { path: '/drafts', element: <DraftsPage /> },
  ] }, { path: '*', element: <NotFound /> },
]
export const router = () => { adoptHistoryState(); return createBrowserRouter(routes) }
