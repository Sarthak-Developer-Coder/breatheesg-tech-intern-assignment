import { createContext, useContext } from 'react'

import type { ApiConfig } from './api'

export type ConfigContextValue = {
  config: ApiConfig
  setConfig: (cfg: ApiConfig) => void
}

export const ConfigContext = createContext<ConfigContextValue | null>(null)

export function useConfig(): ConfigContextValue {
  const ctx = useContext(ConfigContext)
  if (!ctx) throw new Error('useConfig must be used within ConfigContext.Provider')
  return ctx
}
