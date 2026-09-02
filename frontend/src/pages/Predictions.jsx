import { useEffect, useState } from 'react'
import api from '../api/client'
import { PageHeader, Panel, RiskBadge, ErrorState } from '../components/Panel'

function seasonOf(month) {
  if ([12, 1, 2].includes(month)) return 'winter'
  if ([3, 4, 5].includes(month)) return 'summer'
  if ([6, 7, 8, 9].includes(month)) return 'monsoon'
  return 'post_monsoon'
}

export default function Predictions() {
  const [districts, setDistricts] = useState([])
  const [district, setDistrict] = useState('')
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [result, setResult] = useState(null)
  const [explanation, setExplanation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.districts().then((d) => { setDistricts(d); if (d.length) setDistrict(d[0]) }).catch(() => {})
  }, [])

  const runPrediction = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    setExplanation(null)
    const d = new Date(date)
    const payload = {
      district,
      season: seasonOf(d.getMonth() + 1),
      year: d.getFullYear(),
      month: d.getMonth() + 1,
      day: d.getDate(),
      day_of_week: (d.getDay() + 6) % 7, // JS: Sun=0 -> convert to Mon=0
      is_weekend: [0, 6].includes(d.getDay()) ? 1 : 0,
    }
    try {
      const [pred, exp] = await Promise.all([api.predict(payload), api.explain(payload)])
      setResult(pred)
      setExplanation(exp)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="PREDICTIONS"
        title="Crime Type Prediction"
        description="Enter a district and date to see the model's most likely crime category, with SHAP-based explanation. Trained on time/location features only — accuracy is real and modest (see Model Insights)."
      />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 px-8 py-6">
        <Panel title="Input">
          <div className="space-y-4">
            <div>
              <label className="block text-[11.5px] text-ink-dim mb-1.5">District</label>
              <select
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="w-full bg-surface-raised border border-line text-[13px] px-3 py-2 text-ink"
              >
                {districts.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[11.5px] text-ink-dim mb-1.5">Date</label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full bg-surface-raised border border-line text-[13px] px-3 py-2 text-ink"
              />
            </div>
            <button
              onClick={runPrediction}
              disabled={!district || loading}
              className="w-full bg-signal text-void font-medium text-[13px] py-2.5 hover:bg-signal/90 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Running…' : 'Run prediction'}
            </button>
          </div>
        </Panel>

        <Panel title="Prediction" className="lg:col-span-2">
          {error && <ErrorState message={error} />}
          {!error && !result && <p className="text-[13px] text-ink-dim">Run a prediction to see results.</p>}
          {result && (
            <div>
              <div className="flex items-center gap-4 mb-4">
                <div>
                  <div className="text-[11px] text-ink-dim">Most likely category</div>
                  <div className="font-display text-[20px] text-ink font-medium">{result.predicted_crime_group}</div>
                </div>
                <div className="ml-auto text-right">
                  <div className="text-[11px] text-ink-dim">Probability</div>
                  <div className="font-mono text-[18px] text-signal">{(result.probability * 100).toFixed(1)}%</div>
                </div>
                {result.risk_tier && (
                  <div className="text-right">
                    <div className="text-[11px] text-ink-dim mb-1">District risk</div>
                    <RiskBadge tier={result.risk_tier} />
                  </div>
                )}
              </div>

              <div className="mb-4">
                <div className="text-[11.5px] text-ink-dim mb-2">Top predictions</div>
                <div className="space-y-1.5">
                  {result.top_predictions.map((p) => (
                    <div key={p.crime_group} className="flex items-center gap-2">
                      <span className="text-[12px] text-ink-muted w-40 truncate">{p.crime_group}</span>
                      <div className="flex-1 h-1.5 bg-surface-raised">
                        <div className="h-full bg-signal" style={{ width: `${p.probability * 100}%` }} />
                      </div>
                      <span className="font-mono text-[11px] text-ink-dim w-10 text-right">{(p.probability * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {explanation && (
                <div>
                  <div className="text-[11.5px] text-ink-dim mb-2">Features associated with this prediction (SHAP)</div>
                  <div className="space-y-1">
                    {explanation.top_features.map((f) => (
                      <div key={f.feature} className="flex items-center justify-between text-[12px] py-1 border-b border-line last:border-0">
                        <span className="text-ink-muted">{f.feature}</span>
                        <span className={f.direction === 'increases' ? 'text-signal font-mono' : 'text-ink-dim font-mono'}>
                          {f.direction === 'increases' ? '+' : '−'}{Math.abs(f.shap_value).toFixed(3)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <p className="text-[11px] text-ink-dim mt-4 pt-3 border-t border-line">{result.disclaimer}</p>
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}
