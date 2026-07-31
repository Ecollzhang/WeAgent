import { login, register, getProfile } from '../../api/auth'
import { clearUserSessionStorage } from '../../utils/session-storage'

const state = {
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  accessToken: localStorage.getItem('access_token') || '',
  refreshToken: localStorage.getItem('refresh_token') || '',
}

const getters = {
  isAuthenticated: state => !!state.accessToken,
  currentUser: state => state.user,
  userId: state => state.user?.id || null,
}

const mutations = {
  SET_USER(state, user) {
    state.user = user
    localStorage.setItem('user', JSON.stringify(user))
  },
  SET_TOKENS(state, { accessToken, refreshToken }) {
    state.accessToken = accessToken
    state.refreshToken = refreshToken
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
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
