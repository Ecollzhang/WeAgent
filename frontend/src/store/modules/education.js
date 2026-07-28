import {
  acceptCourseInvitation,
  createLessonContent,
  createLessonActivity,
  createAssignment,
  createCourse,
  createCourseInvitation,
  getAssignmentSubmissions,
  getAssignment,
  getContentVersions,
  getCourseAnalytics,
  getCourseAssignments,
  getCourseMembers,
  getCourseWorkflowRuns,
  getCourses,
  getCourseUnits,
  getEducationWorkflowRun,
  getLessonPublication,
  getLessonRelease,
  getLesson,
  getLessonContents,
  getLessonMaterials,
  getMySubmission,
  getSubmissionFeedback,
  publishAssignment,
  publishLesson,
  releaseFeedback,
  runEducationWorkflow,
  saveContentVersion,
  saveLessonVersion,
  saveSubmissionDraft,
  searchEducationResources,
  submitAssignment,
  uploadLessonMaterial,
  updateMyCourseProfile,
} from '../../api/education'

function payload(response) {
  if (response && response.data !== undefined && response.code !== undefined) {
    return response.data
  }
  return response || {}
}

function items(response) {
  const value = payload(response)
  if (Array.isArray(value)) return value
  return Array.isArray(value.items) ? value.items : []
}

