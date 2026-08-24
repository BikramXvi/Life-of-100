// Chart export utilities: PNG (rasterized from the live SVG, with computed
// styles baked in so CSS custom properties like var(--accent) survive being
// serialized into a standalone image) and CSV (from the same row data the
// chart itself renders from).

const STYLE_PROPS = [
  'fill',
  'stroke',
  'color',
  'opacity',
  'fillOpacity',
  'strokeOpacity',
  'fontFamily',
  'fontSize',
  'fontWeight',
  'strokeWidth',
  'strokeDasharray',
  'textAnchor',
] as const

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** Copies resolved computed styles from every element in `original` onto the
 * matching element (same position, same clone) in `clone` -- var(--x)
 * references only resolve against the live document's cascade, so a bare
 * serialization of the SVG would ship literal "var(--accent)" strings that
 * mean nothing once rendered outside this page. */
function bakeComputedStyles(original: SVGElement, clone: SVGElement) {
  const originalEls = [original, ...Array.from(original.querySelectorAll('*'))]
  const cloneEls = [clone, ...Array.from(clone.querySelectorAll('*'))]
  originalEls.forEach((el, i) => {
    const cloneEl = cloneEls[i]
    if (!cloneEl) return
    const computed = getComputedStyle(el)
    const decls = STYLE_PROPS.map((prop) => {
      const value = computed.getPropertyValue(prop.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`))
      return value ? `${prop.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`)}:${value}` : null
    }).filter(Boolean)
    if (decls.length) cloneEl.setAttribute('style', decls.join(';'))
  })
}

export async function exportSvgAsPng(container: HTMLElement | null, filename: string, scale = 2) {
  const svg = container?.querySelector('svg')
  if (!svg) {
    alert('Nothing to export yet.')
    return
  }

  const rect = svg.getBoundingClientRect()
  const width = Math.max(1, Math.round(rect.width))
  const height = Math.max(1, Math.round(rect.height))

  const clone = svg.cloneNode(true) as SVGSVGElement
  bakeComputedStyles(svg, clone)
  clone.setAttribute('width', String(width))
  clone.setAttribute('height', String(height))
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')

  const bg = getComputedStyle(document.documentElement).getPropertyValue('--surface').trim() || '#12151b'
  const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
  bgRect.setAttribute('x', '0')
  bgRect.setAttribute('y', '0')
  bgRect.setAttribute('width', String(width))
  bgRect.setAttribute('height', String(height))
  bgRect.setAttribute('fill', bg)
  clone.insertBefore(bgRect, clone.firstChild)

  const svgString = new XMLSerializer().serializeToString(clone)
  const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(svgBlob)

  try {
    const img = new Image()
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve()
      img.onerror = () => reject(new Error('Failed to rasterize chart SVG.'))
      img.src = url
    })
    const canvas = document.createElement('canvas')
    canvas.width = width * scale
    canvas.height = height * scale
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('Canvas 2D context unavailable.')
    ctx.scale(scale, scale)
    ctx.drawImage(img, 0, 0, width, height)
    const pngBlob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'))
    if (!pngBlob) throw new Error('Failed to encode PNG.')
    downloadBlob(pngBlob, filename)
  } catch (err) {
    alert(String(err))
  } finally {
    URL.revokeObjectURL(url)
  }
}

function csvCell(value: unknown): string {
  const s = value === null || value === undefined ? '' : String(value)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function exportRowsAsCsv(rows: Record<string, unknown>[], filename: string) {
  if (!rows.length) {
    alert('Nothing to export yet.')
    return
  }
  const headers = Array.from(rows.reduce((set, row) => {
    Object.keys(row).forEach((k) => set.add(k))
    return set
  }, new Set<string>()))
  const lines = [
    headers.map(csvCell).join(','),
    ...rows.map((row) => headers.map((h) => csvCell(row[h])).join(',')),
  ]
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  downloadBlob(blob, filename)
}
