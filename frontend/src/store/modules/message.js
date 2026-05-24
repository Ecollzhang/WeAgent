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
    if (message.id && state.messages[conversationId].some(m => m.id === message.id)) {
      return
    }
    state.messages[conversationId].push(message)
  },
  APPEND_STREAMING_DELTA(state, { conversationId, event }) {
    if (!state.messages[conversationId]) {
      Vue.set(state.messages, conversationId, [])
    }
    const id = `stream_${event.runId}`
    const msgs = state.messages[conversationId]
    const idx = msgs.findIndex(m => m.id === id)
    const delta = event.content || ''
    if (idx === -1) {
      msgs.push({
        id,
        conversation_id: conversationId,
        sender_type: 'agent',
        sender_id: String(event.agentId || ''),
        sender_name: event.agentName || 'Agent',
        content: delta,
        message_type: 'text',
        created_at: event.timestamp || new Date().toISOString(),
        is_streaming: true,
      })
      return
    }
    Vue.set(msgs, idx, {
      ...msgs[idx],
      content: `${msgs[idx].content || ''}${delta}`,
      is_streaming: true,
    })
  },
  FINALIZE_STREAMING_MESSAGE(state, { conversationId, event }) {
    const msgs = state.messages[conversationId]
    if (!msgs) return
    const id = `stream_${event.runId}`
    const idx = msgs.findIndex(m => m.id === id)
    if (idx === -1) return
    Vue.set(msgs, idx, {
      ...msgs[idx],
      content: event.content || msgs[idx].content,
      is_streaming: false,
    })
  },
  FAIL_STREAMING_MESSAGE(state, { conversationId, event }) {
    if (!state.messages[conversationId]) {
      Vue.set(state.messages, conversationId, [])
    }
    const id = `stream_${event.runId}`
    const content = event.message || event.content || 'Agent 调用失败'
    const msgs = state.messages[conversationId]
    const idx = msgs.findIndex(m => m.id === id)
    const failedMessage = {
      id,
      conversation_id: conversationId,
      sender_type: 'agent',
      sender_id: String(event.agentId || ''),
      sender_name: event.agentName || 'Agent',
      content,
      message_type: 'text',
      created_at: event.timestamp || new Date().toISOString(),
      is_streaming: false,
      is_failed: true,
    }
    if (idx === -1) {
      msgs.push(failedMessage)
    } else {
      Vue.set(msgs, idx, failedMessage)
    }
  },
  REMOVE_STREAMING_MESSAGES_FOR_AGENT(state, { conversationId, agentId }) {
    const msgs = state.messages[conversationId]
    if (!msgs) return
    Vue.set(state.messages, conversationId, msgs.filter(msg => {
      return !(msg.is_streaming === false && msg.id?.startsWith('stream_') && String(msg.sender_id) === String(agentId))
    }))
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
  SET_PINNED_MESSAGES(state, messages) {
    state.pinnedMessages = messages
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
