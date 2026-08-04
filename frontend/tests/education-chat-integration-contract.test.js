const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')

const dashboard = read('src/views/Dashboard.vue')
assert.ok(
  dashboard.includes('getEducationConversationOptions') &&
    dashboard.includes('bootstrapEducationConversation'),
  'EDU chat creation must use the Education bootstrap boundary'
)
assert.ok(
  dashboard.includes('v-if="isEducationWorkspace"') &&
    dashboard.includes('newConversation.courseId') &&
    dashboard.includes('newConversation.lessonId') &&
    dashboard.includes('membership_role'),
  'EDU chat creation must expose course, optional lesson and read-only membership role'
)
assert.ok(
  dashboard.includes('v-if="!isEducationWorkspace && chatServicesVisible"') &&
    dashboard.includes('service-checkboxes'),
  'low-level service selection must not be shown in the Education workspace'
)
assert.ok(
  !dashboard.includes('type="checkbox" value="edu" v-model="newConversation.services"'),
  'users must not grant the EDU service with a client-side checkbox'
)
assert.ok(
  dashboard.includes('buildEducationAgentTree') &&
    dashboard.includes('educationOptions.agents'),
  'EDU Agent choices must be rendered from the trusted role-filtered manifest'
)
assert.ok(
  dashboard.includes(':key="currentConversation?.id || \'empty-chat\'"'),
  'switching EDU conversations must recreate the chat view so title, messages and send target stay aligned'
)

const educationApi = read('src/api/education.js')
assert.ok(
  educationApi.includes('/conversations/options') &&
    educationApi.includes('/conversations/bootstrap') &&
    educationApi.includes('/context'),
  'Education API client must expose options, bootstrap and durable context recovery'
)

const bubble = read('src/components/MessageBubble/index.vue')
assert.ok(
  bubble.includes('EducationCard') &&
    bubble.includes("ui.chat.card.education") &&
    bubble.includes("el.type === 'education_card'"),
  'chat messages must render the unified gray-controlled Education card'
)

const chatWindow = read('src/components/ChatWindow/index.vue')
assert.ok(
  !chatWindow.includes('kbDomainLabel(conversation.kb_domain)') &&
    chatWindow.includes('{{ kbDomainLabel }}'),
  'the EDU/RAG context badge must render the computed label without calling it as a function'
)

const card = read('src/components/education/EducationCard.vue')
for (const token of ['canonical_ref', '预览', '打开业务页面', '继续协作']) {
  assert.ok(card.includes(token), `Education card contract missing ${token}`)
}

console.log('education chat integration contract ok')
