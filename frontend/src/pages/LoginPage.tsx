import { BarChart3, KanbanSquare, Lock, Mail, Sparkles } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { getErrorMessage } from '@/api/http'
import { Button, Field, Input } from '@/components/ui'
import { useAuth } from '@/contexts/AuthContext'

export default function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('admin@crm.local')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  if (user) return <Navigate to="/" replace />

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      const from = (location.state as { from?: string } | null)?.from ?? '/'
      navigate(from, { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Não foi possível entrar.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid min-h-full lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-slate-900 p-12 text-white lg:flex">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600">
            <BarChart3 className="h-5 w-5" />
          </div>
          <span className="text-lg font-semibold">CRM</span>
        </div>
        <div className="space-y-6">
          <h1 className="text-4xl leading-tight font-bold">
            Clientes, funil e recebimentos
            <br />
            <span className="text-indigo-400">em um só lugar.</span>
          </h1>
          <ul className="space-y-3 text-slate-300">
            <li className="flex items-center gap-3">
              <KanbanSquare className="h-5 w-5 text-indigo-400" /> Funil de vendas em Kanban com histórico de etapas
            </li>
            <li className="flex items-center gap-3">
              <BarChart3 className="h-5 w-5 text-indigo-400" /> Receita, conversão e inadimplência em tempo real
            </li>
            <li className="flex items-center gap-3">
              <Sparkles className="h-5 w-5 text-indigo-400" /> IA para resumos, lead scoring e insights
            </li>
          </ul>
        </div>
        <p className="text-sm text-slate-500">FastAPI · PostgreSQL · React · TypeScript</p>
      </div>

      <div className="flex items-center justify-center p-6">
        <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-5">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Entrar</h2>
            <p className="mt-1 text-sm text-slate-500">Use as credenciais definidas no .env do backend.</p>
          </div>
          {error && <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
          <Field label="E-mail">
            <div className="relative">
              <Mail className="absolute top-2.5 left-3 h-4 w-4 text-slate-400" />
              <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="pl-9" autoFocus />
            </div>
          </Field>
          <Field label="Senha">
            <div className="relative">
              <Lock className="absolute top-2.5 left-3 h-4 w-4 text-slate-400" />
              <Input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="pl-9" />
            </div>
          </Field>
          <Button type="submit" loading={loading} className="w-full">
            Entrar
          </Button>
          <p className="rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-500">
            Primeiro acesso com dados de demonstração: <strong>admin@crm.local</strong> / <strong>Admin@12345</strong>
          </p>
        </form>
      </div>
    </div>
  )
}
