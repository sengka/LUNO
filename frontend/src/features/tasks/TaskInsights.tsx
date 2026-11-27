import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { api, ApiError } from '@/lib/api'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { TimelineError } from '@/features/projects/TimelineFeedback'
import { RiskBadge } from './RiskBadge'
import type { Task } from './types'
export function TaskInsights({projectId}:{projectId?:number}) {
 const [level,setLevel]=useState('ORTA')
 const q=useQuery({queryKey:['tasks',projectId?'risks':'today',projectId,level],queryFn:()=>api.get<Task[]>(projectId?`/projects/${projectId}/risks?level=${level}`:'/me/today'),retry:false})
 return <section className="grid gap-4 rounded-xl border bg-card p-5"><h2 className="text-xl font-semibold text-brand">{projectId?'Riskli görevler':'Bugün ne yapmalıyım?'}</h2>{projectId?<label>En düşük risk seviyesi <select className="rounded border p-2" value={level} onChange={e=>setLevel(e.target.value)}><option value="DUSUK">Düşük ve üstü</option><option value="ORTA">Orta ve üstü</option><option value="YUKSEK">Yüksek</option></select></label>:<p className="text-sm text-muted-foreground">Sana atanan, teslimine 3 gün veya daha az kalan ya da süresi geçen görevler. Sıralama: teslim tarihi, ardından öncelik.</p>}{q.isPending&&<p role="status">Görevler yükleniyor…</p>}{q.isError&&(q.error instanceof ApiError && q.error.status===404 && !projectId ? <Alert variant="destructive" role="alert"><AlertDescription>Bugün görevleri servisi kullanılamıyor. Görevler alınamadı.</AlertDescription><Button variant="outline" onClick={()=>void q.refetch()}>Tekrar dene</Button></Alert> : <TimelineError error={q.error} fetching={q.isFetching} retry={()=>void q.refetch()}/>)}{q.isSuccess&&<>{!q.data.filter(t=>t.status!=='DONE').length&&<p>{projectId?'Bu seviyede riskli görev bulunmuyor.':'Bugün için acil görevin yok.'}</p>}<ul className="grid gap-3">{q.data.filter(t=>t.status!=='DONE').map(t=><li key={t.id}><Link to={`/gorevler/${t.id}`} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3 hover:bg-muted"><span>{t.title}</span><time>{t.due_date}</time><RiskBadge task={t}/></Link></li>)}</ul></>}</section>
}
