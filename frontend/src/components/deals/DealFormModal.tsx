import { Search, X } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'

import { Button, Field, Input, Modal, Select, Textarea } from '@/components/ui'
import { useAuth } from '@/contexts/AuthContext'
import { useClients, useCreateDeal, useUpdateDeal, useUsers } from '@/hooks/queries'
import { DEAL_STAGES, DEFAULT_PROBABILITY } from '@/lib/constants'
import type { ClientSummary, Deal, DealStage } from '@/types/api'

/** Campo de busca de cliente com lista de sugestões. */
function ClientPicker({ value, onChange }: { value: ClientSummary | null; onChange: (c: ClientSummary | null) => void }) {
  const [search, setSearch] = useState('')
  const { data, isFetching } = useClients({ search, limit: 8, order_by: 'name', order_dir: 'asc' })

  if (value) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm">
        <span>
          <strong>{value.name}</strong> {value.company && <span className="text-slate-500">· {value.company}</span>}
        </span>
        <button type="button" onClick={() => onChange(null)} className="text-slate-400 hover:text-slate-700" aria-label="Trocar cliente">
          <X className="h-4 w-4" />
        </button>
      </div>
    )
  }
  return (
    <div className="relative">
      <Search className="absolute top-2.5 left-3 h-4 w-4 text-slate-400" />
      <Input placeholder="Digite para buscar o cliente..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
      <div className="mt-1 max-h-48 overflow-y-auto rounded-lg border border-slate-200 bg-white">
        {isFetching && <p className="px-3 py-2 text-xs text-slate-400">Buscando...</p>}
        {data?.items.map((c) => (
          <button
            type="button"
            key={c.id}
            onClick={() => onChange(c)}
            className="block w-full px-3 py-2 text-left text-sm hover:bg-indigo-50"
          >
            {c.name} <span className="text-slate-500">{c.company && `· ${c.company}`}</span>
          </button>
        ))}
        {data && data.items.length === 0 && <p className="px-3 py-2 text-xs text-slate-400">Nenhum cliente encontrado.</p>}
      </div>
    </div>
  )
}

interface FormState {
  title: string
  estimated_value: string
  stage: DealStage
  probability: string
  expected_close_date: string
  owner_id: string
  description: string
  lost_reason: string
}

export function DealFormModal({
  open,
  onClose,
  deal,
  defaultClient,
  defaultStage = 'prospeccao',
}: {
  open: boolean
  onClose: () => void
  deal?: Deal | null
  defaultClient?: ClientSummary | null
  defaultStage?: DealStage
}) {
  const { user } = useAuth()
  const { data: users } = useUsers({ only_active: true })
  const create = useCreateDeal()
  const update = useUpdateDeal()
  const [client, setClient] = useState<ClientSummary | null>(null)
  const [form, setForm] = useState<FormState>({
    title: '',
    estimated_value: '',
    stage: defaultStage,
    probability: '',
    expected_close_date: '',
    owner_id: '',
    description: '',
    lost_reason: '',
  })

  useEffect(() => {
    if (!open) return
    setClient(deal?.client ?? defaultClient ?? null)
    setForm({
      title: deal?.title ?? '',
      estimated_value: deal ? String(deal.estimated_value) : '',
      stage: deal?.stage ?? defaultStage,
      probability: deal ? String(deal.probability) : String(DEFAULT_PROBABILITY[defaultStage]),
      expected_close_date: deal?.expected_close_date ?? '',
      owner_id: deal?.owner?.id ?? user?.id ?? '',
      description: deal?.description ?? '',
      lost_reason: '',
    })
  }, [open, deal, defaultClient, defaultStage, user])

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((f) => ({ ...f, [key]: value }))
  const isClosed = deal ? deal.stage === 'fechado_ganho' || deal.stage === 'fechado_perdido' : false

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!client) return
    const common = {
      title: form.title.trim(),
      estimated_value: Number(form.estimated_value.replace(',', '.')) || 0,
      expected_close_date: form.expected_close_date || null,
      owner_id: form.owner_id || null,
      description: form.description.trim() || null,
    }
    if (deal) {
      await update.mutateAsync({
        id: deal.id,
        data: { ...common, client_id: client.id, ...(isClosed ? {} : { probability: Number(form.probability) }) },
      })
    } else {
      await create.mutateAsync({
        ...common,
        client_id: client.id,
        stage: form.stage,
        probability: Number(form.probability),
        lost_reason: form.stage === 'fechado_perdido' ? form.lost_reason : null,
      })
    }
    onClose()
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={deal ? 'Editar negociação' : 'Nova negociação'}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" form="deal-form" loading={create.isPending || update.isPending} disabled={!client}>
            Salvar
          </Button>
        </>
      }
    >
      <form id="deal-form" onSubmit={(e) => handleSubmit(e).catch(() => undefined)} className="grid gap-4 sm:grid-cols-2">
        <Field label="Cliente" required className="sm:col-span-2">
          <ClientPicker value={client} onChange={setClient} />
        </Field>
        <Field label="Título" required className="sm:col-span-2">
          <Input value={form.title} onChange={(e) => set('title', e.target.value)} required minLength={3} placeholder="Ex.: Implantação do sistema" />
        </Field>
        <Field label="Valor estimado (R$)" required>
          <Input type="number" min="0" step="0.01" value={form.estimated_value} onChange={(e) => set('estimated_value', e.target.value)} required />
        </Field>
        <Field label="Data prevista de fechamento">
          <Input type="date" value={form.expected_close_date} onChange={(e) => set('expected_close_date', e.target.value)} />
        </Field>
        {!deal && (
          <Field label="Etapa inicial">
            <Select
              value={form.stage}
              onChange={(e) => {
                const stage = e.target.value as DealStage
                setForm((f) => ({ ...f, stage, probability: String(DEFAULT_PROBABILITY[stage]) }))
              }}
              options={DEAL_STAGES.map((s) => ({ value: s.value, label: s.label }))}
            />
          </Field>
        )}
        <Field label="Probabilidade (%)" hint={isClosed ? 'Negociação fechada' : 'Sugestão automática pela etapa'}>
          <Input
            type="number"
            min="0"
            max="100"
            value={form.probability}
            onChange={(e) => set('probability', e.target.value)}
            disabled={isClosed || form.stage === 'fechado_ganho' || form.stage === 'fechado_perdido'}
          />
        </Field>
        <Field label="Responsável">
          <Select
            value={form.owner_id}
            onChange={(e) => set('owner_id', e.target.value)}
            placeholder="Sem responsável"
            options={(users?.items ?? []).map((u) => ({ value: u.id, label: u.name }))}
          />
        </Field>
        {!deal && form.stage === 'fechado_perdido' && (
          <Field label="Motivo da perda" required className="sm:col-span-2">
            <Input value={form.lost_reason} onChange={(e) => set('lost_reason', e.target.value)} required />
          </Field>
        )}
        <Field label="Descrição" className="sm:col-span-2">
          <Textarea value={form.description} onChange={(e) => set('description', e.target.value)} rows={3} />
        </Field>
      </form>
    </Modal>
  )
}
