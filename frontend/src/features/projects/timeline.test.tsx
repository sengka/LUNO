// @vitest-environment jsdom
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router'
import { ApiError } from '@/lib/api'
import { projectsApi } from './api'
import { addDays, toCalendarEvent, toGanttTask } from './timeline-mappers'
import ProjectCalendar from './ProjectCalendar'
import ProjectGantt from './ProjectGantt'
import type { CalendarEvent, GanttItem } from './timeline-types'

const calendarEvent: CalendarEvent = { task_id: 42, title: 'Giriş ekranı', start_date: '2026-10-06', due_date: '2026-10-10', status: 'IN_PROGRESS', assignee: null }
const ganttItem: GanttItem = { ...calendarEvent, start_date: '2026-10-06', due_date: '2026-10-10', progress_percent: 33.3, parent_id: null, depends_on: [40] }

beforeAll(() => {
  // jsdom has no layout engine; supply the SVG measurement API used by Frappe.
  Object.defineProperty(SVGElement.prototype, 'getBBox', { configurable: true, value: () => ({ x: 0, y: 0, width: 100, height: 20 }) })
  Object.defineProperty(HTMLElement.prototype, 'scrollTo', { configurable: true, value: () => {} })
})

afterEach(() => { cleanup(); vi.restoreAllMocks() })

function mount(component: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><Routes><Route path="/" element={component} /><Route path="/gorevler/:id" element={<p>Görev detayına geçildi</p>} /></Routes></MemoryRouter></QueryClientProvider>)
}

describe('API tarih ve alan eşlemeleri', () => {
  it('teslim gününü dahil etmek için ay/yıl/artık gün sınırlarında bir gün ekler', () => {
    expect(addDays('2026-10-31', 1)).toBe('2026-11-01')
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01')
    expect(addDays('2028-02-28', 1)).toBe('2028-02-29')
    expect(addDays('2028-03-01', -1)).toBe('2028-02-29')
    expect(toCalendarEvent(calendarEvent)).toMatchObject({ id: '42', title: 'Giriş ekranı', start: '2026-10-06', end: '2026-10-11', allDay: true })
  })
  it('eksik başlangıç veya teslim tarihini tek günlük etkinlikle karşılar', () => {
    expect(toCalendarEvent({ ...calendarEvent, start_date: null })).toMatchObject({ start: '2026-10-10', end: '2026-10-11' })
    expect(toCalendarEvent({ ...calendarEvent, due_date: null })).toMatchObject({ start: '2026-10-06', end: '2026-10-07' })
    expect(toCalendarEvent({ ...calendarEvent, start_date: null, due_date: null })).toBeNull()
  })
  it('Gantt alanlarını ve kesirli ilerlemeyi korur, Sprint 9 bağımlılıklarını aktarmaz', () => {
    const mapped = toGanttTask(ganttItem)
    expect(mapped).toMatchObject({ id: '42', name: 'Giriş ekranı', start: '2026-10-06', end: '2026-10-10', progress: 33.3 })
    expect(mapped).not.toHaveProperty('dependencies')
  })
})

describe('Takvim', () => {
  it('etkinlikten görev detayına geçer', async () => {
    vi.spyOn(projectsApi, 'calendar').mockImplementation(async (_id, from) => ({ events: [{ ...calendarEvent, start_date: addDays(from, 7), due_date: addDays(from, 8) }] }))
    mount(<ProjectCalendar projectId={1} />)
    fireEvent.click(await screen.findByText('Giriş ekranı'))
    await screen.findByText('Görev detayına geçildi')
  })
  it('Türkçe ay/hafta görünümünü ve Pazartesi başlangıcını gerçek FullCalendar ile gösterir', async () => {
    const api = vi.spyOn(projectsApi, 'calendar').mockResolvedValue({ events: [] })
    mount(<ProjectCalendar projectId={1} />)
    await screen.findByText('Bu tarih aralığında planlanmış görev yok.')
    expect(screen.getByRole('tab', { name: 'Ay' })).toBeTruthy()
    expect(screen.getAllByRole('columnheader')[0].textContent).toContain('Pazartesi')
    fireEvent.click(screen.getByRole('tab', { name: 'Hafta' }))
    await waitFor(() => expect(api.mock.calls.length).toBeGreaterThan(1))
    for (const [, from, to] of api.mock.calls) {
      expect(new Date(`${from}T00:00:00Z`).getUTCDay()).toBe(1)
      expect(new Date(`${to}T00:00:00Z`).getTime() - new Date(`${from}T00:00:00Z`).getTime()).toBeLessThan(93 * 86400000)
    }
  })
  it('API hibánál újrapróbálkozik', async () => {
    vi.spyOn(projectsApi, 'calendar').mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ events: [] })
    mount(<ProjectCalendar projectId={1} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Tekrar dene' }))
    await screen.findByText('Bu tarih aralığında planlanmış görev yok.')
  })
})

describe('Gantt', () => {
  it('gerçek Frappe çubuklarını çizer, alt görev filtresini ve güvenli başlıkları korur', async () => {
    vi.spyOn(projectsApi, 'gantt').mockResolvedValue({ project: { start_date: '2026-10-01', end_date: '2026-11-30' }, items: [ganttItem, { ...ganttItem, task_id: 43, parent_id: 42, title: '<img src=x onerror=alert(1)>', progress_percent: 100 }] })
    const { container } = mount(<ProjectGantt projectId={1} />)
    await screen.findByRole('link', { name: 'Giriş ekranı' })
    await waitFor(() => expect(container.querySelectorAll('.bar-wrapper')).toHaveLength(2))
    expect(container.querySelector('.bar-label')?.textContent).toBe('Giriş ekranı')
    expect(container.querySelector('.bar-label img')).toBeNull()
    expect(container.querySelectorAll('.arrow path')).toHaveLength(0)
    expect(screen.getAllByText('%33,3')).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: 'Gün' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Alt görevleri göster' }))
    await waitFor(() => expect(container.querySelectorAll('.bar-wrapper')).toHaveLength(1))
    fireEvent.click(screen.getByRole('link', { name: 'Giriş ekranı' }))
    await screen.findByText('Görev detayına geçildi')
  })
  it('boş ve erişimi reddedilen projeleri mevcut bileşenlerle gösterir', async () => {
    vi.spyOn(projectsApi, 'gantt').mockResolvedValue({ project: { start_date: '2026-10-01', end_date: '2026-11-30' }, items: [] })
    const view = mount(<ProjectGantt projectId={1} />)
    await screen.findByText(/Gantt’ta gösterilecek görev yok/)
    view.unmount()
    vi.spyOn(projectsApi, 'gantt').mockRejectedValue(new ApiError(403, { code: 'PROJECT_ACCESS_DENIED', message: 'Erişim yok', fields: null, details: null }))
    mount(<ProjectGantt projectId={2} />)
    await screen.findByText('Bu projeye erişimin yok')
    expect(screen.queryByRole('img')).toBeNull()
  })
})
