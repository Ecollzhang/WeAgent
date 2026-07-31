const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')

const sidebar = read('src/components/Sidebar/index.vue')
const shell = read('src/components/education/EducationShell.vue')
const courseSpace = read('src/views/education/CourseSpace.vue')
const router = read('src/router/index.js')
const workspaceSwitcher = read('src/components/WorkspaceSwitcher/index.vue')

for (const label of [
  '教学空间',
  'PPT 与课件',
  '学生画像与评估',
  '模拟考试',
  '课程思维导图',
  '帮助中心',
]) {
  assert.ok(sidebar.includes(label), `global sidebar missing ${label}`)
}

assert.ok(sidebar.includes('educationDomainNavItems'), 'Education domains must be computed')
assert.ok(
  sidebar.includes("activeSubRole"),
  'Education domains must use the workspace role before a course is selected'
)
assert.ok(
  workspaceSwitcher.includes('syncEducationContext'),
  'switching into Education must hydrate course membership for legacy workspaces'
)
assert.ok(
  workspaceSwitcher.includes("dispatch('education/fetchCourses')"),
  'Education navigation must know teacher/student membership before opening a course'
)
assert.ok(
  !sidebar.includes('if (!course || !this.membershipRole) return [teachingSpace]'),
  'Education product domains must not disappear before a course is selected'
)
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
  courseSpace.includes("{ key: 'knowledge', label: '知识中心'"),
  'teacher knowledge center must be a first-class course tab'
)
assert.ok(
  !courseSpace.includes('>课程知识中心</el-button>'),
  'knowledge center must not remain a duplicate header action'
)

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
assert.ok(
  router.includes('ensureEducationWorkspace'),
  'direct Education routes must activate the Education workspace before rendering'
)
assert.ok(
  router.includes("store.dispatch('workspace/fetchWorkspaces', 'edu')"),
  'deep links must not retain a workspace from another domain'
)

console.log('education unified navigation contract ok')
