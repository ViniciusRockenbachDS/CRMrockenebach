import type {
  ClientStatus,
  DealStage,
  InteractionDirection,
  InteractionType,
  LeadSource,
  PaymentMethod,
  PaymentStatus,
  UserRole,
} from '@/types/api'

// Rótulos espelham app/models/enums.py (também disponíveis em GET /api/v1/meta/enums).

export const DEAL_STAGES: { value: DealStage; label: string; color: string; dot: string }[] = [
  { value: 'prospeccao', label: 'Prospecção', color: 'bg-slate-100 text-slate-700', dot: 'bg-slate-400' },
  { value: 'qualificacao', label: 'Qualificação', color: 'bg-sky-100 text-sky-700', dot: 'bg-sky-500' },
  { value: 'proposta', label: 'Proposta', color: 'bg-violet-100 text-violet-700', dot: 'bg-violet-500' },
  { value: 'negociacao', label: 'Negociação', color: 'bg-amber-100 text-amber-800', dot: 'bg-amber-500' },
  { value: 'fechado_ganho', label: 'Fechado Ganho', color: 'bg-emerald-100 text-emerald-700', dot: 'bg-emerald-500' },
  { value: 'fechado_perdido', label: 'Fechado Perdido', color: 'bg-rose-100 text-rose-700', dot: 'bg-rose-500' },
]
export const STAGE_MAP = Object.fromEntries(DEAL_STAGES.map((s) => [s.value, s])) as Record<
  DealStage,
  (typeof DEAL_STAGES)[number]
>
export const DEFAULT_PROBABILITY: Record<DealStage, number> = {
  prospeccao: 10,
  qualificacao: 25,
  proposta: 50,
  negociacao: 75,
  fechado_ganho: 100,
  fechado_perdido: 0,
}

export const CLIENT_STATUS: Record<ClientStatus, { label: string; color: string }> = {
  lead: { label: 'Lead', color: 'bg-slate-100 text-slate-700' },
  prospect: { label: 'Prospect', color: 'bg-sky-100 text-sky-700' },
  cliente: { label: 'Cliente', color: 'bg-emerald-100 text-emerald-700' },
  inativo: { label: 'Inativo', color: 'bg-zinc-200 text-zinc-600' },
  perdido: { label: 'Perdido', color: 'bg-rose-100 text-rose-700' },
}

export const LEAD_SOURCES: Record<LeadSource, string> = {
  site: 'Site',
  indicacao: 'Indicação',
  instagram: 'Instagram',
  facebook: 'Facebook',
  linkedin: 'LinkedIn',
  whatsapp: 'WhatsApp',
  google_ads: 'Google Ads',
  evento: 'Evento',
  prospeccao_ativa: 'Prospecção ativa',
  outro: 'Outro',
}

export const INTERACTION_TYPES: Record<InteractionType, string> = {
  ligacao: 'Ligação',
  email: 'E-mail',
  reuniao: 'Reunião',
  whatsapp: 'WhatsApp',
  visita: 'Visita',
  nota: 'Nota',
  outro: 'Outro',
}

export const INTERACTION_DIRECTIONS: Record<InteractionDirection, string> = {
  saida: 'Saída (empresa → cliente)',
  entrada: 'Entrada (cliente → empresa)',
  interna: 'Anotação interna',
}

export const PAYMENT_STATUS: Record<PaymentStatus, { label: string; color: string }> = {
  pendente: { label: 'Pendente', color: 'bg-amber-100 text-amber-800' },
  pago: { label: 'Pago', color: 'bg-emerald-100 text-emerald-700' },
  atrasado: { label: 'Atrasado', color: 'bg-rose-100 text-rose-700' },
  cancelado: { label: 'Cancelado', color: 'bg-zinc-200 text-zinc-600' },
}

export const PAYMENT_METHODS: Record<PaymentMethod, string> = {
  pix: 'Pix',
  boleto: 'Boleto',
  cartao_credito: 'Cartão de crédito',
  cartao_debito: 'Cartão de débito',
  transferencia: 'Transferência',
  dinheiro: 'Dinheiro',
  outro: 'Outro',
}

export const USER_ROLES: Record<UserRole, string> = {
  admin: 'Administrador',
  gestor: 'Gestor',
  vendedor: 'Vendedor',
}

/** Converte um Record em opções para <Select>. */
export const toOptions = <K extends string>(record: Record<K, string | { label: string }>) =>
  (Object.entries(record) as [K, string | { label: string }][]).map(([value, item]) => ({
    value,
    label: typeof item === 'string' ? item : item.label,
  }))
