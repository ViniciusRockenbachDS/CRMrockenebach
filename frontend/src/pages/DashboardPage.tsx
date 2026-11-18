import { AlertTriangle, DollarSign, Percent, Target, TrendingUp, Wallet } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { FunnelChart, KpiCard, LeadSourcesTable, RevenueChart } from '@/components/dashboard/DashboardWidgets'
import { InsightsPanel } from '@/components/dashboard/InsightsPanel'
import { Card, CardHeader, Field, Input, LoadingState, PageHeader, Select } from '@/components/ui'
import { useDashboard, useUsers } from '@/hooks/queries'
import { formatCurrency, formatDate, formatPercent, todayISO } from '@/lib/format'

function firstDayOfMonth(): string {
  return `${todayISO().slice(0, 8)}01`
}

export default function DashboardPage() {
  const [dateFrom, setDateFrom] = useState(firstDayOfMonth())
  const [dateTo, setDateTo] = useState(todayISO())
  const [ownerId, setOwnerId] = useState('')
  const { data: users } = useUsers({ only_active: true })
  const { data, isLoading, isError } = useDashboard({ date_from: dateFrom, date_to: dateTo, owner_id: ownerId || undefined })

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Visão consolidada de vendas, receita e inadimplência"
        actions={
          <div className="flex flex-wrap items-end gap-2">
            <Field label="De" className="w-36">
              <Input type="date" value={dateFrom} max={dateTo} onChange={(e) => setDateFrom(e.target.value)} />
            </Field>
            <Field label="Até" className="w-36">
              <Input type="date" value={dateTo} min={dateFrom} onChange={(e) => setDateTo(e.target.value)} />
            </Field>
            <Field label="Vendedor" className="w-44">
              <Select
                value={ownerId}
                onChange={(e) => setOwnerId(e.target.value)}
                placeholder="Todos"
                options={(users?.items ?? []).map((u) => ({ value: u.id, label: u.name }))}
              />
            </Field>
          </div>
        }
      />

      {isLoading && <LoadingState />}
      {isError && <p className="text-sm text-rose-600">Não foi possível carregar o dashboard.</p>}

      {data && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              label="Receita recebida"
              value={formatCurrency(data.summary.total_revenue)}
              icon={DollarSign}
              tone="emerald"
              change={data.comparison.total_revenue_pct}
              hint="vs. período anterior"
            />
            <KpiCard
              label="Ticket médio"
              value={formatCurrency(data.summary.average_ticket)}
              icon={Target}
              change={data.comparison.average_ticket_pct}
              hint={`${data.summary.won_deals_count} venda(s) ganha(s)`}
            />
            <KpiCard
              label="Taxa de conversão"
              value={formatPercent(data.summary.conversion_rate)}
              icon={Percent}
              tone="sky"
              hint={`${data.summary.won_deals_count} ganhas · ${data.summary.lost_deals_count} perdidas`}
            />
            <KpiCard
              label="Inadimplência"
              value={formatPercent(data.summary.delinquency_rate)}
              icon={AlertTriangle}
              tone="rose"
              hint={`${formatCurrency(data.summary.overdue_amount)} em atraso`}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <KpiCard
              label="Pipeline aberto"
              value={formatCurrency(data.summary.open_pipeline_value)}
              icon={TrendingUp}
              hint={`${data.summary.open_deals_count} negociações`}
            />
            <KpiCard
              label="Previsão ponderada"
              value={formatCurrency(data.summary.weighted_pipeline_value)}
              icon={Target}
              tone="sky"
              hint="valor × probabilidade"
            />
            <KpiCard
              label="A receber"
              value={formatCurrency(data.summary.receivables)}
              icon={Wallet}
              tone="amber"
              hint={`${data.summary.new_clients_count} novo(s) cliente(s) no período`}
            />
          </div>

          <InsightsPanel dateFrom={dateFrom} dateTo={dateTo} />

          <div className="grid gap-6 xl:grid-cols-3">
            <div className="xl:col-span-2">
              <RevenueChart data={data.revenue_series} />
            </div>
            <FunnelChart data={data.funnel} />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <LeadSourcesTable data={data.lead_sources} />
            <Card>
              <CardHeader title="Top clientes" subtitle="Maior valor recebido" />
              <div className="divide-y divide-slate-100">
                {data.top_clients.length === 0 && <p className="px-5 py-6 text-sm text-slate-500">Sem pagamentos ainda.</p>}
                {data.top_clients.map((t) => (
                  <Link
                    key={t.client.id}
                    to={`/clientes/${t.client.id}`}
                    className="flex items-center justify-between px-5 py-2.5 text-sm hover:bg-slate-50"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-slate-700">{t.client.name}</p>
                      <p className="truncate text-xs text-slate-500">{t.client.company ?? '—'}</p>
                    </div>
                    <span className="font-semibold text-emerald-700">{formatCurrency(t.total_paid)}</span>
                  </Link>
                ))}
              </div>
            </Card>
            <Card>
              <CardHeader title="Maiores atrasos" subtitle="Faturas vencidas mais antigas" />
              <div className="divide-y divide-slate-100">
                {data.top_overdue.length === 0 && <p className="px-5 py-6 text-sm text-slate-500">Nenhuma fatura em atraso. 🎉</p>}
                {data.top_overdue.map((o) => (
                  <Link
                    key={o.payment_id}
                    to={`/clientes/${o.client.id}`}
                    className="flex items-center justify-between px-5 py-2.5 text-sm hover:bg-slate-50"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-slate-700">{o.client.name}</p>
                      <p className="text-xs text-slate-500">
                        {o.invoice_number} · venceu {formatDate(o.due_date)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-rose-600">{formatCurrency(o.amount)}</p>
                      <p className="text-xs text-rose-500">{o.days_overdue} dias</p>
                    </div>
                  </Link>
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}
    </>
  )
}
