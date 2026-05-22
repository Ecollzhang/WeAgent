import { getModelConfig, saveModelConfig } from '../../api/settings'

const state = {
  modelConfig: JSON.parse(localStorage.getItem('model_config') || 'null'),
}

const getters = {
  modelConfig: state => state.modelConfig,
}

const mutations = {
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
    commit('SET_MODEL_CONFIG', config)
    try {
      await saveModelConfig(config)
    } catch (e) {
      // Saved locally even if API fails
    }
  },
}

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
}
