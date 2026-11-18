import { useEffect, useState, type FormEvent } from 'react'

import { Button, Field, Input, Modal, Select, Textarea } from '@/components/ui'
import { useAuth } from '@/contexts/AuthContext'
import { useCreateClient, useUpdateClient, useUsers } from '@/hooks/queries'
import { CLIENT_STATUS, LEAD_SOURCES, toOptions } from '@/lib/constants'
import { formatPhone } from '@/lib/format'
import type { Client, ClientPayload, ClientStatus, LeadSource } from '@/types/api'

interface FormState {
  name: string
  company: string
  job_title: string
  email: string
  phone: string
  whatsapp: string
  document: string
  lead_source: LeadSource
  status: ClientStatus
  owner_id: string
  tags: string
  notes: string
}

const EMPTY: FormState = {
  name: '',
  company: '',
  job_title: '',
  email: '',
  phone: '',
  whatsapp: '',
  document: '',
  lead_source: 'outro',
  status: 'lead',
  owner_id: '',
  tags: '',
  notes: '',
}

function fromClient(client: Client): FormState {
  return {
    name: client.name,
    company: client.company ?? '',
    job_title: client.job_title ?? '',
    email: client.email ?? '',
    phone: client.phone ? formatPhone(client.phone) : '',
    whatsapp: client.whatsapp ? formatPhone(client.whatsapp) : '',
    document: client.document ?? '',
    lead_source: client.lead_source,
    status: client.status,
    owner_id: client.owner?.id ?? '',
    tags: client.tags.join(', '),
    notes: client.notes ?? '',
  }
}

const orNull = (v: string) => (v.trim() ? v.trim() : null)

export function ClientFormModal({
  open,
  onClose,
  client,
  onSaved,
}: {
  open: boolean
  onClose: () => void
  client?: Client | null
  onSaved?: (client: Client) => void
}) {
  const { user } = useAuth()
  const { data: users } = useUsers({ only_active: true })
  const create = useCreateClient()
  const update = useUpdateClient()
  const [form, setForm] = useState<FormState>(EMPTY)

  useEffect(() => {
    if (open) setForm(client ? fromClient(client) : { ...EMPTY, owner_id: user?.id ?? '' })
  }, [open, client, user])

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((f) => ({ ...f, [key]: value }))

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const payload: ClientPayload = {
      name: form.name.trim(),
      company: orNull(form.company),
      job_title: orNull(form.job_title),
      email: orNull(form.email),
      phone: orNull(form.phone),
      whatsapp: orNull(form.whatsapp),
      document: orNull(form.document),
      lead_source: form.lead_source,
      status: form.status,
      owner_id: form.owner_id || null,
      tags: form.tags.split(',').map((t) => t.trim()).filter(Boolean),
      notes: orNull(form.notes),
    }
    const saved = client
      ? await update.mutateAsync({ id: client.id, data: payload })
      : await create.mutateAsync(payload)
    onSaved?.(saved)
    onClose()
  }

  const saving = create.isPending || update.isPending

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={client ? 'Editar cliente' : 'Novo cliente'}
      description="Informe ao menos um meio de contato (e-mail, telefone ou WhatsApp)."
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" form="client-form" loading={saving}>
            Salvar
          </Button>
        </>
      }
    >
      <form id="client-form" onSubmit={(e) => handleSubmit(e).catch(() => undefined)} className="grid gap-4 sm:grid-cols-2">
        <Field label="Nome" required>
          <Input value={form.name} onChange={(e) => set('name', e.target.value)} required minLength={2} />
        </Field>
        <Field label="Empresa">
          <Input value={form.company} onChange={(e) => set('company', e.target.value)} />
        </Field>
        <Field label="Cargo">
          <Input value={form.job_title} onChange={(e) => set('job_title', e.target.value)} />
        </Field>
        <Field label="E-mail">
          <Input type="email" value={form.email} onChange={(e) => set('email', e.target.value)} />
        </Field>
        <Field label="Telefone" hint="Ex.: (47) 99999-8888">
          <Input value={form.phone} onChange={(e) => set('phone', e.target.value)} />
        </Field>
        <Field label="WhatsApp">
          <div className="flex gap-2">
            <Input value={form.whatsapp} onChange={(e) => set('whatsapp', e.target.value)} />
            <Button variant="secondary" size="sm" onClick={() => set('whatsapp', form.phone)} title="Usar o telefone">
              = Tel.
            </Button>
          </div>
        </Field>
        <Field label="CPF / CNPJ">
          <Input value={form.document} onChange={(e) => set('document', e.target.value)} />
        </Field>
        <Field label="Responsável">
          <Select
            value={form.owner_id}
            onChange={(e) => set('owner_id', e.target.value)}
            placeholder="Sem responsável"
            options={(users?.items ?? []).map((u) => ({ value: u.id, label: u.name }))}
          />
        </Field>
        <Field label="Origem do lead">
          <Select value={form.lead_source} onChange={(e) => set('lead_source', e.target.value as LeadSource)} options={toOptions(LEAD_SOURCES)} />
        </Field>
        <Field label="Status">
          <Select value={form.status} onChange={(e) => set('status', e.target.value as ClientStatus)} options={toOptions(CLIENT_STATUS)} />
        </Field>
        <Field label="Tags" hint="Separe por vírgula: vip, indústria" className="sm:col-span-2">
          <Input value={form.tags} onChange={(e) => set('tags', e.target.value)} />
        </Field>
        <Field label="Observações" className="sm:col-span-2">
          <Textarea value={form.notes} onChange={(e) => set('notes', e.target.value)} rows={3} />
        </Field>
      </form>
    </Modal>
  )
}
