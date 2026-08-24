import { Line, LineChart, ResponsiveContainer, YAxis } from 'recharts'
import clsx from 'clsx'

export function Kpi({
  label,
  value,
  delta,
  series,
  color = 'var(--accent)',
  onClick,
}: {
  label: string
  value: string
  delta?: { text: string; positive: boolean } | null
  series?: number[]
  color?: string
  onClick?: () => void
}) {
  const data = series?.map((v, i) => ({ i, v })) ?? []

  return (
    <button
      onClick={onClick}
      disabled={!onClick}
      className={clsx(
        'flex flex-col gap-1.5 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-3.5 text-left transition-colors',
        onClick && 'hover:border-[var(--border-strong)] hover:bg-[var(--surface-hover)] cursor-pointer',
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10.5px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">{label}</span>
        {delta && (
          <span
            className={clsx(
              'text-[11px] font-semibold tabular-nums',
              delta.positive ? 'text-[var(--success)]' : 'text-[var(--danger)]',
            )}
          >
            {delta.text}
          </span>
        )}
      </div>
      <div className="flex items-end justify-between gap-2">
        <span className="font-mono text-[22px] font-semibold tabular-nums leading-none text-[var(--text-primary)]">
          {value}
        </span>
        {data.length > 1 && (
          <div className="h-7 w-20">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <YAxis hide domain={['dataMin', 'dataMax']} />
                <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </button>
  )
}
