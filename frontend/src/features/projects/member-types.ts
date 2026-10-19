import type { Role } from '@/types/api'

export interface ProjectMember {
  user: {
    id: number
    full_name: string
    avatar_url: string | null
  }
  email: string
  system_role: Role
  technical_role: string | null
  capacity_points: number | null
  joined_at: string
}

export interface AddMemberInput {
  email: string
  technical_role?: string
}

export interface ProjectInvite {
  invite_url: string
  expires_at: string
}