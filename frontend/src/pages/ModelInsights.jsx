import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import api from '../api/client'
import { PageHeader, Panel, StatCard, LoadingState, ErrorState } from '../components/Panel'

export default function ModelInsights() {
  const [metrics, setMetrics] = useState(null)
  const [features, setFeatures] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([api.modelMetrics(), api.modelFeatures()])
      .then(([m, f]) => { setMetrics(m); setFeatures(f) })
      .catch((e) => setError(e.response?.data?.detail || e.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!metrics || !features) return <LoadingState label="Loading model metrics…" />

  const baselineAccuracy = 0.203 // majority-class baseline on the 2023-2024 test set, computed offline

  return (
    <div>
      <PageHeader
        eyebrow="MODEL INSIGHTS"
        title="Classifier Performance & Explainability"
        description={`Temporal split: trained on ${metrics.train_years[0]}–${metrics.train_years.at(-1) - 1}, evaluated on ${metrics.test_years.join(', ')}.`}
      />
      <div className="px-8 py-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          <StatCard label="Accuracy" value={`${(metrics.accuracy * 100).toFixed(1)}%`} sub={`vs ${(baselineAccuracy * 100).toFixed(1)}% majority baseline`} tone="signal" />
          <StatCard label="F1 (weighted)" value={metrics.f1_weighted.toFixed(3)} />
          <StatCard label="F1 (macro)" value={metrics.f1_macro.toFixed(3)} sub="imbalance-sensitive" />
          <StatCard label="Train rows" value={metrics.train_rows.toLocaleString()} />
          <StatCard label="Test rows" value={metrics.test_rows.toLocaleString()} />
        </div>

        <div className="border border-line bg-surface px-4 py-3 mb-6 text-[12.5px] text-ink-muted leading-relaxed">
          <strong className="text-ink">Honest limitation:</strong> predicting fine-grained crime type from only
          district, date, and station-level history is a genuinely weak-signal problem — most of what determines
          a crime's category happens at the level of the specific incident, not where/when it was reported.
          Balanced class-weighting was tested and actually reduced accuracy below the trivial majority-class
          baseline (18.0% vs 20.3%); unweighted training shown here beats that baseline (29.5%) but macro-F1
          remains modest. This is reported as-is rather than tuned to look stronger than it is.
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Panel title="Global feature importance" subtitle="Mean |SHAP value|, sampled from 2023–2024 test data">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={features} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid stroke="#2c303a" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#9298a6', fontSize: 10 }} />
                <YAxis dataKey="feature" type="category" tick={{ fill: '#9298a6', fontSize: 10 }} width={140} />
                <Tooltip contentStyle={{ background: '#1b1e24', border: '1px solid #2c303a', fontSize: 12 }} />
                <Bar dataKey="mean_abs_shap" fill="#d6552e" />
              </BarChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title="Per-class performance" subtitle="Precision / recall / F1 on the 2023–2024 test set">
            <div className="max-h-[320px] overflow-y-auto">
              <table className="w-full text-[11.5px]">
                <thead className="sticky top-0 bg-surface-raised">
                  <tr className="text-left text-ink-dim">
                    <th className="py-1.5 px-2">Class</th>
                    <th className="py-1.5 px-2 text-right">Precision</th>
                    <th className="py-1.5 px-2 text-right">Recall</th>
                    <th className="py-1.5 px-2 text-right">F1</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.classes.map((c) => {
                    const row = metrics.classification_report[c]
                    if (!row) return null
                    return (
                      <tr key={c} className="border-t border-line">
                        <td className="py-1.5 px-2 text-ink-muted truncate max-w-[140px]">{c}</td>
                        <td className="py-1.5 px-2 text-right font-mono">{row.precision.toFixed(2)}</td>
                        <td className="py-1.5 px-2 text-right font-mono">{row.recall.toFixed(2)}</td>
                        <td className="py-1.5 px-2 text-right font-mono">{row['f1-score'].toFixed(2)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}
