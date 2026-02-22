import { Outlet, NavLink } from 'react-router-dom'
import { LayoutDashboard, Wallet, ArrowLeftRight, Code2, BookOpen, TreePine, AlertTriangle, Calculator, FileSpreadsheet, Building2, Upload, BarChart3, TrendingUp } from 'lucide-react'
import { clsx } from 'clsx'
import EntitySelector from './EntitySelector'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/analytics', icon: BarChart3, label: 'Analytics', end: true },
  { to: '/entities', icon: Building2, label: 'Entities', end: false },
  { to: '/imports', icon: Upload, label: 'Imports', end: false },
  { to: '/wallets', icon: Wallet, label: 'Wallets', end: false },
  { to: '/transactions', icon: ArrowLeftRight, label: 'Transactions', end: false },
  { to: '/parser', icon: Code2, label: 'Parser Debug', end: false },
  { to: '/journal', icon: BookOpen, label: 'Journal', end: false },
  { to: '/accounts', icon: TreePine, label: 'Accounts', end: false },
  { to: '/errors', icon: AlertTriangle, label: 'Errors', end: false },
  { to: '/tax', icon: Calculator, label: 'Tax', end: true },
  { to: '/tax/analytics', icon: TrendingUp, label: 'Tax Analytics', end: false },
  { to: '/reports', icon: FileSpreadsheet, label: 'Reports', end: false },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-lg font-bold text-gray-900">LeafJots</h1>
          <p className="text-xs text-gray-500">DeFi Accounting</p>
        </div>
        <div className="border-b border-gray-200">
          <EntitySelector />
        </div>
        <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-gray-700 hover:bg-gray-100'
                )
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-gray-200 text-xs text-gray-400">
          LeafJots v0.1.0
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
