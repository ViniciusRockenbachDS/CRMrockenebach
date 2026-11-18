import { Plus, Search, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ClientFormModal } from '@/components/clients/ClientFormModal'
import { Avatar, Button, Card, EmptyState, Input, LoadingState, PageHeader, Pagination, Select, Table, Td, Th } from '@/components/ui'
import { ClientStatusBadge } from '@/components/ui/StatusBadges'
import { useClients, useUsers } from '@/hooks/queries'
import { CLIENT_STATUS, LEAD_SOURCES, toOptions } from '@/lib/constants'
import { formatPhone, formatRelative } from '@/lib/format'
import type { ClientFilters, ClientStatus, LeadSource } from '@/types/api'

const LIMIT = 15

/** Atrasa a atualização do valor para não disparar uma busca a cada tecla. */
function useDebounced<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(t)
  }, [value, delay])
  return debounced
}

export default function ClientsPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [source, setSource] = useState('')
  const [owner, setOwner] = useState('')
  const [noContact, setNoContact] = useState('')
  const [offset, setOffset] = useState(0)
  const [creating, setCreating] = useState(false)
  const debouncedSearch = useDebounced(search)
  const { data: users } = useUsers({ only_active: true })

  const filters: ClientFilters = {
    search: debouncedSearch,
    status: status ? [status as ClientStatus] : undefined,
    lead_source: source ? [source as LeadSource] : undefined,
    owner_id: owner || undefined,
    no_contact_days: noContact ? Number(noContact) : undefined,
    order_by: 'created_at',
    order_dir: 'desc',
    limit: LIMIT,
    offset,
  }
  const { data, isLoading } = useClients(filters)

  useEffect(() => setOffset(0), [debouncedSearch, status, source, owner, noContact])

  return (
    <>
      <PageHeader
        title="Clientes"
        description="Leads, prospects e clientes ativos"
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => setCreating(true)}>
            Novo cliente
          </Button>
        }
      />

      <Card>
        <div className="grid gap-3 border-b border-slate-100 p-4 md:grid-cols-5">
          <div className="relative md:col-span-2">
            <Search className="absolute top-2.5 left-3 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Buscar por nome, empresa, e-mail ou telefone"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={status} onChange={(e) => setStatus(e.target.value)} placeholder="Todos os status" options={toOptions(CLIENT_STATUS)} />
          <Select value={source} onChange={(e) => setSource(e.target.value)} placeholder="Todas as origens" options={toOptions(LEAD_SOURCES)} />
          <div className="grid grid-cols-2 gap-2">
            <Select
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              placeholder="Responsável"
              options={(users?.items ?? []).map((u) => ({ value: u.id, label: u.name.split(' ')[0] }))}
            />
            <Select
              value={noContact}
              onChange={(e) => setNoContact(e.target.value)}
              placeholder="Contato"
              options={[
                { value: '15', label: '+15 dias sem contato' },
                { value: '30', label: '+30 dias sem contato' },
                { value: '60', label: '+60 dias sem contato' },
              ]}
            />
          </div>
        </div>

        {isLoading && <LoadingState />}
        {data && data.items.length === 0 && (
          <EmptyState
            icon={<Users className="h-6 w-6" />}
            title="Nenhum cliente encontrado"
            description="Ajuste os filtros ou cadastre um novo cliente."
            action={<Button onClick={() => setCreating(true)}>Cadastrar cliente</Button>}
          />
        )}
        {data && data.items.length > 0 && (
          <>
            <Table>
              <thead className="bg-slate-50/60">
                <tr>
                  <Th>Cliente</Th>
                  <Th>Contato</Th>
                  <Th>Status</Th>
                  <Th>Origem</Th>
                  <Th>Responsável</Th>
                  <Th>Último contato</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((c) => (
                  <tr key={c.id} onClick={() => navigate(`/clientes/${c.id}`)} className="cursor-pointer hover:bg-slate-50">
                    <Td>
                      <div className="flex items-center gap-3">
                        <Avatar name={c.name} />
                        <div>
                          <p className="font-medium text-slate-900">{c.name}</p>
                          <p className="text-xs text-slate-500">{c.company ?? '—'}</p>
                        </div>
                      </div>
                    </Td>
                    <Td>
                      <p>{c.email ?? '—'}</p>
                      <p className="text-xs text-slate-500">{formatPhone(c.phone ?? c.whatsapp)}</p>
                    </Td>
                    <Td>
                      <ClientStatusBadge status={c.status} />
                    </Td>
                    <Td>{LEAD_SOURCES[c.lead_source]}</Td>
                    <Td>{c.owner?.name ?? '—'}</Td>
                    <Td className="text-slate-500">{formatRelative(c.last_interaction_at)}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
            <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
          </>
        )}
      </Card>

      <ClientFormModal open={creating} onClose={() => setCreating(false)} onSaved={(c) => navigate(`/clientes/${c.id}`)} />
    </>
  )
}
