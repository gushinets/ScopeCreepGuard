import { createContext, useContext } from 'react'

export function featureContext<T>(name: string) {
  const Context = createContext<T | null>(null)
  const useFeature = () => {
    const value = useContext(Context)
    if (!value) throw new Error(`${name} provider is missing`)
    return value
  }
  return [Context, useFeature] as const
}
