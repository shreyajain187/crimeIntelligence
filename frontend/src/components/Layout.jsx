import { NavLink, Outlet } from 'react-router-dom'
import { LayoutDashboard, Map, Flame, Target, TrendingUp, BrainCircuit, Table2, Cpu, Radar } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/overview', label: 'Overview', icon: LayoutDashboard },
  { to: '/map', label: 'Crime Map', icon: Map },
  { to: '/hotspots', label: 'Hotspots', icon: Flame },
  { to: '/predictions', label: 'Predictions', icon: Target },
  { to: '/forecast', label: 'Forecast', icon: TrendingUp },
  { to: '/insights', label: 'Model Insights', icon: BrainCircuit },
  { to: '/explorer', label: 'Data Explorer', icon: Table2 },
  { to: '/system', label: 'System', icon: Cpu },
]

export default function Layout() {
  return (
    <div className="flex h-screen w-full bg-void text-ink font-body">
      <aside className="w-56 shrink-0 border-r border-line flex flex-col">
        <div className="h-16 flex items-center gap-2 px-5 border-b border-line">
          <Radar size={20} className="text-signal" strokeWidth={2} />
          <span className="font-display font-semibold tracking-tight text-[15px]">OmniWatch</span>
        </div>
        <nav className="flex-1 py-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-[13.5px] border-l-2 transition-colors ${
                  isActive
                    ? 'border-signal bg-surface text-ink'
                    : 'border-transparent text-ink-muted hover:text-ink hover:bg-surface/50'
                }`
              }
            >
              <Icon size={16} strokeWidth={1.75} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-4 border-t border-line text-[11px] text-ink-dim font-mono leading-relaxed">
          Karnataka Police FIR
          <br />
          2016 – 2024
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
