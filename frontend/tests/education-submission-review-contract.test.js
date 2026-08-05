const assert = require('assert')
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8')
const contains = (relPath, fragment, message) => {
  assert.ok(read(relPath).includes(fragment), `${message}: ${relPath}`)
}

contains(
  'src/router/index.js',
  '/education/courses/:courseId/assignments/:assignmentId/review/:submissionId',
  'teacher review must be a deep-linked independent workspace'
)

for (const fragment of [
  'getAssignmentOverview',
  'getSubmissionReview',
  'saveSubmissionReviewDraft',
  'publishSubmissionReview',
]) {
  contains(
    'src/api/education.js',
    fragment,
    'review pages need explicit overview and draft lifecycle APIs'
  )
}

for (const fragment of [
  '提交与批改',
  '作业内容',
  '发布设置',
  '作业分析',
  'data-testid="assignment-overview-metrics"',
  'data-testid="assignment-submission-table"',
  '批改下一份',
  'display_name',
]) {
  contains(
    'src/views/education/AssignmentWorkspace.vue',
    fragment,
    'teacher assignment route must be a class overview before review'
  )
}
assert.ok(
  !read('src/views/education/AssignmentWorkspace.vue').includes(
    'if (submissions.length) this.selectSubmission(submissions[0])'
  ),
  'assignment overview must not auto-select the first student'
)
for (const fragment of [
  'studentFeedback.score',
  'studentFeedback.version_number',
  'feedback-score',
]) {
  contains(
    'src/views/education/AssignmentWorkspace.vue',
    fragment,
    'students must see the teacher-confirmed score and feedback version'
  )
}

for (const fragment of [
  'review-workbench',
  'review-rubric-column',
  'review-evidence-column',
  'review-feedback-column',
  'AI 批改建议',
  "product_code: 'submission_review'",
  'canRetryAgent',
  'retryReviewAgent',
  'latestReleasedFeedback',
  'review.review_draft || this.latestReleasedFeedback(review.feedback_versions)',
  '采纳到反馈',
  '保存批改草稿',
  '发布成绩与反馈',
  '返回作业总览',
]) {
  contains(
    'src/views/education/SubmissionReviewWorkspace.vue',
    fragment,
    'independent review page must expose evidence, rubric, AI, and teacher confirmation'
  )
}

for (const fragment of [
  'restoreLegacyRubricScores',
  'scoreRecoveryNotice',
  'source.score',
]) {
  contains(
    'src/views/education/SubmissionReviewWorkspace.vue',
    fragment,
    'released total-only feedback must not reopen as a misleading zero score'
  )
}

console.log('Education submission review contract passed')
