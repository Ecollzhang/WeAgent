const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8')
}

function assertContains(file, needle, message) {
  assert.ok(read(file).includes(needle), `${file}: ${message || `missing ${needle}`}`)
}

assertContains(
  'src/views/Settings.vue',
  "modelConfig.model === 'custom'",
  'custom model name input must only appear when Custom is selected'
)
assertContains(
  'src/views/Settings.vue',
  'v-model="modelConfig.custom_model"',
  'custom model name must be editable from Settings'
)
assertContains(
  'src/views/Settings.vue',
  "custom_model: ''",
  'Settings state must include custom_model'
)

console.log('model settings contract ok')
