import { ArrowDownRight, ArrowUpRight, type LucideIcon } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { Card, CardHeader } from '@/components/ui'
import { cn } from '@/lib/cn'
import { STAGE_MAP } from '@/lib/constants'
import { formatCompactCurrency, formatCurrency, formatMonth, formatPercent } from '@/lib/format'
import type { FunnelStageMetric, LeadSourceMetric, RevenuePoint } from '@/types/api'

export function KpiCard({
  label,
  value,
  icon: Icon,
  change,
  hint,
  tone = 'indigo',
  invertChange = false,
}: {
  label: string
  value: string
  icon: LucideIcon
  change?: number | null
  hint?: string
  tone?: 'indigo' | 'emerald' | 'amber' | 'rose' | 'sky'
  invertChange?: boolean
}) {
  const tones = {
    indigo: 'bg-indigo-50 text-indigo-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    rose: 'bg-rose-50 text-rose-600',
    sky: 'bg-sky-50 text-sky-600',
  }
  const positive = change !== null && change !== undefined && (invertChange ? change < 0 : change >= 0)
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <span className={cn('rounded-lg p-2', tones[tone])}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{value}</p>
      <div className="mt-1 flex items-center gap-2 text-xs">
        {change !== null && change !== undefined && (
          <span className={cn('inline-flex items-center font-medium', positive ? 'text-emerald-600' : 'text-rose-600')}>
            {change >= 0 ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
            {Math.abs(change).toLocaleString('pt-BR')}%
          </span>
        )}
        {hint && <span className="text-slate-500">{hint}</span>}
      </div>
    </Card>
  )
}

export function RevenueChart({ data }: { data: RevenuePoint[] }) {
  const rows = data.map((p) => ({ ...p, month: formatMonth(p.period) }))
  return (
    <Card>
      <CardHeader title="Receita mensal" subtitle="Recebido x previsto (vencimentos) x em atraso — últimos 6 meses" />
      <div className="h-72 px-2 py-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="month" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis tickFormatter={(v: number) => formatCompactCurrency(v)} tickLine={false} axisLine={false} fontSize={12} width={70} />
            <Tooltip formatter={(v) => formatCurrency(Number(v))} cursor={{ fill: "#f1f5f9" }} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="received" name="Recebido" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            <Bar dataKey="expected" name="Previsto" fill="#c7d2fe" radius={[4, 4, 0, 0]} />
            <Bar dataKey="overdue" name="Em atraso" fill="#f43f5e" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

export function FunnelChart({ data }: { data: FunnelStageMetric[] }) {
  const max = Math.max(1, ...data.map((s) => s.count))
  return (
    <Card>
      <CardHeader title="Funil de vendas" subtitle="Abertas: situação atual · Fechadas: no período" />
      <div className="space-y-3 px-5 py-4">
        {data.map((stage) => (
          <div key={stage.stage}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="font-medium text-slate-700">{stage.label}</span>
              <span className="text-slate-500">
                {stage.count} · {formatCompactCurrency(stage.total_value)}
              </span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
              <div
                className={cn('h-full rounded-full', STAGE_MAP[stage.stage].dot)}
                style={{ width: `${(stage.count / max) * 100}%` }}
              />
            </div>
            <div className="mt-1 flex gap-3 text-xs text-slate-400">
              {stage.conversion_from_previous !== null && (
                <span>{formatPercent(stage.conversion_from_previous, 0)} chegam aqui</span>
              )}
              {stage.avg_days_in_stage !== null && <span>~{stage.avg_days_in_stage} dias na etapa</span>}
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

export function LeadSourcesTable({ data }: { data: LeadSourceMetric[] }) {
  return (
    <Card>
      <CardHeader title="Origem dos leads" subtitle="Clientes e vendas ganhas por canal" />
      <div className="divide-y divide-slate-100">
        {data.length === 0 && <p className="px-5 py-6 text-sm text-slate-500">Sem dados.</p>}
        {data.slice(0, 6).map((s) => (
          <div key={s.lead_source} className="flex items-center justify-between px-5 py-2.5 text-sm">
            <div>
              <p className="font-medium text-slate-700">{s.label}</p>
              <p className="text-xs text-slate-500">
                {s.clients_count} cliente(s) · conversão {formatPercent(s.conversion_rate, 0)}
              </p>
            </div>
            <span className="font-semibold text-slate-800">{formatCompactCurrency(s.won_value)}</span>
          </div>
        ))}
      </div>
    </Card>
  )
}
