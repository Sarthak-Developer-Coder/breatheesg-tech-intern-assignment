import { useEffect, useMemo, useState } from 'react'

import type { IngestionJob, Paginated } from '../lib/api'
import { listIngestionJobs } from '../lib/api'
import { useConfig } from '../lib/ConfigContext'

function fmt(dt: string | null): string {
  if (!dt) return ''
  try {
    return new Date(dt).toLocaleString()
  } catch {
    return dt
  }
}

export default function IngestionJobsPage() {
  const { config } = useConfig()

  const [sourceType, setSourceType] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)

  const [data, setData] = useState<Paginated<IngestionJob> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const params = useMemo(
    () => ({ page, source_type: sourceType, status }),
    [page, sourceType, status],
  )

  useEffect(() => {
    let cancelled = false

    async function run() {
      setLoading(true)
      setError(null)
      try {
        const res = await listIngestionJobs(config, params)
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
        <h2 className="text-xl font-semibold">Ingestion Jobs</h2>
        <p className="mt-1 text-sm text-zinc-600">
          Each upload creates a job with raw/parsed/failed counts.
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
          <div className="mb-1 text-zinc-600">status</div>
          <input
            className="w-full rounded border border-zinc-300 px-2 py-1 md:w-40"
            value={status}
            onChange={(e) => {
              setPage(1)
              setStatus(e.target.value)
            }}
          />
        </label>
        <div className="ml-auto text-sm text-zinc-600">
          {loading ? 'Loading…' : data ? `${data.count} total` : ''}
        </div>
      </div>

      {error ? (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <div className="overflow-auto rounded border border-zinc-200">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="bg-zinc-50 text-xs uppercase text-zinc-600">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">File</th>
              <th className="px-3 py-2">Counts</th>
              <th className="px-3 py-2">Created</th>
              <th className="px-3 py-2">Finished</th>
            </tr>
          </thead>
          <tbody>
            {(data?.results ?? []).map((j) => (
              <tr key={j.id} className="border-t border-zinc-200">
                <td className="px-3 py-2 font-medium">{j.id}</td>
                <td className="px-3 py-2">{j.source_type}</td>
                <td className="px-3 py-2">{j.status}</td>
                <td className="px-3 py-2">{j.original_filename}</td>
                <td className="px-3 py-2">
                  <span className="text-zinc-600">raw</span> {j.raw_record_count}{' '}
                  <span className="text-zinc-400">·</span>{' '}
                  <span className="text-zinc-600">parsed</span> {j.parsed_record_count}{' '}
                  <span className="text-zinc-400">·</span>{' '}
                  <span className="text-zinc-600">failed</span> {j.failed_record_count}{' '}
                  <span className="text-zinc-400">·</span>{' '}
                  <span className="text-zinc-600">activities</span> {j.activity_record_count}{' '}
                  <span className="text-zinc-400">·</span>{' '}
                  <span className="text-zinc-600">anomalies</span> {j.anomaly_record_count}
                </td>
                <td className="px-3 py-2">{fmt(j.created_at)}</td>
                <td className="px-3 py-2">{fmt(j.finished_at)}</td>
              </tr>
            ))}
            {!loading && (data?.results?.length ?? 0) === 0 ? (
              <tr>
                <td className="px-3 py-6 text-zinc-600" colSpan={7}>
                  No jobs found.
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
