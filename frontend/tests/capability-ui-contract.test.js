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

function assertNotContains(file, needle, message) {
  assert.ok(!read(file).includes(needle), `${file}: ${message || `unexpected ${needle}`}`)
}

assertContains(
  'src/api/capabilities.js',
  "service.get('/capabilities'",
  'capability API wrapper must list capability records'
)
assertContains(
  'src/api/capabilities.js',
  "service.post('/capabilities/skills'",
  'capability API wrapper must create Skill markdown assets'
)
assertContains(
  'src/api/capabilities.js',
  "service.post(`/capabilities/${id}/versions`",
  'capability API wrapper must create pinned Skill versions'
)
assertContains(
  'src/api/capabilities.js',
  "service.get(`/agents/${agentId}/capabilities/upgrades`",
  'capability API wrapper must expose Agent upgrade status'
)
assertContains(
  'src/router/index.js',
  "path: '/capabilities'",
  'router must keep a compatibility route for old capability links'
)
assertContains(
  'src/router/index.js',
  "redirect: '/tools'",
  'Capability Library route must redirect to unified toolset page'
)
assertNotContains(
  'src/components/Sidebar/index.vue',
  'to="/capabilities"',
  'sidebar must not expose Capability Library as a separate product entry'
)
assertContains(
  'src/views/Tools.vue',
  "type: 'skill'",
  'toolset must show Skill as a peer capability type'
)
assertContains(
  'src/views/Tools.vue',
  "type: 'mcp'",
  'toolset must show MCP as a peer capability type'
)
assertContains(
  'src/views/Tools.vue',
  "type: 'plugin'",
  'toolset must show Plugin as manifest-only scope'
)
assertContains(
  'src/components/AgentEditForm/index.vue',
  'capability_bindings',
  'Agent form must send default capability bindings'
)
assertContains(
  'src/components/AgentEditForm/index.vue',
  'granted_permissions',
  'Agent form must show explicit permission grants'
)

console.log('capability UI contract ok')
