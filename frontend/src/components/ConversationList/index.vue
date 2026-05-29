<template>
  <div class="conversation-list">
    <div class="list-header">
      <h3>会话</h3>
      <el-button type="primary" size="mini" icon="el-icon-plus" @click="$emit('create-conversation')"
                 circle></el-button>
    </div>

    <div class="search-box">
      <el-input
        size="small"
        placeholder="搜索..."
        prefix-icon="el-icon-search"
        v-model="searchQuery"
      >
      </el-input>
    </div>

    <div class="list-items" v-loading="loading">
      <div
        v-for="conv in filteredConversations"
        :key="conv.id"
        class="conversation-item"
        :class="{ active: currentId === conv.id }"
        @click="$emit('select', conv)"
      >
        <div class="item-avatar" :style="convAvatarBg(conv)">
          <template v-if="avatarParticipants(conv).length === 0">
            <i class="el-icon-chat-dot-round"></i>
          </template>
          <template v-else-if="avatarParticipants(conv).length === 1">
            <img v-if="avatarParticipants(conv)[0].avatar" :src="avatarParticipants(conv)[0].avatar" class="avatar-img" />
            <span v-else class="avatar-letter-sm">{{ avatarParticipants(conv)[0].name?.charAt(0) || '?' }}</span>
          </template>
          <template v-else>
            <div class="composite-avatar">
              <template v-for="(p, i) in avatarParticipants(conv).slice(0, 3)">
                <div v-if="p.avatar || p.avatar_url" :key="i" class="composite-item">
                  <img :src="p.avatar || p.avatar_url" class="composite-img" />
                </div>
                <div v-else :key="i" class="composite-item" :style="{ background: p.color || '#4080ff' }">
                  <span class="composite-text">{{ p.name?.charAt(0) || '?' }}</span>
                </div>
              </template>
              <div v-if="avatarParticipants(conv).length > 3" class="composite-item composite-more">
                <span class="composite-text">+{{ avatarParticipants(conv).length - 3 }}</span>
              </div>
            </div>
          </template>
        </div>
        <div class="item-content">
          <div class="item-title">{{ conv.title }}</div>
          <div class="item-preview" v-if="conv.last_message">
            {{ conv.last_message.content }}
          </div>
          <div class="item-preview" v-else>
            <span class="no-messages">暂无消息</span>
          </div>
        </div>
        <div class="item-time" v-if="conv.last_message">
          {{ formatTime(conv.last_message.created_at) }}
        </div>
      </div>

      <div v-if="filteredConversations.length === 0" class="empty-list">
        <i class="el-icon-chat-dot-round"></i>
        <p>暂无会话</p>
      </div>
    </div>
  </div>
</template>

<script>
import { formatTime } from '../../utils/format'

export default {
  name: 'ConversationList',
  props: {
    conversations: Array,
    currentId: String,
    loading: Boolean,
    userAvatar: { type: String, default: '' },
  },
  data() {
    return {
      searchQuery: '',
    }
  },
  computed: {
    filteredConversations() {
      if (!this.searchQuery) return this.conversations || []
      const q = this.searchQuery.toLowerCase()
      let filtered = (this.conversations || []).filter(c =>
        c.title.toLowerCase().includes(q)
      )
      return filtered
    },
  },
  methods: {
    formatTime,

    // Get participants to show in the avatar area.
    // Uses participants_info from API (backend-resolved name/avatar/color).
    // Single conversations: show only the agent (not the user).
    // Group conversations: show user + all agents.
    avatarParticipants(conv) {
      if (!conv || !conv.participants_info) return []
      if (conv.type === 'single') {
        return conv.participants_info.filter(p => p.participant_type !== 'user').slice(0, 1)
      }
      return conv.participants_info
    },

    convAvatarBg(conv) {
      const infos = this.avatarParticipants(conv)
      if (infos.length === 0 || infos.length > 1) return {}
      return { background: infos[0].color || '#4080ff' }
    },
  },
}
</script>

<style scoped>
.conversation-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ffffff;
}

.list-header {
  padding: 16px 16px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.list-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
  color: #1e293b;
}

.list-header .el-button--primary {
  background: #4080ff;
  border: none;
  width: 32px;
  height: 32px;
  font-size: 14px;
}

.search-box {
  padding: 0 12px 8px;
}

.search-box :deep(.el-input__inner) {
  background: #f2f3f5;
  border: none;
  border-radius: 8px;
  height: 36px;
  font-size: 13px;
}

.search-box :deep(.el-input__inner:focus) {
  background: #f2f3f5;
}

.list-items {
  flex: 1;
  overflow-y: auto;
}

.list-items::-webkit-scrollbar {
  width: 4px;
}

.list-items::-webkit-scrollbar-thumb {
  background: #dcdde1;
  border-radius: 4px;
}

.conversation-item {
  display: flex;
  align-items: flex-start;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.conversation-item:hover {
  background: #f5f6f7;
}

.conversation-item.active {
  background: #f0f5ff;
}

.item-avatar {
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
.item-avatar .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-letter-sm {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
}

/* 复合头像 — 2x2 正方形网格 */
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

.item-content {
  flex: 1;
  margin: 0 12px;
  min-width: 0;
}

.item-title {
  font-size: 12px;
  font-weight: 500;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-preview {
  font-size: 11px;
  color: #86909c;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.no-messages {
  font-style: italic;
  color: #c0c4cc;
}

.item-time {
  font-size: 11px;
  color: #c0c4cc;
  white-space: nowrap;
  flex-shrink: 0;
}

.empty-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 40px 16px;
  color: #86909c;
}

.empty-list i {
  font-size: 48px;
  color: #dcdde1;
  margin-bottom: 12px;
}
</style>
