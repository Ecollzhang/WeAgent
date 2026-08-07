import { getWorkspaces, createWorkspace, updateWorkspace, archiveWorkspace, deleteWorkspace } from '../../api/workspace'

// localStorage keys
const ACTIVE_WS_KEY = 'active_workspace'
const LAST_DOMAIN_KEY = 'last_domain'

function loadActiveWs() {
  try {
    const raw = localStorage.getItem(ACTIVE_WS_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    // Discard corrupted entries with no valid workspace id
    if (!data || !data.id) {
      localStorage.removeItem(ACTIVE_WS_KEY)
      localStorage.removeItem(LAST_DOMAIN_KEY)
      return null
    }
    return data
  } catch { return null }
}

function saveActiveWs(ws) {
  if (ws && ws.id) {
    localStorage.setItem(ACTIVE_WS_KEY, JSON.stringify({
      id: ws.id, domain: ws.domain, name: ws.name, sub_role: ws.sub_role || '',
    }))
    // Only remember domain when a real workspace is selected
    localStorage.setItem(LAST_DOMAIN_KEY, ws.domain)
  } else if (!ws || !ws.id) {
    // Don't persist empty-domain browsing — keep previous active workspace
    if (!ws) {
      localStorage.removeItem(ACTIVE_WS_KEY)
    }
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
    activeDomain: state => state.activeWorkspace?.domain || localStorage.getItem(LAST_DOMAIN_KEY) || 'rd',
    activeWorkspaceId: state => state.activeWorkspace?.id || null,
    activeSubRole: state => state.activeWorkspace?.sub_role || '',
    isLoading: state => state.loading,
    workspacesByDomain: state => domain => state.workspaces.filter(w => w.domain === domain),
  },

  mutations: {
    RESET_STATE(state) {
      state.workspaces = []
      state.activeWorkspace = null
      state.loading = false
      saveActiveWs(null)
    },
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

    async deleteWorkspace({ commit, state }, id) {
      const res = await deleteWorkspace(id)
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
