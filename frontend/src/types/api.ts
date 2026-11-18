// Tipos espelhando os schemas Pydantic do backend (app/schemas).
// Valores monetários chegam como number (serializados assim pela API).

export type UUID = string

export type UserRole = 'admin' | 'gestor' | 'vendedor'
export type LeadSource =
  | 'site'
  | 'indicacao'
  | 'instagram'
  | 'facebook'
  | 'linkedin'
  | 'whatsapp'
  | 'google_ads'
  | 'evento'
  | 'prospeccao_ativa'
  | 'outro'
export type ClientStatus = 'lead' | 'prospect' | 'cliente' | 'inativo' | 'perdido'
export type InteractionType = 'ligacao' | 'email' | 'reuniao' | 'whatsapp' | 'visita' | 'nota' | 'outro'
export type InteractionDirection = 'entrada' | 'saida' | 'interna'
export type DealStage =
  | 'prospeccao'
  | 'qualificacao'
  | 'proposta'
  | 'negociacao'
  | 'fechado_ganho'
  | 'fechado_perdido'
export type PaymentStatus = 'pendente' | 'pago' | 'atrasado' | 'cancelado'
export type PaymentMethod =
  | 'pix'
  | 'boleto'
  | 'cartao_credito'
  | 'cartao_debito'
  | 'transferencia'
  | 'dinheiro'
  | 'outro'

// ---------------------------------------------------------------- genéricos
export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface ApiErrorBody {
  code: string
  message: string
  details?: { field?: string; message: string; type?: string }[]
}

export interface PageParams {
  limit?: number
  offset?: number
}

// ---------------------------------------------------------------- usuários / auth
export interface UserSummary {
  id: UUID
  name: string
  email: string
  role: UserRole
}

