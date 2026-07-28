const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')

function contains(relPath, fragment, message) {
  assert.ok(read(relPath).includes(fragment), `${message}: ${relPath}`)
}

const rail = 'src/components/education/EducationModuleRail.vue'
for (const label of [
  '教学空间',
  'PPT 与课件',
  '学生画像与评估',
  '模拟考试',
  '作业弱点',
  '课程思维导图',
]) {
  contains(rail, label, `role rail must expose ${label}`)
}
contains(
  rail,
  'membership_role',
  'course membership, not a cosmetic role toggle, must drive the rail'
)
contains(
  rail,
  'data-testid="education-course-selector"',
  'mixed-role users need an observable course selector'
)
contains(
  'src/components/education/EducationShell.vue',
  'EducationModuleRail',
  'all Education pages must share the product rail'
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
    'product_code: \'courseware\'',
    'ProductAgentRunPanel',
  ],
  'src/views/education/StudentInsights.vue': [
    'data-testid="student-insight-list"',
    '数据不足',
    'product_code: \'student_insight\'',
    'ProductAgentRunPanel',
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
    'ProductAgentRunPanel',
  ],
  'src/views/education/WeaknessCenter.vue': [
    'data-testid="weakness-evidence"',
    'evidence_item_version_ids',
    'product_code: \'weakness_analysis\'',
    'ProductAgentRunPanel',
  ],
  'src/views/education/MindMapCenter.vue': [
    'data-testid="course-mind-map"',
    'saveMindMapVersion',
    'product_code: \'course_mind_map\'',
    'ProductAgentRunPanel',
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
  'data-testid="product-agent-run"',
  'data-testid="product-agent-node"',
  'tool_calls',
  '已写入 Education',
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
