import { useState } from 'react'

import type { IngestionJob } from '../lib/api'
import {
  uploadSapCsv,
  uploadTravelPayload,
  uploadUtilityCsv,
} from '../lib/api'
import { useConfig } from '../lib/ConfigContext'

function JobSummary({ job }: { job: IngestionJob }) {
  return (
    <div className="rounded border border-zinc-200 bg-zinc-50 p-3 text-sm">
      <div className="flex flex-wrap gap-x-6 gap-y-1">
        <div>
          <span className="text-zinc-500">Job</span> #{job.id}
        </div>
        <div>
          <span className="text-zinc-500">Source</span> {job.source_type}
        </div>
        <div>
          <span className="text-zinc-500">Status</span> {job.status}
        </div>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2 md:grid-cols-5">
        <div>
          <div className="text-xs text-zinc-500">raw</div>
          <div className="font-medium">{job.raw_record_count}</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500">parsed</div>
          <div className="font-medium">{job.parsed_record_count}</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500">failed</div>
          <div className="font-medium">{job.failed_record_count}</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500">activities</div>
          <div className="font-medium">{job.activity_record_count}</div>
        </div>
        <div>
          <div className="text-xs text-zinc-500">anomalies</div>
          <div className="font-medium">{job.anomaly_record_count}</div>
        </div>
      </div>
    </div>
  )
}

export default function UploadCenter() {
  const { config } = useConfig()

  const [sapFile, setSapFile] = useState<File | null>(null)
  const [sapLabel, setSapLabel] = useState('')

  const [utilityFile, setUtilityFile] = useState<File | null>(null)
  const [utilityLabel, setUtilityLabel] = useState('')

  const [travelFile, setTravelFile] = useState<File | null>(null)
  const [travelLabel, setTravelLabel] = useState('')

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastJob, setLastJob] = useState<IngestionJob | null>(null)

  async function doSapUpload() {
    if (!sapFile) return
    setBusy(true)
    setError(null)
    try {
      const job = await uploadSapCsv(config, sapFile, sapLabel)
      setLastJob(job)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function doUtilityUpload() {
    if (!utilityFile) return
    setBusy(true)
    setError(null)
    try {
      const job = await uploadUtilityCsv(config, utilityFile, utilityLabel)
      setLastJob(job)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function doTravelUpload() {
    if (!travelFile) return
    setBusy(true)
    setError(null)
    try {
      const raw = await travelFile.text()
      const payload = JSON.parse(raw) as Record<string, unknown>
      const job = await uploadTravelPayload(config, payload, travelLabel)
      setLastJob(job)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Upload Center</h2>
        <p className="mt-1 text-sm text-zinc-600">
          Upload messy source exports. The system stores raw rows and produces
          normalized ActivityRecords.
        </p>
      </div>

      {error ? (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      {lastJob ? <JobSummary job={lastJob} /> : null}

      <section className="space-y-3 rounded border border-zinc-200 p-4">
        <div>
          <h3 className="font-semibold">SAP CSV</h3>
          <p className="text-sm text-zinc-600">
            Supports fuel vs procurement, mixed units, and messy locale numbers.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="text-sm">
            <div className="mb-1 text-zinc-600">File</div>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setSapFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <label className="text-sm">
            <div className="mb-1 text-zinc-600">Source label (optional)</div>
            <input
              className="w-full rounded border border-zinc-300 px-2 py-1"
              value={sapLabel}
              onChange={(e) => setSapLabel(e.target.value)}
            />
          </label>
        </div>
        <button
          className="rounded bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          disabled={busy || !sapFile || !config.actor || !config.tenantSlug}
          onClick={doSapUpload}
          type="button"
        >
          Upload SAP
        </button>
      </section>

      <section className="space-y-3 rounded border border-zinc-200 p-4">
        <div>
          <h3 className="font-semibold">Utility CSV</h3>
          <p className="text-sm text-zinc-600">
            Supports billing periods and peak/off-peak breakdown.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="text-sm">
            <div className="mb-1 text-zinc-600">File</div>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setUtilityFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <label className="text-sm">
            <div className="mb-1 text-zinc-600">Source label (optional)</div>
            <input
              className="w-full rounded border border-zinc-300 px-2 py-1"
              value={utilityLabel}
              onChange={(e) => setUtilityLabel(e.target.value)}
            />
          </label>
        </div>
        <button
          className="rounded bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          disabled={busy || !utilityFile || !config.actor || !config.tenantSlug}
          onClick={doUtilityUpload}
          type="button"
        >
          Upload Utility
        </button>
      </section>

      <section className="space-y-3 rounded border border-zinc-200 p-4">
        <div>
          <h3 className="font-semibold">Travel JSON</h3>
          <p className="text-sm text-zinc-600">
            Supports flight/hotel/ground; estimates missing flight distance when
            possible.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="text-sm">
            <div className="mb-1 text-zinc-600">File</div>
            <input
              type="file"
              accept="application/json,.json"
              onChange={(e) => setTravelFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <label className="text-sm">
            <div className="mb-1 text-zinc-600">Source label (optional)</div>
            <input
              className="w-full rounded border border-zinc-300 px-2 py-1"
              value={travelLabel}
              onChange={(e) => setTravelLabel(e.target.value)}
            />
          </label>
        </div>
        <button
          className="rounded bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          disabled={busy || !travelFile || !config.actor || !config.tenantSlug}
          onClick={doTravelUpload}
          type="button"
        >
          Upload Travel
        </button>
      </section>
    </div>
  )
}
