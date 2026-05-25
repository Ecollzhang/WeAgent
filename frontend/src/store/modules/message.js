import Vue from 'vue'
import { getMessages, sendMessage as apiSendMessage, togglePin, getPinnedMessages } from '../../api/message'

function sortMessages(messages) {
  const rank = { user: 0, agent: 1 }
  const userIndex = {}
  messages.forEach((message, index) => {
    if (message.sender_type === 'user') {
      userIndex[message.id] = index
    }
  })

  return messages.slice().sort((a, b) => {
    if (a.parent_message_id && a.parent_message_id === b.id) return 1
    if (b.parent_message_id && b.parent_message_id === a.id) return -1

    const aParentIndex = a.parent_message_id && userIndex[a.parent_message_id]
    const bParentIndex = b.parent_message_id && userIndex[b.parent_message_id]
    if (aParentIndex !== undefined || bParentIndex !== undefined) {
      const ag = aParentIndex !== undefined ? aParentIndex : userIndex[a.id]
      const bg = bParentIndex !== undefined ? bParentIndex : userIndex[b.id]
      if (ag !== undefined && bg !== undefined && ag !== bg) return ag - bg
    }

    const at = new Date(a.created_at || 0).getTime()
    const bt = new Date(b.created_at || 0).getTime()
    if (at !== bt) return at - bt
    return (rank[a.sender_type] ?? 2) - (rank[b.sender_type] ?? 2)
  })
}

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
    Vue.set(state.messages, conversationId, sortMessages(messages || []))
  },
  APPEND_MESSAGE(state, { conversationId, message }) {
    if (!state.messages[conversationId]) {
      Vue.set(state.messages, conversationId, [])
    }
    if (state.messages[conversationId].some(m => m.id === message.id)) {
      return
    }
    Vue.set(state.messages, conversationId, sortMessages([...state.messages[conversationId], message]))
  },
  UPSERT_MESSAGE(state, { conversationId, message }) {
    if (!state.messages[conversationId]) {
      Vue.set(state.messages, conversationId, [])
    }
    const msgs = state.messages[conversationId]
    const idx = msgs.findIndex(m => m.id === message.id)
    if (idx === -1) {
      msgs.push(message)
    } else {
      Vue.set(msgs, idx, { ...msgs[idx], ...message })
    }
    Vue.set(state.messages, conversationId, sortMessages(msgs))
  },
  UPDATE_MESSAGE(state, { conversationId, messageId, patch }) {
    const msgs = state.messages[conversationId]
    if (!msgs) return
    const idx = msgs.findIndex(m => m.id === messageId)
    if (idx !== -1) {
      Vue.set(msgs, idx, { ...msgs[idx], ...patch })
    }
  },
  ADD_MESSAGE_ELEMENT(state, { conversationId, messageId, element }) {
    const msgs = state.messages[conversationId]
    if (!msgs) return
    const idx = msgs.findIndex(m => m.id === messageId)
    if (idx === -1) return
    const elements = Array.isArray(msgs[idx].elements) ? msgs[idx].elements.slice() : []
    const key = element?.data?.url || element?.data?.name
    const exists = key && elements.some(el => (el?.data?.url || el?.data?.name) === key)
    if (!exists) {
      elements.push(element)
      Vue.set(msgs, idx, { ...msgs[idx], elements })
    }
  },
  APPEND_MESSAGE_ELEMENT(state, { conversationId, messageId, element, patch = {} }) {
    const msgs = state.messages[conversationId]
    if (!msgs || !element) return
    const idx = msgs.findIndex(m => m.id === messageId)
    if (idx === -1) return
    const elements = Array.isArray(msgs[idx].elements) ? msgs[idx].elements.slice() : []
    elements.push(element)
    Vue.set(msgs, idx, { ...msgs[idx], ...patch, elements })
  },
  ADD_MESSAGE_EVENT(state, { conversationId, messageId, event, events }) {
    const msgs = state.messages[conversationId]
    if (!msgs) return
    const idx = msgs.findIndex(m => m.id === messageId)
    if (idx === -1) return
    const meta = { ...(msgs[idx].meta || {}) }
    if (Array.isArray(events)) {
      meta.events = events
    } else if (event) {
      const existing = Array.isArray(meta.events) ? meta.events.slice() : []
      existing.push(event)
      meta.events = existing
    }
    Vue.set(msgs, idx, { ...msgs[idx], meta })
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
