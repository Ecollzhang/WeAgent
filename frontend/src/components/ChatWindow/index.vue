<template>
  <div class="chat-window">
    <div class="chat-header" v-if="conversation">
      <div class="header-left">
        <h3>{{ conversation.title }}</h3>
        <span class="participant-count">
          {{ participantCount }} 个参与者
        </span>
      </div>
      <div class="header-actions">
        <el-button size="mini" icon="el-icon-search" type="text" @click="toggleSearchPanel" title="搜索"></el-button>
        <el-button size="mini" icon="el-icon-folder-opened" type="text" @click="$emit('open-workspace', 'workspace')" title="工作目录"></el-button>
        <el-button size="mini" icon="el-icon-monitor" type="text" @click="$emit('open-services')" title="预览服务"></el-button>
        <el-button size="mini" icon="el-icon-upload2" type="text" @click="$emit('open-attachments')" title="上传文件"></el-button>
        <el-button
          size="mini"
          :icon="favoriteActive ? 'el-icon-star-on' : 'el-icon-star-off'"
          type="text"
          :class="{ 'favorite-active': favoriteActive }"
          @click="$emit('toggle-star')"
          title="收藏"
        ></el-button>
        <el-button size="mini" icon="el-icon-time" type="text" @click="toggleHistoryPanel" title="历史"></el-button>
        <el-dropdown trigger="click" @command="handleMoreCommand">
          <el-button size="mini" icon="el-icon-more" type="text" title="更多"></el-button>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item command="migrate" v-if="conversation.owner_id === userId">
              <i class="el-icon-copy-document"></i> 迁移文件
            </el-dropdown-item>
            <el-dropdown-item command="delete" v-if="conversation.owner_id === userId">
              <i class="el-icon-delete"></i> 删除会话
            </el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
      </div>
    </div>

    <div class="chat-header" v-else>
      <div class="header-left">
        <h3 class="text-primary">WeAgent</h3>
        <span class="participant-count">请选择或创建一个会话</span>
      </div>
      <div class="header-actions">
        <el-button size="mini" icon="el-icon-search" type="text" title="搜索"></el-button>
        <el-button size="mini" icon="el-icon-paperclip" type="text" title="附件"></el-button>
        <el-button size="mini" icon="el-icon-star-off" type="text" title="收藏"></el-button>
        <el-button size="mini" icon="el-icon-time" type="text" title="历史"></el-button>
        <el-button size="mini" icon="el-icon-more" type="text" title="更多"></el-button>
      </div>
    </div>

    <div class="detail-panel" v-if="panelVisible">
      <div class="detail-panel__head">
        <div class="detail-panel__title">
          <i :class="panelMode === 'search' ? 'el-icon-search' : 'el-icon-time'"></i>
          <span>{{ panelMode === 'search' ? '搜索消息' : '对话历史' }}</span>
        </div>
        <el-button type="text" icon="el-icon-close" class="panel-close" @click="closePanel"></el-button>
      </div>
      <div class="detail-panel__body" v-if="panelMode === 'search'">
        <el-input
          ref="panelInput"
          v-model="searchQuery"
          size="small"
          clearable
          placeholder="输入关键词搜索消息"
          @input="handleSearchInput"
          @keydown.enter.native.prevent="jumpToFirstSearchResult"
        />
        <div class="panel-meta">
          {{ searchResults.length }} 条结果
        </div>
        <div class="panel-list" v-if="searchResults.length">
          <button
            v-for="item in searchResults"
            :key="item.message.id"
            type="button"
            class="panel-item"
            @click="jumpToMessage(item.message.id)"
          >
            <div class="panel-item__title">{{ item.title }}</div>
            <div class="panel-item__snippet">{{ item.snippet }}</div>
          </button>
        </div>
        <div v-else class="panel-empty">没有匹配的消息</div>
      </div>
      <div class="detail-panel__body" v-else>
        <div class="panel-list" v-if="historyItems.length">
          <button
            v-for="item in historyItems"
            :key="item.message.id"
            type="button"
            class="panel-item"
            @click="jumpToMessage(item.message.id)"
          >
            <div class="panel-item__title">{{ item.title }}</div>
            <div class="panel-item__snippet">{{ item.snippet }}</div>
          </button>
        </div>
        <div v-else class="panel-empty">暂无用户问题</div>
      </div>
    </div>

    <div class="messages-container" ref="messagesContainer">
      <template v-if="messages && messages.length > 0">
        <div
          v-for="msg in messages"
          :key="msg.id"
          :ref="'message-' + msg.id"
          class="message-wrapper"
          :class="{ highlighted: highlightedMessageId === msg.id }"
        >
          <MessageBubble
            :message="msg"
            :isOwn="msg.sender_type === 'user' && msg.sender_id === userId"
            :sessionId="sessionId"
            @pin="$emit('pin-message', msg.id)"
            @stop-agent="$emit('stop-agent', msg)"
            @open-file="$emit('open-file', $event)"
          />
        </div>
      </template>

      <div v-else-if="conversation" class="empty-messages">
        <i class="el-icon-chat-dot-round"></i>
        <p>发送一条消息开始对话！</p>
      </div>

      <!-- Agent typing indicator -->
      <div v-if="agentResponding" class="typing-indicator">
        <div class="typing-dots">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
        <span class="typing-text">智能体正在响应...</span>
      </div>

      <div v-else-if="!conversation" class="empty-messages">
        <i class="el-icon-s-promotion"></i>
        <h2>欢迎使用 WeAgent</h2>
        <p>多智能体协作平台</p>
        <p class="hint">创建或选择会话开始聊天</p>
      </div>
    </div>

    <!-- 底部标签切换栏 -->
    <div class="chat-tabs" v-if="conversation">
      <span
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
        @click="handleTabSwitch(tab.key)"
      >{{ tab.label }}</span>
    </div>

    <div class="message-input" v-if="conversation">
      <div class="input-wrapper">
        <el-input
          type="text"
          placeholder="输入消息..."
          v-model="inputText"
          @input="handleInputChange"
          @keydown.native="handleInputKeydown"
          class="feishu-input"
        >
        </el-input>
        <div v-if="mentionVisible && mentionCandidates.length" class="mention-menu">
          <button
            v-for="(agent, index) in mentionCandidates"
            :key="agent.agent_id"
            class="mention-item"
            :class="{ active: index === mentionIndex }"
            @mousedown.prevent="selectMention(agent)"
          >
            <span class="mention-avatar" :style="{ background: agent.color || '#4080ff' }">
              <img v-if="agent.avatar" :src="agent.avatar" />
              <span v-else>{{ mentionName(agent).charAt(0) }}</span>
            </span>
            <span class="mention-name">{{ mentionName(agent) }}</span>
          </button>
        </div>
        <el-button type="text" class="send-btn" @click="handleSend" :disabled="!inputText.trim()">
          <i class="el-icon-promotion"></i>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script>
