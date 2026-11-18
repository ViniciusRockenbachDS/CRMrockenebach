import { AlertOctagon, AlertTriangle, Info, RefreshCw, Sparkles } from 'lucide-react'

import { Badge, Button, Card, CardHeader } from '@/components/ui'
import { useInsightsAI } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/format'
import type { Insight, InsightCategory } from '@/types/api'

const SEVERITY = {
  info: { icon: Info, style: 'border-sky-200 bg-sky-50/60', iconColor: 'text-sky-600' },
  atencao: { icon: AlertTriangle, style: 'border-amber-200 bg-amber-50/60', iconColor: 'text-amber-600' },
  critico: { icon: AlertOctagon, style: 'border-rose-200 bg-rose-50/60', iconColor: 'text-rose-600' },
}
const CATEGORY: Record<InsightCategory, string> = {
  funil: 'Funil',
  inadimplencia: 'Inadimplência',
  receita: 'Receita',
  origem_leads: 'Origem de leads',
}

export function InsightsPanel({ dateFrom, dateTo }: { dateFrom?: string; dateTo?: string }) {
  const mutation = useInsightsAI()
  const data = mutation.data

  const generate = (force = false) =>
    mutation.mutate({
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      focus: ['funil', 'inadimplencia', 'receita', 'origem_leads'],
      force_refresh: force,
    })

  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-600" /> Insights da IA
          </span>
        }
        subtitle="Análise automática do funil, receita e inadimplência do período"
        action={
          <Button
            size="sm"
            variant={data ? 'secondary' : 'primary'}
            loading={mutation.isPending}
            icon={data ? <RefreshCw className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}
            onClick={() => generate(Boolean(data))}
          >
            {data ? 'Gerar novamente' : 'Gerar insights'}
          </Button>
        }
      />
      <div className="px-5 py-4">
        {!data && !mutation.isPending && (
          <p className="text-sm text-slate-500">
            Clique em <strong>Gerar insights</strong> para a IA analisar os números do período selecionado.
          </p>
        )}
        {data && (
          <div className="space-y-3">
            <p className="font-medium text-slate-800">{data.headline}</p>
            <div className="grid gap-3 md:grid-cols-2">
              {data.insights.map((insight: Insight, i: number) => {
                const sev = SEVERITY[insight.severity]
                const Icon = sev.icon
                return (
                  <div key={i} className={cn('rounded-lg border p-3', sev.style)}>
                    <div className="flex items-start gap-2">
                      <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', sev.iconColor)} />
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-semibold text-slate-800">{insight.title}</p>
                          <Badge className="bg-white/70 text-slate-500">{CATEGORY[insight.category]}</Badge>
                        </div>
                        <p className="mt-1 text-sm text-slate-600">{insight.description}</p>
                        {insight.recommendation && (
                          <p className="mt-1.5 text-sm font-medium text-slate-700">→ {insight.recommendation}</p>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
            <p className="text-xs text-slate-400">
              {data.meta.provider} · {data.meta.model} · {data.meta.cached ? 'resultado em cache · ' : ''}
              {formatDateTime(data.meta.generated_at)}
            </p>
          </div>
        )}
      </div>
    </Card>
  )
}
