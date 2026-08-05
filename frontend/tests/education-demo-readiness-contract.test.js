const fs = require('fs')
const path = require('path')
const assert = require('assert')

const root = path.resolve(__dirname, '..')
const read = file => fs.readFileSync(path.join(root, file), 'utf8')

const course = read('src/views/education/CourseSpace.vue')
const knowledge = read('src/views/education/KnowledgeCenter.vue')
const workbench = read('src/views/education/LessonWorkbench.vue')
const educationStore = read('src/store/modules/education.js')

assert(course.includes('百分制总分'), 'assignment publishing must explain the fixed 100-point scale')
assert(course.includes('max_score: 100'), 'new assignments must use 100 points')
assert(!course.includes('v-model="assignmentForm.max_score"'), 'teachers should not see a conflicting score input')

for (const token of [
  'questionOrganization',
  'selectedQuestionLessonId',
  'lesson_id: this.questionForm.lessonId',
  'lesson_id: this.stimulusForm.lessonId',
  'paperSelectionDialog',
  '手动选题组卷',
  '选择全部已发布题目',
  '收起题目',
  'Array.isArray(stimulus.questions)',
]) assert(knowledge.includes(token), `knowledge center missing ${token}`)

assert(workbench.includes('workbench-action-grid'), 'lesson actions must use a 2x2 grid')
assert(!workbench.includes('<el-tag v-if="isTeacher && hasUnsavedChanges"'), 'the unsaved-change badge must be removed')
assert(
  educationStore.includes("questionPayload.stimuli"),
  'question-bank state must preserve the hydrated stimulus question groups',
)

console.log('education demo readiness contract ok')
