import {
  acceptCourseInvitation,
  composeCoursePaper,
  createCourseMindMap,
  createCourseQuestion,
  createKnowledgeResource,
  createLessonContent,
  createLessonActivity,
  createUnit as createCourseUnit,
  createLesson as createCourseLesson,
  createAssignment,
  createCourse,
  createCourseInvitation,
  createMockExam as createMockExamApi,
  downloadCourseAsset,
  getAssignmentSubmissions,
  getAssignment,
  getContentVersions,
  getCourseAnalytics,
  getCourseAssets,
  getCourseAssignments,
  getCourseMindMaps,
  getCourseMembers,
  getCoursePapers,
  getCourseProductAgentRuns,
  getCourseQuestions,
  getCourseWorkflowRuns,
  getCourses,
  getCourseUnits,
  getKnowledgeCenter,
  getKnowledgeResources,
  getMockExams,
  getStudentInsights,
  getWeaknessAnalysis,
  getEducationWorkflowRun,
  getEducationProductAgentRun,
  getLessonPublication,
  getLessonRelease,
  getLesson,
  getLessonCoursewareContext,
  getLessonContents,
  getLessonMaterials,
  getMySubmission,
  getSubmissionFeedback,
  publishAssignment,
  publishCoursePaper,
  publishCourseQuestion,
  publishLesson,
  processAssignmentImport,
  releaseFeedback,
  refreshStudentInsights,
  refreshWeaknessAnalysis,
  runEducationWorkflow,
  startEducationProductAgentRun,
  saveContentVersion,
  saveLessonVersion,
  saveMindMapVersion,
  saveMockExamAnswers,
  saveSubmissionDraft,
  searchEducationResources,
  submitAssignment,
  submitMockExam,
  updateCourseAsset,
  uploadAssignmentSource as uploadAssignmentSourceApi,
  uploadCourseAsset,
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
    coursewareContext: null,
    assignments: [],
    activeAssignment: null,
    submissions: [],
    feedback: [],
    members: [],
    analytics: null,
    resourceResults: [],
    agentRun: null,
    productAgentRun: null,
    productAgentRuns: [],
    assets: [],
    knowledgeSummary: null,
    questions: [],
    papers: [],
    knowledgeResources: [],
    mockExams: [],
    activeMockExam: null,
    weakness: null,
    mindMaps: [],
    activeMindMap: null,
    studentInsights: [],
    studentInsightOverview: null,
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
    coursewareContext: state => state.coursewareContext,
    assignments: state => state.assignments,
    members: state => state.members,
    analytics: state => state.analytics,
    loading: state => state.loading,
    saving: state => state.saving,
    agentRun: state => state.agentRun,
    productAgentRun: state => state.productAgentRun,
    productAgentRuns: state => state.productAgentRuns,
    assets: state => state.assets,
    knowledgeSummary: state => state.knowledgeSummary,
    questions: state => state.questions,
    papers: state => state.papers,
    knowledgeResources: state => state.knowledgeResources,
    mockExams: state => state.mockExams,
    activeMockExam: state => state.activeMockExam,
    weakness: state => state.weakness,
    mindMaps: state => state.mindMaps,
    activeMindMap: state => state.activeMindMap,
    studentInsights: state => state.studentInsights,
    studentInsightOverview: state => state.studentInsightOverview,
  },

  mutations: {
    SET_LOADING(state, value) { state.loading = value },
    SET_SAVING(state, value) { state.saving = value },
    SET_COURSES(state, value) { state.courses = value },
    SET_ACTIVE_COURSE(state, value) { state.activeCourse = value },
    SET_UNITS(state, value) { state.units = value },
    SET_ACTIVE_LESSON(state, value) { state.activeLesson = value },
    SET_COURSEWARE_CONTEXT(state, value) { state.coursewareContext = value },
    SET_ASSIGNMENTS(state, value) { state.assignments = value },
    SET_ACTIVE_ASSIGNMENT(state, value) { state.activeAssignment = value },
    SET_SUBMISSIONS(state, value) { state.submissions = value },
    SET_FEEDBACK(state, value) { state.feedback = value },
    SET_MEMBERS(state, value) { state.members = value },
    SET_ANALYTICS(state, value) { state.analytics = value },
    SET_RESOURCE_RESULTS(state, value) { state.resourceResults = value },
    SET_AGENT_RUN(state, value) { state.agentRun = value },
    SET_PRODUCT_AGENT_RUN(state, value) { state.productAgentRun = value },
    SET_PRODUCT_AGENT_RUNS(state, value) { state.productAgentRuns = value },
    SET_ASSETS(state, value) { state.assets = value },
    SET_KNOWLEDGE_SUMMARY(state, value) { state.knowledgeSummary = value },
    SET_QUESTIONS(state, value) { state.questions = value },
    SET_PAPERS(state, value) { state.papers = value },
    SET_KNOWLEDGE_RESOURCES(state, value) { state.knowledgeResources = value },
    SET_MOCK_EXAMS(state, value) { state.mockExams = value },
    SET_ACTIVE_MOCK_EXAM(state, value) { state.activeMockExam = value },
    SET_WEAKNESS(state, value) { state.weakness = value },
    SET_MIND_MAPS(state, value) { state.mindMaps = value },
    SET_ACTIVE_MIND_MAP(state, value) { state.activeMindMap = value },
    SET_STUDENT_INSIGHTS(state, value) { state.studentInsights = value },
    SET_STUDENT_INSIGHT_OVERVIEW(state, value) { state.studentInsightOverview = value },
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

    async createLesson({ dispatch }, { courseId, unitId, unitTitle, lesson }) {
      let resolvedUnitId = unitId || ''
      if (!resolvedUnitId) {
        const unit = payload(await createCourseUnit(courseId, {
          title: unitTitle,
          position: 1,
        }))
        resolvedUnitId = unit.id
      }
      const created = payload(await createCourseLesson(courseId, {
        ...lesson,
        unit_id: resolvedUnitId,
      }))
      await dispatch('fetchCourseOverview', courseId)
      return created
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
      let publishedVersion = null
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
        const releaseManifest = publication.student_release_manifest || {}
        const releaseMaterials = releaseManifest.materials || []
        const learningOutline = (
          publication.student_release_manifest
          && publication.student_release_manifest.learning_outline
        ) || {}
        publishedVersion = {
          id: publication.lesson_plan_version_id || publication.id,
          version_number: publication.version_number,
          published_at: publication.published_at,
          source_json: learningOutline,
        }
        const htmlMaterial = releaseMaterials.find(item => item.kind === 'rich_document')
        if (htmlMaterial) materialVersion = htmlMaterial
      }
      const materials = items(await getLessonMaterials(lessonId))
      const value = {
        ...lesson,
        publication,
        current_version: currentVersion,
        published_version: publishedVersion,
        lesson_plan_content: lessonPlanContent,
        material_version: materialVersion,
        material_content: materialContent,
        materials,
      }
      commit('SET_ACTIVE_LESSON', value)
      return value
    },

    async fetchCoursewareContext({ commit }, lessonId) {
      const context = payload(await getLessonCoursewareContext(lessonId))
      commit('SET_COURSEWARE_CONTEXT', context)
      return context
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

    async uploadAssignmentSource(context, { courseId, formData }) {
      return payload(await uploadAssignmentSourceApi(courseId, formData))
    },

    async processAssignmentImport(context, importId) {
      return payload(await processAssignmentImport(importId))
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

    async startProductAgentRun({ commit, state }, input) {
      const run = payload(await startEducationProductAgentRun(input))
      commit('SET_PRODUCT_AGENT_RUN', run)
      commit('SET_PRODUCT_AGENT_RUNS', [
        run,
        ...state.productAgentRuns.filter(item => item.id !== run.id),
      ])
      return run
    },

    async refreshProductAgentRun({ commit }, runId) {
      const run = payload(await getEducationProductAgentRun(runId))
      commit('SET_PRODUCT_AGENT_RUN', run)
      return run
    },

    async restoreProductAgentRun({ commit }, { courseId, productCode }) {
      const runs = items(await getCourseProductAgentRuns(courseId, {
        product_code: productCode,
      }))
      commit('SET_PRODUCT_AGENT_RUNS', runs)
      const run = runs[0] || null
      commit('SET_PRODUCT_AGENT_RUN', run)
      return run
    },

    async fetchProductAgentRuns({ commit }, { courseId, productCode }) {
      const runs = items(await getCourseProductAgentRuns(courseId, {
        product_code: productCode,
      }))
      commit('SET_PRODUCT_AGENT_RUNS', runs)
      return runs
    },

    async ensureRoleCourse({ dispatch, state }, { courseId, role }) {
      if (!state.courses.length) await dispatch('fetchCourses')
      const candidate = state.courses.find(course => course.id === courseId)
        || state.courses.find(course => course.membership_role === role)
      if (!candidate || (role && candidate.membership_role !== role)) {
        throw new Error(`No ${role || 'active'} course membership is available`)
      }
      if (!state.activeCourse || state.activeCourse.id !== candidate.id) {
        await dispatch('selectCourse', candidate.id)
      }
      return candidate
    },

    async fetchAssets({ commit }, courseId) {
      const value = items(await getCourseAssets(courseId))
      commit('SET_ASSETS', value)
      return value
    },

    async uploadAsset({ dispatch }, { courseId, file, title, purpose, visibilityScope }) {
      const form = new FormData()
      form.append('file', file)
      form.append('title', title || file.name)
      form.append('purpose', purpose || 'courseware')
      form.append('visibility_scope', visibilityScope || 'course_teacher')
      const asset = payload(await uploadCourseAsset(courseId, form))
      await dispatch('fetchAssets', courseId)
      return asset
    },

    async publishAsset({ dispatch }, { courseId, assetId }) {
      const asset = payload(await updateCourseAsset(assetId, {
        visibility_scope: 'course_published',
      }))
      await dispatch('fetchAssets', courseId)
      return asset
    },

    async downloadAsset(context, asset) {
      return downloadCourseAsset(asset.id)
    },

    async fetchKnowledgeCenter({ commit }, courseId) {
      const [summary, questionResponse, paperResponse, resourceResponse] = await Promise.all([
        getKnowledgeCenter(courseId),
        getCourseQuestions(courseId),
        getCoursePapers(courseId),
        getKnowledgeResources(courseId),
      ])
      commit('SET_KNOWLEDGE_SUMMARY', payload(summary))
      commit('SET_QUESTIONS', items(questionResponse))
      commit('SET_PAPERS', items(paperResponse))
      commit('SET_KNOWLEDGE_RESOURCES', items(resourceResponse))
      return payload(summary)
    },

    async createQuestion({ dispatch }, { courseId, question }) {
      const created = payload(await createCourseQuestion(courseId, question))
      await dispatch('fetchKnowledgeCenter', courseId)
      return created
    },

    async publishQuestion({ dispatch }, { courseId, questionId }) {
      const published = payload(await publishCourseQuestion(questionId))
      await dispatch('fetchKnowledgeCenter', courseId)
      return published
    },

    async composePaper({ dispatch }, { courseId, paper }) {
      const created = payload(await composeCoursePaper(courseId, paper))
      await dispatch('fetchKnowledgeCenter', courseId)
      return created
    },

    async publishPaper({ dispatch }, { courseId, paperId }) {
      const published = payload(await publishCoursePaper(paperId))
      await dispatch('fetchKnowledgeCenter', courseId)
      return published
    },

    async addKnowledgeResource({ dispatch }, { courseId, resource }) {
      const created = payload(await createKnowledgeResource(courseId, resource))
      await dispatch('fetchKnowledgeCenter', courseId)
      return created
    },

    async fetchMockExams({ commit }, courseId) {
      const value = items(await getMockExams(courseId))
      commit('SET_MOCK_EXAMS', value)
      return value
    },

    async createMockExam({ commit, dispatch }, { courseId, blueprint }) {
      const attempt = payload(await createMockExamApi(courseId, blueprint))
      commit('SET_ACTIVE_MOCK_EXAM', attempt)
      await dispatch('fetchMockExams', courseId)
      return attempt
    },

    async saveMockExamAnswers({ commit }, { attemptId, answers }) {
      const attempt = payload(await saveMockExamAnswers(attemptId, answers))
      commit('SET_ACTIVE_MOCK_EXAM', attempt)
      return attempt
    },

    async submitMockExam({ commit, dispatch }, { courseId, attemptId }) {
      const attempt = payload(await submitMockExam(attemptId))
      commit('SET_ACTIVE_MOCK_EXAM', attempt)
      await dispatch('fetchMockExams', courseId)
      return attempt
    },

    async fetchWeakness({ commit }, courseId) {
      const value = payload(await getWeaknessAnalysis(courseId))
      commit('SET_WEAKNESS', value)
      return value
    },

    async refreshWeakness({ commit }, courseId) {
      const value = payload(await refreshWeaknessAnalysis(courseId))
      commit('SET_WEAKNESS', value)
      return value
    },

    async fetchMindMaps({ commit }, courseId) {
      const value = items(await getCourseMindMaps(courseId))
      commit('SET_MIND_MAPS', value)
      return value
    },

    async createMindMap({ commit, dispatch }, { courseId, data }) {
      const value = payload(await createCourseMindMap(courseId, data))
      commit('SET_ACTIVE_MIND_MAP', value)
      await dispatch('fetchMindMaps', courseId)
      return value
    },

    async saveMindMapVersion({ commit, dispatch }, { courseId, mindMapId, data }) {
      const value = payload(await saveMindMapVersion(mindMapId, data))
      commit('SET_ACTIVE_MIND_MAP', value)
      await dispatch('fetchMindMaps', courseId)
      return value
    },

    async fetchStudentInsights({ commit }, courseId) {
      const response = payload(await getStudentInsights(courseId))
      const value = Array.isArray(response.items) ? response.items : []
      commit('SET_STUDENT_INSIGHTS', value)
      commit('SET_STUDENT_INSIGHT_OVERVIEW', response.class_overview || null)
      return response
    },

    async refreshStudentInsights({ commit }, courseId) {
      const response = payload(await refreshStudentInsights(courseId))
      const value = Array.isArray(response.items) ? response.items : []
      commit('SET_STUDENT_INSIGHTS', value)
      commit('SET_STUDENT_INSIGHT_OVERVIEW', response.class_overview || null)
      return response
    },
  },
}
