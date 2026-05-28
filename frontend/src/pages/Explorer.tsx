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

export default function ExplorerPage() {
  const { config } = useConfig()

  const [page, setPage] = useState(1)

  const [reviewStatus, setReviewStatus] = useState('')
  const [sourceType, setSourceType] = useState('')
  const [category, setCategory] = useState('')
  const [subcategory, setSubcategory] = useState('')
  const [plantCode, setPlantCode] = useState('')
  const [hasAnomalies, setHasAnomalies] = useState<'all' | 'yes' | 'no'>('all')
  const [isLocked, setIsLocked] = useState<'all' | 'yes' | 'no'>('all')

  const [data, setData] = useState<Paginated<ActivityRecordListItem> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const params = useMemo(() => {
    const p: Record<string, unknown> = { page }
    if (reviewStatus) p.review_status = reviewStatus
    if (sourceType) p.source_type = sourceType
    if (category) p.category = category
    if (subcategory) p.subcategory = subcategory
    if (plantCode) p.plant_code = plantCode
    if (hasAnomalies === 'yes') p.has_anomalies = true
    if (hasAnomalies === 'no') p.has_anomalies = false
    if (isLocked === 'yes') p.is_locked = true
    if (isLocked === 'no') p.is_locked = false
    return p
  }, [
    page,
    reviewStatus,
    sourceType,
    category,
    subcategory,
    plantCode,
    hasAnomalies,
    isLocked,
  ])

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
        <h2 className="text-xl font-semibold">Activity Explorer</h2>
        <p className="mt-1 text-sm text-zinc-600">
          Cross-source exploration with lightweight filters.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 rounded border border-zinc-200 p-3 md:grid-cols-3">
        <label className="text-sm">
          <div className="mb-1 text-zinc-600">review_status</div>
          <input
            className="w-full rounded border border-zinc-300 px-2 py-1"
            value={reviewStatus}
            onChange={(e) => {
              setPage(1)
              setReviewStatus(e.target.value)
            }}
          />
        </label>
        <label className="text-sm">
          <div className="mb-1 text-zinc-600">source_type</div>
          <input
            className="w-full rounded border border-zinc-300 px-2 py-1"
            value={sourceType}
            onChange={(e) => {
              setPage(1)
              setSourceType(e.target.value)
            }}
          />
        </label>
        <label className="text-sm">
          <div className="mb-1 text-zinc-600">plant_code</div>
          <input
            className="w-full rounded border border-zinc-300 px-2 py-1"
            value={plantCode}
            onChange={(e) => {
              setPage(1)
              setPlantCode(e.target.value)
            }}
          />
        </label>
        <label className="text-sm">
          <div className="mb-1 text-zinc-600">category</div>
          <input
            className="w-full rounded border border-zinc-300 px-2 py-1"
            value={category}
            onChange={(e) => {
              setPage(1)
              setCategory(e.target.value)
            }}
          />
        </label>
        <label className="text-sm">
          <div className="mb-1 text-zinc-600">subcategory</div>
          <input
            className="w-full rounded border border-zinc-300 px-2 py-1"
            value={subcategory}
            onChange={(e) => {
              setPage(1)
              setSubcategory(e.target.value)
            }}
          />
        </label>
        <label className="text-sm">
          <div className="mb-1 text-zinc-600">has_anomalies</div>
          <select
            className="w-full rounded border border-zinc-300 px-2 py-1"
            value={hasAnomalies}
            onChange={(e) => {
              setPage(1)
              setHasAnomalies(e.target.value as 'all' | 'yes' | 'no')
            }}
          >
            <option value="all">all</option>
            <option value="yes">yes</option>
            <option value="no">no</option>
          </select>
        </label>
        <label className="text-sm">
          <div className="mb-1 text-zinc-600">is_locked</div>
          <select
            className="w-full rounded border border-zinc-300 px-2 py-1"
            value={isLocked}
            onChange={(e) => {
              setPage(1)
              setIsLocked(e.target.value as 'all' | 'yes' | 'no')
            }}
          >
            <option value="all">all</option>
            <option value="yes">yes</option>
            <option value="no">no</option>
          </select>
        </label>

        <div className="flex items-end text-sm text-zinc-600 md:col-span-2">
          {loading ? 'Loading…' : data ? `${data.count} records` : ''}
        </div>
      </div>

      {error ? (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <div className="overflow-auto rounded border border-zinc-200">
        <table className="w-full min-w-[1200px] text-left text-sm">
          <thead className="bg-zinc-50 text-xs uppercase text-zinc-600">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Plant</th>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Quantity</th>
              <th className="px-3 py-2">CO2e (kg)</th>
              <th className="px-3 py-2">Anomalies</th>
              <th className="px-3 py-2">Locked</th>
            </tr>
          </thead>
          <tbody>
            {(data?.results ?? []).map((a) => (
              <tr key={a.id} className="border-t border-zinc-200">
                <td className="px-3 py-2 font-medium">{a.id}</td>
                <td className="px-3 py-2">{a.review_status}</td>
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
                  {a.anomaly_flags.length ? a.anomaly_flags.join(', ') : '—'}
                </td>
                <td className="px-3 py-2">{a.locked_at ? 'yes' : 'no'}</td>
              </tr>
            ))}
            {!loading && (data?.results?.length ?? 0) === 0 ? (
              <tr>
                <td className="px-3 py-6 text-zinc-600" colSpan={10}>
                  No records.
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
