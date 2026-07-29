function escapeHtml(value) {
  return String(value === null || value === undefined ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function objectText(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  if (Array.isArray(value)) return value.map(objectText).filter(Boolean).join(' · ')
  if (typeof value === 'object') return Object.values(value).map(objectText).filter(Boolean).join(' · ')
  return ''
}

function renderBlock(block) {
  const type = String((block && block.type) || 'text')
  const content = block && block.content
  if (content && typeof content === 'object' && !Array.isArray(content)
      && Array.isArray(content.headers) && Array.isArray(content.rows)) {
    const head = content.headers.map(item => `<th>${escapeHtml(item)}</th>`).join('')
    const rows = content.rows.map(row => `<tr>${row.map(item => `<td>${escapeHtml(item)}</td>`).join('')}</tr>`).join('')
    return `<table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`
  }
  if (Array.isArray(content)) {
    const items = content.map(item => `<li>${escapeHtml(objectText(item))}</li>`).join('')
    return `<ul class="block block-${escapeHtml(type)}">${items}</ul>`
  }
  const text = escapeHtml(objectText(content)).replace(/\n/g, '<br>')
  if (['heading', 'subheading'].includes(type)) return `<h2>${text}</h2>`
  if (type === 'quote') return `<blockquote>${text}</blockquote>`
  return `<div class="block block-${escapeHtml(type)}">${text}</div>`
}

function renderSlideDocumentHtml(document) {
  const source = document && typeof document === 'object' ? document : {}
  const theme = source.theme || {}
  const primary = /^#[0-9a-f]{6}$/i.test(theme.primary_color || '') ? theme.primary_color : '#1f5f5a'
  const accent = /^#[0-9a-f]{6}$/i.test(theme.accent_color || '') ? theme.accent_color : '#e49c54'
  const slides = Array.isArray(source.slides) ? source.slides : []
  const pages = slides.map((slide, index) => `
    <section class="slide" data-slide="${index + 1}">
      <div class="counter">${String(index + 1).padStart(2, '0')}</div>
      <h1>${escapeHtml(slide.title || `Slide ${index + 1}`)}</h1>
      <div class="blocks">${(slide.blocks || []).map(renderBlock).join('')}</div>
      ${slide.speaker_notes ? `<aside>${escapeHtml(slide.speaker_notes)}</aside>` : ''}
    </section>`).join('')
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(source.title || 'Education Courseware')}</title><style>
    :root{--primary:${primary};--accent:${accent}}*{box-sizing:border-box}body{margin:0;padding:32px;background:#eef4f2;color:#233532;font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif}.slide{position:relative;width:min(1120px,100%);min-height:630px;margin:0 auto 32px;padding:64px 72px;background:#fff;border:1px solid #d8e6e2;border-radius:22px;box-shadow:0 20px 60px rgba(33,80,73,.12);overflow:hidden}.slide:before{content:"";position:absolute;inset:0 0 auto 0;height:8px;background:linear-gradient(90deg,var(--primary),var(--accent))}.counter{position:absolute;right:32px;top:28px;color:var(--primary);font-weight:800;letter-spacing:.12em}.slide h1{margin:0 70px 30px 0;color:var(--primary);font-size:34px}.slide h2{margin:20px 0 12px;font-size:24px}.blocks{font-size:18px;line-height:1.75}.block{margin:12px 0}.block-question,.block-key-point,.block-tip{padding:14px 18px;border-left:4px solid var(--accent);background:#f7faf9;border-radius:0 10px 10px 0}blockquote{margin:18px 0;padding:16px 22px;color:#4b625e;background:#f7faf9;border-left:4px solid var(--primary)}table{width:100%;margin:18px 0;border-collapse:collapse;font-size:15px}th,td{padding:10px 12px;border:1px solid #d9e5e2;text-align:left;vertical-align:top}th{background:#edf5f2;color:var(--primary)}aside{margin-top:32px;padding-top:14px;border-top:1px dashed #c7d7d3;color:#72827f;font-size:13px}ul{padding-left:24px}@media(max-width:700px){body{padding:12px}.slide{min-height:0;padding:42px 28px}.slide h1{font-size:26px}}
  </style></head><body>${pages}</body></html>`
}

module.exports = { escapeHtml, objectText, renderSlideDocumentHtml }
