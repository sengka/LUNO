import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router'
import {
  ChevronDownIcon,
  FolderIcon,
  LayoutGridIcon,
  LogOutIcon,
  MenuIcon,
  UsersIcon,
  type LucideIcon,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Logo } from '@/components/Logo'
import { UserAvatar } from '@/components/UserAvatar'
import { useAuth } from '@/features/auth/auth-context'
import { cn } from '@/lib/utils'
import { ROLE_LABELS, type User } from '@/types/api'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  adminOnly?: boolean
}

// Mockup: docs/tasarim/02-dashboard.png. Raporlar menüsü kendi sprintinde eklenecek.
const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Kontrol Paneli', icon: LayoutGridIcon },
  { to: '/projeler', label: 'Projeler', icon: FolderIcon },
  // US-004: Ekip üyesi bu sayfayı menüde görmez
  { to: '/kullanicilar', label: 'Kullanıcılar', icon: UsersIcon, adminOnly: true },
]

function SidebarContent({ user, isAdmin, onNavigate }: { user: User; isAdmin: boolean; onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col gap-8 p-4">
      <Logo className="px-2 pt-2" />

      <nav className="grid gap-1" aria-label="Ana menü">
        {NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin).map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-secondary text-brand'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground',
              )
            }
          >
            <Icon className="size-5" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto flex items-center gap-3 rounded-xl border bg-card p-3">
        <UserAvatar user={user} />
        <div className="grid min-w-0">
          <span className="truncate text-sm font-semibold">{user.full_name}</span>
          <span className="truncate text-xs text-muted-foreground">{ROLE_LABELS[user.role]}</span>
        </div>
      </div>
    </div>
  )
}

export function AppLayout() {
  const { user, isAdmin, signOut } = useAuth()
  const navigate = useNavigate()
  const [signingOut, setSigningOut] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // US-003: token silinir, giriş sayfasına dönülür
  const handleSignOut = async () => {
    setSigningOut(true)
    await signOut()
    navigate('/giris', { replace: true })
  }

  if (!user) return null

  return (
    <div className="min-h-svh lg:pl-64">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r bg-background lg:block">
        <SidebarContent user={user} isAdmin={isAdmin} />
      </aside>

      <header className="sticky top-0 z-10 flex h-16 items-center gap-3 border-b bg-background/90 px-4 backdrop-blur sm:px-6">
        {/* Mobilde yan menü açılır panel olarak gelir */}
        <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Menüyü aç">
              <MenuIcon />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72 p-0">
            <SheetTitle className="sr-only">Menü</SheetTitle>
            <SheetDescription className="sr-only">Sayfalar arasında gezin</SheetDescription>
            <SidebarContent user={user} isAdmin={isAdmin} onNavigate={() => setMobileMenuOpen(false)} />
          </SheetContent>
        </Sheet>

        <Logo className="lg:hidden" />

        <div className="ml-auto flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-auto gap-2 px-2 py-1.5">
                <UserAvatar user={user} className="size-8" />
                <span className="hidden text-sm font-semibold sm:inline">{user.full_name.split(' ')[0]}</span>
                <ChevronDownIcon className="hidden size-4 text-muted-foreground sm:block" />
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

          <div className="hidden h-8 w-px bg-border sm:block" />

          {/* Mockup'taki gibi çıkış üst barda da görünür */}
          <Button
            variant="ghost"
            className="hidden text-muted-foreground sm:inline-flex"
            disabled={signingOut}
            onClick={handleSignOut}
          >
            <LogOutIcon />
            Çıkış yap
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}
