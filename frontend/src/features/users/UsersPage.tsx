import { useState, type ReactNode } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeftIcon, ChevronRightIcon, Loader2Icon, SearchIcon } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useAuth } from '@/features/auth/auth-context'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { ApiError } from '@/lib/api'
import { ROLE_LABELS, type Role, type User } from '@/types/api'
import { usersApi } from './api'

const PAGE_SIZE = 10
const ROLES: Role[] = ['YONETICI', 'EKIP_UYESI']

const dateFormatter = new Intl.DateTimeFormat('tr-TR', { dateStyle: 'medium' })

// US-004: Yönetici, kullanıcıların sistem rolünü değiştirir (FR-010, FR-011)
export function UsersPage() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const debouncedSearch = useDebouncedValue(search.trim())

  const usersQuery = useQuery({
    queryKey: ['users', { search: debouncedSearch, page }],
    queryFn: () => usersApi.list({ search: debouncedSearch, page, limit: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  })

  const data = usersQuery.data
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1">
          <h1 className="text-2xl font-semibold text-brand">Kullanıcılar</h1>
          <p className="text-sm text-muted-foreground">
            Sistemdeki kullanıcıları görüntüle ve rollerini yönet.
          </p>
        </div>

        <div className="relative w-full sm:w-72">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Ad veya e-posta ara"
            className="pl-9"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
            aria-label="Kullanıcı ara"
          />
        </div>
      </div>

      <Card className="py-0">
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Ad soyad</TableHead>
                <TableHead>E-posta</TableHead>
                <TableHead className="hidden md:table-cell">Kayıt tarihi</TableHead>
                <TableHead className="w-48 pr-6">Rol</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {usersQuery.isPending ? (
                <MessageRow>
                  <Loader2Icon className="mx-auto size-5 animate-spin text-primary" />
                </MessageRow>
              ) : usersQuery.isError ? (
                <MessageRow>
                  <span className="text-destructive">
                    {usersQuery.error instanceof ApiError
                      ? usersQuery.error.message
                      : 'Kullanıcılar yüklenemedi.'}
                  </span>
                </MessageRow>
              ) : data && data.items.length === 0 ? (
                <MessageRow>
                  {debouncedSearch ? `"${debouncedSearch}" ile eşleşen kullanıcı yok.` : 'Henüz kullanıcı yok.'}
                </MessageRow>
              ) : (
                data?.items.map((user) => <UserRow key={user.id} user={user} />)
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {data && data.total > 0 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>Toplam {data.total} kullanıcı</span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              aria-label="Önceki sayfa"
            >
              <ChevronLeftIcon />
            </Button>
            <span>
              {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="icon"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              aria-label="Sonraki sayfa"
            >
              <ChevronRightIcon />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function MessageRow({ children }: { children: ReactNode }) {
  return (
    <TableRow>
      <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
        {children}
      </TableCell>
    </TableRow>
  )
}

function UserRow({ user }: { user: User }) {
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const isSelf = currentUser?.id === user.id

  const updateRole = useMutation({
    mutationFn: (role: Role) => usersApi.updateRole(user.id, role),
    onSuccess: (updated) => {
      toast.success(`${updated.full_name} artık ${ROLE_LABELS[updated.role]}.`)
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (error) => {
      toast.error(error instanceof ApiError ? error.message : 'Rol güncellenemedi.')
    },
  })

  return (
    <TableRow>
      <TableCell className="pl-6 font-medium">
        {user.full_name}
        {isSelf && (
          <Badge variant="secondary" className="ml-2">
            Sen
          </Badge>
        )}
      </TableCell>
      <TableCell className="text-muted-foreground">{user.email}</TableCell>
      <TableCell className="hidden text-muted-foreground md:table-cell">
        {dateFormatter.format(new Date(user.created_at))}
      </TableCell>
      <TableCell className="pr-6">
        {/* Kendi rolünü değiştirmek yasak (400 CANNOT_CHANGE_OWN_ROLE) */}
        <Select
          value={user.role}
          onValueChange={(role) => updateRole.mutate(role as Role)}
          disabled={isSelf || updateRole.isPending}
        >
          <SelectTrigger className="w-full" aria-label={`${user.full_name} rolü`}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ROLES.map((role) => (
              <SelectItem key={role} value={role}>
                {ROLE_LABELS[role]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </TableCell>
    </TableRow>
  )
}
