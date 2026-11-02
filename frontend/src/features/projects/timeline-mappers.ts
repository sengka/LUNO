import type { CalendarEvent, GanttItem } from './timeline-types'

const STATUS_COLORS = {
  TODO: '#64748b', IN_PROGRESS: '#b45309', REVIEW_TESTING: '#7c3aed', DONE: '#047857',
}

// Date-only arithmetic avoids daylight-saving and UTC/local conversion shifts.
export function addDays(value: string, days: number) {
  const date = new Date(`${value}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export function toCalendarEvent(event: CalendarEvent) {
  const start = event.start_date ?? event.due_date
  if (!start) return null
  return {
    id: String(event.task_id),
    title: event.title,
    start,
    end: addDays(event.due_date ?? start, 1),
    allDay: true,
    url: `/gorevler/${event.task_id}`,
    className: `task-${event.status.toLowerCase()}`,
    color: STATUS_COLORS[event.status],
    contrastColor: '#ffffff',
    extendedProps: { status: event.status, assignee: event.assignee },
  }
}

export function toGanttTask(item: GanttItem) {
  return {
    id: String(item.task_id),
    name: item.title,
    start: item.start_date,
    end: item.due_date,
    progress: item.progress_percent,
    custom_class: `task-${item.status.toLowerCase()}`,
    // Dependency arrows belong to Sprint 9 (#194).
  }
}
