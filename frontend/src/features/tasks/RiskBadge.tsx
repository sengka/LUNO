import { Badge } from '@/components/ui/badge'
import type { Task } from './types'
const labels = {DUSUK:'Düşük',ORTA:'Orta',YUKSEK:'Yüksek'}
export function RiskBadge({task}:{task:Pick<Task,'status'|'risk_level'>}) {
 if(task.status==='DONE'||!task.risk_level)return null
 return <Badge variant={task.risk_level==='YUKSEK'?'destructive':task.risk_level==='ORTA'?'secondary':'outline'}>Risk: {labels[task.risk_level]}</Badge>
}
