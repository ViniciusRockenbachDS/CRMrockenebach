import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { aiApi, clientsApi, dashboardApi, dealsApi, paymentsApi, usersApi } from '@/api/endpoints'
import { getErrorMessage } from '@/api/http'
import { useToast } from '@/contexts/ToastContext'
import type {
  ClientFilters,
  ClientPayload,
  DashboardFilters,
  DealFilters,
  DealMovePayload,
  DealPayload,
  DealUpdatePayload,
  InsightsPayload,
  InstallmentsPayload,
  InteractionPayload,
  KanbanBoard,
  PaymentFilters,
  PaymentMethod,
  PaymentPayload,
  UserCreatePayload,
  UserUpdatePayload,
} from '@/types/api'

// Chaves centralizadas: facilitam invalidar tudo que depende de uma entidade.
export const qk = {
  users: (params?: object) => ['users', params] as const,
  clients: (filters?: object) => ['clients', filters] as const,
  client: (id: string) => ['client', id] as const,
  interactions: (id: string) => ['interactions', id] as const,
  board: (params?: object) => ['board', params] as const,
  deals: (filters?: object) => ['deals', filters] as const,
  deal: (id: string) => ['deal', id] as const,
  dealHistory: (id: string) => ['deal-history', id] as const,
  payments: (filters?: object) => ['payments', filters] as const,
  paymentsSummary: ['payments-summary'] as const,
  dashboard: (filters?: object) => ['dashboard', filters] as const,
  aiStatus: ['ai-status'] as const,
}

/** Invalida as consultas afetadas por mudanças comerciais (clientes, deals, pagamentos). */
function useInvalidateCommercial() {
  const queryClient = useQueryClient()
  return () =>
    Promise.all(
      ['clients', 'client', 'board', 'deals', 'deal', 'deal-history', 'payments', 'payments-summary', 'dashboard'].map(
        (key) => queryClient.invalidateQueries({ queryKey: [key] }),
      ),
    )
}

function useMutationWithToast<TVars, TData>(
  fn: (vars: TVars) => Promise<TData>,
  successMessage?: string | ((data: TData) => string),
) {
  const toast = useToast()
  const invalidate = useInvalidateCommercial()
  return useMutation({
    mutationFn: fn,
    onSuccess: async (data) => {
      await invalidate()
      if (successMessage) toast.success(typeof successMessage === 'function' ? successMessage(data) : successMessage)
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })
}

// ---------------------------------------------------------------- usuários
export const useUsers = (params: { search?: string; only_active?: boolean; limit?: number; offset?: number } = {}) =>
  useQuery({ queryKey: qk.users(params), queryFn: () => usersApi.list({ limit: 100, ...params }) })

export function useCreateUser() {
  const queryClient = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (data: UserCreatePayload) => usersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast.success('Usuário criado.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UserUpdatePayload }) => usersApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast.success('Usuário atualizado.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

// ---------------------------------------------------------------- clientes
export const useClients = (filters: ClientFilters) =>
  useQuery({ queryKey: qk.clients(filters), queryFn: () => clientsApi.list(filters), placeholderData: keepPreviousData })

export const useClient = (id: string) =>
  useQuery({ queryKey: qk.client(id), queryFn: () => clientsApi.get(id), enabled: Boolean(id) })

export const useInteractions = (clientId: string, limit = 50) =>
  useQuery({ queryKey: qk.interactions(clientId), queryFn: () => clientsApi.interactions(clientId, { limit }) })

export const useCreateClient = () =>
  useMutationWithToast((data: ClientPayload) => clientsApi.create(data), 'Cliente cadastrado.')

export const useUpdateClient = () =>
  useMutationWithToast(({ id, data }: { id: string; data: ClientPayload }) => clientsApi.update(id, data), 'Cliente atualizado.')

export const useDeleteClient = () => useMutationWithToast((id: string) => clientsApi.remove(id), 'Cliente excluído.')

export function useAddInteraction(clientId: string) {
  const queryClient = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (data: InteractionPayload) => clientsApi.addInteraction(clientId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.interactions(clientId) })
      queryClient.invalidateQueries({ queryKey: qk.client(clientId) })
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      toast.success('Interação registrada.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useDeleteInteraction(clientId: string) {
  const queryClient = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (interactionId: string) => clientsApi.removeInteraction(clientId, interactionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.interactions(clientId) })
      queryClient.invalidateQueries({ queryKey: qk.client(clientId) })
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

// ---------------------------------------------------------------- negociações
export const useBoard = (params: { owner_id?: string; search?: string }) =>
  useQuery({ queryKey: qk.board(params), queryFn: () => dealsApi.board(params), placeholderData: keepPreviousData })

export const useDeals = (filters: DealFilters, enabled = true) =>
  useQuery({ queryKey: qk.deals(filters), queryFn: () => dealsApi.list(filters), enabled })

export const useDeal = (id: string | null) =>
  useQuery({ queryKey: qk.deal(id ?? ''), queryFn: () => dealsApi.get(id as string), enabled: Boolean(id) })

export const useDealHistory = (id: string | null) =>
  useQuery({ queryKey: qk.dealHistory(id ?? ''), queryFn: () => dealsApi.history(id as string), enabled: Boolean(id) })

export const useCreateDeal = () => useMutationWithToast((data: DealPayload) => dealsApi.create(data), 'Negociação criada.')

export const useUpdateDeal = () =>
  useMutationWithToast(
    ({ id, data }: { id: string; data: DealUpdatePayload }) => dealsApi.update(id, data),
    'Negociação atualizada.',
  )

export const useDeleteDeal = () => useMutationWithToast((id: string) => dealsApi.remove(id), 'Negociação excluída.')

/** Movimentação no Kanban com atualização otimista (o card muda de coluna na hora). */
export function useMoveDeal(boardKey: object) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const invalidate = useInvalidateCommercial()
  const key = qk.board(boardKey)
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DealMovePayload }) => dealsApi.move(id, data),
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: key })
      const previous = queryClient.getQueryData<KanbanBoard>(key)
      if (previous) {
        const deal = previous.columns.flatMap((c) => c.deals).find((d) => d.id === id)
        if (deal) {
          const moved = { ...deal, stage: data.stage }
          const columns = previous.columns.map((col) => {
            const without = col.deals.filter((d) => d.id !== id)
            if (col.stage !== data.stage) return { ...col, deals: without, count: without.length }
            const index = data.position ?? without.length
            const deals = [...without.slice(0, index), moved, ...without.slice(index)]
            return { ...col, deals, count: deals.length }
          })
          queryClient.setQueryData<KanbanBoard>(key, { ...previous, columns })
        }
      }
      return { previous }
    },
    onError: (error, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous)
      toast.error(getErrorMessage(error))
    },
    onSettled: () => invalidate(),
  })
}

