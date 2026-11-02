import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import Gantt from 'frappe-gantt'
import type { ViewMode } from 'frappe-gantt'
import '../../../node_modules/frappe-gantt/dist/frappe-gantt.css'
import { Button } from '@/components/ui/button'
import { projectsApi } from './api'
import { toGanttTask } from './timeline-mappers'
import type { GanttItem } from './timeline-types'
import { TimelineError, TimelineLegend } from './TimelineFeedback'
import './timeline.css'

// Frappe inserts task labels as SVG innerHTML. Escape API titles at that boundary.
function escapeLabel(value: string) {
  return value.replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]!)
}

function GanttChart({ items, mode, projectId }: { items: GanttItem[]; mode: ViewMode; projectId: number }) {
  const container = useRef<HTMLDivElement>(null)
  const chart = useRef<Gantt | null>(null)
  const navigate = useNavigate()
  useEffect(() => {
    const element = container.current
    if (!element || items.length === 0) return
    chart.current = new Gantt(element, items.map((item) => ({ ...toGanttTask(item), name: escapeLabel(item.title) })), {
      view_mode: mode,
      language: 'tr',
      readonly: true,
      popup: false,
      scroll_to: 'start',
      container_height: 450,
      today_button: false,
      on_click: (task) => navigate(`/gorevler/${task.id}`, { state: { timelineFrom: `/projeler/${projectId}/gantt` } }),
    })
    return () => {
      chart.current?.clear()
      chart.current = null
      element.replaceChildren()
    }
  }, [items, mode, navigate, projectId])
  return <div className="grid min-w-0 gap-3">
    <Button variant="outline" className="justify-self-start" onClick={() => chart.current?.scroll_current()}>Bugüne git</Button>
    <div ref={container} className="min-w-0 overflow-hidden rounded-xl border bg-card" role="img" aria-label="Görev süreleri ve ilerleme oranları. Ayrıntılar aşağıdaki görev tablosunda." />
  </div>
}

export default function ProjectGantt({ projectId }: { projectId: number }) {
  const [mode, setMode] = useState<ViewMode>('Week')
  const [showSubtasks, setShowSubtasks] = useState(true)
  const query = useQuery({ queryKey: ['tasks', 'gantt', projectId], queryFn: () => projectsApi.gantt(projectId), retry: false })
  const items = query.data?.items.filter((item) => showSubtasks || item.parent_id === null) ?? []
  return <section aria-label="Proje Gantt şeması" className="timeline grid min-w-0 gap-4">
    <div><h2 className="text-xl font-semibold text-brand">Gantt şeması</h2><p className="text-sm text-muted-foreground">Görev süreleri ve tamamlanma oranları</p></div>
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div className="flex gap-1" role="group" aria-label="Zaman ölçeği">
        {([['Day', 'Gün'], ['Week', 'Hafta'], ['Month', 'Ay']] as const).map(([value, label]) => <Button key={value} variant={mode === value ? 'default' : 'outline'} aria-pressed={mode === value} onClick={() => setMode(value)}>{label}</Button>)}
      </div>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={showSubtasks} onChange={(event) => setShowSubtasks(event.target.checked)} />Alt görevleri göster</label>
    </div>
    {query.isPending && <p role="status">Gantt şeması yükleniyor…</p>}
    {query.isError && <TimelineError error={query.error} fetching={query.isFetching} retry={() => void query.refetch()} />}
    {query.isSuccess && (items.length ? <>
      <p className="text-sm text-muted-foreground">{items.length} görev · Proje: {query.data.project.start_date} – {query.data.project.end_date}</p>
      <GanttChart items={items} mode={mode} projectId={projectId} />
      <TimelineLegend />
      <p className="text-sm text-muted-foreground">Tarihleri değiştirmek için görevi düzenle.</p>
      <div className="overflow-x-auto rounded-xl border bg-card">
        <table className="w-full text-left text-sm"><caption className="sr-only">Görev tarihleri ve ilerleme oranları</caption>
          <thead><tr className="border-b"><th className="p-3">Görev</th><th className="p-3">Başlangıç</th><th className="p-3">Teslim</th><th className="p-3">İlerleme</th></tr></thead>
          <tbody>{items.map((item) => <tr key={item.task_id} className="border-b last:border-0">
            <td className="p-3"><Link className="text-brand underline" to={`/gorevler/${item.task_id}`} state={{ timelineFrom: `/projeler/${projectId}/gantt` }}>{item.parent_id !== null ? '↳ ' : ''}{item.title}</Link></td>
            <td className="whitespace-nowrap p-3">{item.start_date}</td><td className="whitespace-nowrap p-3">{item.due_date}</td><td className="p-3">%{item.progress_percent.toLocaleString('tr-TR', { maximumFractionDigits: 1 })}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </> : <p role="status" className="rounded-xl border bg-card p-5 text-muted-foreground">Gantt’ta gösterilecek görev yok. Görevlere başlangıç ve teslim tarihi ekleyebilirsin.</p>)}
  </section>
}
