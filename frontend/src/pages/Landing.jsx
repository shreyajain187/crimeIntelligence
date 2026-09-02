import { Link } from 'react-router-dom'
import { Flame, Target, TrendingUp, BrainCircuit } from 'lucide-react'

const CAPABILITIES = [
  {
    icon: Flame,
    title: 'Hotspot Detection',
    body: 'Density-based clustering over real geocoded incidents surfaces where crime concentrates, at the resolution the data actually supports.',
  },
  {
    icon: Target,
    title: 'Crime Prediction',
    body: 'A classifier trained on nine years of FIR records estimates the most likely crime category for a given district, season, and date.',
  },
  {
    icon: TrendingUp,
    title: 'Crime Forecasting',
    body: 'Historical daily incident volume projects forward with an uncertainty band, evaluated against a held-out validation period.',
  },
  {
    icon: BrainCircuit,
    title: 'Explainable AI',
    body: 'Every prediction ships with the features that moved the model toward it — never a black box, never a causal claim.',
  },
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-void text-ink font-body">
      {/* Backdrop: a quiet grid + scattered incident points, not a stock photo */}
      <div className="relative overflow-hidden border-b border-line">
        <BackgroundGrid />
        <div className="relative max-w-5xl mx-auto px-8 pt-28 pb-24">
          <div className="text-[11px] font-mono text-ink-dim mb-5">
            KARNATAKA POLICE FIR RECORDS · 2016–2024 · 1.5M INCIDENTS
          </div>
          <h1 className="font-display font-semibold text-ink leading-[1.05] text-[52px] tracking-tight max-w-3xl">
            OmniWatch
          </h1>
          <p className="font-display text-[22px] text-ink-muted mt-3 max-w-2xl">
            Crime intelligence and predictive safety, built from real police records.
          </p>
          <p className="text-[14.5px] text-ink-muted mt-6 max-w-xl leading-relaxed">
            Transform historical crime data into geographic intelligence, predictive
            insight, and explainable analytics — grounded entirely in nine years of
            real First Information Reports from Karnataka Police.
          </p>
          <Link
            to="/overview"
            className="inline-block mt-9 px-5 py-2.5 bg-signal text-void font-medium text-[13.5px] hover:bg-signal/90 transition-colors"
          >
            Explore Intelligence
          </Link>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-8 py-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-line border border-line">
          {CAPABILITIES.map(({ icon: Icon, title, body }) => (
            <div key={title} className="bg-void p-6">
              <Icon size={18} className="text-signal mb-3.5" strokeWidth={1.75} />
              <h3 className="font-display text-[15px] font-medium text-ink mb-2">{title}</h3>
              <p className="text-[13px] text-ink-muted leading-relaxed">{body}</p>
            </div>
          ))}
        </div>

        <div className="mt-14 border border-line bg-surface px-6 py-5">
          <p className="text-[12.5px] text-ink-muted leading-relaxed">
            OmniWatch provides statistical decision support. Predictions describe
            patterns in historical data and should not be interpreted as certainty.
            Roughly 30% of records include geographic coordinates; the remainder are
            represented at district/station level rather than plotted as points.
          </p>
        </div>
      </div>
    </div>
  )
}

function BackgroundGrid() {
  // Deterministic pseudo-random incident points scattered over a faint grid,
  // evoking a GIS console rather than a decorative illustration.
  const points = Array.from({ length: 60 }, (_, i) => {
    const seed = i * 137.5
    const x = (seed % 100)
    const y = ((seed * 1.618) % 100)
    return { x, y, id: i }
  })
  return (
    <svg
      className="absolute inset-0 w-full h-full opacity-[0.35]"
      preserveAspectRatio="none"
      viewBox="0 0 100 100"
    >
      <defs>
        <pattern id="grid" width="4" height="4" patternUnits="userSpaceOnUse">
          <path d="M 4 0 L 0 0 0 4" fill="none" stroke="#2c303a" strokeWidth="0.15" />
        </pattern>
      </defs>
      <rect width="100" height="100" fill="url(#grid)" />
      {points.map((p) => (
        <circle key={p.id} cx={p.x} cy={p.y} r="0.35" fill="#d6552e" opacity="0.5" />
      ))}
    </svg>
  )
}
