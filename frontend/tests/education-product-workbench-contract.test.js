const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')

function contains(relPath, fragment, message) {
  assert.ok(read(relPath).includes(fragment), `${message}: ${relPath}`)
}

const rail = 'src/components/Sidebar/index.vue'
for (const label of [
  '教学空间',
  'PPT 与课件',
  '学生画像与评估',
  '模拟考试',
  '课程思维导图',
]) {
  contains(rail, label, `global role navigation must expose ${label}`)
}
contains(
  rail,
  'membership_role',
  'course membership, not a cosmetic role toggle, must drive global navigation'
)
contains(
  'src/components/education/EducationCourseContext.vue',
  'data-testid="education-course-selector"',
  'mixed-role users need an observable header course selector'
)
assert.ok(
  !read('src/components/education/EducationShell.vue').includes('EducationModuleRail'),
  'all Education pages must remove the duplicate product rail'
)

const routeContracts = [
  '/education/teacher/courseware',
  '/education/teacher/insights',
  '/education/student/mock-exams',
  '/education/student/weaknesses',
  '/education/student/mind-maps',
  '/education/courses/:courseId/knowledge',
]
for (const route of routeContracts) {
  contains('src/router/index.js', route, `router must expose ${route}`)
}

const apiContracts = [
  '/assets',
  '/knowledge-center',
  '/questions',
  '/papers/compose',
  '/knowledge-resources',
  '/mock-exams',
  '/weakness-analysis',
  '/mind-maps',
  '/student-insights',
  '/product-agent-runs',
]
for (const endpoint of apiContracts) {
  contains('src/api/education.js', endpoint, `frontend API must call ${endpoint}`)
}

const pages = {
  'src/views/education/CoursewareLibrary.vue': [
    'data-testid="courseware-upload"',
    'downloadCourseAsset',
    'exportEducationContent',
    'SlideDocumentEditor',
    'saveContentVersion',
    'saveGeneratedEditor',
    '结构化课件版本',
    "['pptx', 'docx', 'pdf', 'html', 'json']",
    'product_code: \'courseware\'',
    'EmbeddedAgentRecord',
  ],
  'src/views/education/StudentInsights.vue': [
    'data-testid="student-insight-list"',
    '数据不足',
    'product_code: \'student_insight\'',
    'EmbeddedAgentRecord',
  ],
  'src/views/education/KnowledgeCenter.vue': [
    'data-testid="question-bank"',
    'data-testid="paper-bank"',
    'data-testid="course-knowledge-base"',
  ],
  'src/views/education/MockExamCenter.vue': [
    'data-testid="mock-exam-generator"',
    'saveMockExamAnswers',
    'product_code: \'mock_exam\'',
    'EmbeddedAgentRecord',
  ],
  'src/views/education/WeaknessCenter.vue': [
    'data-testid="weakness-evidence"',
    'evidence_item_version_ids',
    'product_code: \'weakness_analysis\'',
    'EmbeddedAgentRecord',
  ],
  'src/views/education/MindMapCenter.vue': [
    'data-testid="course-mind-map"',
    'saveMindMapVersion',
    'product_code: \'course_mind_map\'',
    'EmbeddedAgentRecord',
  ],
}
for (const [file, fragments] of Object.entries(pages)) {
  for (const fragment of fragments) {
    contains(file, fragment, `${file} is missing its persisted product contract`)
  }
}

contains(
  'src/views/education/CourseSpace.vue',
  '课程知识中心',
  'teaching space must link to the course Knowledge Center'
)
for (const fragment of [
  'data-testid="agent-roster-import"',
  "product_code: 'roster_import'",
  'EmbeddedAgentRecord',
  'parseRoster',
]) {
  contains(
    'src/views/education/CourseSpace.vue',
    fragment,
    'teacher roster management must expose the scoped Agent import flow'
  )
}
contains(
  'src/store/modules/education.js',
  'activeCourse',
  'role workbenches must share server-owned active-course context'
)
contains(
  'src/store/modules/education.js',
  'restoreProductAgentRun',
  'product pages must restore persisted Agent progress after refresh'
)
for (const fragment of [
  'productAgentRuns',
  'fetchProductAgentRuns',
  'SET_PRODUCT_AGENT_RUNS',
]) {
  contains(
    'src/store/modules/education.js',
    fragment,
    'product pages must preserve a compact collaboration history'
  )
}
for (const fragment of [
  '协作历史',
  '返回本次聊天',
  'previewLatestArtifact',
  'openConversation',
]) {
  contains(
    'src/components/education/EmbeddedAgentRecord.vue',
    fragment,
    'latest run must link to chat and expose compact history'
  )
}
for (const fragment of [
  'EducationChatContext',
  'educationContext',
  'loadEducationContext',
  'getConversation(conversationId)',
  "commit('conversation/ADD_CONVERSATION', conversation)",
]) {
  contains(
    'src/views/Dashboard.vue',
    fragment,
    'Education chat must link back to its durable business context'
  )
}
contains(
  'src/api/education.js',
  'getEducationConversationContext',
  'chat context must be resolved by an authorized Education API'
)
for (const fragment of [
  'data-testid="product-agent-run"',
  'data-testid="product-agent-node"',
  'tool_calls',
  '已写入 Education',
  'recoverable_draft',
  '修复并保存草稿',
  'recover-draft',
]) {
  contains(
    'src/components/education/ProductAgentRunPanel.vue',
    fragment,
    'product Agent collaboration must be visible and auditable'
  )
}
for (const forbidden of ['Conversation：', 'Sandbox：', 'tool_grant']) {
  assert.ok(
    !read('src/components/education/ProductAgentRunPanel.vue').includes(forbidden),
    `product Agent panel must not expose ${forbidden}`
  )
}

console.log('education product workbench contract ok')
