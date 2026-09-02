import { useEffect, useState } from 'react'
import api from '../api/client'
import { PageHeader, Panel, ErrorState } from '../components/Panel'

const PAGE_SIZE = 30

export default function DataExplorer() {
  const [districts, setDistricts] = useState([])
  const [crimeGroups, setCrimeGroups] = useState([])
  const [district, setDistrict] = useState('')
  const [crimeGroup, setCrimeGroup] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.districts().then(setDistricts).catch(() => {})
    api.crimeGroups().then(setCrimeGroups).catch(() => {})
  }, [])

  useEffect(() => {
    const params = { page, page_size: PAGE_SIZE }
    if (district) params.district = district
    if (crimeGroup) params.crime_group = crimeGroup
    if (search) params.search = search
    api.crimes(params).then(setData).catch((e) => setError(e.message))
  }, [page, district, crimeGroup, search])

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <div>
      <PageHeader
        eyebrow="DATA EXPLORER"
        title="Real FIR Record Explorer"
        description="Search, filter, and page through the actual cleaned dataset — never a sample or mock."
      />
      <div className="px-8 py-4 flex flex-wrap gap-3 items-center border-b border-line">
        <input
          placeholder="Search crime type, location, station…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          className="bg-surface-raised border border-line text-[12.5px] px-3 py-1.5 text-ink w-64"
        />
        <select value={district} onChange={(e) => { setDistrict(e.target.value); setPage(1) }} className="bg-surface-raised border border-line text-[12.5px] px-3 py-1.5 text-ink">
          <option value="">All districts</option>
          {districts.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select value={crimeGroup} onChange={(e) => { setCrimeGroup(e.target.value); setPage(1) }} className="bg-surface-raised border border-line text-[12.5px] px-3 py-1.5 text-ink">
          <option value="">All crime groups</option>
          {crimeGroups.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        {data && <span className="text-[11.5px] font-mono text-ink-dim ml-auto">{data.total.toLocaleString()} matching records</span>}
      </div>

      <div className="px-8 py-6">
        {error && <ErrorState message={error} />}
        {data && (
          <Panel>
            <table className="w-full text-[12px]">
              <thead>
                <tr className="text-left text-ink-dim border-b border-line">
                  <th className="py-2 pr-3">Date</th>
                  <th className="py-2 pr-3">Crime type</th>
                  <th className="py-2 pr-3">Group</th>
                  <th className="py-2 pr-3">District</th>
                  <th className="py-2 pr-3">Station</th>
                  <th className="py-2 pr-3">Geo</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((c) => (
                  <tr key={c.crime_id} className="border-b border-line hover:bg-surface-raised/40">
                    <td className="py-1.5 pr-3 font-mono text-ink-dim">{c.timestamp.slice(0, 10)}</td>
                    <td className="py-1.5 pr-3 text-ink-muted truncate max-w-[180px]">{c.crime_type}</td>
                    <td className="py-1.5 pr-3 text-ink-muted">{c.crime_group}</td>
                    <td className="py-1.5 pr-3 text-ink-muted">{c.district}</td>
                    <td className="py-1.5 pr-3 text-ink-muted">{c.station}</td>
                    <td className="py-1.5 pr-3 font-mono text-ink-dim">{c.has_coordinates ? '✓' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="flex items-center justify-between mt-4 text-[12px] text-ink-muted">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1 border border-line disabled:opacity-30"
              >
                Previous
              </button>
              <span className="font-mono">Page {page} of {totalPages.toLocaleString()}</span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 border border-line disabled:opacity-30"
              >
                Next
              </button>
            </div>
          </Panel>
        )}
      </div>
    </div>
  )
}
