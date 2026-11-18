import { Sparkles } from 'lucide-react'

import { Badge } from '@/components/ui'
import { cn } from '@/lib/cn'
import { CLIENT_STATUS, PAYMENT_STATUS, STAGE_MAP } from '@/lib/constants'
import type { ClientStatus, DealStage, PaymentStatus } from '@/types/api'

export const ClientStatusBadge = ({ status }: { status: ClientStatus }) => (
  <Badge className={CLIENT_STATUS[status].color}>{CLIENT_STATUS[status].label}</Badge>
)

export const StageBadge = ({ stage }: { stage: DealStage }) => (
  <Badge className={STAGE_MAP[stage].color}>
    <span className={cn('h-1.5 w-1.5 rounded-full', STAGE_MAP[stage].dot)} />
    {STAGE_MAP[stage].label}
  </Badge>
)

export const PaymentStatusBadge = ({ status }: { status: PaymentStatus }) => (
  <Badge className={PAYMENT_STATUS[status].color}>{PAYMENT_STATUS[status].label}</Badge>
)

/** Score da IA com cor por faixa: verde ≥ 60, âmbar ≥ 35, vermelho abaixo. */
export function AIScoreBadge({ score, className }: { score: number | null; className?: string }) {
  if (score === null || score === undefined) return null
  const color =
    score >= 60 ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : score >= 35 ? 'bg-amber-50 text-amber-700 ring-amber-200' : 'bg-rose-50 text-rose-700 ring-rose-200'
  return (
    <Badge className={cn('ring-1', color, className)}>
      <Sparkles className="h-3 w-3" />
      {Math.round(score)}%
    </Badge>
  )
}
