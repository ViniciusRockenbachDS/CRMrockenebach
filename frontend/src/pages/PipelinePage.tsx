import { KanbanSquare, Plus, Search, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { DealDetailsModal } from '@/components/deals/DealDetailsModal'
import { DealFormModal } from '@/components/deals/DealFormModal'
import { KanbanBoardView } from '@/components/deals/Kanban'
import { Button, Card, EmptyState, Input, LoadingState, PageHeader, Select } from '@/components/ui'
import { useBoard, useMoveDeal, useScoreBatch, useUsers } from '@/hooks/queries'
import { formatCurrency } from '@/lib/format'
import type { DealStage } from '@/types/api'

export default function PipelinePage() {
  const [search, setSearch] = useState('')
  const [debounced, setDebounced] = useState('')
  const [owner, setOwner] = useState('')
  const [openDealId, setOpenDealId] = useState<string | null>(null)
  const [createStage, setCreateStage] = useState<DealStage | null>(null)
  const { data: users } = useUsers({ only_active: true })

  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(search), 350)
    return () => window.clearTimeout(t)
  }, [search])

  const boardParams = useMemo(() => ({ owner_id: owner || undefined, search: debounced || undefined }), [owner, debounced])
  const { data, isLoading } = useBoard(boardParams)
  const move = useMoveDeal(boardParams)
  const scoreAll = useScoreBatch()

  const totalDeals = data?.columns.reduce((sum, c) => sum + c.count, 0) ?? 0

  return (
    <>
      <PageHeader
        title="Funil de vendas"
        description={
          data
            ? `Pipeline aberto: ${formatCurrency(data.total_open_value)} · previsão ponderada: ${formatCurrency(data.total_weighted_value)}`
            : 'Arraste os cards entre as etapas'
        }
        actions={
          <>
            <Button
              variant="secondary"
              icon={<Sparkles className="h-4 w-4 text-indigo-600" />}
              loading={scoreAll.isPending}
              onClick={() => scoreAll.mutate()}
              title="Calcula a chance de fechamento de todas as negociações abertas"
            >
              Pontuar com IA
            </Button>
            <Button icon={<Plus className="h-4 w-4" />} onClick={() => setCreateStage('prospeccao')}>
              Nova negociação
            </Button>
          </>
        }
      />

      <Card className="mb-4 flex flex-wrap gap-3 p-3">
        <div className="relative min-w-60 flex-1">
          <Search className="absolute top-2.5 left-3 h-4 w-4 text-slate-400" />
          <Input placeholder="Buscar por título ou cliente" value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
        <Select
          className="w-56"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
          placeholder="Todos os responsáveis"
          options={(users?.items ?? []).map((u) => ({ value: u.id, label: u.name }))}
        />
      </Card>

      {isLoading && <LoadingState />}
      {data && totalDeals === 0 && !search && (
        <Card>
          <EmptyState
            icon={<KanbanSquare className="h-6 w-6" />}
            title="Nenhuma negociação no funil"
            description="Crie a primeira negociação vinculada a um cliente."
            action={<Button onClick={() => setCreateStage('prospeccao')}>Nova negociação</Button>}
          />
        </Card>
      )}
      {data && (totalDeals > 0 || search) && (
        <KanbanBoardView
          columns={data.columns}
          onOpenDeal={setOpenDealId}
          onCreate={setCreateStage}
          onMove={(id, stage, position, lostReason) =>
            move.mutate({ id, data: { stage, position, lost_reason: lostReason ?? null } })
          }
        />
      )}
      <p className="mt-2 text-xs text-slate-400">Colunas fechadas exibem os últimos 30 dias.</p>

      <DealDetailsModal dealId={openDealId} onClose={() => setOpenDealId(null)} />
      <DealFormModal open={Boolean(createStage)} onClose={() => setCreateStage(null)} defaultStage={createStage ?? 'prospeccao'} />
    </>
  )
}
