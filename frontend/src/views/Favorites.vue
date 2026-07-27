<template>
  <div class="favorites-page">
    <AppSidebar />

    <main class="favorites-content">
      <header class="favorites-header">
        <div>
          <h2>我的收藏</h2>
          <p>集中查看已收藏的会话，并快速回到对应聊天。</p>
        </div>
        <el-button size="small" icon="el-icon-refresh" @click="refresh" :loading="loading">刷新</el-button>
      </header>

      <section class="filter-bar">
        <el-input
          v-model.trim="searchQuery"
          size="small"
          clearable
          prefix-icon="el-icon-search"
          placeholder="搜索标题、参与者或最近消息"
        />
        <el-select v-model="typeFilter" size="small" placeholder="会话类型">
          <el-option label="全部会话" value="all" />
          <el-option label="单 Agent" value="single" />
          <el-option label="多 Agent" value="group" />
        </el-select>
        <el-select v-model="sortBy" size="small" placeholder="排序">
          <el-option label="最近更新优先" value="updated_desc" />
          <el-option label="最早更新优先" value="updated_asc" />
          <el-option label="标题 A-Z" value="title_asc" />
        </el-select>
        <span class="result-count">{{ filteredFavorites.length }} / {{ favoriteConversations.length }}</span>
      </section>

      <section class="favorites-list" v-loading="loading">
        <article
          v-for="conversation in filteredFavorites"
          :key="conversation.id"
          class="favorite-card"
        >
          <div class="favorite-conv-avatar" :style="convAvatarBg(conversation)">
            <template v-if="avatarParticipants(conversation).length === 0">
              <i class="el-icon-chat-dot-round"></i>
            </template>
            <template v-else-if="avatarParticipants(conversation).length === 1">
              <img
                v-if="avatarParticipants(conversation)[0].avatar || avatarParticipants(conversation)[0].avatar_url"
                :src="avatarParticipants(conversation)[0].avatar || avatarParticipants(conversation)[0].avatar_url"
                class="avatar-img"
              />
              <span v-else class="avatar-letter-sm">
                {{ avatarParticipants(conversation)[0].name?.charAt(0) || '?' }}
              </span>
            </template>
            <template v-else>
              <div class="composite-avatar">
                <template v-for="(participant, index) in avatarParticipants(conversation).slice(0, 3)">
                  <div v-if="participant.avatar || participant.avatar_url" :key="index" class="composite-item">
                    <img :src="participant.avatar || participant.avatar_url" class="composite-img" />
                  </div>
                  <div v-else :key="index" class="composite-item" :style="{ background: participant.color || '#4080ff' }">
                    <span class="composite-text">{{ participant.name?.charAt(0) || '?' }}</span>
                  </div>
                </template>
                <div v-if="avatarParticipants(conversation).length > 3" class="composite-item composite-more">
                  <span class="composite-text">+{{ avatarParticipants(conversation).length - 3 }}</span>
                </div>
              </div>
            </template>
          </div>

          <div class="favorite-main">
            <div class="favorite-title-row">
              <h3>{{ conversation.title }}</h3>
              <el-tag size="mini" :type="conversation.type === 'group' ? 'warning' : 'info'">
                {{ conversation.type === 'group' ? '多 Agent' : '单 Agent' }}
              </el-tag>
              <i class="el-icon-star-on favorite-star"></i>
            </div>
            <p class="favorite-preview">
              {{ messagePreview(conversation) }}
            </p>
            <div class="favorite-meta">
              <span><i class="el-icon-user"></i>{{ participantNames(conversation) }}</span>
              <span><i class="el-icon-time"></i>{{ conversationTime(conversation) }}</span>
            </div>
          </div>

          <div class="favorite-actions">
            <el-button size="mini" type="primary" icon="el-icon-position" @click="openConversation(conversation)">
              进入对话
            </el-button>
            <el-button size="mini" icon="el-icon-star-off" @click="unfavorite(conversation)">
              取消收藏
            </el-button>
            <el-dropdown trigger="click" @command="handleMoreAction($event, conversation)">
              <el-button size="mini" icon="el-icon-more" />
              <el-dropdown-menu slot="dropdown">
                <el-dropdown-item command="copy-title">复制标题</el-dropdown-item>
                <el-dropdown-item command="copy-id">复制会话 ID</el-dropdown-item>
              </el-dropdown-menu>
            </el-dropdown>
          </div>
        </article>

        <div v-if="!loading && filteredFavorites.length === 0" class="favorites-empty">
          <i class="el-icon-star-off"></i>
          <h3>{{ favoriteConversations.length ? '没有匹配结果' : '暂无收藏会话' }}</h3>
          <p>{{ favoriteConversations.length ? '调整过滤条件后再试试。' : '在聊天详情右上角点击星标后，会话会出现在这里。' }}</p>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/Sidebar/index.vue'
import { formatTime } from '../utils/format'

