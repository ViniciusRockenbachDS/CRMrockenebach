import { ArrowLeft, Building2, Mail, MessageCircle, Pencil, Phone, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { AISummaryCard } from '@/components/clients/AISummaryCard'
import { ClientFormModal } from '@/components/clients/ClientFormModal'
import { InteractionForm, InteractionTimeline } from '@/components/clients/Interactions'
import { DealDetailsModal } from '@/components/deals/DealDetailsModal'
import { DealFormModal } from '@/components/deals/DealFormModal'
import { Badge, Button, Card, CardHeader, ConfirmDialog, LoadingState } from '@/components/ui'
import { ClientStatusBadge, PaymentStatusBadge, StageBadge } from '@/components/ui/StatusBadges'
import { useAuth } from '@/contexts/AuthContext'
import { useClient, useDeleteClient, useInteractions, usePayments } from '@/hooks/queries'
import { LEAD_SOURCES } from '@/lib/constants'
import { formatCurrency, formatDate, formatPhone, whatsappLink } from '@/lib/format'

export default function ClientDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { isManager } = useAuth()
  const { data: client, isLoading } = useClient(id)
  const { data: interactions } = useInteractions(id)
  const { data: payments } = usePayments({ client_id: id, limit: 50, order_by: 'due_date', order_dir: 'desc' })
  const remove = useDeleteClient()
  const [editing, setEditing] = useState(false)
  const [creatingDeal, setCreatingDeal] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [openDealId, setOpenDealId] = useState<string | null>(null)

  if (isLoading) return <LoadingState />
  if (!client) return <p className="text-sm text-slate-500">Cliente não encontrado.</p>

  const stats = client.stats
  return (
    <>
      <Link to="/clientes" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft className="h-4 w-4" /> Clientes
      </Link>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">{client.name}</h1>
            <ClientStatusBadge status={client.status} />
          </div>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-500">
            <Building2 className="h-4 w-4" />
            {client.company ?? 'Pessoa física'} {client.job_title && `· ${client.job_title}`}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {client.whatsapp && (
            <a href={whatsappLink(client.whatsapp)} target="_blank" rel="noreferrer">
              <Button variant="success" icon={<MessageCircle className="h-4 w-4" />}>
                WhatsApp
              </Button>
            </a>
          )}
          <Button variant="secondary" icon={<Pencil className="h-4 w-4" />} onClick={() => setEditing(true)}>
            Editar
          </Button>
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => setCreatingDeal(true)}>
            Nova negociação
          </Button>
          {isManager && (
            <Button variant="ghost" icon={<Trash2 className="h-4 w-4" />} onClick={() => setConfirmDelete(true)} />
          )}
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <AISummaryCard clientId={client.id} />
          <Card>
            <CardHeader title="Histórico de interações" subtitle={`${interactions?.total ?? 0} registro(s)`} />
            <div className="space-y-6 px-5 py-4">
              <InteractionForm clientId={client.id} deals={client.deals} />
              <InteractionTimeline clientId={client.id} items={interactions?.items ?? client.recent_interactions} />
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Dados de contato" />
            <dl className="space-y-3 px-5 py-4 text-sm">
              <div className="flex items-center gap-2 text-slate-700">
                <Mail className="h-4 w-4 text-slate-400" /> {client.email ?? '—'}
              </div>
              <div className="flex items-center gap-2 text-slate-700">
                <Phone className="h-4 w-4 text-slate-400" /> {formatPhone(client.phone)}
              </div>
              <div className="grid grid-cols-2 gap-3 border-t border-slate-100 pt-3">
                <div>
                  <dt className="text-xs text-slate-500">Origem</dt>
                  <dd className="font-medium">{LEAD_SOURCES[client.lead_source]}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Responsável</dt>
                  <dd className="font-medium">{client.owner?.name ?? '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">CPF/CNPJ</dt>
                  <dd className="font-medium">{client.document ?? '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Cliente desde</dt>
                  <dd className="font-medium">{formatDate(client.created_at)}</dd>
                </div>
              </div>
              {client.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 border-t border-slate-100 pt-3">
                  {client.tags.map((t) => (
                    <Badge key={t} className="bg-indigo-50 text-indigo-700">
                      #{t}
                    </Badge>
                  ))}
                </div>
              )}
              {client.notes && <p className="border-t border-slate-100 pt-3 whitespace-pre-line text-slate-600">{client.notes}</p>}
            </dl>
          </Card>

          <Card>
            <CardHeader title="Resumo financeiro" />
            <div className="grid grid-cols-2 gap-4 px-5 py-4 text-sm">
              <Stat label="Pipeline aberto" value={formatCurrency(stats.pipeline_value)} sub={`${stats.open_deals} negociação(ões)`} />
              <Stat label="Total ganho" value={formatCurrency(stats.total_won_value)} sub={`${stats.won_deals} ganha(s)`} />
              <Stat label="Recebido" value={formatCurrency(stats.total_paid)} />
              <Stat
                label="Em aberto"
                value={formatCurrency(stats.outstanding_amount)}
                sub={stats.overdue_amount ? `${formatCurrency(stats.overdue_amount)} em atraso` : undefined}
                danger={stats.overdue_amount > 0}
              />
            </div>
          </Card>

          <Card>
            <CardHeader title="Negociações" />
            <div className="divide-y divide-slate-100">
              {client.deals.length === 0 && <p className="px-5 py-4 text-sm text-slate-500">Nenhuma negociação.</p>}
              {client.deals.map((d) => (
                <button key={d.id} onClick={() => setOpenDealId(d.id)} className="flex w-full items-center justify-between gap-2 px-5 py-3 text-left hover:bg-slate-50">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-800">{d.title}</p>
                    <div className="mt-1">
                      <StageBadge stage={d.stage} />
                    </div>
                  </div>
                  <span className="text-sm font-semibold text-slate-700">{formatCurrency(d.estimated_value)}</span>
                </button>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader title="Faturas" />
            <div className="divide-y divide-slate-100">
              {(payments?.items.length ?? 0) === 0 && <p className="px-5 py-4 text-sm text-slate-500">Nenhuma fatura.</p>}
              {payments?.items.map((p) => (
                <div key={p.id} className="flex items-center justify-between px-5 py-3 text-sm">
                  <div>
                    <p className="font-medium text-slate-800">{p.invoice_number}</p>
                    <p className="text-xs text-slate-500">Vence {formatDate(p.due_date)}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">{formatCurrency(p.amount)}</p>
                    <PaymentStatusBadge status={p.status} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      <ClientFormModal open={editing} onClose={() => setEditing(false)} client={client} />
      <DealFormModal open={creatingDeal} onClose={() => setCreatingDeal(false)} defaultClient={client} />
      <DealDetailsModal dealId={openDealId} onClose={() => setOpenDealId(null)} />
      <ConfirmDialog
        open={confirmDelete}
        title="Excluir cliente"
        message="O cliente sai das listagens, mas o histórico é preservado. Clientes com negociações abertas não podem ser excluídos."
        confirmLabel="Excluir"
        danger
        loading={remove.isPending}
        onClose={() => setConfirmDelete(false)}
        onConfirm={() =>
          remove.mutate(client.id, {
            onSuccess: () => navigate('/clientes'),
            onSettled: () => setConfirmDelete(false),
          })
        }
      />
    </>
  )
}

function Stat({ label, value, sub, danger }: { label: string; value: string; sub?: string; danger?: boolean }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className={danger ? 'font-semibold text-rose-600' : 'font-semibold text-slate-900'}>{value}</p>
      {sub && <p className={danger ? 'text-xs text-rose-500' : 'text-xs text-slate-500'}>{sub}</p>}
    </div>
  )
}
