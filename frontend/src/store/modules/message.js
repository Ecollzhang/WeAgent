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

    const aParentIndex = a.parent_message_id ? userIndex[a.parent_message_id] : undefined
    const bParentIndex = b.parent_message_id ? userIndex[b.parent_message_id] : undefined
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

function elementKey(element) {
  if (!element) return ''
  const content = element.content || element?.data?.content || ''
  const title = element?.data?.title || element.title || ''
  const type = element?.type || ''
  const isDiff = type === 'diff'
    || element?.data?.diff_text
    || element?.data?.data?.diff_text
    || element?.data?.diff_stat
    || element?.data?.data?.diff_stat
  if (isDiff) {
    const diffPath = element?.data?.path || element?.data?.data?.path || ''
    const diffSnippet = String(element?.data?.diff_text || element?.data?.data?.diff_text || element.content || '').slice(0, 60)
    return `diff::${diffPath}::${diffSnippet}`
  }
  return (
    element?.data?.progress_key ||
    element?.detail?.progress_key ||
    element?.step_id ||
    element?.data?.url ||
    element?.data?.path ||
    element?.data?.name ||
    [type, element.status || '', title, String(content).slice(0, 240)].join('|')
  )
}

function mergeElements(existing = [], incoming = []) {
  const merged = []
  ;(Array.isArray(existing) ? existing : []).forEach(element => {
    const key = elementKey(element)
    if (!key || !merged.some(item => elementKey(item) === key)) {
      merged.push(element)
    }
  })
  ;(Array.isArray(incoming) ? incoming : []).forEach(element => {
    const key = elementKey(element)
    const index = key ? merged.findIndex(item => elementKey(item) === key) : -1
    if (index !== -1) {
      Vue.set(merged, index, element)
    } else {
      merged.push(element)
    }
  })
  return merged
}

function eventKey(event) {
  if (!event) return ''
  return event.seq != null
    ? `seq:${event.seq}`
    : [event.type || '', event.title || '', event.created_at || ''].join('|')
}

function mergeEvents(existing = [], incoming = []) {
  const merged = []
  ;(Array.isArray(existing) ? existing : []).forEach(event => {
    const key = eventKey(event)
    if (!key || !merged.some(item => eventKey(item) === key)) {
      merged.push(event)
    }
  })
  ;(Array.isArray(incoming) ? incoming : []).forEach(event => {
    const key = eventKey(event)
    const index = key ? merged.findIndex(item => eventKey(item) === key) : -1
    if (index !== -1) {
      Vue.set(merged, index, event)
    } else {
      merged.push(event)
    }
  })
  return merged
}

function mergeMeta(existing, incoming) {
  const oldMeta = existing && typeof existing === 'object' ? existing : {}
  const newMeta = incoming && typeof incoming === 'object' ? incoming : {}
  const next = { ...oldMeta, ...newMeta }
  const events = mergeEvents(oldMeta.events, newMeta.events)
  if (events.length) next.events = events
  return Object.keys(next).length ? next : incoming
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
    const existing = state.messages[conversationId] || []
    const existingById = {}
    existing.forEach(message => {
      existingById[message.id] = message
    })
    const merged = (messages || []).map(message => {
      const old = existingById[message.id]
      if (!old) return message
      const next = { ...old, ...message }
      if (!message.content && old.content) next.content = old.content
      if (!message.raw_output && old.raw_output) next.raw_output = old.raw_output
      next.meta = mergeMeta(old.meta, message.meta)
      if (Array.isArray(old.elements) && old.elements.length) {
        next.elements = Array.isArray(message.elements) && message.elements.length
          ? mergeElements(old.elements, message.elements)
          : old.elements
      }
      return next
    })
    Vue.set(state.messages, conversationId, sortMessages(merged))
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
      const next = { ...msgs[idx], ...message }
      if (!message.content && msgs[idx].content) next.content = msgs[idx].content
      if (!message.raw_output && msgs[idx].raw_output) next.raw_output = msgs[idx].raw_output
      next.meta = mergeMeta(msgs[idx].meta, message.meta)
      if (Array.isArray(msgs[idx].elements) && msgs[idx].elements.length) {
        next.elements = Array.isArray(message.elements) && message.elements.length
          ? mergeElements(msgs[idx].elements, message.elements)
          : msgs[idx].elements
      }
      Vue.set(msgs, idx, next)
    }
    Vue.set(state.messages, conversationId, sortMessages(msgs))
  },
  UPDATE_MESSAGE(state, { conversationId, messageId, patch }) {
    const msgs = state.messages[conversationId]
    if (!msgs) return
    const idx = msgs.findIndex(m => m.id === messageId)
    if (idx !== -1) {
      const cleanedPatch = { ...patch }
      if (!cleanedPatch.content && msgs[idx].content) delete cleanedPatch.content
      if (!cleanedPatch.raw_output && msgs[idx].raw_output) delete cleanedPatch.raw_output
      if (Array.isArray(msgs[idx].elements) && msgs[idx].elements.length) {
        if (!Array.isArray(cleanedPatch.elements) || !cleanedPatch.elements.length) {
          delete cleanedPatch.elements
        } else {
          cleanedPatch.elements = mergeElements(msgs[idx].elements, cleanedPatch.elements)
        }
      }
      const next = { ...msgs[idx], ...cleanedPatch }
      next.meta = mergeMeta(msgs[idx].meta, cleanedPatch.meta)
      Vue.set(msgs, idx, next)
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
    const progressKey = element?.data?.progress_key || element?.detail?.progress_key || element?.step_id
    const replaceIndex = progressKey
      ? elements.findIndex(el => (
        el?.data?.progress_key || el?.detail?.progress_key || el?.step_id
      ) === progressKey)
      : -1
    if (replaceIndex !== -1) {
      Vue.set(elements, replaceIndex, element)
    } else {
      elements.push(element)
    }
    const cleanedPatch = { ...patch }
    delete cleanedPatch.elements
    Vue.set(msgs, idx, { ...msgs[idx], ...cleanedPatch, elements })
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
