import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router/dom'
import { SessionProvider } from '@/features/auth'
import { LocalizationProvider } from '@/shared/i18n/provider'
import { router } from './router'
import './globals.css'

createRoot(document.getElementById('root')!).render(<LocalizationProvider><SessionProvider>
  <RouterProvider router={router()} />
</SessionProvider></LocalizationProvider>)