// ---------------------------------------------------------------- pagamentos
export const usePayments = (filters: PaymentFilters) =>
  useQuery({ queryKey: qk.payments(filters), queryFn: () => paymentsApi.list(filters), placeholderData: keepPreviousData })

export const usePaymentsSummary = () => useQuery({ queryKey: qk.paymentsSummary, queryFn: paymentsApi.summary })

export const useCreatePayment = () =>
  useMutationWithToast((data: PaymentPayload) => paymentsApi.create(data), (p) => `Fatura ${p.invoice_number} criada.`)

export const useCreateInstallments = () =>
  useMutationWithToast(
    (data: InstallmentsPayload) => paymentsApi.createInstallments(data),
    (list) => `${list.length} parcela(s) geradas.`,
  )

export const useMarkPaid = () =>
  useMutationWithToast(
    ({ id, ...data }: { id: string; payment_date: string; method?: PaymentMethod | null; notes?: string | null }) =>
      paymentsApi.markPaid(id, data),
    'Pagamento registrado.',
  )

export const useCancelPayment = () =>
  useMutationWithToast(({ id, reason }: { id: string; reason: string }) => paymentsApi.cancel(id, reason), 'Fatura cancelada.')

// ---------------------------------------------------------------- dashboard e IA
export const useDashboard = (filters: DashboardFilters) =>
  useQuery({ queryKey: qk.dashboard(filters), queryFn: () => dashboardApi.get(filters), placeholderData: keepPreviousData })

export const useAIStatus = () => useQuery({ queryKey: qk.aiStatus, queryFn: aiApi.status, staleTime: 5 * 60_000 })

export function useClientSummaryAI(clientId: string) {
  const toast = useToast()
  return useMutation({
    mutationFn: (force: boolean) => aiApi.clientSummary(clientId, force),
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useScoreDeal() {
  const toast = useToast()
  const invalidate = useInvalidateCommercial()
  return useMutation({
    mutationFn: ({ id, force }: { id: string; force?: boolean }) => aiApi.scoreDeal(id, force),
    onSuccess: () => invalidate(),
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useScoreBatch() {
  const toast = useToast()
  const invalidate = useInvalidateCommercial()
  return useMutation({
    mutationFn: aiApi.scoreBatch,
    onSuccess: async (r) => {
      await invalidate()
      toast.success(`${r.scored} negociação(ões) pontuadas pela IA.`)
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useInsightsAI() {
  const toast = useToast()
  return useMutation({
    mutationFn: (data: InsightsPayload) => aiApi.insights(data),
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}
