import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { TimelineError } from './TimelineFeedback'
interface Sprint {id:number;name:string;is_active:boolean;total_points:number;done_points:number;progress_percent:number}
export function ActiveSprintProgress({projectId}:{projectId:number}) {
 const q=useQuery({queryKey:['tasks','sprints',projectId],queryFn:()=>api.get<Sprint[]>(`/projects/${projectId}/sprints`)})
 if(q.isPending)return <p role="status">Sprint yükleniyor…</p>
 if(q.isError)return <TimelineError error={q.error} fetching={q.isFetching} retry={()=>void q.refetch()}/>
 const s=q.data.find(s=>s.is_active)
 return <section className="grid gap-3 rounded-xl border bg-card p-5"><h2 className="font-semibold text-brand">Aktif sprint ilerlemesi</h2>{!s?<p>Aktif sprint bulunmuyor.</p>:<><h3>{s.name}</h3><p>{s.done_points} / {s.total_points} efor puanı · %{s.progress_percent.toLocaleString('tr-TR')}</p><progress aria-label="Sprint efor ilerlemesi" max={100} value={s.total_points===0?0:s.progress_percent} className="w-full accent-primary"/>{s.total_points===0&&<p>Sprint boş veya görevlerin efor puanları tanımlanmamış; hesaplanabilir toplam efor yok.</p>}</>}</section>
}
