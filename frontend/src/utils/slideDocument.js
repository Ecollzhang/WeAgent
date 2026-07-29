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

const PRESENTATION_THEMES = Object.freeze({
  clear_classroom: Object.freeze({
    label: '清朗课堂',
    description: '留白充足，青绿与暖橙点题',
    background: '#F4FAF8',
    surface: '#FFFFFF',
    primary: '#176D63',
    accent: '#E99B4B',
    text: '#203633',
    muted: '#6B817C',
  }),
  paper_annotation: Object.freeze({
    label: '纸张批注',
    description: '米白纸张、深蓝正文与朱红批注',
    background: '#F3EBDD',
    surface: '#FFF9EE',
    primary: '#243B5A',
    accent: '#C9563F',
    text: '#312E29',
    muted: '#766D62',
  }),
  storybook: Object.freeze({
    label: '童趣绘本',
    description: '柔和粉彩与圆润图形',
    background: '#F5F0FF',
    surface: '#FFFCFA',
    primary: '#31578C',
    accent: '#EF7964',
    secondary: '#71BEB4',
    text: '#29364C',
    muted: '#72809A',
  }),
  dark_focus: Object.freeze({
    label: '深色聚焦',
    description: '深蓝底与高对比亮色',
    background: '#0F172A',
    surface: '#17233A',
    primary: '#67E8F9',
    accent: '#FBBF24',
    text: '#F8FAFC',
    muted: '#CBD5E1',
  }),
})

function normalizePresentationTheme(value) {
  const theme = value && typeof value === 'object' ? value : {}
  const style = String(theme.style || theme.preset || theme.id || 'clear_classroom')
  const normalizedStyle = PRESENTATION_THEMES[style] ? style : 'clear_classroom'
  return { style: normalizedStyle, ...PRESENTATION_THEMES[normalizedStyle] }
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
  const theme = normalizePresentationTheme(source.theme)
  const slides = Array.isArray(source.slides) ? source.slides : []
  const pages = slides.map((slide, index) => `
    <section class="slide" data-slide="${index + 1}">
      <div class="counter">${String(index + 1).padStart(2, '0')}</div>
      <h1>${escapeHtml(slide.title || `Slide ${index + 1}`)}</h1>
      <div class="blocks">${(slide.blocks || []).map(renderBlock).join('')}</div>
      ${slide.speaker_notes ? `<aside>${escapeHtml(slide.speaker_notes)}</aside>` : ''}
    </section>`).join('')
  return `<!doctype html><html lang="zh-CN" data-theme="${theme.style}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(source.title || 'Education Courseware')}</title><style>
    :root{--background:${theme.background};--surface:${theme.surface};--primary:${theme.primary};--accent:${theme.accent};--secondary:${theme.secondary || theme.primary};--text:${theme.text};--muted:${theme.muted}}*{box-sizing:border-box}body{margin:0;padding:32px;background:var(--background);color:var(--text);font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif}.slide{position:relative;width:min(1120px,100%);aspect-ratio:16/9;min-height:630px;margin:0 auto 32px;padding:64px 72px;background:var(--surface);border:1px solid color-mix(in srgb,var(--primary) 18%,transparent);border-radius:22px;box-shadow:0 20px 60px rgba(23,43,61,.14);overflow:hidden}.slide:before{content:"";position:absolute;inset:0 0 auto 0;height:8px;background:linear-gradient(90deg,var(--primary),var(--accent))}.counter{position:absolute;right:32px;top:28px;color:var(--primary);font-weight:800;letter-spacing:.12em}.slide h1{margin:0 70px 30px 0;color:var(--primary);font-size:38px;line-height:1.25}.slide h2{margin:20px 0 12px;font-size:25px}.blocks{font-size:20px;line-height:1.65}.block{margin:12px 0}.block-question,.block-key-point,.block-tip{padding:14px 18px;border-left:4px solid var(--accent);background:color-mix(in srgb,var(--surface) 86%,var(--primary));border-radius:0 10px 10px 0}blockquote{margin:18px 0;padding:16px 22px;color:var(--muted);background:color-mix(in srgb,var(--surface) 86%,var(--primary));border-left:4px solid var(--primary)}table{width:100%;margin:18px 0;border-collapse:collapse;font-size:16px}th,td{padding:10px 12px;border:1px solid color-mix(in srgb,var(--primary) 20%,transparent);text-align:left;vertical-align:top}th{background:color-mix(in srgb,var(--surface) 82%,var(--primary));color:var(--primary)}aside{margin-top:32px;padding-top:14px;border-top:1px dashed var(--muted);color:var(--muted);font-size:13px}ul{padding-left:24px}html[data-theme="paper_annotation"] .slide{border-radius:4px;box-shadow:8px 12px 0 rgba(76,61,42,.08)}html[data-theme="paper_annotation"] .slide:before{inset:0 auto 0 42px;width:3px;height:auto;background:var(--accent)}html[data-theme="storybook"] .slide{border-radius:42px}html[data-theme="storybook"] .slide:after{content:"";position:absolute;right:-32px;bottom:-40px;width:170px;height:170px;border-radius:50%;background:var(--secondary);opacity:.25}html[data-theme="dark_focus"] .slide{box-shadow:0 24px 70px rgba(0,0,0,.38)}html[data-theme="dark_focus"] .block-question,html[data-theme="dark_focus"] .block-key-point,html[data-theme="dark_focus"] .block-tip{background:#21304a}@media(max-width:700px){body{padding:12px}.slide{min-height:0;padding:42px 28px}.slide h1{font-size:28px}.blocks{font-size:17px}}
  </style></head><body>${pages}</body></html>`
}

module.exports = {
  PRESENTATION_THEMES,
  escapeHtml,
  normalizePresentationTheme,
  objectText,
  renderSlideDocumentHtml,
}
