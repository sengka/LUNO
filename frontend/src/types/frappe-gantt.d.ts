declare module 'frappe-gantt' {
  export interface GanttTask {
    id: string
    name: string
    start: string
    end: string
    progress: number
    custom_class?: string
  }
  export type ViewMode = 'Day' | 'Week' | 'Month'
  export default class Gantt {
    constructor(element: HTMLElement, tasks: GanttTask[], options: {
      view_mode: ViewMode
      language: string
      readonly: boolean
      popup: false
      scroll_to: string
      container_height: number
      today_button: boolean
      on_click: (task: GanttTask) => void
    })
    scroll_current(): void
    clear(): void
  }
}