import MessageBubble from '../MessageBubble/index.vue'

export default {
  name: 'ChatWindow',
  components: { MessageBubble },
  props: {
    conversation: Object,
    messages: Array,
    userId: String,
    agentResponding: { type: Boolean, default: false },
    sessionAgents: { type: Array, default: () => [] },
  },
  data() {
    return {
      inputText: '',
      mentionVisible: false,
      mentionQuery: '',
      mentionIndex: 0,
      selectedMentions: [],
      activeTab: 'chat',
      stickToBottom: true,
      panelVisible: false,
      panelMode: 'search',
      searchQuery: '',
      highlightedMessageId: '',
      tabs: [
        { key: 'chat', label: '对话' },
        { key: 'agent_config', label: '智能体配置' },
        { key: 'tool_calls', label: '工具调用' },
        { key: 'logs', label: '日志' },
      ],
    }
  },
  computed: {
    favoriteActive() {
      return !!this.conversation?.is_favorite
    },
    participantCount() {
      if (!this.conversation || !this.conversation.participant_ids) return 0
      return this.conversation.participant_ids.length
    },
    sessionId() {
      return this.conversation?.sandbox_session_id || this.conversation?.id || ''
    },
    mentionCandidates() {
      const query = String(this.mentionQuery || '').toLowerCase()
      const agents = (this.sessionAgents || []).filter(agent => agent?.agent_id)
      const filtered = query
        ? agents.filter(agent => {
          const name = this.mentionName(agent).toLowerCase()
          const id = String(agent.agent_id || '').toLowerCase()
          return name.includes(query) || id.includes(query)
        })
        : agents
      return filtered.slice(0, 8)
    },
    searchResults() {
      const query = this.searchQuery.trim().toLowerCase()
      if (!query) return []
      return (this.messages || [])
        .map(message => {
          const text = this.collectMessageText(message)
          return { message, text }
        })
        .filter(item => item.text.toLowerCase().includes(query))
        .map(item => ({
          message: item.message,
          title: this.buildMessageTitle(item.message),
          snippet: this.buildSearchSnippet(item.text, query),
        }))
        .slice(0, 50)
    },
    historyItems() {
      return (this.messages || [])
        .filter(message => message.sender_type === 'user')
        .map(message => ({
          message,
          title: this.buildMessageTitle(message),
          snippet: this.buildSearchSnippet(this.collectMessageText(message), ''),
        }))
    },
  },
  watch: {
    messages() {
      const shouldScroll = this.isNearBottom()
      this.$nextTick(() => this.scrollToBottom(shouldScroll))
    },
    conversation() {
      this.closePanel()
      this.$nextTick(() => this.scrollToBottom(true))
    },
  },
  mounted() {
    const container = this.$refs.messagesContainer
    if (container) {
      container.addEventListener('scroll', this.handleMessagesScroll, { passive: true })
      this.stickToBottom = this.isNearBottom()
    }
  },
  beforeDestroy() {
    const container = this.$refs.messagesContainer
    if (container) {
      container.removeEventListener('scroll', this.handleMessagesScroll)
    }
  },
  methods: {
    handleSend() {
      if (!this.inputText.trim()) return
      const payload = this.buildMessagePayload()
      this.$emit('send-message', payload)
      this.inputText = ''
      this.mentionVisible = false
      this.mentionQuery = ''
      this.mentionIndex = 0
      this.selectedMentions = []
      this.$nextTick(() => this.scrollToBottom(true))
    },
    handleInputChange() {
      this.syncMentionState()
      this.syncSelectedMentions()
    },
    handleInputKeydown(event) {
      if (this.mentionVisible && this.mentionCandidates.length) {
        if (event.key === 'ArrowDown') {
          event.preventDefault()
          this.mentionIndex = (this.mentionIndex + 1) % this.mentionCandidates.length
          return
        }
        if (event.key === 'ArrowUp') {
          event.preventDefault()
          this.mentionIndex = (this.mentionIndex - 1 + this.mentionCandidates.length) % this.mentionCandidates.length
          return
        }
        if (event.key === 'Enter' || event.key === 'Tab') {
          event.preventDefault()
          this.selectMention(this.mentionCandidates[this.mentionIndex])
          return
        }
        if (event.key === 'Escape') {
          this.mentionVisible = false
          return
        }
      }
      if (event.key === 'Enter') {
        event.preventDefault()
        this.handleSend()
      }
    },
    syncMentionState() {
      const match = /@([^\s@，,：:；;]*)$/.exec(this.inputText)
      if (!match) {
        this.mentionVisible = false
        this.mentionQuery = ''
        this.mentionIndex = 0
        return
      }
      this.mentionQuery = match[1] || ''
      this.mentionVisible = true
      if (this.mentionIndex >= this.mentionCandidates.length) this.mentionIndex = 0
    },
    selectMention(agent) {
      if (!agent) return
      const name = this.mentionName(agent)
      this.inputText = this.inputText.replace(/@([^\s@，,：:；;]*)$/, `@${name} `)
      if (!this.selectedMentions.some(item => item.agent_id === agent.agent_id)) {
        this.selectedMentions.push({
          agent_id: agent.agent_id,
          name,
        })
      }
      this.mentionVisible = false
      this.mentionQuery = ''
      this.mentionIndex = 0
    },
    syncSelectedMentions() {
      this.selectedMentions = this.selectedMentions.filter(item => {
        return this.inputText.includes(`@${item.name}`)
      })
    },
    buildMessagePayload() {
      this.syncSelectedMentions()
      const targetIds = this.selectedMentions.map(item => item.agent_id)
      return {
        content: this.inputText.trim(),
        target_agent_ids: targetIds,
        mentions: this.selectedMentions.slice(),
      }
    },
    mentionName(agent) {
      return agent?.role || agent?.name || agent?.agent_id || ''
    },
    handleMessagesScroll() {
      this.stickToBottom = this.isNearBottom()
    },
    toggleSearchPanel() {
      if (this.panelVisible && this.panelMode === 'search') {
        this.closePanel()
        return
      }
      this.panelMode = 'search'
      this.panelVisible = true
      this.$nextTick(() => {
        const input = this.$refs.panelInput
        if (input && input.focus) input.focus()
      })
    },
    toggleHistoryPanel() {
      if (this.panelVisible && this.panelMode === 'history') {
        this.closePanel()
        return
      }
      this.panelMode = 'history'
      this.panelVisible = true
    },
    closePanel() {
      this.panelVisible = false
      this.searchQuery = ''
    },
    handleSearchInput() {
      if (this.searchResults.length) {
        this.highlightedMessageId = this.searchResults[0].message.id
      }
    },
    jumpToFirstSearchResult() {
      if (this.searchResults.length) {
        this.jumpToMessage(this.searchResults[0].message.id)
      }
    },
    jumpToMessage(messageId) {
      const ref = this.$refs[`message-${messageId}`]
      const target = Array.isArray(ref) ? ref[0] : ref
      if (target && target.scrollIntoView) {
        this.highlightedMessageId = messageId
        this.panelVisible = false
        this.$nextTick(() => {
          target.scrollIntoView({ behavior: 'smooth', block: 'center' })
          setTimeout(() => {
            if (this.highlightedMessageId === messageId) {
              this.highlightedMessageId = ''
            }
          }, 2500)
        })
      }
    },
    buildMessageTitle(message) {
      const raw = String(message?.content || message?.raw_output || '').trim()
      if (!raw) {
        return message?.sender_name || '消息'
      }
      const firstLine = raw.split(/\r?\n/).find(line => line.trim()) || raw
      return firstLine
        .replace(/^#{1,6}\s*/, '')
        .replace(/^[-*+]\s*/, '')
        .replace(/^>\s*/, '')
        .trim()
    },
    buildSearchSnippet(text, query) {
      const plain = String(text || '').replace(/\s+/g, ' ').trim()
      if (!plain) return '无可预览内容'
      if (!query) return plain.slice(0, 96)
      const index = plain.toLowerCase().indexOf(query)
      if (index === -1) return plain.slice(0, 96)
      const start = Math.max(0, index - 22)
      const end = Math.min(plain.length, index + query.length + 42)
      return `${start > 0 ? '...' : ''}${plain.slice(start, end)}${end < plain.length ? '...' : ''}`
    },
    collectMessageText(message) {
      const parts = []
      const push = value => {
        if (value === undefined || value === null) return
        const text = typeof value === 'string' ? value : JSON.stringify(value)
        if (text) parts.push(text)
      }
      push(message?.content)
      push(message?.raw_output)
      const elements = Array.isArray(message?.elements) ? message.elements : []
      elements.forEach(element => {
        if (!element) return
        push(element.title)
        push(element.content)
        push(element.text)
        push(element.name)
        push(element.path)
        push(element.url)
        push(element.message)
        push(element.data)
        push(element.detail)
      })
      return parts.join(' ')
    },
    isNearBottom() {
      const container = this.$refs.messagesContainer
      if (!container) return true
      const distance = container.scrollHeight - container.scrollTop - container.clientHeight
      return distance <= 80
    },
    scrollToBottom(force = false) {
      const container = this.$refs.messagesContainer
      if (container && (force || this.stickToBottom)) {
        container.scrollTop = container.scrollHeight
      }
    },
    handleMoreCommand(command) {
      if (command === 'migrate') {
        this.$emit('open-migration')
      } else if (command === 'delete') {
        this.$emit('delete-conversation')
      }
    },
    handleTabSwitch(key) {
      this.activeTab = key
      if (key === 'logs') {
        this.$emit('open-workspace', 'workspace')
      } else if (key !== 'chat') {
        this.$message.info(key === 'agent_config' ? '智能体配置功能即将上线' :
                          key === 'tool_calls' ? '工具调用记录功能即将上线' :
                          '日志功能即将上线')
      }
    },
  },
}
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

.chat-header {
  height: 60px;
  padding: 0 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  background: #ffffff;
}

.header-left h3 {
  margin: 0;
  font-size: 16px;
  color: #1e293b;
}

.header-left .text-primary {
  color: #4080ff;
}

.participant-count {
  font-size: 12px;
  color: #94a3b8;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #86909c;
}

.header-actions .el-button--text {
  font-size: 16px;
  color: #86909c;
  padding: 6px;
}

.header-actions .el-button--text:hover {
  color: #4080ff;
}

.header-actions .favorite-active {
  color: #e6a23c;
}

.detail-panel {
  position: absolute;
  top: 60px;
  right: 20px;
  width: 340px;
  max-height: calc(100% - 80px);
  background: #ffffff;
  border: 1px solid #e8edf5;
  border-radius: 10px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.14);
  z-index: 20;
  overflow: hidden;
}

