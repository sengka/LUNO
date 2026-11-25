// Sözleşme 2. bölüm: Sprint nesnesi
export interface Sprint {
  id: number
  project_id: number
  name: string
  goal: string | null
  start_date: string
  end_date: string
  capacity_points: number | null
  total_points: number
  done_points: number
  progress_percent: number
  is_active: boolean
}

// Sözleşme 11.3: görev eklenince kapasite aşıldıysa uyarı bayrağı da döner
export interface SprintTasksAddResponse extends Sprint {
  capacity_warning: boolean
}

export interface CreateSprintInput {
  name: string
  goal: string | null
  start_date: string
  end_date: string
  capacity_points: number | null
}
