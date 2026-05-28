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
  'router must expose the Capability Library'
)
assertContains(
  'src/components/Sidebar/index.vue',
  'to="/capabilities"',
  'sidebar must expose Capability Library navigation'
)
assertContains(
  'src/views/CapabilityLibrary.vue',
  "type: 'skill'",
  'library must show Skill as a peer capability type'
)
assertContains(
  'src/views/CapabilityLibrary.vue',
  "type: 'mcp'",
  'library must show MCP as a peer capability type'
)
assertContains(
  'src/views/CapabilityLibrary.vue',
  "type: 'plugin'",
  'library must show Plugin as manifest-only scope'
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
