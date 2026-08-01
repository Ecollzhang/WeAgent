import Vue from 'vue'
import Router from 'vue-router'
import store from '../store'

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
  // ── 领域专属页面（占位）─────────────────────────────
  {
    path: '/projects',
    name: 'projects',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/repos',
    name: 'repos',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/reviews',
    name: 'reviews',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/builds',
    name: 'builds',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/courses',
    name: 'courses',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/assignments',
    name: 'assignments',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/resources',
    name: 'resources',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/students',
    name: 'students',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/grades',
    name: 'grades',
    component: () => import('../views/DomainPlaceholder.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/documents',
    name: 'documents',
    component: () => import('../views/OfficeDocumentsDense.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/meetings',
    name: 'meetings',
    component: () => import('../views/OfficeMeetingTasks.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/approvals',
    name: 'approvals',
    component: () => import('../views/OfficeWorkspace.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/schedules',
    name: 'schedules',
    component: () => import('../views/OfficeWorkspace.vue'),
    meta: { requiresAuth: true },
  },
  { path: '/reports', redirect: '/meetings' },
  { path: '/tasks', redirect: '/meetings' },
  { path: '/organization', name: 'organization', component: () => import('../views/OfficeOrganizationCompact.vue'), meta: { requiresAuth: true } },
  { path: '/notifications', name: 'notifications', component: () => import('../views/OfficeNotifications.vue'), meta: { requiresAuth: true } },
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

// Navigation guard
router.beforeEach((to, from, next) => {
  const isAuthenticated = store.getters['user/isAuthenticated']

  if (to.matched.some(record => record.meta.requiresAuth !== false)) {
    if (!isAuthenticated) {
      next({ name: 'Login' })
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
