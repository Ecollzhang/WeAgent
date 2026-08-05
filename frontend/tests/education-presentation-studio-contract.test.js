const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')
const courseware = read('src/views/education/CoursewareLibrary.vue')
const editor = read('src/components/education/SlideDocumentEditor.vue')
const api = read('src/api/education.js')
const slideUtils = read('src/utils/slideDocument.js')

for (const label of ['清朗课堂', '纸张批注', '童趣绘本', '深色聚焦']) {
  assert.ok(slideUtils.includes(label), `presentation registry must offer ${label}`)
}

for (const fragment of [
  'theme_style',
  'getContentVisualQa',
  '逐页视觉检查',
  'visual-qa-dialog',
]) {
  assert.ok(courseware.includes(fragment), `courseware studio is missing ${fragment}`)
}

for (const fragment of [
  'PRESENTATION_THEMES',
  '课件风格',
  'addSlide',
  'removeSlide',
  'data-testid="presentation-theme-selector"',
]) {
  assert.ok(editor.includes(fragment), `structured editor is missing ${fragment}`)
}

assert.ok(api.includes('/visual-qa'), 'frontend must call the durable visual QA endpoint')
assert.ok(
  courseware.includes('preview_data_url'),
  'visual QA must render the exact exported PPTX page image'
)
assert.ok(
  courseware.includes('v-for="slide in visualQaReport.rendered_pages"'),
  'visual QA must enumerate every exported PPTX page, including generated covers'
)
assert.ok(
  !courseware.includes(':html="renderVisualQaSlide(slide)"'),
  'visual QA must not present a reconstructed HTML slide as the exported PPTX'
)
console.log('education presentation studio contract ok')
