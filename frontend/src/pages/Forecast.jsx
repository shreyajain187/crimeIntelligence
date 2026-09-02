import { useEffect, useState } from 'react'
import { AreaChart, Area, Line, ComposedChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import api from '../api/client'
import { PageHeader, Panel, StatCard, LoadingState, ErrorState } from '../components/Panel'

export default function Forecast() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.forecast().then(setData).catch((e) => setError(e.response?.data?.detail || e.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!data) return <LoadingState label="Loading forecast…" />

  const history = data.history.slice(-120).map((h) => ({ date: h.date.slice(5), actual: h.actual }))
  const forecast = data.forecast.map((f) => ({ date: f.date.slice(5), forecast: f.forecast, lower: f.lower, upper: f.upper }))
  const combined = [...history, ...forecast]

  return (
    <div>
      <PageHeader
        eyebrow="FORECAST"
        title="Crime Volume Forecast"
        description="Daily total incident volume across all of Karnataka, forecast with an XGBoost lag/seasonal model (Prophet was avoided to sidestep its native Stan-compilation dependency)."
      />
      <div className="px-8 py-6">
        <div className="grid grid-cols-3 gap-3 mb-5 max-w-lg">
          <StatCard label="Horizon" value={`${data.horizon_days}d`} />
          <StatCard label="Validation MAE" value={data.mae.toFixed(1)} />
          <StatCard label="Validation RMSE" value={data.rmse.toFixed(1)} />
        </div>

        <Panel title="Historical vs. forecast daily incident volume" subtitle="Last 120 observed days, plus forward horizon with uncertainty band">
          <ResponsiveContainer width="100%" height={380}>
            <ComposedChart data={combined} margin={{ left: -10 }}>
              <CartesianGrid stroke="#2c303a" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: '#9298a6', fontSize: 10 }} minTickGap={30} />
              <YAxis tick={{ fill: '#9298a6', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#1b1e24', border: '1px solid #2c303a', fontSize: 12 }} labelStyle={{ color: '#e9e7de' }} />
              <Area type="monotone" dataKey="upper" stroke="none" fill="#d6552e" fillOpacity={0.08} />
              <Area type="monotone" dataKey="lower" stroke="none" fill="#14161b" fillOpacity={1} />
              <Line type="monotone" dataKey="actual" stroke="#6e93b0" dot={false} strokeWidth={1.5} />
              <Line type="monotone" dataKey="forecast" stroke="#d6552e" dot={false} strokeWidth={2} strokeDasharray="4 3" />
            </ComposedChart>
          </ResponsiveContainer>
        </Panel>
      </div>
    </div>
  )
}
