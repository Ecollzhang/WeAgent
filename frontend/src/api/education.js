import service from './axios'

const EDUCATION_BASE = '/domain/edu'

const url = path => `${EDUCATION_BASE}${path}`

export function getCourses() {
  return service.get(url('/courses'))
}

export function createCourse(data) {
  return service.post(url('/courses'), data)
}

export function getCourse(courseId) {
  return service.get(url(`/courses/${courseId}`))
}

export function getCourseMembers(courseId) {
  return service.get(url(`/courses/${courseId}/members`))
}

export function createCourseInvitation(courseId, data = {}) {
  return service.post(url(`/courses/${courseId}/invitations`), data)
}

export function revokeCourseInvitation(courseId, invitationId) {
  return service.delete(url(`/courses/${courseId}/invitations/${invitationId}`))
}

export function acceptCourseInvitation(token) {
  return service.post(url('/invitations/accept'), { token })
}

export function getCourseUnits(courseId) {
  return service.get(url(`/courses/${courseId}/structure`))
}

export function createUnit(courseId, data) {
  return service.post(url(`/courses/${courseId}/units`), data)
}

export function createLesson(courseId, data) {
  return service.post(url(`/courses/${courseId}/lessons`), data)
}

export function getLessonRelease(lessonId) {
  return service.get(url(`/lessons/${lessonId}/release`))
}

export function getLessonPublication(lessonId) {
  return service.get(url(`/lessons/${lessonId}/publication`))
}

export function saveLessonVersion(lessonId, data) {
  return service.post(url(`/lessons/${lessonId}/contents`), {
    kind: 'lesson_plan',
    visibility_scope: 'course_teacher',
    schema_name: 'weagent.education.lesson-plan',
    schema_version: '1.0',
    source_json: data.source_json,
    rendered_html: data.rendered_html || '',
    change_summary: data.change_summary || '',
  })
}

export function saveContentVersion(contentId, data) {
  return service.post(url(`/contents/${contentId}/versions`), data)
}

export function publishLesson(lessonId) {
  const random = Math.random().toString(36).slice(2)
  return service.post(url(`/lessons/${lessonId}/publish`), {}, {
    headers: { 'Idempotency-Key': `web-${Date.now()}-${random}` },
  })
}

export function getCourseAssignments(courseId) {
  return service.get(url(`/courses/${courseId}/assignments`))
}

export function createAssignment(lessonId, data) {
  return service.post(url(`/lessons/${lessonId}/assignments`), data)
}

export function publishAssignment(assignmentId) {
  return service.post(url(`/assignments/${assignmentId}/publish`))
}

export function getAssignmentSubmissions(assignmentId) {
  return service.get(url(`/assignments/${assignmentId}/submissions`))
}

export function submitAssignment(assignmentId, data) {
  return service.post(url(`/assignments/${assignmentId}/submissions`), {
    answer_json: data.answer_json,
    artifact_ids: data.artifact_ids || [],
    source_version_id: data.source_version_id || null,
  })
}

export function getSubmissionFeedback(submissionId) {
  return service.get(url(`/submissions/${submissionId}/feedback`))
}

export function releaseFeedback(submissionId, data) {
  return service.post(url(`/submissions/${submissionId}/feedback`), {
    feedback_json: data.feedback_json,
    score: data.score,
  })
}

export function getCourseAnalytics(courseId) {
  return service.get(url(`/courses/${courseId}/analytics`))
}

export function searchEducationResources(data) {
  return service.post(url('/resources/search'), data)
}

export function getEducationWorkflows(params = {}) {
  return service.get(url('/workflows'), { params })
}

export function saveEducationWorkflow(data) {
  return service.post(url('/workflows'), data)
}

export function runEducationWorkflow(data) {
  return service.post(url('/workflow-runs'), data)
}
