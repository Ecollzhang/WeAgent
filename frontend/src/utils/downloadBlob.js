export default function downloadBlob(blob, filename) {
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()

  // Chromium accepts blob downloads asynchronously. Revoking the URL in the
  // same task can cancel an otherwise successful download.
  setTimeout(() => {
    link.remove()
    URL.revokeObjectURL(objectUrl)
  }, 30000)
}
