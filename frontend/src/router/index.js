import Vue from 'vue'
import Router from 'vue-router'
import store from '../store'
import { checkEnabled } from '../store/modules/grayscale'

Vue.use(Router)

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/agents',
    name: 'AgentManager',
    component: () => import('../views/AgentManager.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/tools',
    name: 'Tools',
    component: () => import('../views/Tools.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/favorites',
    name: 'Favorites',
    component: () => import('../views/Favorites.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/knowledge-base',
    name: 'KnowledgeBase',
    component: () => import('../views/KnowledgeBase.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/capabilities',
    redirect: '/tools',
  },
  {
    path: '/sandbox',
    redirect: '/favorites',
  },
  // ── 智能研发领域 ──────────────────────────────────
  {
    path: '/projects',
    name: 'projects',
    component: () => import('../views/rd/RdProjects.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/projects/:id',
    name: 'projectDetail',
    component: () => import('../views/rd/RdProjectDetail.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/projects/:id/requirements/:rid',
    name: 'requirementDetail',
    component: () => import('../views/rd/RdRequirementDetail.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/projects/:id/bugs/:bid',
    name: 'bugDetail',
    component: () => import('../views/rd/RdBugDetail.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/projects/:id/gantt',
    name: 'projectGantt',
    component: () => import('../views/rd/RdGanttChart.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/repos',
    name: 'repos',
    component: () => import('../views/rd/RdRepos.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/repos/:id',
    name: 'repoDetail',
    component: () => import('../views/rd/RdRepoDetail.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/rd/callback',
    name: 'githubCallback',
    component: () => import('../views/rd/GithubCallback.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/reviews',
    name: 'reviews',
    component: () => import('../views/rd/RdReviews.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/builds',
    name: 'builds',
    component: () => import('../views/rd/RdBuilds.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/education',
    name: 'EducationHome',
    component: () => import('../views/education/EducationHome.vue'),
    meta: { requiresAuth: true, education: true },
  },
  {
    path: '/education/courses/:courseId',
    name: 'EducationCourse',
    component: () => import('../views/education/CourseSpace.vue'),
    meta: { requiresAuth: true, education: true, educationModule: 'teaching-space' },
  },
  {
    path: '/education/courses/:courseId/knowledge',
    name: 'EducationKnowledgeCenter',
    component: () => import('../views/education/KnowledgeCenter.vue'),
    meta: { requiresAuth: true, education: true, educationModule: 'teaching-space' },
  },
  {
    path: '/education/courses/:courseId/lessons/:lessonId',
    name: 'EducationLesson',
    component: () => import('../views/education/LessonWorkbench.vue'),
    meta: { requiresAuth: true, education: true, educationModule: 'teaching-space' },
  },
  {
    path: '/education/courses/:courseId/assignments/:assignmentId',
    name: 'EducationAssignment',
    component: () => import('../views/education/AssignmentWorkspace.vue'),
    meta: { requiresAuth: true, education: true, educationModule: 'teaching-space' },
  },
  {
    path: '/education/courses/:courseId/assignments/:assignmentId/review/:submissionId',
    name: 'EducationSubmissionReview',
    component: () => import('../views/education/SubmissionReviewWorkspace.vue'),
    meta: { requiresAuth: true, education: true, educationModule: 'teaching-space', educationRole: 'teacher' },
  },
  {
    path: '/education/teacher/courseware',
    name: 'EducationCourseware',
    component: () => import('../views/education/CoursewareLibrary.vue'),
    meta: { requiresAuth: true, education: true, educationModule: 'courseware', educationRole: 'teacher' },
  },
  {
    path: '/education/teacher/insights',
    name: 'EducationStudentInsights',
    component: () => import('../views/education/StudentInsights.vue'),
    meta: { requiresAuth: true, education: true, educationModule: 'insights', educationRole: 'teacher' },
  },
  {
    path: '/education/student/mock-exams',
    name: 'EducationMockExams',
    component: () => import('../views/education/MockExamCenter.vue'),
    meta: { requiresAuth: true, education: true, educationModule: 'mock-exams', educationRole: 'student' },
  },
  {
    path: '/education/student/weaknesses',
    name: 'EducationWeaknesses',
    component: () => import('../views/education/WeaknessCenter.vue'),
    meta: { requiresAuth: true, education: true, educationModule: 'teaching-space', educationRole: 'student' },
  },
  {
    path: '/education/student/mind-maps',
    name: 'EducationMindMaps',
    component: () => import('../views/education/MindMapCenter.vue'),
    meta: { requiresAuth: true, education: true, educationModule: 'mind-maps', educationRole: 'student' },
  },
  {
    path: '/education/help',
    name: 'EducationHelpCenter',
    component: () => import('../views/education/HelpCenter.vue'),
    meta: { requiresAuth: true, education: true, educationModule: 'help' },
  },
  {
    path: '/courses',
    redirect: '/education',
  },
  {
    path: '/assignments',
    redirect: '/education',
  },
  {
    path: '/resources',
    redirect: '/education',
  },
  {
    path: '/students',
    redirect: '/education',
  },
  {
    path: '/grades',
    redirect: '/education',
  },
  {
    path: '/documents',
    name: 'documents',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/meetings',
    name: 'meetings',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/approvals',
    name: 'approvals',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/reports',
    name: 'reports',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/schedules',
    name: 'schedules',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  // ── 管理页面 ───────────────────────────────────────
  {
    path: '/admin/grayscale',
    name: 'GrayscaleConsole',
    component: () => import('../views/GrayscaleConsole.vue'),
    meta: { requiresAuth: true },
  },
]

const router = new Router({
  mode: 'history',
  routes,
})

async function ensureEducationWorkspace(to) {
  const requestedRole = [...to.matched]
    .reverse()
    .map(record => record.meta.educationRole || '')
    .find(Boolean) || ''
  const activeDomain = store.getters['workspace/activeDomain']
  const activeSubRole = store.getters['workspace/activeSubRole']
  if (
    activeDomain === 'edu'
    && (!requestedRole || !activeSubRole || activeSubRole === requestedRole)
  ) {
    return
  }

  try {
    await store.dispatch('workspace/fetchWorkspaces', 'edu')
    const workspaces = store.getters['workspace/workspacesByDomain']('edu')
    const workspace = (
      requestedRole
        ? workspaces.find(item => item.sub_role === requestedRole)
        : null
    ) || workspaces[0]
    await store.dispatch('workspace/selectWorkspace', workspace || {
      id: null,
      domain: 'edu',
      name: '',
      sub_role: requestedRole,
    })
  } catch (error) {
    await store.dispatch('workspace/selectWorkspace', {
      id: null,
      domain: 'edu',
      name: '',
      sub_role: requestedRole,
    })
  }
}

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const isAuthenticated = store.getters['user/isAuthenticated']

  if (to.matched.some(record => record.meta.requiresAuth !== false)) {
    if (!isAuthenticated) {
      next({ name: 'Login' })
    } else if (to.matched.some(record => record.meta.education)) {
      try {
        await store.dispatch('grayscale/loadDomainConfig', 'edu')
        await ensureEducationWorkspace(to)
      } catch (error) {
        next({ name: 'Dashboard' })
        return
      }
      if (!checkEnabled(
        store.state.grayscale,
        'edu',
        'feature.education.enabled'
      )) {
        next({ name: 'Dashboard' })
      } else {
        next()
      }
    } else {
      next()
    }
  } else {
    if (isAuthenticated && (to.name === 'Login' || to.name === 'Register')) {
      next({ name: 'Dashboard' })
    } else {
      next()
    }
  }
})

export default router
