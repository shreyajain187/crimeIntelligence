import { useEffect, useState } from 'react'
import api from '../api/client'
import { PageHeader, Panel, StatCard, LoadingState, ErrorState } from '../components/Panel'

export default function SystemPage() {
  const [meta, setMeta] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.metadata().then(setMeta).catch((e) => setError(e.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!meta) return <LoadingState label="Loading system status…" />

  const backend = meta.compute_backend
  const summary = meta.cleaning_summary

  return (
    <div>
      <PageHeader
        eyebrow="SYSTEM"
        title="Compute Backend & Dataset Provenance"
        description="What OmniWatch is actually running on, and exactly what was done to the raw data before any model saw it."
      />
      <div className="px-8 py-6 space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Active backend" value={backend.active_backend.toUpperCase()} tone={backend.active_backend === 'gpu' ? 'signal' : 'default'} />
          <StatCard label="CUDA available" value={backend.cuda_available ? 'Yes' : 'No'} />
          <StatCard label="RAPIDS available" value={backend.rapids_available ? 'Yes' : 'No'} />
          <StatCard label="GPU" value={backend.gpu_name || 'None detected'} />
        </div>

        <Panel title="Dataset" subtitle={meta.dataset_name}>
          <p className="text-[12.5px] text-ink-muted mb-3">{meta.dataset_description}</p>
          <a href={meta.dataset_source} target="_blank" rel="noreferrer" className="text-[12.5px] text-signal underline">
            {meta.dataset_source}
          </a>
        </Panel>

        {summary && (
          <Panel title="Cleaning summary" subtitle="Exactly what was removed from the raw data, and why">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Original rows" value={summary.original_rows.toLocaleString()} />
              <StatCard label="Duplicates removed" value={summary.duplicate_rows_removed.toLocaleString()} />
              <StatCard label="Invalid coords flagged" value={summary.invalid_coordinate_rows_flagged.toLocaleString()} />
              <StatCard label="Remaining rows" value={summary.remaining_rows.toLocaleString()} />
              <StatCard label="Crime categories" value={summary.crime_categories} />
              <StatCard label="Districts" value={summary.districts} />
              <StatCard label="Stations" value={summary.stations} />
              <StatCard label="With coordinates" value={summary.rows_with_coordinates.toLocaleString()} />
            </div>
          </Panel>
        )}

        <Panel title="Model availability">
          <div className="flex gap-6 text-[13px]">
            <span className="text-ink-muted">Classifier: <span className={meta.classifier_available ? 'text-risk-low' : 'text-risk-veryhigh'}>{meta.classifier_available ? 'trained' : 'not available'}</span></span>
            <span className="text-ink-muted">Forecast: <span className={meta.forecast_available ? 'text-risk-low' : 'text-risk-veryhigh'}>{meta.forecast_available ? 'available' : 'not available'}</span></span>
          </div>
        </Panel>
      </div>
    </div>
  )
}
