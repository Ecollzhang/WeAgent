import { getGrayscaleConfig, getGrayscaleDomains } from '../../api/grayscale'

/**
 * Pure function: check if a config key is visible for a given domain.
 * Components should call this directly with `this.$store.state.grayscale`
 * so Vue tracks the reactive dependency on configsByDomain.
 */
export function checkVisible(state, domain, configKey) {
  const domainConfigs = state.configsByDomain[domain] || []
  let item = domainConfigs.find(c => c.config_key === configKey)
  if (item) {
    return item.visible !== false && item.visible !== 0
  }
  if (domain !== 'common') {
    const commonConfigs = state.configsByDomain['common'] || []
    item = commonConfigs.find(c => c.config_key === configKey)
    if (item) {
      const d = item.domains || []
      if (d.length > 0 && !d.includes(domain)) {
        return false
      }
      return item.visible !== false && item.visible !== 0
    }
  }
  return true
}

/** Pure function: check if a config key is enabled for a given domain. */
export function checkEnabled(state, domain, configKey) {
  const domainConfigs = state.configsByDomain[domain] || []
  let item = domainConfigs.find(c => c.config_key === configKey)
  if (item) {
    return item.enabled !== false && item.enabled !== 0
  }
  if (domain !== 'common') {
    const commonConfigs = state.configsByDomain['common'] || []
    item = commonConfigs.find(c => c.config_key === configKey)
    if (item) {
      const d = item.domains || []
      if (d.length > 0 && !d.includes(domain)) {
        return false
      }
      return item.enabled !== false && item.enabled !== 0
    }
  }
  return true
}

export default {
  namespaced: true,

  state: {
    configsByDomain: {},
    domains: [],
    loading: false,
  },

  getters: {
    configsForDomain: state => domain => state.configsByDomain[domain] || [],
    allDomains: state => state.domains,
    isLoading: state => state.loading,
  },

  mutations: {
    SET_CONFIGS(state, { domain, configs }) {
      state.configsByDomain = { ...state.configsByDomain, [domain]: configs }
    },
    SET_DOMAINS(state, domains) {
      state.domains = domains
    },
    SET_LOADING(state, loading) {
      state.loading = loading
    },
  },

  actions: {
    async fetchGrayscaleConfig({ commit }, domain) {
      commit('SET_LOADING', true)
      try {
        const res = await getGrayscaleConfig(domain)
        if (res.code === 200) {
          commit('SET_CONFIGS', { domain, configs: res.data })
        }
      } finally {
        commit('SET_LOADING', false)
      }
    },

    async fetchGrayscaleDomains({ commit }) {
      const res = await getGrayscaleDomains()
      if (res.code === 200) {
        commit('SET_DOMAINS', res.data)
      }
    },

    async loadDomainConfig({ dispatch }, domain) {
      await Promise.all([
        dispatch('fetchGrayscaleConfig', domain),
        dispatch('fetchGrayscaleConfig', 'common'),
      ])
    },
  },
}
