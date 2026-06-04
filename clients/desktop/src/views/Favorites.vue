<template>
  <main class="dashboard-shell">
    <aside class="app-sidebar">
      <div class="sidebar-logo">W</div>
      <nav class="sidebar-nav">
        <button class="sidebar-btn" title="会话" @click="$router.push('/conversations')"><i class="el-icon-chat-dot-round"></i></button>
        <button class="sidebar-btn" title="智能体" @click="$router.push('/agents')"><i class="el-icon-user"></i></button>
        <button class="sidebar-btn" title="工具" disabled><i class="el-icon-s-tools"></i></button>
        <button class="sidebar-btn active" title="我的收藏"><i class="el-icon-collection-tag"></i></button>
        <button class="sidebar-btn" title="设置" @click="$router.push('/settings')"><i class="el-icon-setting"></i></button>
      </nav>
      <button class="sidebar-user" title="退出登录" @click="logout"><i class="el-icon-switch-button"></i></button>
    </aside>

    <section class="desktop-favorites-page">
      <header class="desktop-favorites-header">
        <div>
          <h1>我的收藏</h1>
          <p>集中查看已经收藏的对话，可以快速回到聊天或取消收藏。</p>
        </div>
        <button class="favorites-refresh" :disabled="loading" @click="loadConversations">
          <i :class="loading ? 'el-icon-loading' : 'el-icon-refresh'"></i>
          <span>刷新</span>
        </button>
      </header>

      <div class="desktop-favorites-tools">
        <label class="favorites-search">
          <i class="el-icon-search"></i>
          <input v-model.trim="searchQuery" placeholder="搜索收藏的对话" />
        </label>
        <select v-model="typeFilter">
          <option value="all">全部类型</option>
          <option value="single">单 Agent</option>
          <option value="group">多 Agent</option>
        </select>
        <select v-model="sortBy">
          <option value="updated_desc">最近更新</option>
          <option value="updated_asc">最早更新</option>
          <option value="title">标题排序</option>
        </select>
      </div>

      <div v-if="loading" class="favorites-state">
        <i class="el-icon-loading"></i>
        <span>正在加载收藏会话...</span>
      </div>

      <div v-else-if="filteredFavorites.length === 0" class="favorites-state">
        <i class="el-icon-star-off"></i>
        <span>{{ favoriteConversations.length ? '没有符合过滤条件的收藏' : '暂无收藏会话' }}</span>
      </div>

      <div v-else class="desktop-favorites-list">
        <article
          v-for="conversation in filteredFavorites"
          :key="conversation.id"
          class="favorite-card"
          role="button"
          tabindex="0"
          @click="openConversation(conversation)"
          @keydown.enter.prevent="openConversation(conversation)"
        >
          <div class="favorite-avatar item-avatar" :style="convAvatarBg(conversation)">
            <template v-if="avatarParticipants(conversation).length === 0">
              <i class="el-icon-chat-dot-round"></i>
            </template>
            <template v-else-if="avatarParticipants(conversation).length === 1">
              <img
                v-if="participantAvatar(avatarParticipants(conversation)[0])"
                :src="participantAvatar(avatarParticipants(conversation)[0])"
                class="avatar-img"
              />
              <span v-else class="avatar-letter-sm">{{ firstLetter(avatarParticipants(conversation)[0].name) }}</span>
            </template>
            <template v-else>
              <div class="composite-avatar">
                <div
                  v-for="(participant, index) in avatarParticipants(conversation).slice(0, 3)"
                  :key="index"
                  class="composite-item"
                  :style="participantAvatar(participant) ? {} : { background: participantColor(participant) }"
                >
                  <img v-if="participantAvatar(participant)" :src="participantAvatar(participant)" class="composite-img" />
                  <span v-else class="composite-text">{{ firstLetter(participant.name) }}</span>
                </div>
                <div v-if="avatarParticipants(conversation).length > 3" class="composite-item composite-more">
                  <span class="composite-text">+{{ avatarParticipants(conversation).length - 3 }}</span>
                </div>
              </div>
            </template>
          </div>

          <div class="favorite-main">
            <div class="favorite-title-row">
              <h2>{{ conversation.title || '未命名会话' }}</h2>
              <span class="favorite-type">{{ conversation.type === 'single' ? '单 Agent' : '多 Agent' }}</span>
            </div>
            <p class="favorite-preview">
              {{ conversation.last_message && conversation.last_message.content ? conversation.last_message.content : '暂无消息' }}
            </p>
            <div class="favorite-meta">
              <span>{{ participantNames(conversation) }}</span>
              <span>{{ formatTime(conversation.updated_at || conversation.created_at) }}</span>
            </div>
          </div>

          <div class="favorite-actions" @click.stop>
            <button title="进入对话" @click="openConversation(conversation)">
              <i class="el-icon-position"></i>
            </button>
            <button title="复制 ID" @click="copyId(conversation)">
              <i class="el-icon-document-copy"></i>
            </button>
            <button title="取消收藏" class="favorite-remove" @click="removeFavorite(conversation)">
              <i class="el-icon-star-on"></i>
            </button>
          </div>
        </article>
      </div>

      <div v-if="error" class="desktop-toast">{{ error }}</div>
    </section>
  </main>
