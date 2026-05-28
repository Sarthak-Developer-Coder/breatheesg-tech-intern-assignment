import { useEffect, useMemo, useState } from 'react'

import type { ActivityRecordListItem, Paginated } from '../lib/api'
import {
  approveActivityRecord,
  editActivityRecord,
  getActivityRecord,
  listReviewQueue,
  rejectActivityRecord,
} from '../lib/api'
import { useConfig } from '../lib/ConfigContext'

type EditState = {
  loading: boolean
  error: string | null
  value: {
    scope: string
    category: string
    subcategory: string
    plant_id: string
    activity_date: string
    period_start: string
    period_end: string
    quantity: string
    normalized_unit: string
    activity_metadata: string
    reason: string
  }
}

function fmtDate(dt: string | null): string {
  if (!dt) return ''
  try {
    return new Date(dt).toLocaleDateString()
  } catch {
    return dt
  }
}

function badgeClass(kind: 'ok' | 'warn'): string {
  return [
    'inline-flex items-center rounded px-2 py-0.5 text-xs font-medium',
    kind === 'ok' ? 'bg-zinc-100 text-zinc-700' : 'bg-amber-100 text-amber-900',
  ].join(' ')
}

function parseNullableInt(raw: string): number | null {
  const trimmed = raw.trim()
  if (!trimmed) return null
  const n = Number(trimmed)
  return Number.isFinite(n) ? n : null
}

