import {
  BarChart3,
  KanbanSquare,
  LogOut,
  Menu,
  Receipt,
  Shield,
  Sparkles,
  Users,
  UsersRound,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

import { Avatar } from '@/components/ui'
import { useAuth } from '@/contexts/AuthContext'
import { useAIStatus } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { USER_ROLES } from '@/lib/constants'

const NAV = [
  { to: '/', label: 'Dashboard', icon: BarChart3, end: true },
  { to: '/clientes', label: 'Clientes', icon: Users },
  { to: '/funil', label: 'Funil de vendas', icon: KanbanSquare },
  { to: '/pagamentos', label: 'Pagamentos', icon: Receipt },
]

export function AppLayout() {
  const { user, logout, isAdmin } = useAuth()
  const { data: ai } = useAIStatus()
  const [open, setOpen] = useState(false)

  const nav = isAdmin ? [...NAV, { to: '/usuarios', label: 'Usuários', icon: UsersRound }] : NAV

  const sidebar = (
    <div className="flex h-full flex-col bg-slate-900 text-slate-300">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white">
          <BarChart3 className="h-5 w-5" />
        </div>
        <div>
          <p className="font-semibold text-white">CRM</p>
          <p className="text-xs text-slate-400">Vendas & Relacionamento</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {nav.map(({ to, label, icon: Icon, ...rest }) => (
          <NavLink
            key={to}
            to={to}
            end={'end' in rest ? rest.end : false}
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive ? 'bg-indigo-600 text-white' : 'hover:bg-slate-800 hover:text-white',
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {ai && (
        <div className="mx-3 mb-3 rounded-lg bg-slate-800/70 px-3 py-2.5 text-xs">
          <p className="flex items-center gap-1.5 font-medium text-slate-200">
            <Sparkles className="h-3.5 w-3.5 text-indigo-400" /> IA {ai.enabled ? 'ativa' : 'desativada'}
          </p>
          <p className="mt-0.5 text-slate-400">
            {ai.provider} · {ai.model}
          </p>
        </div>
      )}

      {user && (
        <div className="flex items-center gap-3 border-t border-slate-800 px-4 py-4">
          <Avatar name={user.name} className="bg-slate-700 text-slate-100" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">{user.name}</p>
            <p className="flex items-center gap-1 text-xs text-slate-400">
              {user.role === 'admin' && <Shield className="h-3 w-3" />}
              {USER_ROLES[user.role]}
            </p>
          </div>
          <button onClick={logout} title="Sair" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white">
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  )

  return (
    <div className="flex h-full">
      <aside className="hidden w-64 shrink-0 lg:block">{sidebar}</aside>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setOpen(false)} />
          <div className="relative h-full w-64">{sidebar}</div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
          <button onClick={() => setOpen(true)} className="rounded-lg p-1.5 hover:bg-slate-100" aria-label="Menu">
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <span className="font-semibold">CRM</span>
          <span className="w-8" />
        </header>
        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
