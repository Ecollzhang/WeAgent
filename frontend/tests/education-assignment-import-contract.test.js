const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')
const contains = (relPath, fragment, message) => {
  assert.ok(read(relPath).includes(fragment), `${message}: ${relPath}`)
}

for (const fragment of [
  'assignment-imports',
  'uploadAssignmentSource',
  'processAssignmentImport',
  "headers: { 'Content-Type': 'multipart/form-data' }",
]) {
  contains(
    'src/api/education.js',
    fragment,
    'assignment source import needs an explicit persisted API contract'
  )
}

for (const fragment of [
  'data-testid="assignment-import-upload"',
  '附件发布',
  '识别为可编辑作业',
  'handleAssignmentSource',
  'assignmentImportStatus',
  'source_asset_ids',
]) {
  contains(
    'src/views/education/CourseSpace.vue',
    fragment,
    'teacher assignment creation must expose attachment and OCR modes'
  )
}

for (const fragment of [
  'assignment-source-assets',
  'source_assets',
  'downloadAssignmentAsset',
]) {
  contains(
    'src/views/education/AssignmentWorkspace.vue',
    fragment,
    'published assignment source files must be downloadable in the student workspace'
  )
}

console.log('Education assignment import contract passed')
