import { Calendar, Plus } from 'lucide-react'
import { useState, type DragEvent } from 'react'

import { Avatar, Button, Field, Input, Modal } from '@/components/ui'
import { AIScoreBadge } from '@/components/ui/StatusBadges'
import { cn } from '@/lib/cn'
import { STAGE_MAP } from '@/lib/constants'
import { formatCompactCurrency, formatCurrency, formatDate } from '@/lib/format'
import type { Deal, DealStage, KanbanColumn as Column } from '@/types/api'

export function DealCard({
  deal,
  onOpen,
  onDragStart,
}: {
  deal: Deal
  onOpen: () => void
  onDragStart: (e: DragEvent<HTMLDivElement>) => void
}) {
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onClick={onOpen}
      className="cursor-grab rounded-lg border border-slate-200 bg-white p-3 shadow-sm transition hover:border-indigo-300 hover:shadow active:cursor-grabbing"
    >
      <p className="line-clamp-2 text-sm font-medium text-slate-800">{deal.title}</p>
      <p className="mt-0.5 truncate text-xs text-slate-500">{deal.client.name}</p>
      <div className="mt-2 flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-900">{formatCurrency(deal.estimated_value)}</span>
        <span className="text-xs text-slate-500">{deal.probability}%</span>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <AIScoreBadge score={deal.ai_score} />
          {deal.expected_close_date && (
            <span className={cn('inline-flex items-center gap-1 text-[11px]', deal.is_overdue ? 'text-rose-600' : 'text-slate-400')}>
              <Calendar className="h-3 w-3" />
              {formatDate(deal.expected_close_date)}
            </span>
          )}
        </div>
        {deal.owner && <Avatar name={deal.owner.name} className="h-6 w-6 text-[10px]" />}
      </div>
    </div>
  )
}

export function KanbanBoardView({
  columns,
  onOpenDeal,
  onMove,
  onCreate,
}: {
  columns: Column[]
  onOpenDeal: (id: string) => void
  onMove: (dealId: string, stage: DealStage, position: number, lostReason?: string) => void
  onCreate: (stage: DealStage) => void
}) {
  const [dragging, setDragging] = useState<Deal | null>(null)
  const [overStage, setOverStage] = useState<DealStage | null>(null)
  const [pendingLost, setPendingLost] = useState<{ deal: Deal; position: number } | null>(null)
  const [lostReason, setLostReason] = useState('')

  function handleDrop(e: DragEvent<HTMLDivElement>, column: Column) {
    e.preventDefault()
    setOverStage(null)
    if (!dragging) return
    // Posição: índice do card sobre o qual soltou (ou fim da coluna).
    const target = (e.target as HTMLElement).closest('[data-index]') as HTMLElement | null
    const position = target ? Number(target.dataset.index) : column.deals.filter((d) => d.id !== dragging.id).length
    if (dragging.stage === column.stage && dragging.position === position) return
    if (column.stage === 'fechado_perdido' && dragging.stage !== 'fechado_perdido') {
      setPendingLost({ deal: dragging, position })
      setLostReason('')
    } else {
      onMove(dragging.id, column.stage, position)
    }
    setDragging(null)
  }

  return (
    <>
      <div className="scroll-thin flex gap-4 overflow-x-auto pb-4">
        {columns.map((column) => {
          const meta = STAGE_MAP[column.stage]
          return (
            <div
              key={column.stage}
              onDragOver={(e) => {
                e.preventDefault()
                setOverStage(column.stage)
              }}
              onDragLeave={() => setOverStage((s) => (s === column.stage ? null : s))}
              onDrop={(e) => handleDrop(e, column)}
              className={cn(
                'flex w-72 shrink-0 flex-col rounded-xl bg-slate-100/80 transition',
                overStage === column.stage && 'bg-indigo-50 ring-2 ring-indigo-300',
              )}
            >
              <div className="px-3 pt-3 pb-2">
                <div className="flex items-center justify-between">
                  <p className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                    <span className={cn('h-2 w-2 rounded-full', meta.dot)} />
                    {column.label}
                    <span className="rounded-full bg-white px-1.5 text-xs text-slate-500">{column.count}</span>
                  </p>
                  {!column.stage.startsWith('fechado') && (
                    <button onClick={() => onCreate(column.stage)} className="rounded p-1 text-slate-400 hover:bg-white hover:text-slate-700" title="Nova negociação">
                      <Plus className="h-4 w-4" />
                    </button>
                  )}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {formatCompactCurrency(column.total_value)}
                  {!column.stage.startsWith('fechado') && ` · ponderado ${formatCompactCurrency(column.weighted_value)}`}
                </p>
              </div>
              <div className="scroll-thin flex min-h-24 flex-1 flex-col gap-2 overflow-y-auto px-3 pb-3" style={{ maxHeight: 'calc(100vh - 260px)' }}>
                {column.deals.map((deal, index) => (
                  <div key={deal.id} data-index={index} className={cn(dragging?.id === deal.id && 'opacity-40')}>
                    <DealCard
                      deal={deal}
                      onOpen={() => onOpenDeal(deal.id)}
                      onDragStart={(e) => {
                        e.dataTransfer.effectAllowed = 'move'
                        setDragging(deal)
                      }}
                    />
                  </div>
                ))}
                {column.deals.length === 0 && (
                  <p className="rounded-lg border border-dashed border-slate-300 py-6 text-center text-xs text-slate-400">
                    Arraste negociações para cá
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <Modal
        open={Boolean(pendingLost)}
        onClose={() => setPendingLost(null)}
        title="Marcar como perdida"
        description={pendingLost?.deal.title}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setPendingLost(null)}>
              Cancelar
            </Button>
            <Button
              variant="danger"
              disabled={!lostReason.trim()}
              onClick={() => {
                if (pendingLost) onMove(pendingLost.deal.id, 'fechado_perdido', pendingLost.position, lostReason.trim())
                setPendingLost(null)
              }}
            >
              Confirmar perda
            </Button>
          </>
        }
      >
        <Field label="Motivo da perda" hint="Fica registrado no histórico e ajuda a IA a entender as perdas.">
          <Input value={lostReason} onChange={(e) => setLostReason(e.target.value)} placeholder="Ex.: Preço acima do orçamento" autoFocus />
        </Field>
      </Modal>
    </>
  )
}
