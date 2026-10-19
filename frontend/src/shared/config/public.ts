/** Public application configuration never reads server environment variables. */
export const publicConfig = Object.freeze({ apiBase: '/api', locales: ['ru', 'en'] as const })
