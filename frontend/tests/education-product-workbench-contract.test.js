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
]
for (const endpoint of apiContracts) {
  contains('src/api/education.js', endpoint, `frontend API must call ${endpoint}`)
}

const pages = {
  'src/views/education/CoursewareLibrary.vue': [
    'data-testid="courseware-upload"',
    'downloadCourseAsset',
  ],
  'src/views/education/StudentInsights.vue': [
    'data-testid="student-insight-list"',
    '数据不足',
  ],
  'src/views/education/KnowledgeCenter.vue': [
    'data-testid="question-bank"',
    'data-testid="paper-bank"',
    'data-testid="course-knowledge-base"',
  ],
  'src/views/education/MockExamCenter.vue': [
    'data-testid="mock-exam-generator"',
    'saveMockExamAnswers',
  ],
  'src/views/education/WeaknessCenter.vue': [
    'data-testid="weakness-evidence"',
    'evidence_item_version_ids',
  ],
  'src/views/education/MindMapCenter.vue': [
    'data-testid="course-mind-map"',
    'saveMindMapVersion',
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

console.log('education product workbench contract ok')

