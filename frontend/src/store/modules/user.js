import { login, register, getProfile } from '../../api/auth'

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
    state.user = user
    sessionStorage.setItem('user', JSON.stringify(user))
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
    sessionStorage.removeItem('user')
    sessionStorage.removeItem('access_token')
    sessionStorage.removeItem('refresh_token')
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
  },
}

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
}
