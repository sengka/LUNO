import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from 'recharts'

const ornekRapor = [
  { kisi: 'Ayşe', tamamlanan: 5 },
  { kisi: 'Emre', tamamlanan: 8 },
  { kisi: 'Zülal', tamamlanan: 3 },
  { kisi: 'Sefa', tamamlanan: 6 },
]

function RaporDemo() {
  return (
    <section className="report-section" aria-labelledby="report-heading">
      <h2 id="report-heading">Kişi bazlı rapor denemesi</h2>
      <p>
        Tamamlanan görev sayıları örnek veridir; gerçek ekip performansını
        göstermez.
      </p>

      <div className="calendar-card">
        <ResponsiveContainer width="100%" height={320}>
          <BarChart
            data={ornekRapor}
            margin={{ top: 25, right: 16, bottom: 10, left: 0 }}
            accessibilityLayer
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="kisi" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar
              dataKey="tamamlanan"
              name="Tamamlanan görev"
              fill="#6366f1"
              radius={[6, 6, 0, 0]}
              maxBarSize={80}
            >
              <LabelList dataKey="tamamlanan" position="top" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        <ul className="report-summary">
          {ornekRapor.map((kayit) => (
            <li key={kayit.kisi}>
              {kayit.kisi}: {kayit.tamamlanan} görev
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

export default RaporDemo