export default {
  name: 'Favorites',
  components: { AppSidebar },
  data() {
    return {
      searchQuery: '',
      typeFilter: 'all',
      sortBy: 'updated_desc',
    }
  },
  computed: {
    activeDomain() { return this.$store.getters['workspace/activeDomain'] },
    loading() {
      return this.$store.state.conversation.loading
    },
    conversations() {
      return this.$store.state.conversation.conversations || []
    },
    favoriteConversations() {
      return this.conversations.filter(conversation => conversation.is_favorite)
    },
    filteredFavorites() {
      const query = this.searchQuery.toLowerCase()
      const filtered = this.favoriteConversations.filter(conversation => {
        const typeMatched = this.typeFilter === 'all' || conversation.type === this.typeFilter
        const text = [
          conversation.title,
          conversation.last_message?.content,
          this.participantNames(conversation),
        ].join(' ').toLowerCase()
        return typeMatched && (!query || text.includes(query))
      })

      return filtered.slice().sort((a, b) => {
        if (this.sortBy === 'title_asc') {
          return String(a.title || '').localeCompare(String(b.title || ''), 'zh-Hans-CN')
        }
        const aTime = new Date(a.updated_at || a.created_at || 0).getTime()
        const bTime = new Date(b.updated_at || b.created_at || 0).getTime()
        return this.sortBy === 'updated_asc' ? aTime - bTime : bTime - aTime
      })
    },
  },
  watch: {
    activeDomain(newDomain, oldDomain) {
      if (newDomain && newDomain !== oldDomain) {
        this.refresh()
      }
    },
  },
  created() {
    this.refresh()
  },
  methods: {
    refresh() {
      const wsId = this.$store.getters['workspace/activeWorkspaceId']
      return this.$store.dispatch('conversation/fetchConversations', wsId)
    },
    openConversation(conversation) {
      this.$router.push({
        path: '/dashboard',
        query: { conversation_id: conversation.id },
      })
    },
    async unfavorite(conversation) {
      try {
        const response = await this.$store.dispatch('conversation/toggleConversationFavorite', {
          conversationId: conversation.id,
          isFavorite: false,
        })
        if (response.code === 200) {
          this.$message.success('已取消收藏')
        } else {
          this.$message.error(response.message || '取消收藏失败')
        }
      } catch (e) {
        this.$message.error('取消收藏失败')
      }
    },
    handleMoreAction(command, conversation) {
      if (command === 'copy-title') {
        this.copyText(conversation.title || '')
      } else if (command === 'copy-id') {
        this.copyText(conversation.id || '')
      }
    },
    copyText(text) {
      if (!text) return
      navigator.clipboard?.writeText(text)
      this.$message.success('已复制')
    },
    avatarParticipants(conversation) {
      if (!conversation || !conversation.participants_info) return []
      if (conversation.type === 'single') {
        return conversation.participants_info.filter(item => item.participant_type !== 'user').slice(0, 1)
      }
      return conversation.participants_info
    },
    convAvatarBg(conversation) {
      const participants = this.avatarParticipants(conversation)
      if (participants.length === 0 || participants.length > 1) return {}
      return { background: participants[0].color || '#4080ff' }
    },
    displayParticipants(conversation) {
      const participants = conversation.participants_info || []
      const agents = participants.filter(item => item.participant_type === 'agent')
      return agents.length ? agents : participants
    },
    participantNames(conversation) {
      const names = this.displayParticipants(conversation)
        .map(item => item.name)
        .filter(Boolean)
      return names.length ? names.join('、') : '暂无参与者'
    },
    messagePreview(conversation) {
      return conversation.last_message?.content || '暂无消息'
    },
    conversationTime(conversation) {
      return formatTime(conversation.last_message?.created_at || conversation.updated_at || conversation.created_at)
    },
  },
}
</script>

<style scoped>
.favorites-page {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}

.favorites-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  overflow: hidden;
}

.favorites-header {
  min-height: 76px;
  padding: 18px 22px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.favorites-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1e293b;
}

.favorites-header p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #86909c;
}

.filter-bar {
  padding: 14px 22px;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 140px 150px auto;
  gap: 10px;
  align-items: center;
  border-bottom: 1px solid #f5f6f8;
  background: #fbfcff;
}

.result-count {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
}

.favorites-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px 24px;
}

.favorites-list::-webkit-scrollbar {
  width: 4px;
}

.favorites-list::-webkit-scrollbar-thumb {
  background: #d8e0ea;
  border-radius: 999px;
}

.favorite-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  background: #ffffff;
  transition: border-color 0.16s, box-shadow 0.16s;
}

.favorite-card + .favorite-card {
  margin-top: 10px;
}

.favorite-card:hover {
  border-color: #c7d7ff;
  box-shadow: 0 8px 20px rgba(64,128,255,0.08);
}

.favorite-conv-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #cad6ed, #b9c6e3);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
  overflow: hidden;
}

.favorite-conv-avatar .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-letter-sm {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
}

.composite-avatar {
  display: flex;
  flex-wrap: wrap;
  width: 100%;
  height: 100%;
  padding: 1px;
  gap: 1px;
  box-sizing: border-box;
  align-content: flex-start;
  justify-content: center;
}

.composite-item {
  flex: 0 0 calc(50% - 0.5px);
  aspect-ratio: 1;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.composite-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.composite-text {
  font-size: 9px;
  font-weight: 700;
  color: #fff;
  line-height: 1;
}

.composite-more {
  background: rgba(0,0,0,0.35);
}

.favorite-main {
  flex: 1;
  min-width: 0;
}

.favorite-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.favorite-title-row h3 {
  margin: 0;
  font-size: 15px;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.favorite-star {
  color: #e6a23c;
  flex-shrink: 0;
}

.favorite-preview {
  margin: 6px 0 0;
  font-size: 13px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.favorite-meta {
  margin-top: 8px;
  display: flex;
  gap: 14px;
  min-width: 0;
  font-size: 12px;
  color: #94a3b8;
}

.favorite-meta span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.favorite-meta i {
  margin-right: 4px;
}

.favorite-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.favorites-empty {
  height: 100%;
  min-height: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
}

.favorites-empty i {
  font-size: 42px;
  margin-bottom: 10px;
}

.favorites-empty h3 {
  margin: 0 0 6px;
  font-size: 17px;
  color: #475569;
}

.favorites-empty p {
  margin: 0;
  font-size: 13px;
}
</style>
