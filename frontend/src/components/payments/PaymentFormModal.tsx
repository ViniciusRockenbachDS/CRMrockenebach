import { useEffect, useState, type FormEvent } from 'react'

import { Button, Field, Input, Modal, Select } from '@/components/ui'
import { useCreateInstallments, useCreatePayment, useDeals } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { PAYMENT_METHODS, toOptions } from '@/lib/constants'
import { formatCurrency, todayISO } from '@/lib/format'
import type { PaymentMethod } from '@/types/api'

interface DealOption {
  id: string
  title: string
  estimated_value: number
}

export function PaymentFormModal({
  open,
  onClose,
  defaultDeal,
}: {
  open: boolean
  onClose: () => void
  defaultDeal?: DealOption | null
}) {
  const { data: wonDeals } = useDeals({ stage: ['fechado_ganho'], limit: 100, order_by: 'created_at' }, open && !defaultDeal)
  const createOne = useCreatePayment()
  const createMany = useCreateInstallments()

  const [mode, setMode] = useState<'single' | 'installments'>('single')
  const [dealId, setDealId] = useState('')
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState<PaymentMethod>('pix')
  const [dueDate, setDueDate] = useState(todayISO())
  const [installments, setInstallments] = useState('3')
  const [description, setDescription] = useState('')
  const [alreadyPaid, setAlreadyPaid] = useState(false)
  const [paymentDate, setPaymentDate] = useState(todayISO())

  useEffect(() => {
    if (!open) return
    setMode('single')
    setDealId(defaultDeal?.id ?? '')
    setAmount(defaultDeal ? String(defaultDeal.estimated_value) : '')
    setMethod('pix')
    setDueDate(todayISO())
    setInstallments('3')
    setDescription('')
    setAlreadyPaid(false)
    setPaymentDate(todayISO())
  }, [open, defaultDeal])

  const deals: DealOption[] = defaultDeal ? [defaultDeal] : (wonDeals?.items ?? [])

  function onSelectDeal(id: string) {
    setDealId(id)
    const deal = deals.find((d) => d.id === id)
    if (deal) setAmount(String(deal.estimated_value))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const value = Number(amount.replace(',', '.'))
    if (!dealId || !value) return
    if (mode === 'single') {
      await createOne.mutateAsync({
        deal_id: dealId,
        amount: value,
        method,
        due_date: dueDate,
        description: description || null,
        status: alreadyPaid ? 'pago' : 'pendente',
        payment_date: alreadyPaid ? paymentDate : null,
      })
    } else {
      await createMany.mutateAsync({
        deal_id: dealId,
        total_amount: value,
        installments: Number(installments),
        first_due_date: dueDate,
        method,
        description: description || null,
      })
    }
    onClose()
  }

  const parcels = Number(installments) || 1
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Lançar cobrança"
      description="Faturas só podem ser lançadas em negociações em Fechado Ganho."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" form="payment-form" loading={createOne.isPending || createMany.isPending} disabled={!dealId}>
            Salvar
          </Button>
        </>
      }
    >
      <form id="payment-form" onSubmit={(e) => handleSubmit(e).catch(() => undefined)} className="space-y-4">
        <div className="inline-flex rounded-lg bg-slate-100 p-1 text-sm">
          {(['single', 'installments'] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={cn('rounded-md px-3 py-1.5 font-medium', mode === m ? 'bg-white shadow-sm' : 'text-slate-500')}
            >
              {m === 'single' ? 'Fatura única' : 'Parcelado'}
            </button>
          ))}
        </div>

        <Field label="Negociação ganha" required>
          <Select
            value={dealId}
            onChange={(e) => onSelectDeal(e.target.value)}
            placeholder={deals.length ? 'Selecione' : 'Nenhuma negociação ganha'}
            options={deals.map((d) => ({ value: d.id, label: `${d.title} — ${formatCurrency(d.estimated_value)}` }))}
            disabled={Boolean(defaultDeal)}
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={mode === 'single' ? 'Valor (R$)' : 'Valor total (R$)'} required>
            <Input type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </Field>
          <Field label="Método">
            <Select value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)} options={toOptions(PAYMENT_METHODS)} />
          </Field>
          <Field label={mode === 'single' ? 'Vencimento' : '1º vencimento'} required>
            <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
          </Field>
          {mode === 'installments' ? (
            <Field label="Parcelas" hint={amount ? `${parcels}x de ${formatCurrency(Number(amount) / parcels)}` : undefined}>
              <Input type="number" min="1" max="120" value={installments} onChange={(e) => setInstallments(e.target.value)} />
            </Field>
          ) : (
            <Field label="Descrição">
              <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Ex.: Entrada" />
            </Field>
          )}
        </div>

        {mode === 'single' && (
          <div className="rounded-lg border border-slate-200 p-3">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input type="checkbox" checked={alreadyPaid} onChange={(e) => setAlreadyPaid(e.target.checked)} className="h-4 w-4 rounded" />
              Já foi recebido
            </label>
            {alreadyPaid && (
              <Field label="Data do pagamento" className="mt-3 max-w-xs">
                <Input type="date" value={paymentDate} max={todayISO()} onChange={(e) => setPaymentDate(e.target.value)} />
              </Field>
            )}
          </div>
        )}
      </form>
    </Modal>
  )
}
