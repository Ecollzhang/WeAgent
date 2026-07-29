const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')

const sidebar = read('src/components/Sidebar/index.vue')
const shell = read('src/components/education/EducationShell.vue')
const courseSpace = read('src/views/education/CourseSpace.vue')
const router = read('src/router/index.js')

for (const label of [
  '教学空间',
  'PPT 与课件',
  '学生画像与评估',
  '模拟考试',
  '课程思维导图',
]) {
  assert.ok(sidebar.includes(label), `global sidebar missing ${label}`)
}

assert.ok(sidebar.includes('educationDomainNavItems'), 'Education domains must be computed')
assert.ok(sidebar.includes('membership_role'), 'server membership must choose domain set')
assert.ok(sidebar.includes('isNavActive'), 'active domain must use route metadata')
assert.ok(!shell.includes('EducationModuleRail'), 'a second Education rail is forbidden')
assert.ok(shell.includes('EducationCourseContext'), 'course context must be in the header')

for (const marker of [
  "{ key: 'materials', label: '课件与材料'",
  "{ key: 'assignments', label: '完成作业'",
  "{ key: 'weaknesses', label: '作业弱点'",
  'student-published-assets',
  "activeTab === 'weaknesses'",
]) {
  assert.ok(courseSpace.includes(marker), `student teaching space missing ${marker}`)
}

assert.ok(
  router.includes("educationModule: 'teaching-space'"),
  'teaching-space routes must provide exact active metadata'
)
assert.ok(
  router.includes("educationRole: 'teacher'"),
  'teacher product routes must declare their role'
)
assert.ok(
  router.includes("educationRole: 'student'"),
  'student product routes must declare their role'
)

console.log('education unified navigation contract ok')