export interface User extends UserSummary {
  is_active: boolean
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface LoginResponse extends TokenPair {
  user: User
}

export interface UserCreatePayload {
  name: string
  email: string
  password: string
  role: UserRole
}

export interface UserUpdatePayload {
  name?: string
  email?: string
  role?: UserRole
  is_active?: boolean
}

// ---------------------------------------------------------------- clientes
export interface ClientSummary {
  id: UUID
  name: string
  company: string | null
  email: string | null
  status: ClientStatus
}

export interface ClientListItem extends ClientSummary {
  phone: string | null
  whatsapp: string | null
  lead_source: LeadSource
  tags: string[]
  owner: UserSummary | null
  last_interaction_at: string | null
  created_at: string
}

export interface Client extends ClientListItem {
  job_title: string | null
  document: string | null
  notes: string | null
  custom_fields: Record<string, unknown>
  updated_at: string
}

export interface ClientStats {
  open_deals: number
  won_deals: number
  lost_deals: number
  pipeline_value: number
  total_won_value: number
  total_paid: number
  outstanding_amount: number
  overdue_amount: number
}

export interface DealSummary {
  id: UUID
  title: string
  stage: DealStage
  estimated_value: number
  probability: number
  expected_close_date: string | null
  client_id: UUID
}

export interface ClientDetail extends Client {
  stats: ClientStats
  recent_interactions: Interaction[]
  deals: DealSummary[]
}

export interface ClientPayload {
  name?: string
  company?: string | null
  job_title?: string | null
  email?: string | null
  phone?: string | null
  whatsapp?: string | null
  document?: string | null
  lead_source?: LeadSource
  status?: ClientStatus
  notes?: string | null
  tags?: string[]
  owner_id?: UUID | null
}

export interface ClientFilters extends PageParams {
  search?: string
  status?: ClientStatus[]
  lead_source?: LeadSource[]
  owner_id?: UUID
  tag?: string
  no_contact_days?: number
  order_by?: 'name' | 'created_at' | 'last_interaction_at' | 'status'
  order_dir?: 'asc' | 'desc'
}

// ---------------------------------------------------------------- interações
export interface Interaction {
  id: UUID
  client_id: UUID
  deal_id: UUID | null
  user: UserSummary | null
  type: InteractionType
  direction: InteractionDirection
  subject: string | null
  content: string
  occurred_at: string
  duration_minutes: number | null
  sentiment: number | null
  created_at: string
  updated_at: string
}

export interface InteractionPayload {
  type: InteractionType
  direction?: InteractionDirection
  subject?: string | null
  content: string
  occurred_at?: string | null
  duration_minutes?: number | null
  deal_id?: UUID | null
}

// ---------------------------------------------------------------- negociações
export interface Deal {
  id: UUID
  client_id: UUID
  client: ClientSummary
  owner: UserSummary | null
  title: string
  description: string | null
  estimated_value: number
  currency: string
  probability: number
  stage: DealStage
  stage_label: string
  position: number
  expected_close_date: string | null
  closed_at: string | null
  lost_reason: string | null
  stage_changed_at: string
  ai_score: number | null
  ai_scored_at: string | null
  weighted_value: number
  is_overdue: boolean
  created_at: string
  updated_at: string
}

export interface DealPayload {
  client_id: UUID
  title: string
  description?: string | null
  estimated_value: number
  probability?: number | null
  stage?: DealStage
  expected_close_date?: string | null
  owner_id?: UUID | null
  lost_reason?: string | null
}

export type DealUpdatePayload = Partial<Omit<DealPayload, 'stage' | 'lost_reason'>>

export interface DealMovePayload {
  stage: DealStage
  position?: number | null
  probability?: number | null
  lost_reason?: string | null
  note?: string | null
}

export interface DealStageHistory {
  id: UUID
  deal_id: UUID
  from_stage: DealStage | null
  to_stage: DealStage
  changed_by: UserSummary | null
  changed_at: string
  estimated_value_snapshot: number
  probability_snapshot: number
  seconds_in_previous_stage: number | null
  note: string | null
}

export interface KanbanColumn {
  stage: DealStage
  label: string
  count: number
  total_value: number
  weighted_value: number
  deals: Deal[]
}

export interface KanbanBoard {
  columns: KanbanColumn[]
  total_open_value: number
  total_weighted_value: number
}

export interface DealFilters extends PageParams {
  search?: string
  stage?: DealStage[]
  client_id?: UUID
  owner_id?: UUID
  only_open?: boolean
  order_by?: 'created_at' | 'estimated_value' | 'expected_close_date' | 'probability' | 'ai_score'
  order_dir?: 'asc' | 'desc'
}

// ---------------------------------------------------------------- pagamentos
export interface Payment {
  id: UUID
  deal_id: UUID
  deal: DealSummary
  client: ClientSummary | null
  invoice_number: string
  description: string | null
  amount: number
  method: PaymentMethod
  status: PaymentStatus
  status_label: string
  due_date: string
  payment_date: string | null
  installment_number: number
  installment_total: number
  external_reference: string | null
  notes: string | null
  days_overdue: number
  created_at: string
  updated_at: string
}

export interface PaymentPayload {
  deal_id: UUID
  description?: string | null
  amount: number
  method: PaymentMethod
  due_date: string
  status?: 'pendente' | 'pago'
  payment_date?: string | null
  notes?: string | null
}

export interface InstallmentsPayload {
  deal_id: UUID
  total_amount: number
  installments: number
  first_due_date: string
  method: PaymentMethod
  description?: string | null
}

export interface PaymentFilters extends PageParams {
  status?: PaymentStatus[]
  method?: PaymentMethod[]
  deal_id?: UUID
  client_id?: UUID
  overdue_only?: boolean
  order_by?: 'due_date' | 'amount' | 'payment_date' | 'created_at'
  order_dir?: 'asc' | 'desc'
}

export interface ReceivablesSummary {
  total_pending: number
  total_overdue: number
  total_paid_period: number
  count_overdue: number
  generated_at: string
}

// ---------------------------------------------------------------- dashboard
export interface KPISummary {
  total_revenue: number
  average_ticket: number
  conversion_rate: number
  won_deals_count: number
  lost_deals_count: number
  open_deals_count: number
  open_pipeline_value: number
  weighted_pipeline_value: number
  receivables: number
  overdue_amount: number
  overdue_count: number
  delinquency_rate: number
  new_clients_count: number
}

export interface KPIComparison {
  total_revenue_pct: number | null
  conversion_rate_pct: number | null
  average_ticket_pct: number | null
  new_clients_pct: number | null
}

export interface FunnelStageMetric {
  stage: DealStage
  label: string
  count: number
  total_value: number
  weighted_value: number
  avg_days_in_stage: number | null
  conversion_from_previous: number | null
}

export interface RevenuePoint {
  period: string
  received: number
  expected: number
  overdue: number
}

export interface LeadSourceMetric {
  lead_source: LeadSource
  label: string
  clients_count: number
  won_deals_count: number
  won_value: number
  conversion_rate: number
}

export interface Dashboard {
  period_start: string
  period_end: string
  summary: KPISummary
  comparison: KPIComparison
  funnel: FunnelStageMetric[]
  revenue_series: RevenuePoint[]
  lead_sources: LeadSourceMetric[]
  top_clients: { client: ClientSummary; total_paid: number; deals_won: number }[]
  top_overdue: {
    payment_id: UUID
    invoice_number: string
    client: ClientSummary
    amount: number
    due_date: string
    days_overdue: number
  }[]
  generated_at: string
}

export interface DashboardFilters {
  date_from?: string
  date_to?: string
  owner_id?: UUID
}

// ---------------------------------------------------------------- IA
export interface AIMeta {
  insight_id: UUID | null
  provider: string
  model: string
  prompt_version: string
  cached: boolean
  generated_at: string
}

export interface AIStatus {
  enabled: boolean
  provider: string
  model: string
  features: string[]
}

export interface ClientSummaryAI {
  client_id: UUID
  summary: string
  key_points: string[]
  sentiment: 'positivo' | 'neutro' | 'negativo' | 'indefinido'
  risks: string[]
  next_best_actions: string[]
  interactions_analyzed: number
  meta: AIMeta
}

export interface LeadScoreFactor {
  feature: string
  description: string
  value: unknown
  impact: number
}

export interface LeadScore {
  deal_id: UUID
  score: number
  current_probability: number
  confidence: 'baixa' | 'media' | 'alta'
  factors: LeadScoreFactor[]
  recommendation: string | null
  meta: AIMeta
}

export type InsightCategory = 'funil' | 'inadimplencia' | 'receita' | 'origem_leads'

export interface Insight {
  category: InsightCategory
  title: string
  description: string
  severity: 'info' | 'atencao' | 'critico'
  metric: string | null
  value: number | null
  recommendation: string | null
  related_entity_ids: UUID[]
}

export interface InsightsResponse {
  period_start: string
  period_end: string
  headline: string
  insights: Insight[]
  meta: AIMeta
}

export interface InsightsPayload {
  date_from?: string
  date_to?: string
  focus?: InsightCategory[]
  owner_id?: UUID
  force_refresh?: boolean
}
