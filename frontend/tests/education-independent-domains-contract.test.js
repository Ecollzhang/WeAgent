const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')

function contains(relPath, fragment, message) {
  assert.ok(read(relPath).includes(fragment), `${message}: ${relPath}`)
}

const rail = read('src/components/education/EducationModuleRail.vue')
assert.ok(rail.includes('Education 教育中心'), 'rail must use a product-domain name')
assert.ok(rail.includes('教师领域'), 'teacher routes must be labelled as domains')
assert.ok(rail.includes('学习领域'), 'student routes must be labelled as domains')
assert.ok(!rail.includes('教学协作台'), 'normal navigation must not be an Agent console')
assert.ok(!rail.includes('教师工作台'), 'normal navigation must not be a workbench tab set')

contains(
  'src/api/education.js',
  '/courseware-context',
  'courseware must load one stable lesson context projection'
)
for (const fragment of [
  'fetchCoursewareContext',
  'selectedLessonId',
  'coursewareContext',
  '课时上下文',
  'canManageCourseware',
  'membership_role === \'teacher\'',
]) {
  contains(
    'src/views/education/CoursewareLibrary.vue',
    fragment,
    'courseware domain must be driven by course and lesson context'
  )
}

for (const fragment of ['作业满分', 'assignmentForm.max_score', 'max_score: this.assignmentForm.max_score']) {
  contains(
    'src/views/education/CourseSpace.vue',
    fragment,
    'assignments need an explicit scale for trustworthy class statistics'
  )
}

for (const fragment of [
  'studentInsightOverview',
  '最高分',
  '最低分',
  '平均分',
  '中位数',
  '完成率',
  '成绩分布',
  '待教师确认',
  'ScoreDistributionChart',
]) {
  contains(
    'src/views/education/StudentInsights.vue',
    fragment,
    'student insight domain must show official class analytics'
  )
}

for (const page of [
  'src/views/education/CoursewareLibrary.vue',
  'src/views/education/StudentInsights.vue',
  'src/views/education/MockExamCenter.vue',
  'src/views/education/WeaknessCenter.vue',
  'src/views/education/MindMapCenter.vue',
]) {
  contains(page, 'EmbeddedAgentRecord', 'Agent detail must be secondary and collapsible')
}

contains('src/router/index.js', '/education/help', 'help center route must exist')
contains('src/views/education/HelpCenter.vue', '教师快速开始', 'teacher guide must exist')
contains('src/views/education/HelpCenter.vue', '学生快速开始', 'student guide must exist')
contains(
  'src/views/education/HelpCenter.vue',
  'help-visual',
  'help center must combine visuals with short instructions'
)

for (const relPath of [
  'src/views/education/CoursewareLibrary.vue',
  'src/views/education/StudentInsights.vue',
  'src/views/education/HelpCenter.vue',
]) {
  contains(relPath, 'prefers-reduced-motion', 'domain motion must respect user settings')
}

console.log('education independent domains contract ok')
