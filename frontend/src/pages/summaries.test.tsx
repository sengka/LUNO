// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router'
import { api } from '@/lib/api'
import { HomePage } from './HomePage'
import { ReportsPage } from './ReportsPage'
import { ActiveSprintProgress } from '@/features/projects/ActiveSprintProgress'
afterEach(()=>{cleanup();vi.restoreAllMocks()})
function mount(node:React.ReactNode){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})}><MemoryRouter initialEntries={['/projeler/1/raporlar']}><Routes><Route path="/projeler/:projectId/raporlar" element={node}/></Routes></MemoryRouter></QueryClientProvider>)}
it('dashboard boş veriyi ve okunmamış bildirim sayısını gerçek alanlardan gösterir',async()=>{vi.spyOn(api,'get').mockResolvedValue({projects:[],my_task_counts:{TODO:0,IN_PROGRESS:0,REVIEW_TESTING:0,DONE:0},upcoming_tasks:[],unread_notification_count:7});mount(<HomePage/>);await screen.findByText('7');expect(screen.getByText('Henüz üyesi olduğun proje yok.')).toBeTruthy()})
it('dashboard API hatasını boş veriye dönüştürmez',async()=>{vi.spyOn(api,'get').mockRejectedValue(new Error('offline'));mount(<HomePage/>);await screen.findByRole('alert');expect(screen.queryByText('Henüz üyesi olduğun proje yok.')).toBeNull()})
it('sprint toplam efor sıfırsa hesaplanamayan efor mesajı gösterir',async()=>{vi.spyOn(api,'get').mockResolvedValue([{id:1,name:'Sprint',is_active:true,total_points:0,done_points:0,progress_percent:0}]);mount(<ActiveSprintProgress projectId={1}/>);await screen.findByText(/hesaplanabilir toplam efor yok/);expect(screen.getByRole('progressbar').getAttribute('value')).toBe('0')})
it('aktif sprint yok durumunu gösterir',async()=>{vi.spyOn(api,'get').mockResolvedValue([]);mount(<ActiveSprintProgress projectId={1}/>);await screen.findByText('Aktif sprint bulunmuyor.')})
it('sprint görev sayısını değil API efor ilerlemesini kullanır',async()=>{vi.spyOn(api,'get').mockResolvedValue([{id:1,name:'Sprint',is_active:true,total_points:20,done_points:5,progress_percent:25}]);mount(<ActiveSprintProgress projectId={1}/>);await screen.findByText(/5 \/ 20 efor/);expect(screen.getByRole('progressbar').getAttribute('value')).toBe('25')})
it('dönem seçimi yeni API sorgusunu tetikler',async()=>{const spy=vi.spyOn(api,'get').mockImplementation(async(path)=>path.endsWith('/sprints')?[]:path.includes('/members')?{members:[]}:{from:'2026-11-01',to:'2026-11-30',created_count:0,completed_count:0,series:[]});mount(<ReportsPage/>);await screen.findByText('Bu dönemde görev hareketi yok.');fireEvent.change(screen.getByLabelText('Dönem'),{target:{value:'MONTHLY'}});await waitFor(()=>expect(spy.mock.calls.some(([path])=>path.includes('period=MONTHLY'))).toBe(true))})
