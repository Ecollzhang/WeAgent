import Vue from 'vue'
import { getMessages, sendMessage as apiSendMessage, togglePin, getPinnedMessages } from '../../api/message'

const state = {
  messages: {},
  pinnedMessages: [],
  loading: false,
}

const getters = {
  getMessagesByConversation: state => conversationId => {
    return state.messages[conversationId] || []
  },
  pinnedMessages: state => state.pinnedMessages,
  isLoading: state => state.loading,
}

const mutations = {
  SET_MESSAGES(state, { conversationId, messages }) {
    Vue.set(state.messages, conversationId, messages)
  },
  APPEND_MESSAGE(state, { conversationId, message }) {
    if (!state.messages[conversationId]) {
      Vue.set(state.messages, conversationId, [])
    }
    state.messages[conversationId].push(message)
  },
  UPDATE_MESSAGE_ID(state, { conversationId, tempId, realId }) {
    const msgs = state.messages[conversationId]
    if (msgs) {
      const idx = msgs.findIndex(m => m.id === tempId)
      if (idx !== -1) {
        Vue.set(msgs, idx, { ...msgs[idx], id: realId })
      }
    }
  },
  UPDATE_DEPLOY_STATUS(state, { conversationId, deployId, status, progress, logs, preview_url }) {
    if (!state.messages[conversationId]) return
    for (const msg of state.messages[conversationId]) {
      if (!msg.elements) continue
      const elems = typeof msg.elements === 'string' ? JSON.parse(msg.elements) : msg.elements
      for (const el of elems) {
        if (el.type === 'deploy_status' && el.data && el.data.deploy_id === deployId) {
          el.data.status = status
          el.data.progress = progress
          if (logs) el.data.logs = logs
          if (preview_url) el.data.preview_url = preview_url
          return
        }
      }
    }
  },
  SET_PINNED_MESSAGES(state, messages) {
  },
  SET_LOADING(state, loading) {
    state.loading = loading
  },
}

const actions = {
  async fetchMessages({ commit }, { conversationId, page = 1, perPage = 50 }) {
    commit('SET_LOADING', true)
    try {
      const response = await getMessages(conversationId, { page, per_page: perPage })
      if (response.code === 200) {
        commit('SET_MESSAGES', {
          conversationId,
          messages: response.data.items || [],
        })
        return response.data
      }
    } finally {
      commit('SET_LOADING', false)
    }
  },

  async sendMessage({ commit }, data) {
    const response = await apiSendMessage(data)
    if (response.code === 201) {
      commit('APPEND_MESSAGE', {
        conversationId: data.conversation_id,
        message: response.data,
      })
      return response.data
    }
    return null
  },

  addMessage({ commit }, { conversationId, message }) {
    commit('APPEND_MESSAGE', { conversationId, message })
  },

  async togglePin({ commit }, messageId) {
    const response = await togglePin(messageId)
    return response
  },

  async fetchPinnedMessages({ commit }, conversationId) {
    const response = await getPinnedMessages(conversationId)
    if (response.code === 200) {
      commit('SET_PINNED_MESSAGES', response.data)
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
