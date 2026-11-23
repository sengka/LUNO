import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { api } from '@/lib/api'
import { TimelineError } from '@/features/projects/TimelineFeedback'
import type { Task } from '@/features/tasks/types'
import { statuses } from './report-statuses'
interface Dashboard { projects: {id:number;name:string;progress_percent:number;my_open_tasks:number}[]; my_task_counts:Record<string,number>; upcoming_tasks:Task[]; unread_notification_count:number }
export function HomePage() {
 const q=useQuery({queryKey:['tasks','dashboard'],queryFn:()=>api.get<Dashboard>('/dashboard')})
 return <div className="grid gap-6"><h1 className="text-2xl font-semibold text-brand">Kontrol Paneli</h1>{q.isPending&&<p role="status">Özet yükleniyor…</p>}{q.isError&&<TimelineError error={q.error} fetching={q.isFetching} retry={()=>void q.refetch()}/>}{q.isSuccess&&<>
 <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{statuses.map(([key,label])=><section key={key} className="rounded-xl border bg-card p-5"><h2>{label}</h2><p className="text-3xl font-semibold">{q.data.my_task_counts[key]}</p></section>)}</div>
 <section className="rounded-xl border bg-card p-5"><h2>Okunmamış bildirimler</h2><p className="text-2xl">{q.data.unread_notification_count}</p></section>
 <section className="grid gap-3"><h2 className="text-xl font-semibold text-brand">Yaklaşan teslimler</h2>{!q.data.upcoming_tasks.length&&<p>Yaklaşan teslim bulunmuyor.</p>}{q.data.upcoming_tasks.map(t=><Link key={t.id} to={`/gorevler/${t.id}`} className="flex flex-wrap justify-between gap-3 rounded-xl border bg-card p-4"><span>{t.title}</span><time>{t.due_date}</time></Link>)}</section>
 <section className="grid gap-4"><h2 className="text-xl font-semibold text-brand">Projelerim</h2>{!q.data.projects.length&&<p>Henüz üyesi olduğun proje yok.</p>}<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{q.data.projects.map(p=><Link key={p.id} to={`/projeler/${p.id}`} className="grid gap-3 rounded-xl border bg-card p-5"><h3>{p.name}</h3><p>İlerleme: %{p.progress_percent.toLocaleString('tr-TR')}</p><progress aria-label={`${p.name} ilerlemesi`} max={100} value={p.progress_percent} className="w-full accent-primary"/><p>{p.my_open_tasks} açık görevim</p></Link>)}</div></section></>}</div>
}
