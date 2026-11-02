import type { ActiveTaskStatus } from '@/features/tasks/types'

export interface CalendarEvent {
  task_id: number
  title: string
  start_date: string | null
  due_date: string | null
  status: ActiveTaskStatus
  assignee: { id: number; full_name: string; avatar_url: string | null } | null
}

export interface CalendarResponse { events: CalendarEvent[] }

export interface GanttItem {
  task_id: number
  title: string
  start_date: string
  due_date: string
  progress_percent: number
  status: ActiveTaskStatus
  parent_id: number | null
  depends_on: number[]
}

export interface GanttResponse {
  project: { start_date: string; end_date: string }
  items: GanttItem[]
}
