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
  'src/components/AgentEditForm/index.vue',
  '默认工具能力',
  'Agent form must expose default tool capabilities as a first-class section'
)
assertContains(
  'src/components/AgentEditForm/index.vue',
  'getToolsetCategories',
  'Agent capability selector must filter by the same toolset categories'
)
assertContains(
  'src/components/AgentEditForm/index.vue',
  'capabilityPickerType',
  'Agent capability selector must expose Skill/MCP/Plugin/Tool groups'
)
assertContains(
  'src/components/AgentEditForm/index.vue',
  'version_policy: \'pinned\'',
  'Agent capability selector must default new bindings to pinned versions'
)
assertContains(
  'src/components/AgentEditForm/index.vue',
  'granted_permissions',
  'Agent capability selector must preserve explicit permission grants'
)
assertContains(
  'src/components/AgentEditForm/index.vue',
  'getAgentCapabilityUpgrades',
  'Agent edit mode must surface manual upgrade hints'
)
assertContains(
  'src/components/AgentEditForm/index.vue',
  'deleteAgentCapability',
  'Agent edit mode must call the real unbind API for existing capability bindings'
)
assertContains(
  'src/components/AgentEditForm/index.vue',
  '能力已解绑',
  'Agent edit mode should tell users when a persisted binding was unbound'
)
assertContains(
  'src/views/AgentManager.vue',
  'capability_bindings: formData.capability_bindings || []',
  'Agent save flow must submit default capability bindings'
)

console.log('agent capability selector contract ok')
