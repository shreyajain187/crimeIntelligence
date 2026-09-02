import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from 'recharts'
import api from '../api/client'
import { PageHeader, StatCard, Panel, RiskBadge, LoadingState, ErrorState } from '../components/Panel'

export default function Overview() {
  const [stats, setStats] = useState(null)
  const [riskScores, setRiskScores] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([api.stats(), api.riskScores()])
      .then(([s, r]) => { setStats(s); setRiskScores(r) })
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <ErrorState message={`Could not reach the OmniWatch API: ${error}`} />
  if (!stats || !riskScores) return <LoadingState label="Loading dataset overview…" />

  const chartData = stats.top_crime_groups.map((g) => ({
    name: g.crime_group.length > 18 ? g.crime_group.slice(0, 16) + '…' : g.crime_group,
    count: g.count,
  }))

  return (
    <div>
      <PageHeader
        eyebrow="OVERVIEW"
        title="Karnataka Crime Intelligence Overview"
        description="Real incident statistics drawn directly from 1.5 million cleaned FIR records, 2016–2024."
      />
      <div className="px-8 py-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Total incidents" value={stats.total_incidents.toLocaleString()} />
          <StatCard label="Crime categories" value={stats.crime_categories} />
          <StatCard label="Active hotspots" value={stats.active_hotspots.toLocaleString()} tone="signal" />
          <StatCard label="Districts covered" value={stats.districts_covered} />
          <StatCard label="With coordinates" value={`${((stats.records_with_coordinates / stats.total_incidents) * 100).toFixed(0)}%`} sub={`${stats.records_with_coordinates.toLocaleString()} records`} />
          <StatCard label="Highest-density district" value={stats.highest_density_district} />
          <StatCard label="Data range" value={stats.date_range[0].slice(0, 4)} sub={`through ${stats.date_range[1].slice(0, 10)}`} />
          <StatCard label="Top category" value={stats.top_crime_groups[0]?.crime_group.slice(0, 14)} sub={`${stats.top_crime_groups[0]?.count.toLocaleString()} incidents`} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mt-6">
          <Panel title="Incident volume by category" subtitle="Top reported crime groups, all-time" className="lg:col-span-3">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData} margin={{ left: -10 }}>
                <CartesianGrid stroke="#2c303a" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#9298a6', fontSize: 10 }} interval={0} angle={-25} textAnchor="end" height={60} />
                <YAxis tick={{ fill: '#9298a6', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ background: '#1b1e24', border: '1px solid #2c303a', fontSize: 12 }}
                  labelStyle={{ color: '#e9e7de' }}
                />
                <Bar dataKey="count" fill="#d6552e" />
              </BarChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title="District risk ranking" subtitle="Transparent 0–100 composite score" className="lg:col-span-2">
            <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
              {riskScores.slice(0, 10).map((r) => (
                <div key={r.district} className="flex items-center justify-between text-[12.5px] py-1.5 border-b border-line last:border-0">
                  <span className="text-ink-muted truncate max-w-[120px]">{r.district}</span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-ink-dim">{r.risk_score.toFixed(0)}</span>
                    <RiskBadge tier={r.risk_tier} />
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}