export default function ReviewQueuePage() {
  const { config } = useConfig()

  const [page, setPage] = useState(1)
  const [sourceType, setSourceType] = useState('')
  const [hasAnomalies, setHasAnomalies] = useState<'all' | 'yes' | 'no'>('all')

  const [data, setData] = useState<Paginated<ActivityRecordListItem> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [reasons, setReasons] = useState<Record<number, string>>({})
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editState, setEditState] = useState<EditState | null>(null)

  const params = useMemo(() => {
    const p: Record<string, unknown> = { page }
    if (sourceType) p.source_type = sourceType
    if (hasAnomalies === 'yes') p.has_anomalies = true
    if (hasAnomalies === 'no') p.has_anomalies = false
    return p
  }, [page, sourceType, hasAnomalies])

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      const res = await listReviewQueue(config, params)
      setData(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoading(true)
      setError(null)
      try {
        const res = await listReviewQueue(config, params)
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

  async function startEdit(id: number) {
    setEditingId(id)
    setEditState({
      loading: true,
      error: null,
      value: {
        scope: '',
        category: '',
        subcategory: '',
        plant_id: '',
        activity_date: '',
        period_start: '',
        period_end: '',
        quantity: '',
        normalized_unit: '',
        activity_metadata: '{}',
        reason: reasons[id] ?? '',
      },
    })

    try {
      const detail = await getActivityRecord(config, id)
      setEditState({
        loading: false,
        error: null,
        value: {
          scope: detail.scope ?? '',
          category: detail.category ?? '',
          subcategory: detail.subcategory ?? '',
          plant_id: detail.plant_id ? String(detail.plant_id) : '',
          activity_date: detail.activity_date ?? '',
          period_start: detail.period_start ?? '',
          period_end: detail.period_end ?? '',
          quantity: detail.quantity ?? '',
          normalized_unit: detail.normalized_unit ?? '',
          activity_metadata: JSON.stringify(detail.activity_metadata ?? {}, null, 2),
          reason: reasons[id] ?? '',
        },
      })
    } catch (e) {
      setEditState((prev) =>
        prev
          ? {
              ...prev,
              loading: false,
              error: e instanceof Error ? e.message : String(e),
            }
          : prev,
      )
    }
  }

  async function saveEdit(id: number) {
    if (!editState) return

    setEditState((prev) => (prev ? { ...prev, loading: true, error: null } : prev))

    let metadata: Record<string, unknown>
    try {
      metadata = JSON.parse(editState.value.activity_metadata) as Record<string, unknown>
    } catch {
      setEditState((prev) =>
        prev
          ? { ...prev, loading: false, error: 'activity_metadata must be valid JSON' }
          : prev,
      )
      return
    }

    try {
      const updated = await editActivityRecord(
        config,
        id,
        {
          scope: editState.value.scope,
          category: editState.value.category,
          subcategory: editState.value.subcategory,
          plant_id: parseNullableInt(editState.value.plant_id),
          activity_date: editState.value.activity_date || null,
          period_start: editState.value.period_start || null,
          period_end: editState.value.period_end || null,
          quantity: editState.value.quantity,
          normalized_unit: editState.value.normalized_unit,
          activity_metadata: metadata,
        },
        editState.value.reason,
      )

      setReasons((r) => ({ ...r, [id]: editState.value.reason }))
      setEditingId(null)
      setEditState(null)

      setData((prev) => {
        if (!prev) return prev
        const nextResults = prev.results.map((row) =>
          row.id === id ? (updated as unknown as ActivityRecordListItem) : row,
        )
        return { ...prev, results: nextResults }
      })
    } catch (e) {
      setEditState((prev) =>
        prev
          ? { ...prev, loading: false, error: e instanceof Error ? e.message : String(e) }
          : prev,
      )
      return
    }

    setEditState((prev) => (prev ? { ...prev, loading: false } : prev))
  }

  async function approve(id: number) {
    setLoading(true)
    setError(null)
    try {
      await approveActivityRecord(config, id, reasons[id] ?? '')
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  async function reject(id: number) {
    setLoading(true)
    setError(null)
    try {
      await rejectActivityRecord(config, id, reasons[id] ?? '')
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const canAct = Boolean(config.actor && config.tenantSlug)

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Review Queue</h2>
        <p className="mt-1 text-sm text-zinc-600">
          Pending records only. Edit before approving; approvals lock rows for
          audit.
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
          <div className="mb-1 text-zinc-600">has_anomalies</div>
          <select
            className="w-full rounded border border-zinc-300 px-2 py-1 md:w-40"
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

        <div className="ml-auto text-sm text-zinc-600">
          {loading ? 'Loading…' : data ? `${data.count} pending` : ''}
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
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Plant</th>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Quantity</th>
              <th className="px-3 py-2">CO2e (kg)</th>
              <th className="px-3 py-2">Anomalies</th>
              <th className="px-3 py-2">Confidence</th>
              <th className="px-3 py-2">Reason</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(data?.results ?? []).map((a) => (
              <tr key={a.id} className="border-t border-zinc-200 align-top">
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
                  <div className="text-xs text-zinc-500">
                    src: {a.source_quantity} {a.source_unit}
                  </div>
                </td>
                <td className="px-3 py-2">{a.co2e_kg}</td>
                <td className="px-3 py-2">
                  {a.anomaly_flags.length ? (
                    <span className={badgeClass('warn')}>
                      {a.anomaly_flags.join(', ')}
                    </span>
                  ) : (
                    <span className={badgeClass('ok')}>none</span>
                  )}
                </td>
                <td className="px-3 py-2">{a.confidence_score}</td>
                <td className="px-3 py-2">
                  <input
                    className="w-56 rounded border border-zinc-300 px-2 py-1"
                    value={reasons[a.id] ?? ''}
                    onChange={(e) =>
                      setReasons((r) => ({ ...r, [a.id]: e.target.value }))
                    }
                    placeholder="optional"
                  />
                </td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-2">
                    <button
                      className="rounded border border-zinc-300 px-2 py-1 text-sm disabled:opacity-50"
                      type="button"
                      disabled={!canAct || loading}
                      onClick={() => startEdit(a.id)}
                    >
                      Edit
                    </button>
                    <button
                      className="rounded bg-zinc-900 px-2 py-1 text-sm text-white disabled:opacity-50"
                      type="button"
                      disabled={!canAct || loading}
                      onClick={() => approve(a.id)}
                    >
                      Approve
                    </button>
                    <button
                      className="rounded border border-zinc-300 px-2 py-1 text-sm disabled:opacity-50"
                      type="button"
                      disabled={!canAct || loading}
                      onClick={() => reject(a.id)}
                    >
                      Reject
                    </button>
                  </div>
                </td>
              </tr>
            ))}

            {editingId && editState ? (
              <tr className="border-t border-zinc-200">
                <td className="px-3 py-3" colSpan={11}>
                  <div className="space-y-3 rounded border border-zinc-200 bg-zinc-50 p-3">
                    <div className="flex items-center gap-2">
                      <div className="font-medium">Editing #{editingId}</div>
                      <button
                        className="ml-auto rounded border border-zinc-300 px-2 py-1 text-sm"
                        type="button"
                        onClick={() => {
                          setEditingId(null)
                          setEditState(null)
                        }}
                      >
                        Close
                      </button>
                    </div>

                    {editState.error ? (
                      <div className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-800">
                        {editState.error}
                      </div>
                    ) : null}

                    <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                      <label className="text-sm">
                        <div className="mb-1 text-zinc-600">scope</div>
                        <input
                          className="w-full rounded border border-zinc-300 px-2 py-1"
                          value={editState.value.scope}
                          onChange={(e) =>
                            setEditState((prev) =>
                              prev
                                ? {
                                    ...prev,
                                    value: { ...prev.value, scope: e.target.value },
                                  }
                                : prev,
                            )
                          }
                        />
                      </label>
                      <label className="text-sm">
                        <div className="mb-1 text-zinc-600">category</div>
                        <input
                          className="w-full rounded border border-zinc-300 px-2 py-1"
                          value={editState.value.category}
                          onChange={(e) =>
                            setEditState((prev) =>
                              prev
                                ? {
                                    ...prev,
                                    value: { ...prev.value, category: e.target.value },
                                  }
                                : prev,
                            )
                          }
                        />
                      </label>
                      <label className="text-sm">
                        <div className="mb-1 text-zinc-600">subcategory</div>
                        <input
                          className="w-full rounded border border-zinc-300 px-2 py-1"
                          value={editState.value.subcategory}
                          onChange={(e) =>
                            setEditState((prev) =>
                              prev
                                ? {
                                    ...prev,
                                    value: { ...prev.value, subcategory: e.target.value },
                                  }
                                : prev,
                            )
                          }
                        />
                      </label>

                      <label className="text-sm">
                        <div className="mb-1 text-zinc-600">plant_id</div>
                        <input
                          className="w-full rounded border border-zinc-300 px-2 py-1"
                          value={editState.value.plant_id}
                          onChange={(e) =>
                            setEditState((prev) =>
                              prev
                                ? {
                                    ...prev,
                                    value: { ...prev.value, plant_id: e.target.value },
                                  }
                                : prev,
                            )
                          }
                          placeholder="(blank for none)"
                        />
                      </label>
                      <label className="text-sm">
                        <div className="mb-1 text-zinc-600">activity_date</div>
                        <input
                          className="w-full rounded border border-zinc-300 px-2 py-1"
                          value={editState.value.activity_date}
                          onChange={(e) =>
                            setEditState((prev) =>
                              prev
                                ? {
                                    ...prev,
                                    value: { ...prev.value, activity_date: e.target.value },
                                  }
                                : prev,
                            )
                          }
                          placeholder="YYYY-MM-DD"
                        />
                      </label>
                      <label className="text-sm">
                        <div className="mb-1 text-zinc-600">quantity</div>
                        <input
                          className="w-full rounded border border-zinc-300 px-2 py-1"
                          value={editState.value.quantity}
                          onChange={(e) =>
                            setEditState((prev) =>
                              prev
                                ? {
                                    ...prev,
                                    value: { ...prev.value, quantity: e.target.value },
                                  }
                                : prev,
                            )
                          }
                        />
                      </label>

                      <label className="text-sm">
                        <div className="mb-1 text-zinc-600">period_start</div>
                        <input
                          className="w-full rounded border border-zinc-300 px-2 py-1"
                          value={editState.value.period_start}
                          onChange={(e) =>
                            setEditState((prev) =>
                              prev
                                ? {
                                    ...prev,
                                    value: { ...prev.value, period_start: e.target.value },
                                  }
                                : prev,
                            )
                          }
                          placeholder="YYYY-MM-DD"
                        />
                      </label>
                      <label className="text-sm">
                        <div className="mb-1 text-zinc-600">period_end</div>
                        <input
                          className="w-full rounded border border-zinc-300 px-2 py-1"
                          value={editState.value.period_end}
                          onChange={(e) =>
                            setEditState((prev) =>
                              prev
                                ? {
                                    ...prev,
                                    value: { ...prev.value, period_end: e.target.value },
                                  }
                                : prev,
                            )
                          }
                          placeholder="YYYY-MM-DD"
                        />
                      </label>
                      <label className="text-sm">
                        <div className="mb-1 text-zinc-600">normalized_unit</div>
                        <input
                          className="w-full rounded border border-zinc-300 px-2 py-1"
                          value={editState.value.normalized_unit}
                          onChange={(e) =>
                            setEditState((prev) =>
                              prev
                                ? {
                                    ...prev,
                                    value: {
                                      ...prev.value,
                                      normalized_unit: e.target.value,
                                    },
                                  }
                                : prev,
                            )
                          }
                        />
                      </label>
                    </div>

                    <label className="block text-sm">
                      <div className="mb-1 text-zinc-600">activity_metadata (JSON)</div>
                      <textarea
                        className="h-40 w-full rounded border border-zinc-300 px-2 py-1 font-mono text-xs"
                        value={editState.value.activity_metadata}
                        onChange={(e) =>
                          setEditState((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  value: { ...prev.value, activity_metadata: e.target.value },
                                }
                              : prev,
                          )
                        }
                      />
                    </label>

                    <label className="block text-sm">
                      <div className="mb-1 text-zinc-600">reason</div>
                      <input
                        className="w-full rounded border border-zinc-300 px-2 py-1"
                        value={editState.value.reason}
                        onChange={(e) =>
                          setEditState((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  value: { ...prev.value, reason: e.target.value },
                                }
                              : prev,
                          )
                        }
                        placeholder="optional"
                      />
                    </label>

                    <div className="flex items-center gap-2">
                      <button
                        className="rounded bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
                        type="button"
                        disabled={!canAct || editState.loading}
                        onClick={() => saveEdit(editingId)}
                      >
                        Save Edit
                      </button>
                      <div className="text-sm text-zinc-600">
                        {editState.loading ? 'Saving…' : ''}
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            ) : null}

            {!loading && (data?.results?.length ?? 0) === 0 ? (
              <tr>
                <td className="px-3 py-6 text-zinc-600" colSpan={11}>
                  No pending records.
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
