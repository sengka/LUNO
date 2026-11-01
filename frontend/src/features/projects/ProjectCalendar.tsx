import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/react/daygrid'
import classicThemePlugin from '@fullcalendar/react/themes/classic'
import trLocale from '@fullcalendar/react/locales/tr'
import '@fullcalendar/react/skeleton.css'
import '@fullcalendar/react/themes/classic/theme.css'
import '@fullcalendar/react/themes/classic/palette.css'
import { projectsApi } from './api'
import { addDays, toCalendarEvent } from './timeline-mappers'
import { TimelineError, TimelineLegend } from './TimelineFeedback'
import './timeline.css'

export default function ProjectCalendar({ projectId }: { projectId: number }) {
  const navigate = useNavigate()
  const [range, setRange] = useState<{ from: string; to: string } | null>(null)
  const query = useQuery({
    queryKey: ['tasks', 'calendar', projectId, range],
    queryFn: () => projectsApi.calendar(projectId, range!.from, range!.to),
    enabled: range !== null,
    retry: false,
  })
  const events = (query.data?.events ?? []).flatMap((event) => {
    const mapped = toCalendarEvent(event)
    return mapped ? [mapped] : []
  })

  return <section aria-label="Proje takvimi" className="timeline grid min-w-0 gap-4">
    <div><h2 className="text-xl font-semibold text-brand">Takvim</h2><p className="text-sm text-muted-foreground">Görev başlangıçları ve teslim tarihleri</p></div>
    {query.isError && <TimelineError error={query.error} fetching={query.isFetching} retry={() => void query.refetch()} />}
    {range && query.isPending && <p role="status">Takvim yükleniyor…</p>}
    <div className="min-w-0 rounded-xl border bg-card p-3 sm:p-5" aria-busy={query.isFetching}>
      <FullCalendar
        plugins={[dayGridPlugin, classicThemePlugin]}
        locale={trLocale}
        firstDay={1}
        todayText="Bugün"
        class="project-calendar"
        headerToolbarClass="calendar-toolbar"
        toolbarTitleClass="calendar-title"
        eventClass="calendar-event"
        initialView="dayGridMonth"
        headerToolbar={{ left: 'title', center: '', right: 'prev,next today dayGridMonth,dayGridWeek' }}
        height="auto"
        dayMaxEvents={3}
        fixedWeekCount={false}
        events={query.isError ? [] : events}
        editable={false}
        datesSet={({ startStr, endStr }) => {
          const from = startStr.slice(0, 10)
          // FullCalendar's end is exclusive; API's `to` is inclusive.
          const to = addDays(endStr.slice(0, 10), -1)
          setRange((current) => current?.from === from && current.to === to ? current : { from, to })
        }}
        eventClick={({ event, jsEvent }) => {
          jsEvent.preventDefault()
          navigate(`/gorevler/${event.id}`, { state: { timelineFrom: `/projeler/${projectId}/takvim` } })
        }}
        eventDidMount={({ el, event }) => {
          const assignee = event.extendedProps.assignee as { full_name: string } | null
          el.title = `${event.title}${assignee ? ` · ${assignee.full_name}` : ''}`
        }}
      />
    </div>
    {query.isSuccess && events.length === 0 && <p role="status" className="rounded-xl border bg-card p-5 text-muted-foreground">Bu tarih aralığında planlanmış görev yok.</p>}
    <TimelineLegend />
  </section>
}
