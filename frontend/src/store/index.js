import Vue from 'vue'
import Vuex from 'vuex'
import user from './modules/user'
import conversation from './modules/conversation'
import message from './modules/message'
import agent from './modules/agent'
import settings from './modules/settings'

Vue.use(Vuex)

export default new Vuex.Store({
  modules: {
    user,
    conversation,
    message,
    agent,
    settings,
  },
})
