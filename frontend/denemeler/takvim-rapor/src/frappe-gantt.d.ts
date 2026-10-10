declare module 'frappe-gantt' {
  export interface GanttTask {
    id: string
    name: string
    start: string
    end: string
    progress: number
    dependencies?: string
  }

  export interface GanttOptions {
    view_mode?: 'Day' | 'Week' | 'Month' | 'Year'
    language?: string
    readonly?: boolean
    scroll_to?: string
    container_height?: number
    view_mode_select?: boolean
  }

  export default class Gantt {
    constructor(
      element: HTMLElement,
      tasks: GanttTask[],
      options?: GanttOptions,
    )
  }
}