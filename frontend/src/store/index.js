import Vue from 'vue'
import Vuex from 'vuex'
import user from './modules/user'
import conversation from './modules/conversation'
import message from './modules/message'
import agent from './modules/agent'
import settings from './modules/settings'
import workspace from './modules/workspace'
import grayscale from './modules/grayscale'
import office from './modules/office'
import rd from './modules/rd'

Vue.use(Vuex)

export default new Vuex.Store({
  modules: {
    user,
    conversation,
    message,
    agent,
    settings,
    workspace,
    grayscale,
    office,
    rd,
  },
})
