import { getWorkspaces, createWorkspace, updateWorkspace, archiveWorkspace } from '../../api/workspace'

// localStorage keys
const ACTIVE_WS_KEY = 'active_workspace'

function loadActiveWs() {
  try {
    const raw = localStorage.getItem(ACTIVE_WS_KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

function saveActiveWs(ws) {
  if (ws) {
    localStorage.setItem(ACTIVE_WS_KEY, JSON.stringify({
      id: ws.id, domain: ws.domain, name: ws.name, sub_role: ws.sub_role || '',
    }))
  } else {
    localStorage.removeItem(ACTIVE_WS_KEY)
  }
}

export default {
  namespaced: true,

  state: {
    workspaces: [],
    activeWorkspace: loadActiveWs(),
    loading: false,
  },

  getters: {
    allWorkspaces: state => state.workspaces,
    activeWorkspace: state => state.activeWorkspace,
    activeDomain: state => state.activeWorkspace?.domain || 'rd',
    activeWorkspaceId: state => state.activeWorkspace?.id || null,
    activeSubRole: state => state.activeWorkspace?.sub_role || '',
    isLoading: state => state.loading,
    workspacesByDomain: state => domain => state.workspaces.filter(w => w.domain === domain),
  },

  mutations: {
    SET_WORKSPACES(state, workspaces) {
      state.workspaces = workspaces
    },
    SET_ACTIVE_WORKSPACE(state, ws) {
      state.activeWorkspace = ws
      saveActiveWs(ws)
    },
    ADD_WORKSPACE(state, ws) {
      state.workspaces.push(ws)
    },
    UPDATE_WORKSPACE(state, updated) {
      const idx = state.workspaces.findIndex(w => w.id === updated.id)
      if (idx >= 0) state.workspaces.splice(idx, 1, updated)
    },
    REMOVE_WORKSPACE(state, id) {
      state.workspaces = state.workspaces.filter(w => w.id !== id)
    },
    SET_LOADING(state, loading) {
      state.loading = loading
    },
  },

  actions: {
    async fetchWorkspaces({ commit }, domain = '') {
      commit('SET_LOADING', true)
      try {
        const res = await getWorkspaces(domain)
        if (res.code === 200) {
          commit('SET_WORKSPACES', res.data)
        }
      } finally {
        commit('SET_LOADING', false)
      }
    },

    async createWorkspace({ commit }, data) {
      const res = await createWorkspace(data)
      if (res.code === 201) {
        commit('ADD_WORKSPACE', res.data)
        commit('SET_ACTIVE_WORKSPACE', res.data)
      }
      return res
    },

    async updateWorkspace({ commit }, { id, data }) {
      const res = await updateWorkspace(id, data)
      if (res.code === 200) {
        commit('UPDATE_WORKSPACE', res.data)
        const active = loadActiveWs()
        if (active && active.id === id) {
          commit('SET_ACTIVE_WORKSPACE', res.data)
        }
      }
      return res
    },

    async archiveWorkspace({ commit, state }, id) {
      const res = await archiveWorkspace(id)
      if (res.code === 200) {
        commit('REMOVE_WORKSPACE', id)
        if (state.activeWorkspace?.id === id) {
          commit('SET_ACTIVE_WORKSPACE', null)
        }
      }
      return res
    },

    selectWorkspace({ commit }, ws) {
      commit('SET_ACTIVE_WORKSPACE', ws)
    },
  },
}
