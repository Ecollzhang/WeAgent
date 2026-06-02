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
  'src/api/toolsets.js',
  "service.get('/toolsets/categories'",
  'toolset category API wrapper must list categories'
)
assertContains(
  'src/api/toolsets.js',
  "service.post('/toolsets/categories'",
  'toolset category API wrapper must create user categories'
)
assertContains(
  'src/api/capabilities.js',
  "service.post('/capabilities/import/preview'",
  'toolset import must use preview before creating capabilities'
)
assertContains(
  'src/api/capabilities.js',
  "service.post('/capabilities/import/confirm'",
  'toolset import must require an explicit confirm call'
)
assertContains(
  'src/api/capabilities.js',
  "service.post('/capabilities/import/mcp-manifest'",
  'toolset import must expose a dedicated MCP manifest endpoint'
)
assertContains(
  'src/api/capabilities.js',
  "service.get(`/capabilities/${id}/assets`",
  'toolset detail must be able to load capability assets'
)
assertContains(
  'src/api/capabilities.js',
  "service.get(`/capabilities/${id}/audits`",
  'toolset detail must be able to load capability audit records'
)
assertContains(
  'src/api/capabilities.js',
  "service.get(`/capabilities/${id}/delete-impact`",
  'toolset detail must be able to preview delete impact before deleting'
)
assertContains(
  'src/api/capabilities.js',
  "service.delete(`/capabilities/${id}`",
  'toolset detail must be able to delete user capabilities'
)
assertContains(
  'src/api/capabilities.js',
  "service.get(`/capabilities/${id}/provider-configs`",
  'configurable tools must load provider profiles from the backend'
)
assertContains(
  'src/api/capabilities.js',
  "service.post(`/capabilities/${id}/provider-configs`",
  'configurable tools must create provider profiles through the backend'
)
assertContains(
  'src/api/capabilities.js',
  "service.put(`/capabilities/${id}/provider-configs/${configId}`",
  'configurable tools must update provider profiles through the backend'
)
assertContains(
  'src/api/capabilities.js',
  "service.post(`/capabilities/${id}/provider-configs/${configId}/test`",
  'configurable tools must test provider profiles through the backend'
)
assertContains(
  'src/api/capabilities.js',
  "service.post(`/capabilities/${id}/provider-configs/${configId}/enable`",
  'configurable tools must enable provider profiles through the backend'
)
assertContains(
  'src/api/capabilities.js',
  "service.post(`/capabilities/${id}/provider-configs/${configId}/disable`",
  'configurable tools must disable provider profiles through the backend'
)
assertContains(
  'src/api/capabilities.js',
  "service.delete(`/agents/${agentId}/capabilities/${bindingId}`",
  'agent capability bindings must have a real unbind API'
)
assertContains(
  'src/router/index.js',
  "path: '/capabilities'",
  'legacy capability route must still exist for compatibility'
)
assertContains(
  'src/router/index.js',
  "redirect: '/tools'",
  'legacy capability route must redirect to the unified toolset page'
)
assertNotContains(
  'src/components/Sidebar/index.vue',
  'to="/capabilities"',
  'sidebar must not expose a separate capability library entry'
)
assertContains(
  'src/views/Tools.vue',
  'activeCategoryId',
  'toolset page must keep category as first-level selection'
)
assertContains(
  'src/views/Tools.vue',
  "type: 'skill'",
  'toolset page must show Skill as a peer type'
)
assertContains(
  'src/views/Tools.vue',
  "type: 'mcp'",
  'toolset page must show MCP as a peer type'
)
assertContains(
  'src/views/Tools.vue',
  "type: 'plugin'",
  'toolset page must show Plugin as a peer type'
)
assertContains(
  'src/views/Tools.vue',
  "type: 'tool'",
  'toolset page must show Tool as a peer type'
)
assertContains(
  'src/views/Tools.vue',
  'categoryDialog',
  'toolset page must expose user category management'
)
assertContains(
  'src/views/Tools.vue',
  'category_id: this.activeCategoryId',
  'new/imported capabilities must land in the active category'
)
assertContains(
  'src/views/Tools.vue',
  'clearSelection',
  'detail panel must be collapsible'
)
assertContains(
  'src/views/Tools.vue',
  'ensureActiveTypeHasContent',
  'category changes must focus a non-empty capability type when possible'
)
assertContains(
  'src/views/Tools.vue',
  'toolDefinition',
  'Tool details must show a human-readable definition instead of raw manifest JSON'
)
assertContains(
  'src/views/Tools.vue',
  'sourceLabel',
  'Tool details must translate internal sources such as builtin into user-facing labels'
)
assertContains(
  'src/views/Tools.vue',
  '内部标识',
  'Tool IDs should be shown as internal identifiers, not as the primary source'
)
assertContains(
  'src/views/Tools.vue',
  'toolStatusLabel',
  'Tool cards/details must expose implemented/partial/requires-config/deferred status'
)
assertContains(
  'src/views/Tools.vue',
  'isVisibleCapability',
  'toolset page must filter hidden/deferred capabilities out of the primary catalog'
)
assertContains(
  'src/views/Tools.vue',
  'isConfigurableTool',
  'requires-config tools shown in the catalog must have a real configuration entry point'
)
assertContains(
  'src/views/Tools.vue',
  'providerConfigDialog',
  'toolset page must model a frontend provider configuration window'
)
assertContains(
  'src/views/Tools.vue',
  'providerConfigs',
  'toolset page must keep provider profile list state'
)
assertContains(
  'src/views/Tools.vue',
  'fetchProviderConfigs',
  'toolset page must load saved provider profiles'
)
assertContains(
  'src/views/Tools.vue',
  'handleSaveProviderConfig',
  'toolset page must create or update provider profiles'
)
assertContains(
  'src/views/Tools.vue',
  'handleTestProviderConfig',
  'toolset page must let users test provider profiles'
)
assertContains(
  'src/views/Tools.vue',
  'handleEnableProviderConfig',
  'toolset page must let users enable tested provider profiles'
)
assertContains(
  'src/views/Tools.vue',
  'handleDisableProviderConfig',
  'toolset page must let users disable provider profiles'
)
assertContains(
  'src/views/Tools.vue',
  'openProviderConfigDialog',
  'tool details must expose a user-facing configuration action for configurable tools'
)
assertContains(
  'src/views/Tools.vue',
  '配置能力',
  'configurable provider tools must use user-facing configuration wording'
)
assertContains(
  'src/views/Tools.vue',
  "path: 'TOOL.md'",
  'Tool file view must expose TOOL.md as the Agent-facing documentation'
)
assertContains(
  'src/views/Tools.vue',
  'toolHandler',
  'Tool details must summarize the runtime handler separately from raw manifest JSON'
)

