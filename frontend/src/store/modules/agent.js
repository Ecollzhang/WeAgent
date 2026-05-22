import { getAgents, createAgent, updateAgent as apiUpdateAgent, deleteAgent } from '../../api/agent'

const state = {
  agents: [],
  loading: false,
}

const getters = {
  allAgents: state => state.agents,
  isLoading: state => state.loading,
  getAgentById: state => id => state.agents.find(a => a.id === id),
}

const mutations = {
  SET_AGENTS(state, agents) {
    state.agents = agents
  },
  ADD_AGENT(state, agent) {
    state.agents.push(agent)
  },
  UPDATE_AGENT(state, updatedAgent) {
    const i = state.agents.findIndex(a => a.id === updatedAgent.id)
    if (i !== -1) state.agents.splice(i, 1, updatedAgent)
  },
  REMOVE_AGENT(state, agentId) {
    state.agents = state.agents.filter(a => a.id !== agentId)
  },
  SET_LOADING(state, loading) {
    state.loading = loading
  },
}

const actions = {
  async fetchAgents({ commit }) {
    commit('SET_LOADING', true)
    try {
      const response = await getAgents()
      if (response.code === 200) {
        commit('SET_AGENTS', response.data)
      }
    } finally {
      commit('SET_LOADING', false)
    }
  },

  async createAgent({ commit }, data) {
    const response = await createAgent(data)
    if (response.code === 201) {
      commit('ADD_AGENT', response.data)
    }
    return response
  },

  async updateAgent({ commit }, { id, data }) {
    const response = await apiUpdateAgent(id, data)
    if (response.code === 200) {
      commit('UPDATE_AGENT', response.data)
    }
    return response
  },

  async deleteAgent({ commit }, agentId) {
    const response = await deleteAgent(agentId)
    if (response.code === 200) {
      commit('REMOVE_AGENT', agentId)
    }
    return response
  },
}

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
}
