import { NavLink, Outlet } from 'react-router-dom'

import { saveConfig } from '../lib/appConfig'
import { useConfig } from '../lib/ConfigContext'

function navClass(isActive: boolean): string {
  return [
    'block rounded px-3 py-2 text-sm',
    isActive ? 'bg-zinc-900 text-white' : 'text-zinc-700 hover:bg-zinc-100',
  ].join(' ')
}

export default function Shell() {
  const { config, setConfig } = useConfig()

  function update(partial: Partial<typeof config>) {
    const next = { ...config, ...partial }
    setConfig(next)
    saveConfig(next)
  }

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      <header className="border-b border-zinc-200">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center">
          <div className="flex items-baseline gap-3">
            <h1 className="text-lg font-semibold">Activity Review</h1>
            <span className="text-sm text-zinc-500">prototype</span>
          </div>

          <div className="flex flex-1 flex-col gap-2 md:ml-auto md:flex-row md:items-center md:justify-end">
            <label className="flex items-center gap-2 text-sm">
              <span className="w-20 text-zinc-600">API</span>
              <input
                className="w-full rounded border border-zinc-300 px-2 py-1 text-sm md:w-64"
                value={config.baseUrl}
                onChange={(e) => update({ baseUrl: e.target.value })}
              />
            </label>

            <label className="flex items-center gap-2 text-sm">
              <span className="w-20 text-zinc-600">Tenant</span>
              <input
                className="w-full rounded border border-zinc-300 px-2 py-1 text-sm md:w-40"
                value={config.tenantSlug}
                onChange={(e) => update({ tenantSlug: e.target.value })}
              />
            </label>

            <label className="flex items-center gap-2 text-sm">
              <span className="w-20 text-zinc-600">Analyst</span>
              <input
                className="w-full rounded border border-zinc-300 px-2 py-1 text-sm md:w-64"
                value={config.actor}
                onChange={(e) => update({ actor: e.target.value })}
              />
            </label>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-4 py-6 md:grid-cols-[200px_1fr]">
        <nav className="space-y-1">
          <NavLink to="/uploads" className={({ isActive }) => navClass(isActive)}>
            Upload Center
          </NavLink>
          <NavLink to="/jobs" className={({ isActive }) => navClass(isActive)}>
            Ingestion Jobs
          </NavLink>
          <NavLink to="/review" className={({ isActive }) => navClass(isActive)}>
            Review Queue
          </NavLink>
          <NavLink to="/approved" className={({ isActive }) => navClass(isActive)}>
            Approved Records
          </NavLink>
          <NavLink to="/explorer" className={({ isActive }) => navClass(isActive)}>
            Activity Explorer
          </NavLink>
        </nav>

        <main className="min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