assertContains(
  'src/views/Tools.vue',
  'openImportWizard',
  'toolset page must expose a unified import wizard'
)
assertContains(
  'src/views/Tools.vue',
  'previewCapabilityImport',
  'toolset import wizard must call preview API'
)
assertContains(
  'src/views/Tools.vue',
  'confirmCapabilityImport',
  'toolset import wizard must call confirm API'
)
assertContains(
  'src/views/Tools.vue',
  'importMcpManifest',
  'toolset import wizard must call the dedicated MCP manifest API'
)
assertContains(
  'src/views/Tools.vue',
  'label="mcp"',
  'toolset import wizard must expose MCP manifest as a frontend source'
)
assertContains(
  'src/views/Tools.vue',
  "source_type: 'mcp'",
  'toolset import dialog must model MCP manifest source state'
)
assertContains(
  'src/views/Tools.vue',
  'mcp_manifest_text',
  'toolset import dialog must store editable MCP manifest JSON'
)
assertContains(
  'src/views/Tools.vue',
  'upload_base64',
  'zip bundle upload must be represented as a base64 preview payload'
)
assertNotContains(
  'src/views/Tools.vue',
  'label="repo"',
  'repo import should not be exposed while only local backend paths are supported'
)
assertNotContains(
  'src/views/Tools.vue',
  "sourceType === 'repo'",
  'repo import branch should not be part of the user-facing import wizard'
)
assertContains(
  'src/views/Tools.vue',
  'getCapabilityAssets',
  'detail file view must load persisted skill bundle assets'
)
assertContains(
  'src/views/Tools.vue',
  'getCapabilityAudits',
  'detail audit view must load security audit records'
)
assertContains(
  'src/views/Tools.vue',
  'handleDeleteCapability',
  'toolset detail panel must expose user capability deletion'
)
assertContains(
  'src/views/Tools.vue',
  'getCapabilityDeleteImpact',
  'toolset deletion must show backend impact before archiving'
)
assertContains(
  'src/views/Tools.vue',
  'capabilityIconClass',
  'toolset cards must resolve icons from capability definitions'
)
assertContains(
  'src/views/Tools.vue',
  'toolDefinition(capability).icon',
  'Tool cards must prefer the Tool manifest icon over the generic Tool type icon'
)
assertNotContains(
  'src/views/Tools.vue',
  ':class="typeMeta(capability.type).icon"',
  'capability cards must not force every Tool to use the generic type icon'
)
assertNotContains(
  'src/views/Tools.vue',
  '.detail-header span',
  'detail header text styles must not broadly override the detail icon container'
)

console.log('toolset UI contract ok')
