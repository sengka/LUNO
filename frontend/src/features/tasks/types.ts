export type TaskStatus = 'ONAY_BEKLIYOR' | 'REDDEDILDI' | 'TODO' | 'IN_PROGRESS' | 'REVIEW_TESTING' | 'DONE'
type Level = 'DUSUK' | 'ORTA' | 'YUKSEK'
export type TaskPriority = Level
export const PRIORITY_LABELS: Record<TaskPriority, string> = {
  DUSUK: 'Düşük', ORTA: 'Orta', YUKSEK: 'Yüksek',
}
export const STORY_POINT_OPTIONS = [1, 2, 3, 5, 8, 13] as const
export type StoryPoints = (typeof STORY_POINT_OPTIONS)[number]
export interface Label {
  id: number
  name: string
  color: string
}
export interface CreateLabelInput {
  name: string
  color?: string
}
// 6.10: yalnızca zorunlu başlığı gönder; diğer alanlar ve parent_id sunucuya bırakılır.
export interface CreateSubtaskInput {
  title: string
}
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
  priority: TaskPriority | null
  story_points: StoryPoints | null
  start_date: string | null
  due_date: string | null
  assignee: UserSummary | null
  created_by: UserSummary | null
  sprint_id: number | null
  labels: Label[]
  subtask_count: number
  subtask_done_count: number
  depends_on: number[]
  risk_level: Level | null
  comment_count: number
  file_count: number
  created_at: string
  updated_at: string
}

// Sprint düzenlemesi sonraki görevlere bırakılır.
export interface UpdateTaskInput {
  title?: string
  description?: string | null
  start_date?: string | null
  due_date?: string | null
  // İsteklerde null ile temizleme sözleşmede tanımlı değil; değişmeyen alanı gönderme.
  priority?: TaskPriority
  story_points?: StoryPoints
  label_ids?: number[]
}


// Kanban ve durum seçiminde kullanılan aktif durumlar (sözleşme 1.3, 6.5)
export type ActiveTaskStatus = 'TODO' | 'IN_PROGRESS' | 'REVIEW_TESTING' | 'DONE'
export const BOARD_STATUSES: ActiveTaskStatus[] = ['TODO', 'IN_PROGRESS', 'REVIEW_TESTING', 'DONE']
export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  TODO: 'To Do',
  IN_PROGRESS: 'In Progress',
  REVIEW_TESTING: 'Review & Testing',
  DONE: 'Done',
  ONAY_BEKLIYOR: 'Onay bekliyor',
  REDDEDILDI: 'Reddedildi',
}

// 6.2: Görev oluşturma; isteğe bağlı öncelik ve efor (US-032).
export interface CreateTaskInput {
  title: string
  description: string | null
  start_date: string | null
  due_date: string | null
  assignee_id: number | null
  priority?: TaskPriority
  story_points?: StoryPoints
}

// 7.1: Kanban panosu
export interface BoardColumn {
  status: ActiveTaskStatus
  tasks: Task[]
}
export interface BoardResponse {
  columns: BoardColumn[]
}

