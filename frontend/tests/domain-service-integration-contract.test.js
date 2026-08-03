const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const repoRoot = path.resolve(root, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')

const dashboard = read('src/views/Dashboard.vue')
assert.ok(
  dashboard.includes("checkVisible(this.$store.state.grayscale, this.activeDomain, 'ui.chat.services')"),
  'public conversation service selection must use the common grayscale contract'
)
assert.ok(
  dashboard.includes('v-if="chatServicesVisible"'),
  'a disabled public service selector must not remain visible'
)
assert.ok(
  dashboard.includes('type="checkbox" value="edu" v-model="newConversation.services"'),
  'the already-integrated Education service must be selectable in public chat'
)
assert.ok(
  !dashboard.includes('EDU · 待上线'),
  'the public chat must not describe the live Education service as unavailable'
)

const projectDetail = read('src/views/rd/RdProjectDetail.vue')
assert.ok(
  projectDetail.includes("path: '/dashboard'") &&
    projectDetail.includes('project_id: this.project.id'),
  'RD project pages must carry project context into the conversation shortcut'
)

const bubble = read('src/components/MessageBubble/index.vue')
for (const key of [
  'ui.chat.card.requirement',
  'ui.chat.card.bug',
  'ui.chat.card.iteration',
  'ui.chat.card.project',
]) {
  assert.ok(bubble.includes(key), `domain card missing grayscale key ${key}`)
}

const axiosSource = read('src/api/axios.js')
assert.ok(
  !axiosSource.includes("console.log('[axios-"),
  'the shared HTTP client must not log authenticated request or response bodies'
)

const localSettings = fs.readFileSync(
  path.join(repoRoot, '.claude', 'settings.local.json'),
  'utf8'
)
assert.ok(
  !localSettings.includes('backend/venv/Scripts/python.exe') &&
    !localSettings.includes('Bash(docker rm:*)'),
  'developer-local command permissions must not be merged into product code'
)

console.log('domain service integration contract ok')
