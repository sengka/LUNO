import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'

interface AvatarUser {
  full_name: string
  avatar_url: string | null
}

function initials(fullName: string) {
  return fullName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toLocaleUpperCase('tr'))
    .join('')
}

export function UserAvatar({ user, className }: { user: AvatarUser; className?: string }) {
  return (
    <Avatar className={cn('size-9', className)}>
      {user.avatar_url && <AvatarImage src={user.avatar_url} alt="" />}
      <AvatarFallback className="bg-secondary font-medium text-secondary-foreground">
        {initials(user.full_name)}
      </AvatarFallback>
    </Avatar>
  )
}
