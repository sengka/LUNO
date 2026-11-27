// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'
import { RiskBadge } from './RiskBadge'
import { TaskInsights } from './TaskInsights'
import { CapacityValue } from '@/features/projects/CapacityValue'
import { api } from '@/lib/api'
afterEach(()=>{cleanup();vi.restoreAllMocks()})
function mount(node:React.ReactNode){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})}><MemoryRouter>{node}</MemoryRouter></QueryClientProvider>)}
it('Done geçişinde risk gizlenir, geri açılınca görünür',()=>{const v=render(<RiskBadge task={{status:'IN_PROGRESS',risk_level:'YUKSEK'}}/>);expect(screen.getByText('Risk: Yüksek')).toBeTruthy();v.rerender(<RiskBadge task={{status:'DONE',risk_level:'YUKSEK'}}/>);expect(screen.queryByText(/Risk:/)).toBeNull();v.rerender(<RiskBadge task={{status:'TODO',risk_level:'ORTA'}}/>);expect(screen.getByText('Risk: Orta')).toBeTruthy()})
it('null risk rozeti çizilmez',()=>{const v=render(<RiskBadge task={{status:'TODO',risk_level:null}}/>);expect(v.container.textContent).toBe('')})
it('tanımsız kapasite sıfırdan ayrılır ve uyarı verilmez',()=>{const v=render(<CapacityValue points={null}/>);expect(screen.getByText('Kapasite tanımsız')).toBeTruthy();expect(screen.queryByRole('alert')).toBeNull();v.rerender(<CapacityValue points={0}/>);expect(screen.getByText('0 puan')).toBeTruthy()})
it('bugün boş durumu ve gerçek uç',async()=>{const spy=vi.spyOn(api,'get').mockResolvedValue([]);mount(<TaskInsights/>);await screen.findByText('Bugün için acil görevin yok.');expect(spy).toHaveBeenCalledWith('/me/today')})
it('hata boş veri değildir ve yeniden denenir',async()=>{vi.spyOn(api,'get').mockRejectedValueOnce(new Error('offline')).mockResolvedValue([]);mount(<TaskInsights/>);fireEvent.click(await screen.findByRole('button',{name:'Tekrar dene'}));await screen.findByText('Bugün için acil görevin yok.')})
it('API sırası korunur ve görev detayı bağlantısı vardır',async()=>{vi.spyOn(api,'get').mockResolvedValue([{id:9,title:'Önce',status:'TODO',risk_level:'YUKSEK',due_date:'2026-11-27'},{id:2,title:'Sonra',status:'TODO',risk_level:null,due_date:'2026-11-28'}]);mount(<TaskInsights/>);await screen.findByText('Önce');expect(screen.getAllByRole('link').map(l=>l.getAttribute('href'))).toEqual(['/gorevler/9','/gorevler/2'])})
