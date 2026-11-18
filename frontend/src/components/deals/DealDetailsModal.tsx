import { ArrowRight, Pencil, Receipt, RefreshCw, Sparkles, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { DealFormModal } from '@/components/deals/DealFormModal'
import { PaymentFormModal } from '@/components/payments/PaymentFormModal'
import { Badge, Button, ConfirmDialog, Input, LoadingState, Modal, Select } from '@/components/ui'
import { AIScoreBadge, StageBadge } from '@/components/ui/StatusBadges'
import { useAuth } from '@/contexts/AuthContext'
import { useDeal, useDealHistory, useDeleteDeal, useMoveDeal, useScoreDeal } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { DEAL_STAGES, STAGE_MAP } from '@/lib/constants'
import { formatCurrency, formatDate, formatDateTime } from '@/lib/format'
import type { DealStage, LeadScore } from '@/types/api'

function ScorePanel({ score }: { score: LeadScore }) {
  return (
    <div className="space-y-3 rounded-xl border border-indigo-100 bg-indigo-50/50 p-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-3xl font-bold text-indigo-700">{Math.round(score.score)}%</span>
        <div className="text-xs text-slate-600">
          <p>chance prevista de ganho</p>
          <p>
            vendedor estimou <strong>{score.current_probability}%</strong> · confiança <strong>{score.confidence}</strong>
          </p>
        </div>
      </div>
      {score.recommendation && <p className="text-sm font-medium text-slate-800">→ {score.recommendation}</p>}
      <div className="space-y-1.5">
        {score.factors.map((f) => (
          <div key={f.feature} className="flex items-center gap-2 text-xs">
            <div className="flex w-24 justify-end">
              {f.impact < 0 && <div className="h-2 rounded-l-full bg-rose-400" style={{ width: `${Math.abs(f.impact) * 100}%` }} />}
            </div>
            <div className="w-24">
              {f.impact > 0 && <div className="h-2 rounded-r-full bg-emerald-500" style={{ width: `${f.impact * 100}%` }} />}
            </div>
            <span className="flex-1 text-slate-600">{f.description}</span>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-slate-400">
        {score.meta.provider} · {score.meta.model} {score.meta.cached && '· em cache'}
      </p>
    </div>
  )
}

export function DealDetailsModal({ dealId, onClose }: { dealId: string | null; onClose: () => void }) {
  const { isManager } = useAuth()
  const { data: deal, isLoading } = useDeal(dealId)
  const { data: history } = useDealHistory(dealId)
  const move = useMoveDeal({})
  const score = useScoreDeal()
  const remove = useDeleteDeal()
  const [targetStage, setTargetStage] = useState<DealStage | ''>('')
  const [lostReason, setLostReason] = useState('')
  const [editing, setEditing] = useState(false)
  const [paying, setPaying] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  useEffect(() => {
    setTargetStage('')
    setLostReason('')
    score.reset()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dealId])

  const isOpen = deal ? !['fechado_ganho', 'fechado_perdido'].includes(deal.stage) : false

  function handleMove() {
    if (!deal || !targetStage) return
    move.mutate(
      { id: deal.id, data: { stage: targetStage, lost_reason: targetStage === 'fechado_perdido' ? lostReason : null } },
      {
        onSuccess: () => {
          setTargetStage('')
          setLostReason('')
        },
      },
    )
  }

  return (
    <>
      <Modal open={Boolean(dealId)} onClose={onClose} title={deal?.title ?? 'Negociação'} size="lg">
        {isLoading || !deal ? (
          <LoadingState />
        ) : (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-2">
              <StageBadge stage={deal.stage} />
              <AIScoreBadge score={deal.ai_score} />
              {deal.is_overdue && <Badge className="bg-rose-100 text-rose-700">Previsão vencida</Badge>}
              <Link to={`/clientes/${deal.client.id}`} onClick={onClose} className="ml-auto text-sm font-medium text-indigo-600 hover:underline">
                {deal.client.name} →
              </Link>
            </div>

            <div className="grid grid-cols-2 gap-4 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-4">
              <Info label="Valor" value={formatCurrency(deal.estimated_value)} />
              <Info label="Probabilidade" value={`${deal.probability}%`} />
              <Info label="Valor ponderado" value={formatCurrency(deal.weighted_value)} />
              <Info label="Previsão" value={formatDate(deal.expected_close_date)} />
              <Info label="Responsável" value={deal.owner?.name ?? '—'} />
              <Info label="Criada em" value={formatDate(deal.created_at)} />
              {deal.closed_at && <Info label="Fechada em" value={formatDate(deal.closed_at)} />}
              {deal.lost_reason && <Info label="Motivo da perda" value={deal.lost_reason} />}
            </div>
            {deal.description && <p className="text-sm whitespace-pre-line text-slate-600">{deal.description}</p>}

            <div className="space-y-2">
              <p className="text-sm font-semibold text-slate-800">Mover para outra etapa</p>
              <div className="flex flex-wrap gap-2">
                <Select
                  className="max-w-xs"
                  value={targetStage}
                  onChange={(e) => setTargetStage(e.target.value as DealStage)}
                  placeholder="Escolha a etapa"
                  options={DEAL_STAGES.filter((s) => s.value !== deal.stage).map((s) => ({ value: s.value, label: s.label }))}
                />
                {targetStage === 'fechado_perdido' && (
                  <Input className="max-w-xs" placeholder="Motivo da perda (obrigatório)" value={lostReason} onChange={(e) => setLostReason(e.target.value)} />
                )}
                <Button
                  icon={<ArrowRight className="h-4 w-4" />}
                  disabled={!targetStage || (targetStage === 'fechado_perdido' && !lostReason.trim())}
                  loading={move.isPending}
                  onClick={handleMove}
                >
                  Mover
                </Button>
              </div>
            </div>

            {isOpen && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
                    <Sparkles className="h-4 w-4 text-indigo-600" /> Lead scoring (IA)
                  </p>
                  <Button
                    size="sm"
                    variant="secondary"
                    loading={score.isPending}
                    icon={score.data ? <RefreshCw className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}
                    onClick={() => score.mutate({ id: deal.id, force: Boolean(score.data) })}
                  >
                    {score.data ? 'Recalcular' : 'Calcular chance de fechamento'}
                  </Button>
                </div>
                {score.data && <ScorePanel score={score.data} />}
              </div>
            )}

            <div>
              <p className="mb-2 text-sm font-semibold text-slate-800">Histórico de etapas</p>
              <ol className="space-y-2">
                {history?.map((h) => (
                  <li key={h.id} className="flex items-center gap-2 text-sm">
                    <span className={cn('h-2 w-2 rounded-full', STAGE_MAP[h.to_stage].dot)} />
                    <span className="text-slate-700">
                      {h.from_stage ? `${STAGE_MAP[h.from_stage].label} → ` : ''}
                      <strong>{STAGE_MAP[h.to_stage].label}</strong>
                    </span>
                    <span className="text-xs text-slate-400">
                      {formatDateTime(h.changed_at)} {h.changed_by && `· ${h.changed_by.name}`}
                      {h.seconds_in_previous_stage !== null && ` · ${Math.round(h.seconds_in_previous_stage / 86400)} dia(s) na etapa anterior`}
                    </span>
                  </li>
                ))}
              </ol>
            </div>

            <div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-4">
              {isManager && (
                <Button variant="ghost" icon={<Trash2 className="h-4 w-4" />} onClick={() => setConfirmDelete(true)}>
                  Excluir
                </Button>
              )}
              <Button variant="secondary" icon={<Pencil className="h-4 w-4" />} onClick={() => setEditing(true)}>
                Editar
              </Button>
              {deal.stage === 'fechado_ganho' && (
                <Button variant="success" icon={<Receipt className="h-4 w-4" />} onClick={() => setPaying(true)}>
                  Lançar cobrança
                </Button>
              )}
            </div>
          </div>
        )}
      </Modal>

      {deal && (
        <>
          <DealFormModal open={editing} onClose={() => setEditing(false)} deal={deal} />
          <PaymentFormModal open={paying} onClose={() => setPaying(false)} defaultDeal={deal} />
          <ConfirmDialog
            open={confirmDelete}
            title="Excluir negociação"
            message="A negociação sai do funil, mas o histórico é preservado. Negociações com faturas ativas não podem ser excluídas."
            confirmLabel="Excluir"
            danger
            loading={remove.isPending}
            onClose={() => setConfirmDelete(false)}
            onConfirm={() =>
              remove.mutate(deal.id, {
                onSuccess: () => {
                  setConfirmDelete(false)
                  onClose()
                },
                onSettled: () => setConfirmDelete(false),
              })
            }
          />
        </>
      )}
    </>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="font-medium text-slate-800">{value}</p>
    </div>
  )
}
