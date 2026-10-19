import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router/dom'
import { Analytics } from '@vercel/analytics/react'
import { SessionProvider } from '@/features/auth'
import { LocalizationProvider } from '@/shared/i18n/provider'
import { router } from './router'
import '@fontsource-variable/geist'
import '@fontsource-variable/geist-mono'
import './globals.css'

createRoot(document.getElementById('root')!).render(<LocalizationProvider><SessionProvider>
  <RouterProvider router={router()} />{import.meta.env.PROD && <Analytics />}
</SessionProvider></LocalizationProvider>)
