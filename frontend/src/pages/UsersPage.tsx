import { Plus, UsersRound } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { Avatar, Badge, Button, Card, EmptyState, Field, Input, LoadingState, Modal, PageHeader, Select, Table, Td, Th } from '@/components/ui'
import { useAuth } from '@/contexts/AuthContext'
import { useCreateUser, useUpdateUser, useUsers } from '@/hooks/queries'
import { USER_ROLES, toOptions } from '@/lib/constants'
import { formatDateTime } from '@/lib/format'
import type { UserRole } from '@/types/api'

export default function UsersPage() {
  const { user: me } = useAuth()
  const { data, isLoading } = useUsers()
  const update = useUpdateUser()
  const [creating, setCreating] = useState(false)

  return (
    <>
      <PageHeader
        title="Usuários"
        description="Equipe com acesso ao CRM"
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={() => setCreating(true)}>
            Novo usuário
          </Button>
        }
      />
      <Card>
        {isLoading && <LoadingState />}
        {data && data.items.length === 0 && <EmptyState icon={<UsersRound className="h-6 w-6" />} title="Nenhum usuário" />}
        {data && data.items.length > 0 && (
          <Table>
            <thead className="bg-slate-50/60">
              <tr>
                <Th>Usuário</Th>
                <Th>Papel</Th>
                <Th>Último acesso</Th>
                <Th>Situação</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((u) => (
                <tr key={u.id}>
                  <Td>
                    <div className="flex items-center gap-3">
                      <Avatar name={u.name} />
                      <div>
                        <p className="font-medium text-slate-900">{u.name}</p>
                        <p className="text-xs text-slate-500">{u.email}</p>
                      </div>
                    </div>
                  </Td>
                  <Td>
                    <Select
                      className="w-40"
                      value={u.role}
                      disabled={u.id === me?.id}
                      onChange={(e) => update.mutate({ id: u.id, data: { role: e.target.value as UserRole } })}
                      options={toOptions(USER_ROLES)}
                    />
                  </Td>
                  <Td className="text-slate-500">{formatDateTime(u.last_login_at)}</Td>
                  <Td>
                    <div className="flex items-center gap-2">
                      <Badge className={u.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-zinc-200 text-zinc-600'}>
                        {u.is_active ? 'Ativo' : 'Inativo'}
                      </Badge>
                      {u.id !== me?.id && (
                        <Button size="sm" variant="ghost" onClick={() => update.mutate({ id: u.id, data: { is_active: !u.is_active } })}>
                          {u.is_active ? 'Desativar' : 'Reativar'}
                        </Button>
                      )}
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
      <UserFormModal open={creating} onClose={() => setCreating(false)} />
    </>
  )
}

function UserFormModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const create = useCreateUser()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>('vendedor')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    await create.mutateAsync({ name, email, password, role })
    setName('')
    setEmail('')
    setPassword('')
    onClose()
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Novo usuário"
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" form="user-form" loading={create.isPending}>
            Criar
          </Button>
        </>
      }
    >
      <form id="user-form" onSubmit={(e) => handleSubmit(e).catch(() => undefined)} className="space-y-4">
        <Field label="Nome" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
        </Field>
        <Field label="E-mail" required>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field label="Senha inicial" required hint="Mínimo 8 caracteres, com letras e números">
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
        </Field>
        <Field label="Papel">
          <Select value={role} onChange={(e) => setRole(e.target.value as UserRole)} options={toOptions(USER_ROLES)} />
        </Field>
      </form>
    </Modal>
  )
}
