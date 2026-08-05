const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')

const helper = read('src/utils/downloadBlob.js')
const card = read('src/components/education/EducationCard.vue')
const library = read('src/views/education/CoursewareLibrary.vue')

assert.ok(
  helper.includes('document.body.appendChild(link)') &&
    helper.includes('setTimeout') &&
    helper.includes('URL.revokeObjectURL(objectUrl)'),
  'blob downloads must keep the object URL alive until Chromium has accepted the download'
)

for (const source of [card, library]) {
  assert.ok(
    source.includes('downloadBlob'),
    'Education courseware downloads must use the shared safe blob download helper'
  )
}

const cardDownload = card.slice(
  card.indexOf('async downloadPptx()'),
  card.indexOf('openBusiness()', card.indexOf('async downloadPptx()'))
)
const libraryDownload = library.slice(
  library.indexOf('async downloadGenerated('),
  library.indexOf('openGeneratedEditor(', library.indexOf('async downloadGenerated('))
)
for (const method of [cardDownload, libraryDownload]) {
  assert.ok(
    !method.includes('URL.revokeObjectURL(objectUrl)'),
    'courseware export handlers must not synchronously revoke a just-clicked download URL'
  )
}

console.log('education export download contract ok')
