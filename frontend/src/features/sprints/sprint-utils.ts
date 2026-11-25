import type { Sprint } from './types'

export type SprintPhase = 'active' | 'done' | 'planned'

// Mockup'taki rozetler: Aktif / Tamamlandı / Planlandı
export function sprintPhase(sprint: Sprint, today = new Date().toISOString().slice(0, 10)): SprintPhase {
  if (sprint.is_active) return 'active'
  return sprint.end_date < today ? 'done' : 'planned'
}

export const PHASE_LABELS: Record<SprintPhase, string> = {
  active: 'Aktif',
  done: 'Tamamlandı',
  planned: 'Planlandı',
}

export const PHASE_STYLES: Record<SprintPhase, string> = {
  active: 'bg-secondary text-secondary-foreground',
  done: 'bg-emerald-50 text-emerald-700',
  planned: 'bg-amber-50 text-amber-700',
}

const dayMonth = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'short' })

// "5 – 11 Eki" / "28 Eyl – 4 Eki"
export function formatSprintRange(start: string, end: string) {
  const s = new Date(`${start}T00:00:00`)
  const e = new Date(`${end}T00:00:00`)
  if (s.getMonth() === e.getMonth() && s.getFullYear() === e.getFullYear()) {
    return `${s.getDate()} – ${dayMonth.format(e)}`
  }
  return `${dayMonth.format(s)} – ${dayMonth.format(e)}`
}

export function formatPercent(value: number) {
  return value.toLocaleString('tr-TR', { maximumFractionDigits: 1 })
}
