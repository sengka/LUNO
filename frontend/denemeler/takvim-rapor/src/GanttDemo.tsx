import { useEffect, useRef } from 'react'
import Gantt from 'frappe-gantt'
import '../node_modules/frappe-gantt/dist/frappe-gantt.css'

function GanttDemo() {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Her kurulumda yeni veriler oluşturuyoruz.
    const tasks = [
      {
        id: 'takvim',
        name: 'Takvim denemesi',
        start: '2026-10-10',
        end: '2026-10-11',
        progress: 100,
      },
      {
        id: 'gantt',
        name: 'Gantt denemesi',
        start: '2026-10-12',
        end: '2026-10-14',
        progress: 40,
        dependencies: 'takvim',
      },
      {
        id: 'grafik',
        name: 'Grafik denemesi',
        start: '2026-10-15',
        end: '2026-10-16',
        progress: 0,
        dependencies: 'gantt',
      },
    ]

    new Gantt(container, tasks, {
      view_mode: 'Day',
      language: 'tr',
      readonly: true,
      scroll_to: 'start',
      container_height: 300,
      view_mode_select: true,
    })

    // React bileşeni kaldırıldığında çizimi temizliyoruz.
    return () => {
      container.replaceChildren()
    }
  }, [])

  return (
    <section className="gantt-section" aria-labelledby="gantt-heading">
      <h2 id="gantt-heading">Gantt denemesi</h2>
      <p>
        Örnek tarihler ve ilerleme oranlarıdır. Oklar, görevler arasındaki
        bağımlılığı gösterir.
      </p>

      <div className="calendar-card gantt-card">
        <div ref={containerRef} />
      </div>

      <ul className="gantt-summary">
        <li>Takvim denemesi: 10–11 Ekim · %100 tamamlandı</li>
        <li>Gantt denemesi: 12–14 Ekim · %40 tamamlandı</li>
        <li>Grafik denemesi: 15–16 Ekim · Henüz başlanmadı</li>
      </ul>
    </section>
  )
}

export default GanttDemo