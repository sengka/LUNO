import { useQuery } from '@tanstack/react-query'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { UserAvatar } from '@/components/UserAvatar'
import { membersApi } from '@/features/projects/members-api'

const UNASSIGNED = 'atanmamis'

interface AssigneeSelectProps {
  id?: string
  projectId: number
  value: number | null
  onChange: (assigneeId: number | null) => void
  disabled?: boolean
  invalid?: boolean
}

// US-012: Atanan kişi yalnızca proje üyeleri arasından seçilir (sözleşme 5.6, FR-030)
export function AssigneeSelect({ id, projectId, value, onChange, disabled, invalid }: AssigneeSelectProps) {
  // ProjectMembers ile aynı anahtar: üye listesi bir kez yüklenir
  const membersQuery = useQuery({
    queryKey: ['projects', 'members', projectId],
    queryFn: () => membersApi.list(projectId),
    retry: false,
  })

  const placeholder = membersQuery.isPending
    ? 'Üyeler yükleniyor…'
    : membersQuery.isError
      ? 'Üyeler alınamadı'
      : 'Atanmamış'

  return (
    <Select
      value={value === null ? UNASSIGNED : String(value)}
      onValueChange={(next) => onChange(next === UNASSIGNED ? null : Number(next))}
      disabled={disabled || !membersQuery.isSuccess}
    >
      <SelectTrigger id={id} className="w-full" aria-invalid={invalid}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={UNASSIGNED}>Atanmamış</SelectItem>
        {membersQuery.data?.map((member) => (
          <SelectItem key={member.user.id} value={String(member.user.id)}>
            <UserAvatar user={member.user} className="size-5 text-[10px]" />
            {member.user.full_name}
            {member.technical_role && (
              <span className="text-xs text-muted-foreground">· {member.technical_role}</span>
            )}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
