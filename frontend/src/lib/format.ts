const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const compactCurrency = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  notation: 'compact',
  maximumFractionDigits: 1,
})

export const formatCurrency = (value: number | null | undefined) => currency.format(value ?? 0)
export const formatCompactCurrency = (value: number | null | undefined) => compactCurrency.format(value ?? 0)

export const formatPercent = (ratio: number | null | undefined, digits = 1) =>
  `${((ratio ?? 0) * 100).toLocaleString('pt-BR', { maximumFractionDigits: digits })}%`

/** Datas "YYYY-MM-DD" são tratadas como data local (sem deslocamento de fuso). */
function parseDate(value: string): Date {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value)
}

export const formatDate = (value: string | null | undefined) =>
  value ? parseDate(value).toLocaleDateString('pt-BR') : '—'

export const formatDateTime = (value: string | null | undefined) =>
  value
    ? parseDate(value).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
    : '—'

export const formatMonth = (value: string) =>
  parseDate(value).toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' }).replace('.', '')

export function formatRelative(value: string | null | undefined): string {
  if (!value) return 'nunca'
  const days = Math.floor((Date.now() - parseDate(value).getTime()) / 86_400_000)
  if (days <= 0) return 'hoje'
  if (days === 1) return 'ontem'
  if (days < 30) return `há ${days} dias`
  const months = Math.floor(days / 30)
  return months === 1 ? 'há 1 mês' : `há ${months} meses`
}

/** +5547999998888 → (47) 99999-8888 */
export function formatPhone(value: string | null | undefined): string {
  if (!value) return '—'
  const digits = value.replace(/\D/g, '').replace(/^55/, '')
  if (digits.length === 11) return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`
  if (digits.length === 10) return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`
  return value
}

export const whatsappLink = (value: string) => `https://wa.me/${value.replace(/\D/g, '')}`

export const todayISO = () => {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60_000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

export function initials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')
}
