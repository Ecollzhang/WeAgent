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
    path: '/sandbox',
    redirect: '/favorites',
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
