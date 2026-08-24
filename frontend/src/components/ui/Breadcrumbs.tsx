import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'

export function Breadcrumbs({ items }: { items: { label: string; to?: string }[] }) {
  return (
    <div className="flex items-center gap-1.5 px-6 pt-4 text-[11.5px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1.5">
          {i > 0 && <ChevronRight size={12} />}
          {item.to ? (
            <Link to={item.to} className="hover:text-[var(--text-primary)]">
              {item.label}
            </Link>
          ) : (
            <span className="text-[var(--text-secondary)]">{item.label}</span>
          )}
        </span>
      ))}
    </div>
  )
}
