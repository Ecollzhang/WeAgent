const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')

function contains(relPath, fragment, message) {
  assert.ok(read(relPath).includes(fragment), `${message}: ${relPath}`)
}

const sandboxApi = read('src/api/sandbox.js')
contains(
  'src/api/sandbox.js',
  'export function readSessionRawFile',
  'sandbox files must be read through the authenticated API client'
)
assert.ok(
  sandboxApi.includes("responseType: 'text'") || sandboxApi.includes('responseType'),
  'authenticated raw-file reads must preserve text payloads'
)

contains(
  'src/utils/educationErrors.js',
  'asset_storage_capacity_exceeded',
  'upload capacity failures must map to a stable actionable message'
)
for (const page of [
  'src/views/education/CoursewareLibrary.vue',
  'src/views/education/KnowledgeCenter.vue',
  'src/views/education/LessonWorkbench.vue',
]) {
  contains(page, 'educationErrorMessage', 'all Education upload surfaces must share stable error mapping')
}

const workbench = read('src/components/ArtifactWorkbench/index.vue')
contains(
  'src/components/ArtifactWorkbench/index.vue',
  'readSessionRawFile',
  'artifact workbench must use authenticated raw-file reads'
)
assert.ok(
  !workbench.includes('fetch(getSessionRawFileUrl'),
  'artifact workbench must not use unauthenticated native fetch'
)
for (const kind of ["'markdown'", "'json'"]) {
  contains(
    'src/components/ArtifactWorkbench/index.vue',
    kind,
    `artifact workbench must expose a ${kind} preview kind`
  )
}
contains(
  'src/components/ArtifactWorkbench/index.vue',
  'URL.createObjectURL',
  'HTML previews must render from an authenticated Blob URL'
)

const messageBubble = read('src/components/MessageBubble/index.vue')
contains(
  'src/components/MessageBubble/index.vue',
  'readSessionRawFile',
  'message artifact previews must use authenticated reads'
)
contains(
  'src/components/MessageBubble/index.vue',
  'artifactJsonSummary',
  'JSON chat artifacts must show a readable summary instead of a compile preview'
)
assert.ok(
  !messageBubble.includes('fetch(getSessionRawFileUrl'),
  'message artifact previews must not issue unauthenticated native fetch'
)

const record = read('src/components/education/EmbeddedAgentRecord.vue')
contains(
  'src/components/education/EmbeddedAgentRecord.vue',
  'adoptedObject',
  'latest-product preview must be gated by a persisted adopted object'
)
assert.ok(
  !/previewLatestArtifact\(\)[\s\S]{0,400}\$router\.push/.test(record),
  'preview must not silently navigate away from the current business page'
)
contains(
  'src/components/education/EmbeddedAgentRecord.vue',
  'openBusinessPage',
  'business navigation must remain a separate explicit action'
)

for (const page of [
  'src/views/education/CoursewareLibrary.vue',
  'src/views/education/StudentInsights.vue',
]) {
  contains(page, '@preview=', 'business pages must handle adopted-object preview directly')
}
contains(
  'src/views/education/CoursewareLibrary.vue',
  'data-testid="courseware-adopted-preview"',
  'courseware latest product must open an in-page compiled preview'
)
contains(
  'src/views/education/CoursewareLibrary.vue',
  'visual-qa-slide-preview',
  'visual QA must show the compiled result for every slide'
)
contains(
  'src/views/education/StudentInsights.vue',
  'data-testid="student-insight-adopted-preview"',
  'student insight latest product must open a readable business summary'
)

console.log('education bugfix preview contract ok')
