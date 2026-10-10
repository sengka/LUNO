import { cn } from '@/lib/utils'

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className="flex size-9 items-center justify-center rounded-full bg-primary text-lg font-bold text-primary-foreground">
        L
      </span>
      <span className="text-xl font-bold tracking-tight text-brand">LUNO</span>
    </div>
  )
}
