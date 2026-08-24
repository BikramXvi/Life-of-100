import { useRef, type ReactNode } from 'react'
import { Download, ImageDown } from 'lucide-react'
import { exportRowsAsCsv, exportSvgAsPng } from '../../lib/chartExport'

/** Wraps a chart (anything that renders a single top-level <svg>, e.g. a
 * recharts ResponsiveContainer) with hover-revealed PNG/CSV export controls.
 * PNG rasterizes the live SVG; CSV re-serializes the same row data the chart
 * was fed, so both exports always match what's on screen. */
export function ChartFrame({
  csvData,
  csvFilename,
  pngFilename,
  height = 220,
  children,
}: {
  csvData?: Record<string, unknown>[]
  csvFilename?: string
  pngFilename?: string
  height?: number | string
  children: ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)

  return (
    <div className="group/chart relative" style={{ height }}>
      {(csvData || pngFilename) && (
        <div className="absolute right-0 top-0 z-10 flex gap-1 opacity-0 transition-opacity group-hover/chart:opacity-100">
          {pngFilename && (
            <button
              onClick={() => exportSvgAsPng(ref.current, pngFilename)}
              title="Export chart as PNG"
              className="flex items-center gap-1 rounded border border-[var(--border)] bg-[var(--bg-elevated)] px-1.5 py-0.5 text-[10px] text-[var(--text-tertiary)] hover:border-[var(--border-strong)] hover:text-[var(--text-secondary)]"
            >
              <ImageDown size={10} /> PNG
            </button>
          )}
          {csvData && (
            <button
              onClick={() => exportRowsAsCsv(csvData, csvFilename ?? 'data.csv')}
              title="Export data as CSV"
              className="flex items-center gap-1 rounded border border-[var(--border)] bg-[var(--bg-elevated)] px-1.5 py-0.5 text-[10px] text-[var(--text-tertiary)] hover:border-[var(--border-strong)] hover:text-[var(--text-secondary)]"
            >
              <Download size={10} /> CSV
            </button>
          )}
        </div>
      )}
      <div ref={ref} className="h-full w-full">
        {children}
      </div>
    </div>
  )
}