</template>

<script>
import { getConversations, updateConversationFavorite } from '../services/api'
import { backendUrl, getServerUrl } from '../services/config'
import { clearAuth } from '../services/session'

export default {
  name: 'Favorites',
  data() {
    return {
      conversations: [],
      serverUrl: '',
      searchQuery: '',
      typeFilter: 'all',
      sortBy: 'updated_desc',
      loading: false,
      error: '',
    }
  },
  computed: {
    favoriteConversations() {
      return this.conversations.filter(item => item && item.is_favorite)
    },
    filteredFavorites() {
      const query = this.searchQuery.toLowerCase()
      const list = this.favoriteConversations.filter(item => {
        const title = String(item.title || '').toLowerCase()
        const preview = String((item.last_message && item.last_message.content) || '').toLowerCase()
        const participants = this.participantNames(item).toLowerCase()
        const matchedQuery = !query || title.includes(query) || preview.includes(query) || participants.includes(query)
        const matchedType = this.typeFilter === 'all' || item.type === this.typeFilter
        return matchedQuery && matchedType
      })
      return list.sort((a, b) => {
        if (this.sortBy === 'title') {
          return String(a.title || '').localeCompare(String(b.title || ''), 'zh-CN')
        }
        const at = new Date(a.updated_at || a.created_at || 0).getTime() || 0
        const bt = new Date(b.updated_at || b.created_at || 0).getTime() || 0
        return this.sortBy === 'updated_asc' ? at - bt : bt - at
      })
    },
  },
  async created() {
    this.serverUrl = await getServerUrl()
    await this.loadConversations()
  },
  methods: {
    async loadConversations() {
      this.loading = true
      this.error = ''
      try {
        const response = await getConversations()
        this.conversations = Array.isArray(response.data) ? response.data : []
      } catch (error) {
        this.handleRequestError(error, '加载收藏失败')
      } finally {
        this.loading = false
      }
    },
    openConversation(conversation) {
      if (!conversation || !conversation.id) return
      this.$router.push({ path: '/conversations', query: { conversation_id: conversation.id } })
    },
    async removeFavorite(conversation) {
      if (!conversation || !conversation.id) return
      this.error = ''
      const index = this.conversations.findIndex(item => String(item.id) === String(conversation.id))
      const previous = index >= 0 ? { ...this.conversations[index] } : null
      if (index >= 0) {
        this.$set(this.conversations, index, { ...this.conversations[index], is_favorite: false })
      }
      try {
        await updateConversationFavorite(conversation.id, false)
      } catch (error) {
        if (index >= 0 && previous) this.$set(this.conversations, index, previous)
        this.handleRequestError(error, '取消收藏失败')
      }
    },
    async copyId(conversation) {
      if (!conversation || !conversation.id || !navigator.clipboard) return
      await navigator.clipboard.writeText(conversation.id)
    },
    avatarParticipants(conversation) {
      if (!conversation || !conversation.participants_info) return []
      if (conversation.type === 'single') {
        return conversation.participants_info.filter(p => p.participant_type !== 'user').slice(0, 1)
      }
      return conversation.participants_info
    },
    convAvatarBg(conversation) {
      const infos = this.avatarParticipants(conversation)
      if (infos.length !== 1 || this.participantAvatar(infos[0])) return {}
      return { background: this.participantColor(infos[0]) }
    },
    participantAvatar(participant) {
      const avatar = participant && (participant.avatar || participant.avatar_url)
      return avatar ? backendUrl(this.serverUrl, avatar) : ''
    },
    participantColor(participant) {
      return (participant && (participant.color || participant.avatar_color)) || '#4080ff'
    },
    participantNames(conversation) {
      const names = ((conversation && conversation.participants_info) || [])
        .filter(item => item.participant_type !== 'user')
        .map(item => item.name)
        .filter(Boolean)
      return names.length ? names.join('、') : '暂无参与者'
    },
    firstLetter(value) {
      return String(value || '?').charAt(0).toUpperCase()
    },
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return ''
      return date.toLocaleString([], { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    },
    handleRequestError(error, fallback) {
      this.error = (error && error.response && error.response.data && error.response.data.message) || (error && error.message) || fallback
      if (error && error.response && error.response.status === 401) {
        clearAuth()
        this.$router.replace('/login')
      }
    },
    logout() {
      clearAuth()
      this.$router.replace('/login')
    },
  },
}
</script>
