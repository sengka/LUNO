import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router'
import { LogOutIcon } from 'lucide-react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Logo } from '@/components/Logo'
import { useAuth } from '@/features/auth/auth-context'
import { cn } from '@/lib/utils'
import { ROLE_LABELS } from '@/types/api'

function initials(fullName: string) {
  return fullName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toLocaleUpperCase('tr'))
    .join('')
}

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    'rounded-md px-3 py-2 text-sm font-medium transition-colors',
    isActive ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground hover:text-foreground',
  )

export function AppLayout() {
  const { user, isAdmin, signOut } = useAuth()
  const navigate = useNavigate()
  const [signingOut, setSigningOut] = useState(false)

  // US-003: token silinir, giriş sayfasına dönülür
  const handleSignOut = async () => {
    setSigningOut(true)
    await signOut()
    navigate('/giris', { replace: true })
  }

  if (!user) return null

  return (
    <div className="min-h-svh">
      <header className="sticky top-0 z-10 border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Logo />

          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={navLinkClass}>
              Ana sayfa
            </NavLink>
            {/* US-004: Ekip üyesi bu sayfayı menüde görmez */}
            {isAdmin && (
              <NavLink to="/kullanicilar" className={navLinkClass}>
                Kullanıcılar
              </NavLink>
            )}
          </nav>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="ml-auto h-auto gap-2 px-2 py-1.5">
                <Avatar className="size-8">
                  {user.avatar_url && <AvatarImage src={user.avatar_url} alt="" />}
                  <AvatarFallback className="bg-secondary text-secondary-foreground">
                    {initials(user.full_name)}
                  </AvatarFallback>
                </Avatar>
                <span className="hidden text-sm font-medium sm:inline">{user.full_name}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="grid gap-0.5">
                <span className="truncate">{user.full_name}</span>
                <span className="truncate text-xs font-normal text-muted-foreground">{user.email}</span>
                <span className="text-xs font-normal text-muted-foreground">{ROLE_LABELS[user.role]}</span>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive" disabled={signingOut} onSelect={handleSignOut}>
                <LogOutIcon />
                Çıkış yap
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}
