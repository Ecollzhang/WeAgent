import { getModelConfig, saveModelConfig } from '../../api/settings'

const state = {
  modelConfig: JSON.parse(localStorage.getItem('model_config') || 'null'),
}

const getters = {
  modelConfig: state => state.modelConfig,
}

const mutations = {
  RESET_STATE(state) {
    state.modelConfig = null
    localStorage.removeItem('model_config')
  },
  SET_MODEL_CONFIG(state, config) {
    state.modelConfig = config
    localStorage.setItem('model_config', JSON.stringify(config))
  },
}

const actions = {
  async fetchModelConfig({ commit }) {
    try {
      const response = await getModelConfig()
      if (response.code === 200) {
        commit('SET_MODEL_CONFIG', response.data)
      }
    } catch (e) {
      // Use local config if API fails
    }
  },

  async saveModelConfig({ commit }, config) {
    try {
      const response = await saveModelConfig(config)
      if (response.code === 200) {
        commit('SET_MODEL_CONFIG', response.data)
        return response.data
      }
    } catch (e) {
      // Saved locally even if API fails
    }
    commit('SET_MODEL_CONFIG', config)
    return config
  },
}

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
}
