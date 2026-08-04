const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')

const dashboard = read('src/views/Dashboard.vue')
assert.ok(
  dashboard.includes('rememberConversationSelection') &&
    dashboard.includes('restoreConversationSelection') &&
    dashboard.includes('fallbackConversation') &&
    dashboard.includes('routeConversation'),
  'chat selection must survive refresh and workspace switches instead of hiding the composer'
)

const chatWindow = read('src/components/ChatWindow/index.vue')
assert.ok(
  chatWindow.includes("'ui.chat.header.compact_title'") &&
    chatWindow.includes('compact-education-title') &&
    chatWindow.includes('education-title-popover') &&
    chatWindow.includes('trigger="click"'),
  'Education chat titles must use a gray-controlled single-line click popover treatment'
)

const courseware = read('src/views/education/CoursewareLibrary.vue')
assert.ok(
  courseware.includes('getCachedVisualQa') &&
    courseware.includes('cacheVisualQa') &&
    courseware.includes('visualQaCacheKey'),
  'PPTX visual QA must reuse the version-scoped in-memory result after the first load'
)

const educationHome = read('src/views/education/EducationHome.vue')
assert.ok(
  educationHome.includes('v-if="agentCourseCreateVisible"') &&
    educationHome.includes("'feature.education.chat.manual_create'"),
  'Agent course bootstrap entry must follow the Education chat grayscale switch'
)

console.log('education chat UI stability contract ok')
