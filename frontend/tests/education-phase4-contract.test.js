const fs = require('fs')
const path = require('path')
const assert = require('assert')

const root = path.resolve(__dirname, '..')
const read = file => fs.readFileSync(path.join(root, file), 'utf8')

const knowledge = read('src/views/education/KnowledgeCenter.vue')
const graph = read('src/components/education/MindMapGraphEditor.vue')
const review = read('src/views/education/SubmissionReviewWorkspace.vue')
const insights = read('src/views/education/StudentInsights.vue')
const shell = read('src/components/education/EducationShell.vue')
const course = read('src/views/education/CourseSpace.vue')
const help = read('src/views/education/HelpCenter.vue')
const courseware = read('src/views/education/CoursewareLibrary.vue')
const mindMapCenter = read('src/views/education/MindMapCenter.vue')
const main = read('src/main.js')

for (const token of [
  'stimulus-card',
  'questionTypeOptions',
  'true_false',
  'editQuestion',
  'previewPaper',
  'paperPreviewDialog',
  'previewMode',
]) assert(knowledge.includes(token), `knowledge center missing ${token}`)

for (const token of [
  "this.chart.on('dblclick'",
  'color_token',
  'COLOR_TOKENS',
  ':class="{ editable }"',
  'clearSiblingPositions',
  'getDataURL',
]) assert(graph.includes(token), `mind map editor missing ${token}`)

assert(review.includes('aiSuggestionOpen'), 'AI suggestion must be collapsible')
assert(review.includes('feedbackForm.comment'), 'review must use one teacher feedback field')
assert(!review.includes('锚定批注'), 'fake anchored annotation UI must be removed')
assert(insights.includes("mode: 'grades'"), 'insights must default to grade overview mode')
assert(insights.includes('visibleStudentCount: 3'), 'profiles must initially show three students')
assert(insights.includes('selectedAssignmentId'), 'grade overview must select one assignment')
assert(!shell.includes('WEAGENT EDUCATION'), 'redundant Education eyebrow must be removed')
assert(course.includes('teacher-actions-grid'), 'teacher actions must use a dedicated 2x2 grid')
assert(!course.includes('教师空间'), 'redundant teacher-space tag must be removed')
assert(
  help.includes("membership_role === 'student'"),
  'help center must open on the current course role instead of always showing the teacher guide'
)
assert(
  help.includes('courseRole: {') && help.includes('immediate: true'),
  'help center must react when the course role is hydrated after the component mounts'
)
assert(main.includes("./styles/education-dialog.css"), 'Education dialogs need one shared scroll contract')
assert(course.includes('custom-class="education-dialog education-dialog--editor"'), 'assignment dialog must use the shared editor shell')
assert(courseware.includes('custom-class="education-dialog education-dialog--visual"'), 'visual QA must use the shared large dialog shell')
assert(mindMapCenter.includes('custom-class="education-dialog"'), 'mind-map creation must use the shared dialog shell')

console.log('education phase 4 contract ok')
