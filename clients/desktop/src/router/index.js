import Vue from 'vue'
import Router from 'vue-router'
import { hasServerUrl, hasAccessToken } from '../services/session'

Vue.use(Router)

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/server', name: 'ServerSetup', component: () => import('../views/ServerSetup.vue') },
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  { path: '/register', name: 'Register', component: () => import('../views/Register.vue') },
  { path: '/conversations', name: 'Conversations', component: () => import('../views/Conversations.vue') },
  { path: '/agents', name: 'Agents', component: () => import('../views/Agents.vue') },
  { path: '/favorites', name: 'Favorites', component: () => import('../views/Favorites.vue') },
  { path: '/tools', name: 'Tools', component: () => import('../views/Tools.vue') },
  { path: '/settings', name: 'Settings', component: () => import('../views/Settings.vue') },
]

const router = new Router({
  mode: 'hash',
  routes,
})

router.beforeEach(async (to, from, next) => {
  if (to.name !== 'ServerSetup' && !(await hasServerUrl())) {
    next({ name: 'ServerSetup', query: { redirect: to.fullPath } })
    return
  }

  if (!['ServerSetup', 'Login', 'Register'].includes(to.name) && !hasAccessToken()) {
    next({ name: 'Login' })
    return
  }

  next()
})

export default router
