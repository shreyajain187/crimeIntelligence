export function Panel({ title, subtitle, action, children, className = '' }) {
  return (
    <div className={`border border-line bg-surface ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-line">
          <div>
            {title && <h3 className="text-[13px] font-medium text-ink">{title}</h3>}
            {subtitle && <p className="text-[11px] text-ink-dim mt-0.5">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  )
}

export function PageHeader({ eyebrow, title, description }) {
  return (
    <div className="px-8 pt-8 pb-6 border-b border-line">
      {eyebrow && <div className="text-[11px] font-mono text-ink-dim mb-1">{eyebrow}</div>}
      <h1 className="font-display text-[22px] font-semibold text-ink">{title}</h1>
      {description && <p className="text-[13px] text-ink-muted mt-1.5 max-w-2xl">{description}</p>}
    </div>
  )
}

export function StatCard({ label, value, sub, tone = 'default' }) {
  const toneClass = {
    default: 'text-ink',
    signal: 'text-signal',
  }[tone]
  return (
    <div className="border border-line bg-surface px-4 py-3.5">
      <div className="text-[11px] text-ink-dim mb-1.5">{label}</div>
      <div className={`font-mono text-[22px] font-medium ${toneClass}`}>{value}</div>
      {sub && <div className="text-[11px] text-ink-muted mt-1">{sub}</div>}
    </div>
  )
}

export function RiskBadge({ tier }) {
  const colors = {
    Low: 'bg-risk-low/15 text-risk-low border-risk-low/30',
    Moderate: 'bg-risk-moderate/15 text-risk-moderate border-risk-moderate/30',
    High: 'bg-risk-high/15 text-risk-high border-risk-high/30',
    'Very High': 'bg-risk-veryhigh/15 text-risk-veryhigh border-risk-veryhigh/30',
  }
  return (
    <span className={`inline-block px-2 py-0.5 text-[11px] font-medium border ${colors[tier] || colors.Moderate}`}>
      {tier}
    </span>
  )
}

export function LoadingState({ label = 'Loading…' }) {
  return <div className="px-8 py-16 text-center text-ink-dim text-[13px] font-mono">{label}</div>
}

export function ErrorState({ message }) {
  return (
    <div className="px-8 py-16 text-center text-risk-veryhigh text-[13px] font-mono max-w-lg mx-auto">
      {message || 'Something went wrong loading this data.'}
    </div>
  )
}
