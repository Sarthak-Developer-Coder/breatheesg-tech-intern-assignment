import { useEffect, useMemo, useState } from 'react'

import type { ActivityRecordListItem, Paginated } from '../lib/api'
import { listActivityRecords } from '../lib/api'
import { useConfig } from '../lib/ConfigContext'

function fmtDate(dt: string | null): string {
  if (!dt) return ''
  try {
    return new Date(dt).toLocaleDateString()
  } catch {
    return dt
  }
}

export default function ApprovedRecordsPage() {
  const { config } = useConfig()

  const [page, setPage] = useState(1)
  const [sourceType, setSourceType] = useState('')
  const [category, setCategory] = useState('')

  const [data, setData] = useState<Paginated<ActivityRecordListItem> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const params = useMemo(
    () => ({ page, review_status: 'approved', source_type: sourceType, category }),
    [page, sourceType, category],
  )

  useEffect(() => {
    let cancelled = false

    async function run() {
      setLoading(true)
      setError(null)
      try {
        const res = await listActivityRecords(config, params)
        if (!cancelled) setData(res)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    run()
    return () => {
      cancelled = true
    }
  }, [config, params])

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Approved Records</h2>
        <p className="mt-1 text-sm text-zinc-600">
          Approved rows are locked and auditable.
        </p>
      </div>

      <div className="flex flex-col gap-3 rounded border border-zinc-200 p-3 md:flex-row md:items-end">
        <label className="text-sm">
          <div className="mb-1 text-zinc-600">source_type</div>
          <input
            className="w-full rounded border border-zinc-300 px-2 py-1 md:w-40"
            value={sourceType}
            onChange={(e) => {
              setPage(1)
              setSourceType(e.target.value)
            }}
          />
        </label>
        <label className="text-sm">
          <div className="mb-1 text-zinc-600">category</div>
          <input
            className="w-full rounded border border-zinc-300 px-2 py-1 md:w-56"
            value={category}
            onChange={(e) => {
              setPage(1)
              setCategory(e.target.value)
            }}
          />
        </label>
        <div className="ml-auto text-sm text-zinc-600">
          {loading ? 'Loading…' : data ? `${data.count} approved` : ''}
        </div>
      </div>

      {error ? (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <div className="overflow-auto rounded border border-zinc-200">
        <table className="w-full min-w-[1100px] text-left text-sm">
          <thead className="bg-zinc-50 text-xs uppercase text-zinc-600">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Plant</th>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Quantity</th>
              <th className="px-3 py-2">CO2e (kg)</th>
              <th className="px-3 py-2">Approved</th>
            </tr>
          </thead>
          <tbody>
            {(data?.results ?? []).map((a) => (
              <tr key={a.id} className="border-t border-zinc-200">
                <td className="px-3 py-2 font-medium">{a.id}</td>
                <td className="px-3 py-2">{a.source_type}</td>
                <td className="px-3 py-2">
                  <div className="font-medium">{a.plant_code || '—'}</div>
                  <div className="text-xs text-zinc-500">{a.plant_name}</div>
                </td>
                <td className="px-3 py-2">{fmtDate(a.activity_date)}</td>
                <td className="px-3 py-2">
                  <div className="font-medium">{a.category}</div>
                  <div className="text-xs text-zinc-500">{a.subcategory}</div>
                </td>
                <td className="px-3 py-2">
                  {a.quantity} {a.normalized_unit}
                </td>
                <td className="px-3 py-2">{a.co2e_kg}</td>
                <td className="px-3 py-2">
                  <div className="font-medium">{a.approved_by || '—'}</div>
                  <div className="text-xs text-zinc-500">{fmtDate(a.approved_at)}</div>
                </td>
              </tr>
            ))}
            {!loading && (data?.results?.length ?? 0) === 0 ? (
              <tr>
                <td className="px-3 py-6 text-zinc-600" colSpan={8}>
                  No approved records.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-2">
        <button
          className="rounded border border-zinc-300 px-3 py-1 text-sm disabled:opacity-50"
          disabled={page <= 1 || loading}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          type="button"
        >
          Prev
        </button>
        <div className="text-sm text-zinc-600">Page {page}</div>
        <button
          className="rounded border border-zinc-300 px-3 py-1 text-sm disabled:opacity-50"
          disabled={!data?.next || loading}
          onClick={() => setPage((p) => p + 1)}
          type="button"
        >
          Next
        </button>
      </div>
    </div>
  )
}
