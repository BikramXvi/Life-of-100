import clsx from 'clsx'
import type { ReactNode } from 'react'

export function Panel({
  title,
  subtitle,
  action,
  children,
  className,
  padded = true,
}: {
  title?: ReactNode
  subtitle?: string
  action?: ReactNode
  children: ReactNode
  className?: string
  padded?: boolean
}) {
  return (
    <div className={clsx('rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)]', className)}>
      {title && (
        <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-2.5">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">{title}</div>
            {subtitle && <div className="mt-0.5 text-[11.5px] text-[var(--text-tertiary)]">{subtitle}</div>}
          </div>
          {action}
        </div>
      )}
      {/* min-h-0 + flex-1 are no-ops unless the Panel root itself is a flex
          column (opted into via className, e.g. "flex min-h-0 flex-col") --
          harmless everywhere else. Unpadded panels additionally become a
          flex column themselves so a single scrollable child inside can use
          flex-1 + min-h-0 to actually shrink and scroll instead of growing
          to fit all its content and blowing out the layout. */}
      <div className={clsx('min-h-0 flex-1', !padded && 'flex flex-col', padded && 'p-4')}>{children}</div>
    </div>
  )
}
