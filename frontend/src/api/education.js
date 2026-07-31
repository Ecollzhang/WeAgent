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

export function updateMyCourseProfile(courseId, displayName) {
  return service.put(url(`/courses/${courseId}/me/profile`), {
    display_name: displayName,
  })
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

export function getLesson(lessonId) {
  return service.get(url(`/lessons/${lessonId}`))
}

export function getLessonContents(lessonId) {
  return service.get(url(`/lessons/${lessonId}/contents`))
}

export function getLessonCoursewareContext(lessonId) {
  return service.get(url(`/lessons/${lessonId}/courseware-context`))
}

export function getContentVersions(contentId) {
  return service.get(url(`/contents/${contentId}/versions`))
}

export function getContentVisualQa(contentId) {
  return service.get(url(`/contents/${contentId}/visual-qa`))
}

export function exportEducationContent(contentId, format) {
  return service.get(url(`/contents/${contentId}/export`), {
    params: { format },
    responseType: 'blob',
  })
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

export function createLessonContent(lessonId, data) {
  return service.post(url(`/lessons/${lessonId}/contents`), data)
}

export function saveContentVersion(contentId, data) {
  return service.post(url(`/contents/${contentId}/versions`), data)
}

export function getLessonMaterials(lessonId) {
  return service.get(url(`/lessons/${lessonId}/materials`))
}

export function uploadLessonMaterial(lessonId, formData) {
  return service.post(url(`/lessons/${lessonId}/materials`), formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function createLessonActivity(lessonId, data) {
  return service.post(url(`/lessons/${lessonId}/activities`), data)
}

export function downloadLessonMaterial(materialId) {
  return service.get(url(`/materials/${materialId}/download`), {
    responseType: 'blob',
  })
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

export function getAssignment(assignmentId) {
  return service.get(url(`/assignments/${assignmentId}`))
}

export function getAssignmentOverview(assignmentId) {
  return service.get(url(`/assignments/${assignmentId}/overview`))
}

export function getSubmissionReview(submissionId) {
  return service.get(url(`/submissions/${submissionId}/review`))
}

export function saveSubmissionReviewDraft(submissionId, data) {
  return service.put(url(`/submissions/${submissionId}/review-draft`), data)
}

export function publishSubmissionReview(submissionId) {
  return service.post(url(`/submissions/${submissionId}/review/publish`))
}

export function createAssignment(lessonId, data) {
  return service.post(url(`/lessons/${lessonId}/assignments`), data)
}

export function uploadAssignmentSource(courseId, formData) {
  return service.post(url(`/courses/${courseId}/assignment-imports`), formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function processAssignmentImport(importId) {
  return service.post(url(`/assignment-imports/${importId}/process`))
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

export function saveSubmissionDraft(assignmentId, answerJson) {
  return service.put(url(`/assignments/${assignmentId}/submission/draft`), {
    answer_json: answerJson,
  })
}

export function getMySubmission(assignmentId) {
  return service.get(url(`/assignments/${assignmentId}/submission`))
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

export function getEducationWorkflowRun(runId) {
  return service.get(url(`/workflow-runs/${runId}`))
}

export function getCourseWorkflowRuns(courseId) {
  return service.get(url(`/courses/${courseId}/workflow-runs`))
}

export function startEducationProductAgentRun(data) {
  return service.post(url('/product-agent-runs'), data)
}

export function getEducationProductAgentRun(runId) {
  return service.get(url(`/product-agent-runs/${runId}`))
}

export function getCourseProductAgentRuns(courseId, params = {}) {
  return service.get(url(`/courses/${courseId}/product-agent-runs`), { params })
}

export function getEducationConversationContext(conversationId) {
  return service.get(url(`/conversations/${conversationId}/product-context`))
}

// Durable course assets -----------------------------------------------------

export function getCourseAssets(courseId) {
  return service.get(url(`/courses/${courseId}/assets`))
}

export function uploadCourseAsset(courseId, formData) {
  return service.post(url(`/courses/${courseId}/assets`), formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function updateCourseAsset(assetId, data) {
  return service.patch(url(`/assets/${assetId}`), data)
}

export function downloadCourseAsset(assetId) {
  return service.get(url(`/assets/${assetId}/download`), {
    responseType: 'blob',
  })
}

// Course Knowledge Center --------------------------------------------------

export function getKnowledgeCenter(courseId) {
  return service.get(url(`/courses/${courseId}/knowledge-center`))
}

export function getCourseQuestions(courseId) {
  return service.get(url(`/courses/${courseId}/questions`))
}

export function createCourseQuestion(courseId, data) {
  return service.post(url(`/courses/${courseId}/questions`), data)
}

export function createQuestionVersion(questionId, data) {
  return service.post(url(`/questions/${questionId}/versions`), data)
}

export function publishCourseQuestion(questionId) {
  return service.post(url(`/questions/${questionId}/publish`))
}

export function getCoursePapers(courseId) {
  return service.get(url(`/courses/${courseId}/papers`))
}

export function composeCoursePaper(courseId, data) {
  return service.post(url(`/courses/${courseId}/papers/compose`), data)
}

export function publishCoursePaper(paperId) {
  return service.post(url(`/papers/${paperId}/publish`))
}

export function getKnowledgeResources(courseId) {
  return service.get(url(`/courses/${courseId}/knowledge-resources`))
}

export function createKnowledgeResource(courseId, data) {
  return service.post(url(`/courses/${courseId}/knowledge-resources`), data)
}

// Student products and evidence -------------------------------------------

export function getMockExams(courseId) {
  return service.get(url(`/courses/${courseId}/mock-exams`))
}

export function createMockExam(courseId, data) {
  return service.post(url(`/courses/${courseId}/mock-exams`), data)
}

export function getMockExam(attemptId) {
  return service.get(url(`/mock-exams/${attemptId}`))
}

export function saveMockExamAnswers(attemptId, answers) {
  return service.put(url(`/mock-exams/${attemptId}/answers`), { answers })
}

export function submitMockExam(attemptId) {
  return service.post(url(`/mock-exams/${attemptId}/submit`))
}

export function getWeaknessAnalysis(courseId) {
  return service.get(url(`/courses/${courseId}/weakness-analysis`))
}

export function refreshWeaknessAnalysis(courseId) {
  return service.post(url(`/courses/${courseId}/weakness-analysis`))
}

export function getCourseMindMaps(courseId) {
  return service.get(url(`/courses/${courseId}/mind-maps`))
}

export function createCourseMindMap(courseId, data) {
  return service.post(url(`/courses/${courseId}/mind-maps`), data)
}

export function getCourseMindMap(mindMapId) {
  return service.get(url(`/mind-maps/${mindMapId}`))
}

export function saveMindMapVersion(mindMapId, data) {
  return service.post(url(`/mind-maps/${mindMapId}/versions`), data)
}

export function getStudentInsights(courseId) {
  return service.get(url(`/courses/${courseId}/student-insights`))
}

export function refreshStudentInsights(courseId) {
  return service.post(url(`/courses/${courseId}/student-insights/refresh`))
}
