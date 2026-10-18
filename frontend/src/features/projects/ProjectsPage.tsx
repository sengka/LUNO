import { useState } from 'react'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api'
import { projectsApi } from './api'

export function ProjectsPage() {
  const [page, setPage] = useState(1)

  const projectsQuery = useQuery({
    queryKey: ['projects', 'list', page],
    queryFn: () => projectsApi.list(page),
    retry: false,
  })

  return (
    <div className="grid gap-6">
      <header>
        <h1 className="text-2xl font-semibold">Projelerim</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Üyesi olduğun projeleri görüntüle.
        </p>
      </header>

      {projectsQuery.isPending ? (
        <p role="status">Projeler yükleniyor…</p>
      ) : projectsQuery.isError ? (
        <div className="grid gap-3">
          <Alert variant="destructive" role="alert">
            <AlertDescription>
              {projectsQuery.error instanceof ApiError
                ? projectsQuery.error.message
                : 'Projeler alınamadı.'}
            </AlertDescription>
          </Alert>

          <Button
            variant="outline"
            className="justify-self-start"
            disabled={projectsQuery.isFetching}
            onClick={() => void projectsQuery.refetch()}
          >
            Tekrar dene
          </Button>
        </div>
      ) : (
        <>
          {projectsQuery.data.items.length === 0 ? (
            <p className="rounded-xl border bg-card p-6 text-muted-foreground">
              Bu sayfada gösterilecek proje yok.
            </p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {projectsQuery.data.items.map((project) => (
                <Link
                  key={project.id}
                  to={`/projeler/${project.id}`}
                  className="grid gap-3 rounded-xl border bg-card p-5 transition-colors hover:border-primary focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <h2 className="break-words text-lg font-semibold">
                    {project.name}
                  </h2>

                  <p className="line-clamp-3 break-words text-sm text-muted-foreground">
                    {project.description || 'Açıklama eklenmemiş.'}
                  </p>

                  <p className="text-sm text-muted-foreground">
                    {project.member_count} üye
                  </p>
                </Link>
              ))}
            </div>
          )}

          <nav
            aria-label="Proje listesi sayfaları"
            className="flex flex-wrap items-center justify-between gap-3"
          >
            <Button
              variant="outline"
              disabled={page === 1}
              onClick={() => setPage((current) => current - 1)}
            >
              Önceki
            </Button>

            <span className="text-sm text-muted-foreground">
              Sayfa {page} · Toplam {projectsQuery.data.total} proje
            </span>

            <Button
              variant="outline"
              disabled={
                page * projectsQuery.data.limit >= projectsQuery.data.total
              }
              onClick={() => setPage((current) => current + 1)}
            >
              Sonraki
            </Button>
          </nav>
        </>
      )}
    </div>
  )
}