.detail-panel__head {
  height: 48px;
  padding: 0 12px 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #eef2f7;
  background: #fbfdff;
}

.detail-panel__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}

.panel-close {
  padding: 4px;
}

.detail-panel__body {
  padding: 12px;
}

.panel-meta {
  margin: 10px 0 8px;
  font-size: 12px;
  color: #94a3b8;
}

.panel-list {
  max-height: 52vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.panel-list::-webkit-scrollbar,
.messages-container::-webkit-scrollbar {
  width: 4px;
}

.panel-list::-webkit-scrollbar-thumb,
.messages-container::-webkit-scrollbar-thumb {
  background: #d8e0ea;
  border-radius: 999px;
}

.panel-item {
  width: 100%;
  padding: 10px 12px;
  text-align: left;
  border: 1px solid #e8edf5;
  border-radius: 8px;
  background: #ffffff;
  appearance: none;
  font: inherit;
  color: inherit;
  cursor: pointer;
}

.panel-item:hover {
  border-color: #bfd3ff;
  background: #f8fbff;
}

.panel-item__title {
  font-size: 13px;
  line-height: 1.4;
  color: #1f2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.panel-item__snippet {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.45;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.panel-empty {
  padding: 24px 0 8px;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  background: #fafafa;
}

.messages-container::-webkit-scrollbar {
  width: 4px;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #dcdde1;
  border-radius: 4px;
}

.message-wrapper {
  margin-bottom: 12px;
}

.message-wrapper.highlighted {
  border-radius: 10px;
  box-shadow: 0 0 0 2px rgba(64, 128, 255, 0.14);
}

.empty-messages {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
}

.empty-messages i {
  font-size: 64px;
  margin-bottom: 16px;
  color: #cbd5e1;
}

.empty-messages h2 {
  font-size: 22px;
  color: #1e293b;
  margin-bottom: 8px;
}

.empty-messages .hint {
  font-size: 13px;
  margin-top: 8px;
}

/* 底部标签栏 */
.chat-tabs {
  height: 42px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 8px;
  background: rgba(250,250,250,0.8);
  flex-shrink: 0;
}

.tab-item {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-item:hover {
  background: #f0f0f0;
}

.tab-item.active {
  background: #4080ff;
  color: #fff;
}

/* 飞书风格输入框 */
.message-input {
  height: 68px;
  padding: 10px 16px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
  background: #ffffff;
}

.input-wrapper {
  display: flex;
  align-items: center;
  background: #f2f3f5;
  border-radius: 8px;
  padding: 0 12px;
  height: 44px;
  position: relative;
}

.input-wrapper .feishu-input :deep(.el-input__inner) {
  border: none;
  background: transparent;
  font-size: 14px;
  height: 44px;
  padding: 0;
}

.input-wrapper .feishu-input :deep(.el-input__inner:focus) {
  box-shadow: none;
}

.input-wrapper .feishu-input {
  flex: 1;
}

.send-btn {
  font-size: 18px;
  color: #4080ff;
  padding: 8px;
}

.send-btn:disabled {
  color: #c0c4cc;
}

.mention-menu {
  position: absolute;
  left: 8px;
  bottom: 50px;
  width: 240px;
  max-height: 260px;
  overflow-y: auto;
  padding: 6px;
  border: 1px solid #e8eaed;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  z-index: 10;
}

.mention-item {
  width: 100%;
  height: 38px;
  border: none;
  background: transparent;
  border-radius: 6px;
  padding: 0 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  text-align: left;
}

.mention-item:hover,
.mention-item.active {
  background: #f0f5ff;
}

.mention-avatar {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  overflow: hidden;
}

.mention-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.mention-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: #1e293b;
}

/* Typing indicator */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}

.typing-dots {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dot {
  width: 8px;
  height: 8px;
  background: #c0d3f0;
  border-radius: 50%;
  animation: typingBounce 1.4s ease-in-out infinite;
}

.dot:nth-child(1) { animation-delay: 0s; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-6px); opacity: 1; }
}

.typing-text {
  font-size: 12px;
  color: #94a3b8;
}
</style>
