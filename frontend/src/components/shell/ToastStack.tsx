import { useEffect } from 'react'
import { AlertTriangle, Info, X } from 'lucide-react'
import { useNotificationStore } from '../../lib/notifications'
import clsx from 'clsx'

function ToastCard({ id, title, detail, level }: { id: string; title: string; detail: string; level: string }) {
  const dismiss = useNotificationStore((s) => s.dismissToast)

  useEffect(() => {
    const t = setTimeout(() => dismiss(id), 6000)
    return () => clearTimeout(t)
  }, [id, dismiss])

  return (
    <div
      className={clsx(
        'animate-slide-in flex items-start gap-2.5 rounded-md border bg-[var(--bg-elevated)] p-3 shadow-lg',
        level === 'critical' && 'border-[var(--danger)]/50',
        level === 'warning' && 'border-[var(--warning)]/50',
        level === 'info' && 'border-[var(--border-strong)]',
      )}
      style={{ width: 300 }}
    >
      {level === 'info' ? (
        <Info size={16} className="mt-0.5 shrink-0 text-[var(--accent)]" />
      ) : (
        <AlertTriangle size={16} className={clsx('mt-0.5 shrink-0', level === 'critical' ? 'text-[var(--danger)]' : 'text-[var(--warning)]')} />
      )}
      <div className="flex-1">
        <div className="text-[12.5px] font-semibold text-[var(--text-primary)]">{title}</div>
        <div className="mt-0.5 text-[11.5px] text-[var(--text-tertiary)]">{detail}</div>
      </div>
      <button onClick={() => dismiss(id)} className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)]">
        <X size={14} />
      </button>
    </div>
  )
}

export function ToastStack() {
  const toasts = useNotificationStore((s) => s.toasts)
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <ToastCard key={t.id} id={t.id} title={t.title} detail={t.detail} level={t.level} />
      ))}
    </div>
  )
}
