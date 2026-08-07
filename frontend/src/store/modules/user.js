import { login, register, getProfile } from '../../api/auth'
import { clearUserSessionStorage } from '../../utils/session-storage'

const state = {
  user: JSON.parse(sessionStorage.getItem('user') || 'null'),
  accessToken: sessionStorage.getItem('access_token') || '',
  refreshToken: sessionStorage.getItem('refresh_token') || '',
}

const getters = {
  isAuthenticated: state => !!state.accessToken,
  currentUser: state => state.user,
  userId: state => state.user?.id || null,
}

const mutations = {
  SET_USER(state, user) {
    // Normalize avatar from avatar_url (backend uses avatar_url, frontend uses avatar)
    if (user && !user.avatar && user.avatar_url) {
      user = { ...user, avatar: user.avatar_url }
    }
    state.user = user
    sessionStorage.setItem('user', JSON.stringify(user))
    // Also cache avatar in localStorage for fallback across sessions
    if (user && (user.avatar || user.avatar_url)) {
      localStorage.setItem('user_avatar', user.avatar || user.avatar_url)
    }
  },
  SET_TOKENS(state, { accessToken, refreshToken }) {
    state.accessToken = accessToken
    state.refreshToken = refreshToken
    sessionStorage.setItem('access_token', accessToken)
    sessionStorage.setItem('refresh_token', refreshToken)
  },
  CLEAR_AUTH(state) {
    state.user = null
    state.accessToken = ''
    state.refreshToken = ''
    clearUserSessionStorage()
  },
}

const actions = {
  async login({ commit }, credentials) {
    const response = await login(credentials)
    if (response.code === 200) {
      const { user, access_token, refresh_token } = response.data
      commit('SET_USER', user)
      commit('SET_TOKENS', { accessToken: access_token, refreshToken: refresh_token })
    }
    return response
  },

  async register({ commit }, data) {
    const response = await register(data)
    if (response.code === 201) {
      const { user, access_token, refresh_token } = response.data
      commit('SET_USER', user)
      commit('SET_TOKENS', { accessToken: access_token, refreshToken: refresh_token })
    }
    return response
  },

  async fetchProfile({ commit, state }) {
    if (!state.accessToken) return
    try {
      const response = await getProfile()
      if (response.code === 200) {
        commit('SET_USER', response.data)
      }
    } catch (e) {
      // Ignore profile fetch errors on init
    }
  },

  logout({ commit }) {
    commit('CLEAR_AUTH')
    commit('workspace/RESET_STATE', null, { root: true })
    commit('conversation/RESET_STATE', null, { root: true })
    commit('message/RESET_STATE', null, { root: true })
    commit('agent/RESET_STATE', null, { root: true })
    commit('settings/RESET_STATE', null, { root: true })
    commit('education/RESET_STATE', null, { root: true })
  },
}

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
}
