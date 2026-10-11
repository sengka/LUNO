import { useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import trLocale from '@fullcalendar/core/locales/tr'
import GanttDemo from './GanttDemo'
import RaporDemo from './RaporDemo'
import './App.css'

const ornekGorevler = [
  {
    id: '1',
    title: 'Takvim kütüphanesini dene',
    start: '2026-10-10',
    allDay: true,
    backgroundColor: '#6366f1',
    borderColor: '#6366f1',
  },
  {
    id: '2',
    title: 'Gantt örneğini hazırla',
    start: '2026-10-11',
    allDay: true,
    backgroundColor: '#0891b2',
    borderColor: '#0891b2',
  },
  {
    id: '3',
    title: 'Grafik örneğini hazırla',
    start: '2026-10-12',
    allDay: true,
    backgroundColor: '#059669',
    borderColor: '#059669',
  },
]

function App() {
  const [secilenGorev, setSecilenGorev] = useState('')

  return (
    <main className="demo">
      <header className="demo-header">
        <span className="badge">LUNO · Görev #83</span>
        <h1>Takvim denemesi</h1>
        <p>Örnek görev tarihleri — gerçek proje verisi değildir.</p>
      </header>

      <section className="calendar-card" aria-label="Görev takvimi">
        <FullCalendar
          plugins={[dayGridPlugin]}
          initialView="dayGridMonth"
          initialDate="2026-10-10"
          locale={trLocale}
          firstDay={1}
          height="auto"
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,dayGridWeek',
          }}
          events={ornekGorevler}
          eventClick={(bilgi) => {
            setSecilenGorev(bilgi.event.title)
          }}
        />
      </section>

      <p className="selection" role="status">
        {secilenGorev
          ? `Seçilen görev: ${secilenGorev}`
          : 'Detayını görmek için takvimdeki bir göreve tıkla.'}
      </p>
      <GanttDemo />
      <RaporDemo />
    </main>
  )
}

export default App