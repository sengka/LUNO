export interface Project {
  id: number
  name: string
  description: string | null
  start_date: string | null
  end_date: string | null
  progress_percent: number
  member_count: number
  created_by: {
    id: number
    full_name: string
    avatar_url: string | null
  } | null
  created_at: string
  updated_at: string
}

export interface UpdateProjectInput {
  name?: string
  description?: string | null
  start_date?: string | null
  end_date?: string | null
}