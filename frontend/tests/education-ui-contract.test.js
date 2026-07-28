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
  'saveSubmissionDraft',
  'student drafts must persist through the Education service'
)
assertContains(
  'src/api/education.js',
  '`/assignments/${assignmentId}/submission`',
  'students must recover their own draft and immutable submission history'
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
assertContains(
  'src/store/index.js',
  'education,',
  'Education Vuex module must be registered in the application store'
)
assertContains(
  'src/router/index.js',
  "path: '/education'",
  'Education home must have a production route'
)
assertContains(
  'src/router/index.js',
  "'feature.education.enabled'",
  'Education routes must honor the gray feature gate'
)
assertContains(
  'src/components/Sidebar/index.vue',
  "label: '教学空间', route: '/education'",
  'the sidebar must expose one membership-driven Education space'
)
assertNotContains(
  'src/components/Sidebar/index.vue',
  'activeSubRole',
  'sidebar navigation must not treat workspace sub_role as authority'
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
  'src/store/modules/education.js',
  'lesson.current_published_version_id',
  'draft lessons must not request a publication that cannot exist yet'
)
assertContains(
  'src/store/modules/education.js',
  'student_release_manifest.learning_outline',
  'student lesson pages must receive the safe published learning outline'
)
assertContains(
  'src/store/modules/education.js',
  'published_version: publishedVersion',
  'the student version label must use the immutable publication metadata'
)
assertContains(
  'src/store/modules/education.js',
  'saveContentVersion',
  'subsequent lesson saves must append a version instead of creating duplicate content'
)

assertContains(
  'src/views/education/EducationHome.vue',
  'data-testid="education-course-list"',
  'course list needs a stable UAT locator'
)
assertContains(
  'src/views/education/EducationHome.vue',
  'title="教学空间"',
  'Education navigation and page naming must be consistent'
)
assertContains(
  'src/views/education/EducationHome.vue',
  '创建课程后是教师；通过邀请码加入后是学生',
  'the UI must explain that role comes from course membership rather than a toggle'
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
  'src/views/education/CourseSpace.vue',
  'data-testid="copy-invitation-token"',
  'teacher invitations need a one-click copy action'
)
assertContains(
  'src/views/education/CourseSpace.vue',
  'data-testid="create-lesson-open"',
  'a teacher must be able to start the first lesson from an empty course'
)
assertContains(
  'src/views/education/CourseSpace.vue',
  'data-testid="create-lesson-submit"',
  'the new lesson dialog needs a stable browser UAT action'
)
assertContains(
  'src/store/modules/education.js',
  'createCourseUnit',
  'the course workspace must persist a unit before creating its first lesson'
)
assertContains(
  'src/store/modules/education.js',
  'createCourseLesson',
  'the course workspace must persist and refresh a newly created lesson'
)
assertContains(
  'src/views/education/CourseSpace.vue',
  'navigator.clipboard.writeText',
  'the invitation copy action must use the clipboard API when available'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  'data-testid="lesson-plan-editor"',
  'lesson plans need an editable structured workspace'
)
assertContains(
  'src/api/education.js',
  'getEducationWorkflowRun',
  'the Education UI must poll the persisted workflow run instead of inventing local progress'
)
assertContains(
  'src/store/modules/education.js',
  'restoreLessonAgentRun',
  'refreshing the lesson page must restore the latest persisted Agent run for that lesson'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  "'education/restoreLessonAgentRun'",
  'the workbench must show a completed Agent run after a browser refresh'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  'data-testid="start-agent-workflow"',
  'teachers need a visible action that starts the real Agent workflow'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  'data-testid="agent-run-node-list"',
  'the lesson workbench must expose persisted Agent node states'
)
assertNotContains(
  'src/views/education/LessonWorkbench.vue',
  '/workspace/agents/',
  'internal Agent workspace paths must not be exposed in the teacher interface'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  'applyAgentDraft',
  'Agent output must be adoptable into the editable lesson plan instead of remaining decorative'
)
assertContains(
  'src/components/education/LessonPlanEditor.vue',
  "import EditableLessonSection from './EditableLessonSection.vue'",
  'lesson fields must use a precompiled Vue component in the runtime-only build'
)
assertNotContains(
  'src/components/education/LessonPlanEditor.vue',
  'template: `',
  'runtime templates make lesson fields disappear in the production Vue build'
)
assertContains(
  'src/components/education/LessonPlanEditor.vue',
  "updateField('objectives', $event)",
  'lesson fields must emit atomic object updates so save baselines stay stable'
)
assertContains(
  'src/components/education/LessonPlanEditor.vue',
  '叙事类课文',
  'primary Chinese lesson plans must retain text-type-specific choices'
)
assertContains(
  'src/components/education/LessonPlanEditor.vue',
  '读后续写',
  'high-school English lesson plans must retain reading/writing-specific choices'
)
assertContains(
  'src/components/education/EditableLessonSection.vue',
  'class="field-heading"',
  'lesson field titles and expand actions must share one horizontal heading'
)
assertContains(
  'src/components/education/EditableLessonSection.vue',
  'StructuredTextEditor',
  'expanded lesson fields must use the courseware-inspired structured editor'
)
assertContains(
  'src/components/education/RichMaterialEditor.vue',
  '@wangeditor/editor-for-vue',
  'courseware editing must use the approved Vue 2 rich-text editor adapter'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  'AgentArtifactPreview',
  'every Agent artifact needs a rendered preview surface'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  'artifactSummary',
  'collapsed Agent nodes must still summarize their outputs'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  'data-testid="agent-business-tool-calls"',
  'Agent nodes must show audited Education business-tool calls'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  '已写入业务系统',
  'the UI must distinguish durable business adoption from sandbox files'
)
assertContains(
  'src/components/education/AgentArtifactPreview.vue',
  'output.questions',
  'exercise Agent artifacts must render their canonical questions array'
)
assertContains(
  'src/components/education/AgentArtifactPreview.vue',
  '添加到学习活动',
  'a valid exercise artifact must be convertible into a learning activity'
)
assertContains(
  'src/api/education.js',
  'createLessonActivity',
  'teachers need an API for persisted learning activity cards'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  'createLearningActivity',
  'teachers need an activity creation workflow in the lesson workbench'
)
assertNotContains(
  'src/views/education/LessonWorkbench.vue',
  '<h2>课内活动</h2>',
  'the learning activity page must not be named classroom activity'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  '自定义组合 · 下一阶段',
  'the fixed MVP workflow must expose the boundary for later custom Agent teams'
)
assertNotContains(
  'src/views/education/LessonWorkbench.vue',
  'Conversation：',
  'internal conversation ids must not be exposed in the teacher interface'
)
assertNotContains(
  'src/views/education/LessonWorkbench.vue',
  'Sandbox：',
  'internal sandbox ids must not be exposed in the teacher interface'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  "event.key.toLowerCase() === 's'",
  'Ctrl/Cmd+S must save the current lesson version'
)
assertContains(
  'src/views/education/LessonWorkbench.vue',
  'hasUnsavedChanges',
  'publishing and navigation must observe unsaved lesson changes'
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
  'src/views/education/AssignmentWorkspace.vue',
  "'education/saveSubmissionDraft'",
  'the editor must save a server draft before final submission'
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
