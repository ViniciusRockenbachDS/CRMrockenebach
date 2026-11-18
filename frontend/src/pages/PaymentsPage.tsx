import { AlertTriangle, CheckCircle2, Clock, Plus, Receipt, XCircle } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { KpiCard } from '@/components/dashboard/DashboardWidgets'
import { PaymentFormModal } from '@/components/payments/PaymentFormModal'
import {
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  LoadingState,
  Modal,
  PageHeader,
  Pagination,
  Select,
  Table,
  Td,
  Textarea,
  Th,
} from '@/components/ui'
import { PaymentStatusBadge } from '@/components/ui/StatusBadges'
import { useAuth } from '@/contexts/AuthContext'
import { useCancelPayment, useMarkPaid, usePayments, usePaymentsSummary } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { PAYMENT_METHODS, toOptions } from '@/lib/constants'
import { formatCurrency, formatDate, todayISO } from '@/lib/format'
import type { Payment, PaymentMethod, PaymentStatus } from '@/types/api'

const LIMIT = 20
const TABS: { value: PaymentStatus | 'todos'; label: string }[] = [
  { value: 'todos', label: 'Todas' },
  { value: 'atrasado', label: 'Atrasadas' },
  { value: 'pendente', label: 'Pendentes' },
  { value: 'pago', label: 'Pagas' },
  { value: 'cancelado', label: 'Canceladas' },
]

