import { getConversations, createConversation, deleteConversation } from '../../api/conversation'

const state = {
  conversations: [],
  currentConversation: null,
  loading: false,
}

const getters = {
  allConversations: state => state.conversations,
  currentConversation: state => state.currentConversation,
  isLoading: state => state.loading,
}

const mutations = {
  SET_CONVERSATIONS(state, conversations) {
    state.conversations = conversations
  },
  SET_CURRENT_CONVERSATION(state, conversation) {
    state.currentConversation = conversation
  },
  ADD_CONVERSATION(state, conversation) {
    state.conversations.unshift(conversation)
  },
  REMOVE_CONVERSATION(state, conversationId) {
    state.conversations = state.conversations.filter(c => c.id !== conversationId)
    if (state.currentConversation && state.currentConversation.id === conversationId) {
      state.currentConversation = null
    }
  },
  SET_LOADING(state, loading) {
    state.loading = loading
  },
}

const actions = {
  async fetchConversations({ commit }) {
    commit('SET_LOADING', true)
    try {
      const response = await getConversations()
      if (response.code === 200) {
        commit('SET_CONVERSATIONS', response.data)
      }
    } finally {
      commit('SET_LOADING', false)
    }
  },

  async createConversation({ commit }, data) {
    const response = await createConversation(data)
    if (response.code === 201) {
      commit('ADD_CONVERSATION', response.data)
    }
    return response
  },

  async deleteConversation({ commit }, conversationId) {
    const response = await deleteConversation(conversationId)
    if (response.code === 200) {
      commit('REMOVE_CONVERSATION', conversationId)
    }
    return response
  },

  selectConversation({ commit }, conversation) {
    commit('SET_CURRENT_CONVERSATION', conversation)
  },
}

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
}
