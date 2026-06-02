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
  'src/api/capabilities.js',
  "service.get(`/capabilities/${id}/provider-configs`",
  'provider profile list API must exist'
)
assertContains(
  'src/api/capabilities.js',
  "service.post(`/capabilities/${id}/provider-configs`",
  'provider profile create API must exist'
)
assertContains(
  'src/api/capabilities.js',
  "service.put(`/capabilities/${id}/provider-configs/${configId}`",
  'provider profile update API must exist'
)
assertContains(
  'src/api/capabilities.js',
  "service.post(`/capabilities/${id}/provider-configs/${configId}/test`",
  'provider profile test API must exist'
)
assertContains(
  'src/api/capabilities.js',
  "service.post(`/capabilities/${id}/provider-configs/${configId}/enable`",
  'provider profile enable API must exist'
)
assertContains(
  'src/api/capabilities.js',
  "service.post(`/capabilities/${id}/provider-configs/${configId}/disable`",
  'provider profile disable API must exist'
)
assertContains(
  'src/views/Tools.vue',
  '已保存配置',
  'provider config dialog must show saved profiles'
)
assertContains(
  'src/views/Tools.vue',
  'handleSaveProviderConfig',
  'provider config dialog must save profiles'
)
assertContains(
  'src/views/Tools.vue',
  'handleTestProviderConfig',
  'provider config dialog must test profiles'
)
assertContains(
  'src/views/Tools.vue',
  'handleEnableProviderConfig',
  'provider config dialog must enable profiles'
)
assertContains(
  'src/views/Tools.vue',
  'handleDisableProviderConfig',
  'provider config dialog must disable profiles'
)
assertContains(
  'src/views/Tools.vue',
  'handleSaveAndEnableProviderConfig',
  'provider config dialog must support save-and-enable flow'
)

console.log('tool provider config UI contract ok')
