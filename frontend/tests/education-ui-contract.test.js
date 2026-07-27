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

function assertNotContains(file, needle, message) {
  assert.ok(!read(file).includes(needle), `${file}: ${message || `unexpected ${needle}`}`)
}

assertContains(
  'src/api/education.js',
  "const EDUCATION_BASE = '/domain/edu'",
  'Education requests must use the authenticated core domain proxy'
)
assertContains(
  'src/api/education.js',
  'acceptCourseInvitation',
  'students must be able to join a course through an invitation'
)
assertContains(
  'src/api/education.js',
  '`/courses/${courseId}/structure`',
  'course space must consume the membership-filtered structure manifest'
)
assertContains(
  'src/api/education.js',
  'publishLesson',
  'teachers must be able to publish a lesson snapshot'
)
assertContains(
  'src/api/education.js',
  "'Idempotency-Key'",
  'lesson publication must provide the server-required idempotency key'
)
assertContains(
  'src/api/education.js',
  'submitAssignment',
  'students must be able to submit assignments'
)
assertContains(
  'src/api/education.js',
  'answer_json: data.answer_json',
  'submission payload must preserve the immutable answer contract'
)
assertContains(
  'src/api/education.js',
  'releaseFeedback',
  'teachers must be able to release reviewed feedback'
)
assertContains(
  'src/api/education.js',
  'feedback_json: data.feedback_json',
  'released feedback must use the backend review contract'
)
assertContains(
  'src/api/education.js',
  'getCourseAnalytics',
  'teachers must be able to retrieve learning analytics'
)

assertContains(
  'src/store/modules/education.js',
  'activeCourse.membership_role',
  'role must be derived from server membership, not workspace sub_role'
)
assertNotContains(
  'src/store/modules/education.js',
  'activeSubRole',
  'Education authorization state must not use the client-selected workspace role'
)
assertContains(
  'src/store/modules/education.js',
  'selectCourse',
  'course selection must refresh server-owned membership context'
)

assertContains(
  'src/views/education/EducationHome.vue',
  'data-testid="education-course-list"',
  'course list needs a stable UAT locator'
)
assertContains(
  'src/views/education/EducationHome.vue',
  'data-testid="create-course-submit"',
  'course creation needs a stable UAT locator'
)
assertContains(
  'src/views/education/EducationHome.vue',
  'data-testid="join-course-submit"',
  'invitation join needs a stable UAT locator'
)
assertContains(
  'src/views/education/CourseSpace.vue',
  "isTeacher",
  'course space must render by server membership'
)
assertContains(
  'src/views/education/CourseSpace.vue',
  'data-testid="course-membership-role"',
  'UAT must be able to observe the server-authoritative role'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  'data-testid="lesson-plan-editor"',
  'lesson plans need an editable structured workspace'
)
assertContains(
  'src/views/education/AssignmentWorkspace.vue',
  'data-testid="student-submission-editor"',
  'students need a stable submission editor locator'
)
assertContains(
  'src/views/education/AssignmentWorkspace.vue',
  'data-testid="teacher-feedback-editor"',
  'teachers need a stable review locator'
)

assertContains(
  'src/components/education/SafeHtmlPreview.vue',
  'sandbox=""',
  'generated HTML must be rendered in a restrictive iframe sandbox'
)
assertNotContains(
  'src/components/education/SafeHtmlPreview.vue',
  'allow-same-origin',
  'generated HTML must not share the application origin'
)
assertNotContains(
  'src/components/education/SafeHtmlPreview.vue',
  'allow-scripts',
  'generated HTML must not execute scripts'
)

console.log('education UI contract ok')
