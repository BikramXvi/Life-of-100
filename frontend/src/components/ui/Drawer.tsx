import type { ReactNode } from 'react'
import { X } from 'lucide-react'

export function Drawer({ open, onClose, title, subtitle, children }: { open: boolean; onClose: () => void; title: string; subtitle?: string; children: ReactNode }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="animate-slide-in relative flex h-full w-[380px] flex-col border-l border-[var(--border-strong)] bg-[var(--bg-elevated)] shadow-2xl">
        <div className="flex items-start justify-between border-b border-[var(--border)] px-4 py-3.5">
          <div>
            <div className="font-mono text-[15px] font-semibold text-[var(--text-primary)]">{title}</div>
            {subtitle && <div className="mt-0.5 text-[12px] text-[var(--text-tertiary)]">{subtitle}</div>}
          </div>
          <button onClick={onClose} className="rounded p-1 text-[var(--text-tertiary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]">
            <X size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  )
}

export function DrawerRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-[var(--border)] py-2 text-[12.5px]">
      <span className="text-[var(--text-tertiary)]">{label}</span>
      <span className="font-medium text-[var(--text-primary)] tabular-nums">{value}</span>
    </div>
  )
}
