import {
  acceptCourseInvitation,
  createAssignment,
  createCourse,
  createCourseInvitation,
  getAssignmentSubmissions,
  getAssignment,
  getContentVersions,
  getCourseAnalytics,
  getCourseAssignments,
  getCourseMembers,
  getCourses,
  getCourseUnits,
  getLessonPublication,
  getLessonRelease,
  getLesson,
  getLessonContents,
  getMySubmission,
  getSubmissionFeedback,
  publishAssignment,
  publishLesson,
  releaseFeedback,
  saveLessonVersion,
  saveSubmissionDraft,
  searchEducationResources,
  submitAssignment,
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

    async fetchLesson({ commit, state }, lessonId) {
      const lesson = payload(await getLesson(lessonId))
      let publication = {}
      try {
        publication = payload(
          await (state.activeCourse.membership_role === 'teacher'
            ? getLessonPublication(lessonId)
            : getLessonRelease(lessonId))
        )
      } catch (error) {
        if (lesson.status === 'published') throw error
      }
      let currentVersion = null
      if (state.activeCourse.membership_role === 'teacher') {
        const contents = items(await getLessonContents(lessonId))
        const plan = contents.find(item => item.kind === 'lesson_plan')
        if (plan) {
          const versions = items(await getContentVersions(plan.id))
          currentVersion = versions[versions.length - 1] || null
        }
      }
      const value = {
        ...lesson,
        publication,
        current_version: currentVersion,
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
        return payload(await saveLessonVersion(lessonId, {
          source_json: source,
          rendered_html: version.rendered_html || '',
          change_summary: version.change_summary || '网页端编辑',
        }))
      } finally {
        commit('SET_SAVING', false)
      }
    },

    async publishLesson(context, { lessonId, versionId }) {
      return payload(await publishLesson(lessonId, versionId))
    },

    async fetchAssignment({ commit }, { assignmentId }) {
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
  },
}
