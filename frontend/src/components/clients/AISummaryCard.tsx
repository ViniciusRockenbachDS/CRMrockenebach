import { AlertTriangle, CheckCircle2, RefreshCw, Sparkles } from 'lucide-react'

import { Badge, Button, Card, CardHeader } from '@/components/ui'
import { useClientSummaryAI } from '@/hooks/queries'
import { formatDateTime } from '@/lib/format'

const SENTIMENT = {
  positivo: 'bg-emerald-100 text-emerald-700',
  neutro: 'bg-slate-100 text-slate-600',
  negativo: 'bg-rose-100 text-rose-700',
  indefinido: 'bg-slate-100 text-slate-500',
}

export function AISummaryCard({ clientId }: { clientId: string }) {
  const mutation = useClientSummaryAI(clientId)
  const data = mutation.data

  return (
    <Card className="border-indigo-100 bg-gradient-to-br from-indigo-50/60 to-white">
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-600" /> Resumo inteligente
          </span>
        }
        subtitle="A IA lê o histórico de interações, negociações e pagamentos"
        action={
          <Button
            size="sm"
            variant={data ? 'secondary' : 'primary'}
            loading={mutation.isPending}
            icon={data ? <RefreshCw className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}
            onClick={() => mutation.mutate(Boolean(data))}
          >
            {data ? 'Atualizar' : 'Gerar resumo'}
          </Button>
        }
      />
      <div className="space-y-4 px-5 py-4 text-sm">
        {!data && !mutation.isPending && <p className="text-slate-500">Gere um resumo para se preparar antes de falar com o cliente.</p>}
        {data && (
          <>
            <div className="flex items-start gap-2">
              <Badge className={SENTIMENT[data.sentiment]}>Sentimento: {data.sentiment}</Badge>
              <span className="text-xs text-slate-400">{data.interactions_analyzed} interações analisadas</span>
            </div>
            <p className="leading-relaxed text-slate-700">{data.summary}</p>
            {data.key_points.length > 0 && (
              <div>
                <p className="mb-1 font-medium text-slate-800">Pontos-chave</p>
                <ul className="list-disc space-y-0.5 pl-5 text-slate-600">
                  {data.key_points.map((p, i) => (
                    <li key={i}>{p}</li>
                  ))}
                </ul>
              </div>
            )}
            {data.risks.length > 0 && (
              <div className="rounded-lg bg-rose-50 p-3">
                <p className="mb-1 flex items-center gap-1.5 font-medium text-rose-700">
                  <AlertTriangle className="h-4 w-4" /> Riscos
                </p>
                <ul className="space-y-0.5 text-rose-700/90">
                  {data.risks.map((r, i) => (
                    <li key={i}>• {r}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="rounded-lg bg-emerald-50 p-3">
              <p className="mb-1 flex items-center gap-1.5 font-medium text-emerald-700">
                <CheckCircle2 className="h-4 w-4" /> Próximas ações sugeridas
              </p>
              <ul className="space-y-0.5 text-emerald-800/90">
                {data.next_best_actions.map((a, i) => (
                  <li key={i}>• {a}</li>
                ))}
              </ul>
            </div>
            <p className="text-xs text-slate-400">
              {data.meta.provider} · {data.meta.model}
              {data.meta.cached && ' · em cache'} · {formatDateTime(data.meta.generated_at)}
            </p>
          </>
        )}
      </div>
    </Card>
  )
}