export default {
  namespaced: true,

  state: {
    courses: [],
    activeCourse: null,
    units: [],
    activeLesson: null,
    assignments: [],
    activeAssignment: null,
    submissions: [],
    feedback: [],
    members: [],
    analytics: null,
    resourceResults: [],
    agentRun: null,
    loading: false,
    saving: false,
  },

  getters: {
    courses: state => state.courses,
    activeCourse: state => state.activeCourse,
    membershipRole: state => state.activeCourse && state.activeCourse.membership_role
      ? state.activeCourse.membership_role
      : '',
    isTeacher: (state, getters) => getters.membershipRole === 'teacher',
    isStudent: (state, getters) => getters.membershipRole === 'student',
    canManageCourse: (state, getters) => getters.isTeacher,
    units: state => state.units,
    assignments: state => state.assignments,
    members: state => state.members,
    analytics: state => state.analytics,
    loading: state => state.loading,
    saving: state => state.saving,
    agentRun: state => state.agentRun,
  },

  mutations: {
    SET_LOADING(state, value) { state.loading = value },
    SET_SAVING(state, value) { state.saving = value },
    SET_COURSES(state, value) { state.courses = value },
    SET_ACTIVE_COURSE(state, value) { state.activeCourse = value },
    SET_UNITS(state, value) { state.units = value },
    SET_ACTIVE_LESSON(state, value) { state.activeLesson = value },
    SET_ASSIGNMENTS(state, value) { state.assignments = value },
    SET_ACTIVE_ASSIGNMENT(state, value) { state.activeAssignment = value },
    SET_SUBMISSIONS(state, value) { state.submissions = value },
    SET_FEEDBACK(state, value) { state.feedback = value },
    SET_MEMBERS(state, value) { state.members = value },
    SET_ANALYTICS(state, value) { state.analytics = value },
    SET_RESOURCE_RESULTS(state, value) { state.resourceResults = value },
    SET_AGENT_RUN(state, value) { state.agentRun = value },
    UPSERT_COURSE(state, course) {
      const index = state.courses.findIndex(item => item.id === course.id)
      if (index < 0) state.courses.push(course)
      else state.courses.splice(index, 1, course)
    },
  },

  actions: {
    async fetchCourses({ commit }) {
      commit('SET_LOADING', true)
      try {
        const response = await getCourses()
        const value = items(response)
        commit('SET_COURSES', value)
        return value
      } finally {
        commit('SET_LOADING', false)
      }
    },

    async createCourse({ commit }, data) {
      commit('SET_SAVING', true)
      try {
        const course = payload(await createCourse(data))
        commit('UPSERT_COURSE', course)
        return course
      } finally {
        commit('SET_SAVING', false)
      }
    },

    async joinCourse({ dispatch }, token) {
      const result = payload(await acceptCourseInvitation(token))
      await dispatch('fetchCourses')
      return result
    },

    async selectCourse({ commit, state }, courseId) {
      commit('SET_LOADING', true)
      try {
        let course = state.courses.find(item => item.id === courseId)
        if (!course || !course.membership_role) {
          const refreshed = items(await getCourses())
          commit('SET_COURSES', refreshed)
          course = refreshed.find(item => item.id === courseId)
        }
        if (!course || !course.membership_role) {
          throw new Error('Course membership is unavailable')
        }
        commit('SET_ACTIVE_COURSE', course)
        return course
      } finally {
        commit('SET_LOADING', false)
      }
    },

    async fetchCourseOverview({ commit, getters }, courseId) {
      const requests = [
        getCourseUnits(courseId),
        getCourseAssignments(courseId),
      ]
      if (getters.isTeacher) {
        requests.push(getCourseMembers(courseId), getCourseAnalytics(courseId))
      }
      const results = await Promise.all(requests)
      const structure = payload(results[0])
      const units = Array.isArray(structure.units) ? structure.units.slice() : []
      if (Array.isArray(structure.ungrouped_lessons) && structure.ungrouped_lessons.length) {
        units.push({
          id: 'ungrouped',
          title: '未分组课时',
          lessons: structure.ungrouped_lessons,
        })
      }
      commit('SET_UNITS', units)
      commit('SET_ASSIGNMENTS', items(results[1]))
      if (getters.isTeacher) {
        commit('SET_MEMBERS', items(results[2]))
        commit('SET_ANALYTICS', payload(results[3]))
      } else {
        commit('SET_MEMBERS', [])
        commit('SET_ANALYTICS', null)
      }
      return results
    },

    async createInvitation(context, { courseId, limits }) {
      return payload(await createCourseInvitation(courseId, limits))
    },

    async updateMyDisplayName({ dispatch }, { courseId, displayName }) {
      const result = payload(await updateMyCourseProfile(courseId, displayName))
      await dispatch('fetchCourseOverview', courseId)
      return result
    },

    async fetchLesson({ commit, state }, lessonId) {
      const lesson = payload(await getLesson(lessonId))
      let publication = {}
      if (lesson.status === 'published' || lesson.current_published_version_id) {
        publication = payload(
          await (state.activeCourse.membership_role === 'teacher'
            ? getLessonPublication(lessonId)
            : getLessonRelease(lessonId))
        )
      }
      let currentVersion = null
      let lessonPlanContent = null
      let materialVersion = null
      let materialContent = null
      if (state.activeCourse.membership_role === 'teacher') {
        const contents = items(await getLessonContents(lessonId))
        lessonPlanContent = contents.find(item => item.kind === 'lesson_plan') || null
        materialContent = contents.find(item => item.kind === 'rich_document') || null
        if (lessonPlanContent) {
          const versions = items(await getContentVersions(lessonPlanContent.id))
          currentVersion = versions[versions.length - 1] || null
        }
        if (materialContent) {
          const versions = items(await getContentVersions(materialContent.id))
          materialVersion = versions[versions.length - 1] || null
        }
      } else {
        const releaseMaterials = (
          publication.student_release_manifest
          && publication.student_release_manifest.materials
        ) || []
        const htmlMaterial = releaseMaterials.find(item => item.kind === 'rich_document')
        if (htmlMaterial) materialVersion = htmlMaterial
      }
      const materials = items(await getLessonMaterials(lessonId))
      const value = {
        ...lesson,
        publication,
        current_version: currentVersion,
        lesson_plan_content: lessonPlanContent,
        material_version: materialVersion,
        material_content: materialContent,
        materials,
      }
      commit('SET_ACTIVE_LESSON', value)
      return value
    },

    async saveLesson({ commit, state }, { lessonId, version }) {
      commit('SET_SAVING', true)
      try {
        const plan = version.lesson_plan_json || {}
        const lesson = state.activeLesson || {}
        const source = {
          subject_code: state.activeCourse.subject_code,
          learning_domain: lesson.learning_domain,
          text_genre_code: lesson.text_genre_code,
          lesson_type_code: plan.lesson_type_code || lesson.lesson_type_code,
          duration_minutes: plan.duration_minutes || lesson.duration_minutes,
          objectives: String(plan.objectives || '')
            .split('\n')
            .map(item => item.trim())
            .filter(Boolean),
          stages: [{
            name: '教学活动',
            description: plan.activities || '',
            assessment: plan.assessment || '',
          }],
        }
        if (!source.objectives.length) {
          throw new Error('请至少填写一条教学目标')
        }
        const versionPayload = {
          source_json: source,
          rendered_html: version.rendered_html
            || (version.content && version.content.html)
            || '',
          change_summary: version.change_summary || '网页端编辑',
          schema_name: 'weagent.education.lesson-plan',
          schema_version: '1.0',
        }
        const response = lesson.lesson_plan_content
          ? await saveContentVersion(lesson.lesson_plan_content.id, versionPayload)
          : await saveLessonVersion(lessonId, versionPayload)
        const result = payload(response)
        const materialHtml = (version.content && version.content.html) || ''
        let materialResult = null
        if (materialHtml.trim()) {
          const materialPayload = {
            schema_name: 'weagent.education.rich-document',
            schema_version: '1.0',
            source_json: {
              title: lesson.title || '学习材料',
              format: 'html',
            },
            rendered_html: materialHtml,
            change_summary: version.change_summary || '可视化课件编辑',
          }
          materialResult = payload(
            lesson.material_content
              ? await saveContentVersion(lesson.material_content.id, materialPayload)
              : await createLessonContent(lessonId, {
                ...materialPayload,
                kind: 'rich_document',
                visibility_scope: 'course_students',
              })
          )
        }
        commit('SET_ACTIVE_LESSON', {
          ...lesson,
          current_version: result.version || null,
          lesson_plan_content: result.content || lesson.lesson_plan_content || null,
          material_version: materialResult
            ? materialResult.version
            : lesson.material_version || null,
          material_content: materialResult
            ? materialResult.content
            : lesson.material_content || null,
        })
        return { ...result, material: materialResult }
      } finally {
        commit('SET_SAVING', false)
      }
    },

    async publishLesson(context, { lessonId, versionId }) {
      return payload(await publishLesson(lessonId, versionId))
    },

    async uploadMaterial({ commit, state }, { lessonId, file, title }) {
      const data = new FormData()
      data.append('file', file)
      data.append('title', title || file.name)
      const material = payload(await uploadLessonMaterial(lessonId, data))
      const lesson = state.activeLesson || {}
      commit('SET_ACTIVE_LESSON', {
        ...lesson,
        materials: [...(lesson.materials || []), material],
      })
      return material
    },

    async createLearningActivity({ dispatch }, { lessonId, activity }) {
      const created = payload(await createLessonActivity(lessonId, activity))
      await dispatch('fetchLesson', lessonId)
      return created
    },

    async fetchAssignment({ commit }, input) {
      const assignmentId = typeof input === 'string' ? input : input.assignmentId
      const assignment = payload(await getAssignment(assignmentId))
      commit('SET_ACTIVE_ASSIGNMENT', assignment)
      return assignment
    },

    async createAssignment({ dispatch }, { courseId, lessonId, assignment }) {
      const created = payload(await createAssignment(lessonId, assignment))
      await dispatch('fetchCourseOverview', courseId)
      return created
    },

    async publishAssignment(context, assignmentId) {
      return payload(await publishAssignment(assignmentId))
    },

    async fetchSubmissions({ commit }, assignmentId) {
      const value = items(await getAssignmentSubmissions(assignmentId))
      commit('SET_SUBMISSIONS', value)
      return value
    },

    async fetchFeedback({ commit }, submissionId) {
      const value = items(await getSubmissionFeedback(submissionId))
      commit('SET_FEEDBACK', value)
      return value
    },

    async submitAssignment(context, { assignmentId, submission }) {
      return payload(await submitAssignment(assignmentId, submission))
    },

    async saveSubmissionDraft(context, { assignmentId, answerJson }) {
      return payload(await saveSubmissionDraft(assignmentId, answerJson))
    },

    async fetchMySubmission(context, assignmentId) {
      return payload(await getMySubmission(assignmentId))
    },

    async releaseFeedback(context, { submissionId, feedback }) {
      return payload(await releaseFeedback(submissionId, feedback))
    },

    async searchResources({ commit }, criteria) {
      const value = items(await searchEducationResources(criteria))
      commit('SET_RESOURCE_RESULTS', value)
      return value
    },

    async startLessonAgentRun({ commit }, input) {
      const run = payload(await runEducationWorkflow(input))
      commit('SET_AGENT_RUN', run)
      return run
    },

    async refreshAgentRun({ commit }, runId) {
      const run = payload(await getEducationWorkflowRun(runId))
      commit('SET_AGENT_RUN', run)
      return run
    },

    async restoreLessonAgentRun({ commit }, { courseId, lessonId }) {
      const runs = items(await getCourseWorkflowRuns(courseId))
      const run = runs.find(item => item.lesson_id === lessonId) || null
      commit('SET_AGENT_RUN', run)
      return run
    },
  },
}
