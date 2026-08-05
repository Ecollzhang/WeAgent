const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relative => fs.readFileSync(path.join(root, relative), 'utf8')
const assert = (condition, message) => {
  if (!condition) throw new Error(message)
}

const api = read('src/api/education.js')
const store = read('src/store/modules/education.js')
const page = read('src/views/education/AssignmentWorkspace.vue')

assert(api.includes('export function updateAssignment'), 'assignment update API is required')
assert(api.includes('service.patch(url(`/assignments/${assignmentId}`)'), 'assignment update must PATCH')
assert(store.includes('async saveAssignmentVersion'), 'store must expose versioned assignment save')
assert(page.includes("import RichMaterialEditor"), 'teacher content editor must reuse rich editor')
assert(page.includes('<RichMaterialEditor'), 'teacher content needs visual rich-text editing')
assert(page.includes('editingContent'), 'assignment page needs explicit edit state')
assert(page.includes('assignmentDraft'), 'assignment edit form needs isolated draft state')
assert(page.includes('hasUnsavedChanges'), 'publish flow must detect unsaved changes')
assert(page.includes('saveAssignmentVersion'), 'teacher page must save immutable versions')
assert(page.includes("event.key.toLowerCase() === 's'"), 'Ctrl/Cmd+S shortcut is required')
assert(page.includes('published_version'), 'teacher must see published snapshot version')
assert(page.includes('current_version'), 'teacher must see current draft version')
assert(page.includes('assignment-content-section'), 'content, attachments and rubric need separated sections')
assert(page.includes('max-height: 420px'), 'long assignment content needs a bounded scroll surface')
assert(
  page.includes('<p class="instruction">{{ instructionText }}</p>'),
  'student assignment instructions must use the bounded scroll surface'
)

console.log('education assignment version editor contract ok')
