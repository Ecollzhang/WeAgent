function textFromValue(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string' || typeof value === 'number') return String(value).trim()
  if (Array.isArray(value)) return value.map(textFromValue).filter(Boolean).join('\n')
  if (typeof value === 'object') {
    const preferred = [
      'description', 'text', 'objective', 'title', 'name',
      'teacher_activity', 'student_activity', 'assessment',
    ]
    const parts = preferred.map(key => textFromValue(value[key])).filter(Boolean)
    if (parts.length) return parts.join(' · ')
  }
  return ''
}

function normalizeObjectives(value) {
  return Array.isArray(value)
    ? value.map(textFromValue).filter(Boolean).join('\n')
    : textFromValue(value)
}

function normalizeActivities(value) {
  if (!Array.isArray(value)) return textFromValue(value)
  return value.map((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return textFromValue(item)
    if (item.description) return textFromValue(item.description)
    return [
      textFromValue(item.name || item.title),
      textFromValue(item.teacher_activity),
      textFromValue(item.student_activity),
    ].filter(Boolean).join(' · ')
  }).filter(Boolean).join('\n\n')
}

function formatVersionTime(value, locale = 'zh-CN') {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleString(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function normalizeChoiceOption(option, index) {
  const expectedLabel = String.fromCharCode(65 + index)
  const rawLabel = option && typeof option === 'object'
    ? String(option.label || expectedLabel).trim().toUpperCase()
    : expectedLabel
  const label = /^[A-Z]$/.test(rawLabel) ? rawLabel : expectedLabel
  const rawText = option && typeof option === 'object'
    ? textFromValue(option.text || option.value)
    : textFromValue(option)
  const escapedLabel = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const text = rawText.replace(
    new RegExp(`^${escapedLabel}(?:[.)、．:：]|\\s)\\s*`, 'i'),
    ''
  )
  return `${label}. ${text}`
}

module.exports = {
  normalizeActivities,
  normalizeChoiceOption,
  normalizeObjectives,
  formatVersionTime,
}
