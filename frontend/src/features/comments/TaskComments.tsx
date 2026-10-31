import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2Icon, SendIcon } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { UserAvatar } from '@/components/UserAvatar'
import { useAuth } from '@/features/auth/auth-context'
import { taskKeys } from '@/features/tasks/api'
import type { Task } from '@/features/tasks/types'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { commentKeys, commentsApi } from './api'
import { COMMENT_MAX_LENGTH, type Comment } from './types'

const timeFormatter = new Intl.DateTimeFormat('tr-TR', { hour: '2-digit', minute: '2-digit' })
const dayFormatter = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'short' })
const fullDayFormatter = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'short', year: 'numeric' })
const fullFormatter = new Intl.DateTimeFormat('tr-TR', { dateStyle: 'long', timeStyle: 'short' })

function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

// Mockup'taki gibi: "Bugün · 10:42", "Dün · 09:15", "7 Eki · 16:20"
function formatCommentDate(value: string) {
  const date = new Date(value)
  const now = new Date()
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)

  let day: string
  if (isSameDay(date, now)) day = 'Bugün'
  else if (isSameDay(date, yesterday)) day = 'Dün'
  else if (date.getFullYear() === now.getFullYear()) day = dayFormatter.format(date)
  else day = fullDayFormatter.format(date)

  return `${day} · ${timeFormatter.format(date)}`
}

// US-020 · Mockup: docs/tasarim/05-gorev-detay.png ("Yorumlar")
export function TaskComments({ task }: { task: Task }) {
  const queryClient = useQueryClient()

  const commentsQuery = useInfiniteQuery({
    queryKey: commentKeys.task(task.id),
    queryFn: ({ pageParam }) => commentsApi.listForTask(task.id, pageParam),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page * last.limit < last.total ? last.page + 1 : undefined),
  })

  const comments = commentsQuery.data?.pages.flatMap((page) => page.items) ?? []
  const total = commentsQuery.data?.pages[0]?.total ?? task.comment_count

  const onCommentAdded = () => {
    void queryClient.invalidateQueries({ queryKey: commentKeys.task(task.id) })
    // Görev detayındaki ve Kanban kartındaki yorum sayısı güncellensin
    void queryClient.invalidateQueries({ queryKey: taskKeys.detail(task.id) })
    void queryClient.invalidateQueries({ queryKey: taskKeys.board(task.project_id) })
  }

  return (
    <section aria-labelledby="task-comments-title" className="mt-10 grid gap-5">
      <h2 id="task-comments-title" className="flex items-center gap-2 text-lg font-semibold text-brand">
        Yorumlar
        <span className="rounded-full bg-secondary px-2 text-sm font-medium text-secondary-foreground">{total}</span>
      </h2>

      {commentsQuery.isPending ? (
        <div role="status" className="flex justify-center py-6">
          <Loader2Icon className="size-5 animate-spin text-primary" />
          <span className="sr-only">Yorumlar yükleniyor…</span>
        </div>
      ) : commentsQuery.isError ? (
        <div className="grid gap-3">
          <Alert variant="destructive" role="alert">
            <AlertDescription>
              {commentsQuery.error instanceof ApiError ? commentsQuery.error.message : 'Yorumlar alınamadı.'}
            </AlertDescription>
          </Alert>
          <Button variant="outline" className="justify-self-start" onClick={() => void commentsQuery.refetch()}>
            Tekrar dene
          </Button>
        </div>
      ) : comments.length === 0 ? (
        <p className="text-sm text-muted-foreground">Henüz yorum yok. İlk yorumu sen yaz.</p>
      ) : (
        <ol className="grid gap-5">
          {comments.map((comment) => (
            <CommentItem key={comment.id} comment={comment} />
          ))}
        </ol>
      )}

      {commentsQuery.hasNextPage && (
        <Button
          variant="ghost"
          className="justify-self-start"
          disabled={commentsQuery.isFetchingNextPage}
          onClick={() => void commentsQuery.fetchNextPage()}
        >
          {commentsQuery.isFetchingNextPage && <Loader2Icon className="animate-spin" />}
          Daha fazla yorum göster
        </Button>
      )}

      <CommentForm taskId={task.id} onAdded={onCommentAdded} />
    </section>
  )
}

function CommentItem({ comment }: { comment: Comment }) {
  return (
    <li className="flex gap-3">
      <UserAvatar user={comment.author} className="size-9 shrink-0" />
      <div className="grid min-w-0 flex-1 gap-1">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
          <span className="font-semibold">{comment.author.full_name}</span>
          <time
            dateTime={comment.created_at}
            title={fullFormatter.format(new Date(comment.created_at))}
            className="text-xs text-muted-foreground"
          >
            {formatCommentDate(comment.created_at)}
          </time>
        </div>
        {/* Metin olduğu gibi gösterilir; HTML olarak yorumlanmaz */}
        <p className="whitespace-pre-wrap break-words text-sm text-muted-foreground">{comment.body}</p>
      </div>
    </li>
  )
}

function CommentForm({ taskId, onAdded }: { taskId: number; onAdded: () => void }) {
  const { user } = useAuth()
  const [body, setBody] = useState('')
  const [error, setError] = useState<string | null>(null)

  const trimmed = body.trim()
  const tooLong = body.length > COMMENT_MAX_LENGTH
  const showCounter = body.length > COMMENT_MAX_LENGTH - 200

  const addComment = useMutation({
    mutationFn: (text: string) => commentsApi.addToTask(taskId, text),
    // Hata kutunun altında gösterilir
    meta: { skipForbiddenToast: true },
    onSuccess: () => {
      setBody('')
      setError(null)
      onAdded()
    },
    onError: (failure) => {
      if (failure instanceof ApiError && failure.fields?.body) setError(failure.fields.body)
      else setError(failure instanceof ApiError ? failure.message : 'Yorum gönderilemedi. Lütfen tekrar dene.')
    },
  })

  const submit = () => {
    if (!trimmed || tooLong || addComment.isPending) return
    setError(null)
    addComment.mutate(trimmed)
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    submit()
  }

  // Ctrl+Enter (Mac'te Cmd+Enter) ile gönder
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault()
      submit()
    }
  }

  if (!user) return null

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <UserAvatar user={user} className="size-9 shrink-0" />
      <div className="grid flex-1 gap-2">
        <div className="grid gap-2 rounded-xl border bg-card p-2 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50">
          <label htmlFor="comment-body" className="sr-only">
            Yorumun
          </label>
          <Textarea
            id="comment-body"
            value={body}
            onChange={(event) => setBody(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Yorumunu yaz…"
            rows={2}
            aria-invalid={tooLong || !!error}
            className="min-h-16 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0 dark:bg-transparent"
          />
          <div className="flex items-center justify-between gap-3 px-1">
            <span className={cn('text-xs text-muted-foreground', tooLong && 'font-medium text-destructive')}>
              {showCounter ? `${body.length} / ${COMMENT_MAX_LENGTH}` : 'Göndermek için Ctrl + Enter'}
            </span>
            <Button type="submit" disabled={!trimmed || tooLong || addComment.isPending}>
              {addComment.isPending ? <Loader2Icon className="animate-spin" /> : <SendIcon />}
              Gönder
            </Button>
          </div>
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
      </div>
    </form>
  )
}