export default function PaymentsPage() {
  const { isManager } = useAuth()
  const [tab, setTab] = useState<PaymentStatus | 'todos'>('todos')
  const [offset, setOffset] = useState(0)
  const [creating, setCreating] = useState(false)
  const [paying, setPaying] = useState<Payment | null>(null)
  const [canceling, setCanceling] = useState<Payment | null>(null)

  const { data: summary } = usePaymentsSummary()
  const { data, isLoading } = usePayments({
    status: tab === 'todos' ? undefined : [tab],
    limit: LIMIT,
    offset,
    order_by: 'due_date',
    order_dir: tab === 'pago' ? 'desc' : 'asc',
  })

  return (
    <>
      <PageHeader
        title="Pagamentos"
        description="Faturas, recebimentos e inadimplência"
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => setCreating(true)}>
            Lançar cobrança
          </Button>
        }
      />

      {summary && (
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <KpiCard label="A receber (no prazo)" value={formatCurrency(summary.total_pending)} icon={Clock} tone="amber" />
          <KpiCard
            label="Em atraso"
            value={formatCurrency(summary.total_overdue)}
            icon={AlertTriangle}
            tone="rose"
            hint={`${summary.count_overdue} fatura(s)`}
          />
          <KpiCard label="Recebido no mês" value={formatCurrency(summary.total_paid_period)} icon={CheckCircle2} tone="emerald" />
        </div>
      )}

      <Card>
        <div className="flex gap-1 overflow-x-auto border-b border-slate-100 px-4 pt-3">
          {TABS.map((t) => (
            <button
              key={t.value}
              onClick={() => {
                setTab(t.value)
                setOffset(0)
              }}
              className={cn(
                '-mb-px border-b-2 px-3 py-2 text-sm font-medium whitespace-nowrap',
                tab === t.value ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500 hover:text-slate-700',
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        {isLoading && <LoadingState />}
        {data && data.items.length === 0 && (
          <EmptyState icon={<Receipt className="h-6 w-6" />} title="Nenhuma fatura aqui" description="Lance cobranças a partir de negociações ganhas." />
        )}
        {data && data.items.length > 0 && (
          <>
            <Table>
              <thead className="bg-slate-50/60">
                <tr>
                  <Th>Fatura</Th>
                  <Th>Cliente / negociação</Th>
                  <Th>Vencimento</Th>
                  <Th>Valor</Th>
                  <Th>Método</Th>
                  <Th>Status</Th>
                  <Th className="text-right">Ações</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((p) => {
                  const open = p.status === 'pendente' || p.status === 'atrasado'
                  return (
                    <tr key={p.id} className="hover:bg-slate-50">
                      <Td>
                        <p className="font-medium text-slate-900">{p.invoice_number}</p>
                        <p className="text-xs text-slate-500">
                          Parcela {p.installment_number}/{p.installment_total}
                        </p>
                      </Td>
                      <Td>
                        {p.client ? (
                          <Link to={`/clientes/${p.client.id}`} className="font-medium text-indigo-600 hover:underline">
                            {p.client.name}
                          </Link>
                        ) : (
                          '—'
                        )}
                        <p className="max-w-60 truncate text-xs text-slate-500">{p.deal.title}</p>
                      </Td>
                      <Td>
                        <p>{formatDate(p.due_date)}</p>
                        {p.days_overdue > 0 && <p className="text-xs font-medium text-rose-600">{p.days_overdue} dias de atraso</p>}
                        {p.payment_date && <p className="text-xs text-emerald-600">pago em {formatDate(p.payment_date)}</p>}
                      </Td>
                      <Td className="font-semibold text-slate-900">{formatCurrency(p.amount)}</Td>
                      <Td>{PAYMENT_METHODS[p.method]}</Td>
                      <Td>
                        <PaymentStatusBadge status={p.status} />
                      </Td>
                      <Td className="text-right">
                        {open && (
                          <div className="flex justify-end gap-1">
                            <Button size="sm" variant="success" onClick={() => setPaying(p)}>
                              Receber
                            </Button>
                            {isManager && (
                              <Button size="sm" variant="ghost" onClick={() => setCanceling(p)} title="Cancelar fatura">
                                <XCircle className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        )}
                      </Td>
                    </tr>
                  )
                })}
              </tbody>
            </Table>
            <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
          </>
        )}
      </Card>

      <PaymentFormModal open={creating} onClose={() => setCreating(false)} />
      <MarkPaidModal payment={paying} onClose={() => setPaying(null)} />
      <CancelModal payment={canceling} onClose={() => setCanceling(null)} />
    </>
  )
}

function MarkPaidModal({ payment, onClose }: { payment: Payment | null; onClose: () => void }) {
  const markPaid = useMarkPaid()
  const [date, setDate] = useState(todayISO())
  const [method, setMethod] = useState<PaymentMethod | ''>('')

  return (
    <Modal
      open={Boolean(payment)}
      onClose={onClose}
      title="Registrar recebimento"
      description={payment ? `${payment.invoice_number} · ${formatCurrency(payment.amount)}` : undefined}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="success"
            loading={markPaid.isPending}
            onClick={() =>
              payment &&
              markPaid.mutate({ id: payment.id, payment_date: date, method: method || null }, { onSuccess: onClose })
            }
          >
            Confirmar recebimento
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Data do pagamento">
          <Input type="date" value={date} max={todayISO()} onChange={(e) => setDate(e.target.value)} />
        </Field>
        <Field label="Método utilizado" hint="Deixe em branco para manter o previsto">
          <Select value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)} placeholder="Manter previsto" options={toOptions(PAYMENT_METHODS)} />
        </Field>
      </div>
    </Modal>
  )
}

function CancelModal({ payment, onClose }: { payment: Payment | null; onClose: () => void }) {
  const cancel = useCancelPayment()
  const [reason, setReason] = useState('')
  return (
    <Modal
      open={Boolean(payment)}
      onClose={onClose}
      title="Cancelar fatura"
      description={payment?.invoice_number}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Voltar
          </Button>
          <Button
            variant="danger"
            disabled={reason.trim().length < 3}
            loading={cancel.isPending}
            onClick={() => payment && cancel.mutate({ id: payment.id, reason: reason.trim() }, { onSuccess: onClose })}
          >
            Cancelar fatura
          </Button>
        </>
      }
    >
      <Field label="Motivo">
        <Textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
      </Field>
    </Modal>
  )
}
