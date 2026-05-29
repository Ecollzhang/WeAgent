/**
 * Format a date to a relative time string.
 */
export function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = parseAppDate(dateStr)
  const now = new Date()
  const diff = now - date

  // Less than 1 minute
  if (diff < 60 * 1000) {
    return 'just now'
  }

  // Less than 1 hour
  if (diff < 60 * 60 * 1000) {
    const minutes = Math.floor(diff / (60 * 1000))
    return `${minutes} min ago`
  }

  // Less than 24 hours
  if (diff < 24 * 60 * 60 * 1000) {
    const hours = Math.floor(diff / (60 * 60 * 1000))
    return `${hours}h ago`
  }

  // Less than 7 days
  if (diff < 7 * 24 * 60 * 60 * 1000) {
    const days = Math.floor(diff / (24 * 60 * 60 * 1000))
    return `${days}d ago`
  }

  // Format as date
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')

  if (year === now.getFullYear()) {
    return `${month}-${day} ${hours}:${minutes}`
  }

  return `${year}-${month}-${day} ${hours}:${minutes}`
}

function parseAppDate(dateStr) {
  const value = String(dateStr || '').trim()
  if (!value) return new Date(NaN)

  const hasTimezone = /(?:z|[+-]\d{2}:?\d{2})$/i.test(value)
  if (hasTimezone) return new Date(value)

  const localDate = new Date(value)
  const utcDate = new Date(value.replace(' ', 'T') + 'Z')
  const now = new Date()

  // Backward compatibility: older backend returned UTC without "Z", which
  // browsers parsed as local time and showed fresh messages as 8h ago.
  const localDiff = now - localDate
  const utcDiff = now - utcDate
  if (
    Math.abs(utcDiff) < 10 * 60 * 1000 &&
    localDiff > 7 * 60 * 60 * 1000 &&
    localDiff < 9 * 60 * 60 * 1000
  ) {
    return utcDate
  }

  return localDate
}

/**
 * Truncate text to a maximum length.
 */
export function truncate(text, maxLength = 100) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}
