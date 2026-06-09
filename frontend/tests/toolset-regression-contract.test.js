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
  'src/views/SandboxTest.vue',
  "sendMode: 'chain'",
  'sandbox UI must default to the multi-agent chain mode'
)
assertContains(
  'src/views/SandboxTest.vue',
  'async handleChainSend',
  'sandbox UI must keep the multi-agent chain send path'
)
assertContains(
  'src/views/SandboxTest.vue',
  "type === 'agent_progress'",
  'sandbox UI must keep realtime agent progress event handling'
)
assertContains(
  'src/views/SandboxTest.vue',
  "type === 'file_write'",
  'sandbox UI must keep file/artifact event handling'
)
assertContains(
  'src/views/SandboxTest.vue',
  'tool_results: toolResults || []',
  'sandbox UI must preserve tool result display data on agent messages'
)
assertContains(
  'src/components/MessageBubble/index.vue',
  'currentProgress',
  'message bubbles must surface active progress'
)
assertContains(
  'src/components/MessageBubble/index.vue',
  'artifactElements',
  'message bubbles must render structured artifact elements'
)
assertContains(
  'src/components/MessageBubble/index.vue',
  "$emit('show-artifact'",
  'message bubbles must emit artifact preview events'
)
assertContains(
  'src/components/ArtifactPreview/index.vue',
  "name: 'ArtifactPreview'",
  'artifact preview component must remain available'
)

console.log('toolset regression contract ok')
