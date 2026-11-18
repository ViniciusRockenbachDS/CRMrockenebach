import { cleanParams, http } from '@/api/http'
import type {
  AIStatus,
  Client,
  ClientDetail,
  ClientFilters,
  ClientListItem,
  ClientPayload,
  ClientSummaryAI,
  Dashboard,
  DashboardFilters,
  Deal,
  DealFilters,
  DealMovePayload,
  DealPayload,
  DealStageHistory,
  DealUpdatePayload,
  InsightsPayload,
  InsightsResponse,
  InstallmentsPayload,
  Interaction,
  InteractionPayload,
  KanbanBoard,
  LeadScore,
  LoginResponse,
  Page,
  PageParams,
  Payment,
  PaymentFilters,
  PaymentMethod,
  PaymentPayload,
  ReceivablesSummary,
  User,
  UserCreatePayload,
  UserUpdatePayload,
} from '@/types/api'

export const authApi = {
  login: (email: string, password: string) =>
    http.post<LoginResponse>('/auth/login', { email, password }).then((r) => r.data),
  me: () => http.get<User>('/auth/me').then((r) => r.data),
  changePassword: (current_password: string, new_password: string) =>
    http.post('/auth/me/password', { current_password, new_password }).then((r) => r.data),
}

export const usersApi = {
  list: (params: PageParams & { search?: string; only_active?: boolean } = {}) =>
    http.get<Page<User>>('/users', { params: cleanParams(params) }).then((r) => r.data),
  create: (data: UserCreatePayload) => http.post<User>('/users', data).then((r) => r.data),
  update: (id: string, data: UserUpdatePayload) => http.patch<User>(`/users/${id}`, data).then((r) => r.data),
}

export const clientsApi = {
  list: (filters: ClientFilters) =>
    http.get<Page<ClientListItem>>('/clients', { params: cleanParams(filters) }).then((r) => r.data),
  get: (id: string) => http.get<ClientDetail>(`/clients/${id}`).then((r) => r.data),
  create: (data: ClientPayload) => http.post<Client>('/clients', data).then((r) => r.data),
  update: (id: string, data: ClientPayload) => http.patch<Client>(`/clients/${id}`, data).then((r) => r.data),
  remove: (id: string) => http.delete(`/clients/${id}`),
  interactions: (id: string, params: PageParams = {}) =>
    http.get<Page<Interaction>>(`/clients/${id}/interactions`, { params }).then((r) => r.data),
  addInteraction: (id: string, data: InteractionPayload) =>
    http.post<Interaction>(`/clients/${id}/interactions`, data).then((r) => r.data),
  removeInteraction: (clientId: string, interactionId: string) =>
    http.delete(`/clients/${clientId}/interactions/${interactionId}`),
}

export const dealsApi = {
  list: (filters: DealFilters) =>
    http.get<Page<Deal>>('/deals', { params: cleanParams(filters) }).then((r) => r.data),
  board: (params: { owner_id?: string; search?: string; closed_days?: number } = {}) =>
    http.get<KanbanBoard>('/deals/board', { params: cleanParams(params) }).then((r) => r.data),
  get: (id: string) => http.get<Deal>(`/deals/${id}`).then((r) => r.data),
  create: (data: DealPayload) => http.post<Deal>('/deals', data).then((r) => r.data),
  update: (id: string, data: DealUpdatePayload) => http.patch<Deal>(`/deals/${id}`, data).then((r) => r.data),
  move: (id: string, data: DealMovePayload) => http.post<Deal>(`/deals/${id}/move`, data).then((r) => r.data),
  history: (id: string) => http.get<DealStageHistory[]>(`/deals/${id}/history`).then((r) => r.data),
  remove: (id: string) => http.delete(`/deals/${id}`),
}

export const paymentsApi = {
  list: (filters: PaymentFilters) =>
    http.get<Page<Payment>>('/payments', { params: cleanParams(filters) }).then((r) => r.data),
  summary: () => http.get<ReceivablesSummary>('/payments/summary').then((r) => r.data),
  create: (data: PaymentPayload) => http.post<Payment>('/payments', data).then((r) => r.data),
  createInstallments: (data: InstallmentsPayload) =>
    http.post<Payment[]>('/payments/installments', data).then((r) => r.data),
  markPaid: (id: string, data: { payment_date: string; method?: PaymentMethod | null; notes?: string | null }) =>
    http.post<Payment>(`/payments/${id}/pay`, data).then((r) => r.data),
  cancel: (id: string, reason: string) => http.post<Payment>(`/payments/${id}/cancel`, { reason }).then((r) => r.data),
}

export const dashboardApi = {
  get: (filters: DashboardFilters) =>
    http.get<Dashboard>('/dashboard', { params: cleanParams(filters) }).then((r) => r.data),
}

export const aiApi = {
  status: () => http.get<AIStatus>('/ai/status').then((r) => r.data),
  clientSummary: (clientId: string, force_refresh = false) =>
    http.post<ClientSummaryAI>(`/ai/clients/${clientId}/summary`, { force_refresh }).then((r) => r.data),
  scoreDeal: (dealId: string, force_refresh = false) =>
    http.post<LeadScore>(`/ai/deals/${dealId}/score`, { force_refresh }).then((r) => r.data),
  scoreBatch: () => http.post<{ scored: number; skipped: number }>('/ai/deals/score-batch', {}).then((r) => r.data),
  insights: (data: InsightsPayload) => http.post<InsightsResponse>('/ai/insights', data).then((r) => r.data),
}
