import { Calendar, Mail, MapPin, MessageCircle, Phone, StickyNote, Trash2, Users } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { Button, Input, Select, Textarea } from '@/components/ui'
import { useAddInteraction, useDeleteInteraction } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { INTERACTION_DIRECTIONS, INTERACTION_TYPES, toOptions } from '@/lib/constants'
import { formatDateTime } from '@/lib/format'
import type { DealSummary, Interaction, InteractionDirection, InteractionType } from '@/types/api'

const TYPE_ICON: Record<InteractionType, typeof Phone> = {
  ligacao: Phone,
  email: Mail,
  reuniao: Users,
  whatsapp: MessageCircle,
  visita: MapPin,
  nota: StickyNote,
  outro: Calendar,
}

export function InteractionForm({ clientId, deals }: { clientId: string; deals: DealSummary[] }) {
  const add = useAddInteraction(clientId)
  const [type, setType] = useState<InteractionType>('ligacao')
  const [direction, setDirection] = useState<InteractionDirection>('saida')
  const [subject, setSubject] = useState('')
  const [content, setContent] = useState('')
  const [dealId, setDealId] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!content.trim()) return
    await add.mutateAsync({
      type,
      direction: type === 'nota' ? 'interna' : direction,
      subject: subject.trim() || null,
      content: content.trim(),
      deal_id: dealId || null,
    })
    setSubject('')
    setContent('')
  }

  return (
    <form onSubmit={(e) => handleSubmit(e).catch(() => undefined)} className="space-y-3">
      <div className="grid gap-2 sm:grid-cols-3">
        <Select value={type} onChange={(e) => setType(e.target.value as InteractionType)} options={toOptions(INTERACTION_TYPES)} />
        <Select
          value={direction}
          onChange={(e) => setDirection(e.target.value as InteractionDirection)}
          options={toOptions(INTERACTION_DIRECTIONS)}
          disabled={type === 'nota'}
        />
        <Select
          value={dealId}
          onChange={(e) => setDealId(e.target.value)}
          placeholder="Sem negociação vinculada"
          options={deals.map((d) => ({ value: d.id, label: d.title }))}
        />
      </div>
      <Input placeholder="Assunto (opcional)" value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={200} />
      <Textarea
        placeholder="O que aconteceu nesta interação? (é a base do resumo feito pela IA)"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={3}
        required
      />
      <div className="flex justify-end">
        <Button type="submit" loading={add.isPending} disabled={!content.trim()}>
          Registrar interação
        </Button>
      </div>
    </form>
  )
}

export function InteractionTimeline({ clientId, items }: { clientId: string; items: Interaction[] }) {
  const remove = useDeleteInteraction(clientId)
  if (items.length === 0) {
    return <p className="py-6 text-center text-sm text-slate-500">Nenhuma interação registrada ainda.</p>
  }
  return (
    <ol className="relative space-y-5 border-l border-slate-200 pl-6">
      {items.map((item) => {
        const Icon = TYPE_ICON[item.type]
        const tone =
          item.sentiment === null ? 'bg-slate-100 text-slate-500' : item.sentiment > 0.2 ? 'bg-emerald-100 text-emerald-600' : item.sentiment < -0.2 ? 'bg-rose-100 text-rose-600' : 'bg-slate-100 text-slate-500'
        return (
          <li key={item.id} className="group relative">
            <span className={cn('absolute top-0 -left-[35px] flex h-7 w-7 items-center justify-center rounded-full ring-4 ring-white', tone)}>
              <Icon className="h-3.5 w-3.5" />
            </span>
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-medium text-slate-800">
                  {item.subject ?? INTERACTION_TYPES[item.type]}
                  <span className="ml-2 text-xs font-normal text-slate-400">
                    {INTERACTION_TYPES[item.type]} · {formatDateTime(item.occurred_at)}
                    {item.user && ` · ${item.user.name}`}
                  </span>
                </p>
                <p className="mt-1 text-sm whitespace-pre-line text-slate-600">{item.content}</p>
              </div>
              <button
                onClick={() => remove.mutate(item.id)}
                className="rounded p-1 text-slate-300 opacity-0 group-hover:opacity-100 hover:bg-rose-50 hover:text-rose-600"
                title="Excluir interação"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
