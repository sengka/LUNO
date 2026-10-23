export type TaskStatus = 'ONAY_BEKLIYOR' | 'REDDEDILDI' | 'TODO' | 'IN_PROGRESS' | 'REVIEW_TESTING' | 'DONE'
type Level = 'DUSUK' | 'ORTA' | 'YUKSEK'
interface UserSummary {
  id: number
  full_name: string
  avatar_url: string | null
}

export interface Task {
  id: number
  project_id: number
  parent_id: number | null
  title: string
  description: string | null
  status: TaskStatus
  priority: Level | null
  story_points: 1 | 2 | 3 | 5 | 8 | 13 | null
  start_date: string | null
  due_date: string | null
  assignee: UserSummary | null
  created_by: UserSummary | null
  sprint_id: number | null
  labels: { id: number; name: string; color: string }[]
  subtask_count: number
  subtask_done_count: number
  depends_on: number[]
  risk_level: Level | null
  comment_count: number
  file_count: number
  created_at: string
  updated_at: string
}

// #156: diğer düzenlenebilir alanlar sonraki görevlere bırakılır.
export interface UpdateTaskInput {
  title?: string
  description?: string | null
  start_date?: string | null
  due_date?: string | null
}
