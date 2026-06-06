<template>
  <main class="dashboard-shell">
    <aside class="app-sidebar">
      <div class="sidebar-logo">W</div>
      <nav class="sidebar-nav">
        <button class="sidebar-btn active" title="会话"><i class="el-icon-chat-dot-round"></i></button>
        <button class="sidebar-btn" title="智能体" @click="$router.push('/agents')"><i class="el-icon-user"></i></button>
        <button class="sidebar-btn" title="工具" disabled><i class="el-icon-s-tools"></i></button>
        <button class="sidebar-btn" title="我的收藏" @click="$router.push('/favorites')"><i class="el-icon-collection-tag"></i></button>
        <button class="sidebar-btn" title="设置" @click="$router.push('/settings')"><i class="el-icon-setting"></i></button>
      </nav>
      <button class="sidebar-user" title="退出登录" @click="logout"><i class="el-icon-switch-button"></i></button>
    </aside>

    <section class="conversation-panel">
      <div class="list-header">
        <h3>会话</h3>
        <button class="create-circle" :disabled="creating" @click="openCreateDialog">+</button>
      </div>

      <div class="search-box">
        <i class="el-icon-search"></i>
        <input v-model.trim="searchQuery" placeholder="搜索..." />
      </div>

      <div class="list-items">
        <div v-if="convLoading" class="list-state">
          <i class="el-icon-loading"></i>
          <span>正在加载会话...</span>
        </div>
        <div
          v-for="conv in filteredConversations"
          v-else
          :key="conv.id"
          class="conversation-item"
          :class="{ active: currentId === conv.id }"
          role="button"
          tabindex="0"
          @click="selectConversation(conv)"
          @keydown.enter.prevent="selectConversation(conv)"
        >
          <div class="item-avatar" :style="convAvatarBg(conv)">
            <template v-if="avatarParticipants(conv).length === 0">
              <i class="el-icon-chat-dot-round"></i>
            </template>
            <template v-else-if="avatarParticipants(conv).length === 1">
              <img
                v-if="participantAvatar(avatarParticipants(conv)[0])"
                :src="participantAvatar(avatarParticipants(conv)[0])"
                class="avatar-img"
              />
              <span v-else class="avatar-letter-sm">{{ firstLetter(avatarParticipants(conv)[0].name) }}</span>
            </template>
            <template v-else>
              <div class="composite-avatar">
                <div
                  v-for="(p, i) in avatarParticipants(conv).slice(0, 3)"
                  :key="i"
                  class="composite-item"
                  :style="participantAvatar(p) ? {} : { background: participantColor(p) }"
                >
                  <img v-if="participantAvatar(p)" :src="participantAvatar(p)" class="composite-img" />
                  <span v-else class="composite-text">{{ firstLetter(p.name) }}</span>
                </div>
                <div v-if="avatarParticipants(conv).length > 3" class="composite-item composite-more">
                  <span class="composite-text">+{{ avatarParticipants(conv).length - 3 }}</span>
                </div>
              </div>
            </template>
          </div>
          <div class="item-content">
            <div class="item-title-row">
              <div class="item-title">{{ conv.title || '未命名会话' }}</div>
              <i v-if="conv.is_favorite" class="el-icon-star-on item-favorite"></i>
            </div>
            <div class="item-preview">
              <span v-if="conv.last_message">{{ conv.last_message.content }}</span>
              <span v-else class="no-messages">暂无消息</span>
            </div>
          </div>
          <div class="item-time">{{ formatTime((conv.last_message && conv.last_message.created_at) || conv.updated_at || conv.created_at) }}</div>
        </div>
        <div v-if="!convLoading && filteredConversations.length === 0" class="list-state">
          <i class="el-icon-chat-dot-round"></i>
          <span>{{ searchQuery ? '没有匹配的会话' : '暂无会话' }}</span>
        </div>
      </div>
    </section>

    <section class="chat-panel">
      <header class="chat-header">
        <div>
          <h3>{{ currentConversation ? currentConversation.title : 'WeAgent' }}</h3>
          <span>{{ currentConversation ? participantCount(currentConversation) + ' 个参与者' : '请选择或创建一个会话' }}</span>
        </div>
        <div class="header-actions">
          <button :disabled="!currentConversation" title="搜索消息" @click="toggleSearchPanel"><i class="el-icon-search"></i></button>
          <button :disabled="!currentConversation" title="工作目录" @click="handleOpenWorkspace()"><i class="el-icon-folder-opened"></i></button>
          <button disabled><i class="el-icon-monitor"></i></button>
          <button :disabled="!currentConversation" title="上传文件" @click="handleOpenAttachments()"><i class="el-icon-upload2"></i></button>
          <button
            :disabled="!currentConversation"
            :class="{ 'favorite-active': currentConversation && currentConversation.is_favorite }"
            title="收藏"
            @click="toggleFavorite"
          >
            <i :class="currentConversation && currentConversation.is_favorite ? 'el-icon-star-on' : 'el-icon-star-off'"></i>
          </button>
          <button :disabled="!currentConversation" title="历史" @click="toggleHistoryPanel"><i class="el-icon-time"></i></button>
          <div class="more-menu-wrap">
            <button :disabled="!currentConversation" @click="showMoreMenu = !showMoreMenu"><i class="el-icon-more"></i></button>
            <div v-if="showMoreMenu && currentConversation" class="more-menu">
              <button type="button" @click="handleDeleteConversation(currentConversation)">
                <i class="el-icon-delete"></i>
                <span>删除会话</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <div v-if="detailPanelVisible" class="desktop-detail-panel">
        <div class="desktop-detail-head">
          <div>
            <i :class="detailPanelMode === 'search' ? 'el-icon-search' : 'el-icon-time'"></i>
            <span>{{ detailPanelMode === 'search' ? '搜索消息' : '对话历史' }}</span>
          </div>
          <button type="button" @click="closeDetailPanel"><i class="el-icon-close"></i></button>
        </div>
        <div v-if="detailPanelMode === 'search'" class="desktop-detail-body">
          <div class="desktop-panel-search">
            <i class="el-icon-search"></i>
            <input
              ref="messageSearchInput"
              v-model.trim="messageSearchQuery"
              placeholder="输入关键词搜索消息"
              @keydown.enter.prevent="jumpToFirstSearchResult"
            />
          </div>
          <div class="desktop-panel-meta">{{ messageSearchResults.length }} 条结果</div>
          <div v-if="messageSearchResults.length" class="desktop-panel-list">
            <button
              v-for="item in messageSearchResults"
              :key="item.message.id"
              type="button"
              class="desktop-panel-item"
              @click="jumpToMessage(item.message.id)"
            >
              <strong>{{ item.title }}</strong>
              <span>{{ item.snippet }}</span>
            </button>
          </div>
          <div v-else class="desktop-panel-empty">没有匹配的消息</div>
        </div>
        <div v-else class="desktop-detail-body">
          <div v-if="historyItems.length" class="desktop-panel-list">
            <button
              v-for="item in historyItems"
              :key="item.message.id"
              type="button"
              class="desktop-panel-item"
              @click="jumpToMessage(item.message.id)"
            >
              <strong>{{ item.title }}</strong>
              <span>{{ item.snippet }}</span>
            </button>
          </div>
          <div v-else class="desktop-panel-empty">暂无用户问题</div>
        </div>
      </div>

      <div ref="messagesContainer" class="messages-container live-messages">
        <div v-if="messagesLoading" class="empty-messages">
          <i class="el-icon-loading"></i>
          <h2>正在加载消息</h2>
          <p>稍等一下，桌面端正在读取当前会话。</p>
        </div>

        <div v-else-if="!currentConversation" class="empty-messages">
          <i class="el-icon-s-promotion"></i>
          <h2>欢迎使用 WeAgent</h2>
          <p>创建或选择会话后，就可以在桌面端发送消息。</p>
        </div>

        <div v-else-if="currentMessages.length === 0" class="empty-messages">
          <i class="el-icon-chat-line-round"></i>
          <h2>发送第一条消息</h2>
          <p>会话已关联 Agent，消息会按 Web 端同样的逻辑分发。</p>
        </div>

        <div v-else class="message-list">
          <div
            v-for="message in currentMessages"
            :key="message.id"
            :ref="'message-' + message.id"
            class="message-row desktop-message-row"
            :class="{ own: isOwnMessage(message), highlighted: highlightedMessageId === message.id }"
          >
            <div class="message-avatar" :style="messageAvatarStyle(message)">
              <img v-if="messageAvatar(message)" :src="messageAvatar(message)" class="message-avatar-img" />
              <span v-else>{{ firstLetter(senderName(message)) }}</span>
            </div>
            <MessageBubble
              class="desktop-message-bubble"
              :message="message"
              :is-own="isOwnMessage(message)"
              :server-url="serverUrl"
              @open-file="handleOpenMessageFile"
            />
          </div>
        </div>
      </div>

      <div v-if="currentConversation" class="chat-tabs">
        <span
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-item"
          :class="{ active: activeTab === tab.key }"
          @click="handleTabSwitch(tab.key)"
        >{{ tab.label }}</span>
      </div>

      <form class="message-input" @submit.prevent="handleSendMessage">
        <div class="input-wrapper">
          <input
            v-model="draft"
            :disabled="!currentConversation || sending"
            :placeholder="currentConversation ? '输入消息...' : '请先选择或创建会话'"
            @input="handleInputChange"
            @keydown="handleInputKeydown"
          />
          <div v-if="mentionVisible && mentionCandidates.length" class="mention-menu">
            <button
              v-for="(agent, index) in mentionCandidates"
              :key="agent.agent_id"
              type="button"
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
          <button :disabled="!currentConversation || sending || !draft.trim()" type="submit">
            <i :class="sending ? 'el-icon-loading' : 'el-icon-s-promotion'"></i>
          </button>
        </div>
      </form>

      <div v-if="error" class="desktop-toast">
        {{ error }}
      </div>
    </section>

    <div v-if="attachmentsVisible" class="desktop-modal-backdrop drawer-backdrop" @click.self="attachmentsVisible = false">
      <section class="desktop-drawer attachments-drawer">
        <header class="desktop-modal-header">
          <div>
            <h2>上传文件</h2>
            <p>文件会上传到 Agent 容器的 userInput 目录。</p>
          </div>
          <button class="icon-close" @click="attachmentsVisible = false"><i class="el-icon-close"></i></button>
        </header>
        <div class="attachment-body">
          <label v-if="currentSessionAgents.length > 1" class="dialog-field inline-field">
            <span>目标 Agent</span>
            <select v-model="attachmentAgentId" @change="loadAttachments">
              <option v-for="agent in currentSessionAgents" :key="agent.agent_id" :value="agent.agent_id">
                {{ mentionName(agent) }}
              </option>
            </select>
          </label>
          <label class="upload-drop">
            <i class="el-icon-upload"></i>
            <span>{{ selectedUploadFile ? selectedUploadFile.name : '点击选择文件' }}</span>
            <small>支持图片、PDF、代码、文本等文件</small>
            <input ref="attachmentInput" type="file" @change="handleAttachmentFileChange" />
          </label>
          <div class="desktop-modal-actions">
            <button class="workspace-secondary" @click="loadAttachments">刷新</button>
            <button class="workspace-primary" :disabled="attachmentsLoading || !selectedUploadFile" @click="handleAttachmentUpload">
              {{ attachmentsLoading ? '上传中...' : '上传到容器' }}
            </button>
          </div>
          <div class="attachment-list">
            <div v-if="attachmentsLoading" class="mini-state"><i class="el-icon-loading"></i> 正在加载...</div>
            <div v-else-if="attachments.length === 0" class="mini-state">暂无上传文件</div>
            <div v-for="file in attachments" v-else :key="file.path" class="attachment-item">
              <i class="el-icon-document"></i>
              <div>
                <strong>{{ file.name || file.path }}</strong>
                <span>{{ file.path }}</span>
              </div>
              <button type="button" @click="previewAttachment(file)">查看</button>
              <button type="button" class="text-danger" @click="handleDeleteAttachment(file)">删除</button>
            </div>
          </div>
        </div>
      </section>
    </div>


    <div v-if="showCreate" class="desktop-modal-backdrop" @click.self="cancelCreate">
      <section class="desktop-modal create-agent-dialog">
        <header class="desktop-modal-header">
          <div>
            <h2>新建会话</h2>
            <p>选择一个或多个 Agent，桌面端会按 Web 端相同规则创建单聊或群聊。</p>
          </div>
          <button class="icon-close" @click="cancelCreate"><i class="el-icon-close"></i></button>
        </header>

        <label class="dialog-field">
          <span>会话标题</span>
          <input v-model.trim="newConversation.title" placeholder="选择 Agent 后自动生成" />
        </label>

        <div class="agent-picker">
          <div class="agent-picker-header">
            <span>选择 Agent</span>
            <small>已选择 {{ newConversation.selectedAgents.length }} 个</small>
          </div>
          <div v-if="agentsLoading" class="picker-state">
            <i class="el-icon-loading"></i>
            <span>正在加载 Agent...</span>
          </div>
          <label
            v-for="agent in agents"
            v-else
            :key="agent.id"
            class="agent-pick-item"
            :class="{ selected: newConversation.selectedAgents.includes(agent.id) }"
          >
            <input type="checkbox" :value="agent.id" v-model="newConversation.selectedAgents" />
            <span class="agent-pick-avatar" :style="agentAvatarStyle(agent)">
              <img v-if="agentAvatar(agent)" :src="agentAvatar(agent)" />
              <span v-else>{{ firstLetter(agent.name) }}</span>
            </span>
            <span class="agent-pick-main">
              <strong>{{ agent.name }}</strong>
              <small>{{ agent.adapter_name || agent.agent_type || 'custom' }}</small>
            </span>
            <i class="el-icon-check"></i>
          </label>
          <div v-if="!agentsLoading && agents.length === 0" class="picker-state">
            <i class="el-icon-user"></i>
            <span>暂无 Agent，请先到“我的 Agent”创建。</span>
          </div>
        </div>

        <footer class="desktop-modal-actions">
          <button class="workspace-secondary" @click="cancelCreate">取消</button>
          <button class="workspace-primary" :disabled="creating || newConversation.selectedAgents.length === 0" @click="handleCreateConversation">
            {{ creating ? '创建中...' : '创建' }}
          </button>
        </footer>
      </section>
    </div>

    <ArtifactWorkbench
      :visible.sync="artifactWorkbenchVisible"
      :session-id="currentSessionId"
      :initial-root="artifactWorkbenchRoot"
      :initial-path="artifactWorkbenchPath"
      :initial-agent-id="artifactWorkbenchAgentId"
      :initial-artifact="artifactWorkbenchArtifact"
    />
  </main>
</template>

<script>
import {
  createConversation,
  deleteConversation,
  deleteConversationAttachment,
  getConversationAttachments,
  getAgents,
  getConversations,
  getMessages,
  getProfile,
  sendMessage,
  updateConversationFavorite,
  uploadConversationAttachment,
} from '../services/api'
import { backendUrl, getServerUrl } from '../services/config'
import { clearAuth } from '../services/session'
import socketClient from '../services/socket'
import { getAgentFileUrl, getFileTree, getWorkspaceFileUrl, readAgentFile } from '../services/sandbox'
import ArtifactWorkbench from '../components/ArtifactWorkbench/index.vue'
import MessageBubble from '../components/MessageBubble.vue'

export default {
  name: 'Conversations',
  components: {
    ArtifactWorkbench,
    MessageBubble,
  },
  data() {
    return {
      conversations: [],
      messagesByConversation: {},
      agents: [],
      profile: {},
      serverUrl: '',
      searchQuery: '',
      currentId: '',
      newConversation: {
        title: '',
        selectedAgents: [],
      },
      draft: '',
      showCreate: false,
      convLoading: false,
      messagesLoading: false,
      agentsLoading: false,
      creating: false,
      sending: false,
      error: '',
      showMoreMenu: false,
      activeTab: 'chat',
      mentionVisible: false,
      mentionQuery: '',
      mentionIndex: 0,
      selectedMentions: [],
      detailPanelVisible: false,
      detailPanelMode: 'search',
      messageSearchQuery: '',
      highlightedMessageId: '',
      highlightTimer: null,
      attachmentsVisible: false,
      attachmentsLoading: false,
      attachments: [],
      selectedUploadFile: null,
      attachmentAgentId: '',
      artifactWorkbenchVisible: false,
      artifactWorkbenchArtifact: null,
      artifactWorkbenchPath: '',
      artifactWorkbenchRoot: '/workspace',
      previewUrl: '',
      tabs: [
        { key: 'chat', label: '对话' },
        { key: 'agent_config', label: '智能体配置' },
        { key: 'tool_calls', label: '工具调用' },
        { key: 'logs', label: '日志' },
      ],
      socketHandlers: [],
    }
  },
  computed: {
    filteredConversations() {
      if (!this.searchQuery) return this.conversations
      const query = this.searchQuery.toLowerCase()
      return this.conversations.filter(item => String(item.title || '').toLowerCase().includes(query))
    },
    currentConversation() {
      return this.conversations.find(item => item.id === this.currentId) || null
    },
    currentMessages() {
      return this.messagesByConversation[this.currentId] || []
    },
    messageSearchResults() {
      const query = this.messageSearchQuery.trim().toLowerCase()
      if (!query) return []
      return this.currentMessages
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
      return this.currentMessages
        .filter(message => message.sender_type === 'user')
        .map(message => ({
          message,
          title: this.buildMessageTitle(message),
          snippet: this.buildSearchSnippet(this.collectMessageText(message), ''),
        }))
    },
    currentSessionAgents() {
      const participants = (this.currentConversation && this.currentConversation.participants_info) || []
      return participants
        .filter(p => p.participant_type === 'agent')
        .map(p => ({
          agent_id: p.participant_id,
          role: p.name,
          name: p.name,
          workspace_name: this.safeWorkspaceName(p.name || p.participant_id),
          avatar: this.participantAvatar(p),
          color: this.participantColor(p),
        }))
    },
    mentionCandidates() {
      const query = String(this.mentionQuery || '').toLowerCase()
      const agents = (this.currentSessionAgents || []).filter(agent => agent && agent.agent_id)
      const filtered = query
        ? agents.filter(agent => {
          const name = this.mentionName(agent).toLowerCase()
          const id = String(agent.agent_id || '').toLowerCase()
          return name.includes(query) || id.includes(query)
        })
        : agents
      return filtered.slice(0, 8)
    },
    currentSessionId() {
      return (this.currentConversation && (this.currentConversation.sandbox_session_id || this.currentConversation.id)) || ''
    },
  },
  watch: {
    'newConversation.selectedAgents': function updateTitle() {
      const names = this.newConversation.selectedAgents
        .map(id => this.agents.find(agent => agent.id === id))
        .filter(Boolean)
        .map(agent => agent.name)
      this.newConversation.title = [this.profile.username || '我', ...names].join('、')
    },
    '$route.query.conversation_id': function handleConversationQueryChange() {
      this.selectConversationFromRoute()
    },
  },
  async created() {
    this.serverUrl = await getServerUrl()
    await socketClient.connect()
    this.registerSocketHandlers()
    await Promise.all([this.loadProfile(), this.loadAgents(), this.loadConversations()])
  },
  beforeDestroy() {
    if (this.currentId) socketClient.leaveConversation(this.currentId)
    window.clearTimeout(this.highlightTimer)
    this.unregisterSocketHandlers()
  },
  methods: {
    async loadProfile() {
      try {
        const response = await getProfile()
        this.profile = response.data || {}
      } catch (error) {
        this.handleRequestError(error, '加载个人信息失败')
      }
    },
    async loadAgents() {
      this.agentsLoading = true
      try {
        const response = await getAgents()
        this.agents = Array.isArray(response.data) ? response.data : []
      } catch (error) {
        this.handleRequestError(error, '加载 Agent 失败')
      } finally {
        this.agentsLoading = false
      }
    },
    async loadConversations() {
      this.error = ''
      this.convLoading = true
      try {
        const response = await getConversations()
        this.conversations = Array.isArray(response.data) ? response.data : []
        if (await this.selectConversationFromRoute()) return
        if (!this.currentId && this.conversations.length) {
          await this.selectConversation(this.conversations[0])
        }
      } catch (error) {
        this.handleRequestError(error, '加载会话失败')
      } finally {
        this.convLoading = false
      }
    },
    openCreateDialog() {
      this.showCreate = true
      if (!this.agents.length) this.loadAgents()
    },
    async handleCreateConversation() {
      if (!this.newConversation.selectedAgents.length || this.creating) return
      this.error = ''
      this.creating = true
      try {
        const participantIds = this.newConversation.selectedAgents.map(id => `agent_${id}`)
        const response = await createConversation({
          title: this.newConversation.title || '新建会话',
          type: participantIds.length > 1 ? 'group' : 'single',
          participant_ids: participantIds,
        })
        if (response.code === 201 && response.data) {
          this.conversations = [response.data, ...this.conversations]
          this.cancelCreate()
          await this.selectConversation(response.data)
        } else {
          this.error = response.message || '创建会话失败'
        }
      } catch (error) {
        this.handleRequestError(error, '创建会话失败')
      } finally {
        this.creating = false
      }
    },
    async handleDeleteConversation(conversation) {
      if (!conversation || !conversation.id) return
      if (!window.confirm(`删除会话「${conversation.title || '未命名会话'}」？`)) return
      this.error = ''
      try {
        if (this.currentId === conversation.id) {
          socketClient.leaveConversation(conversation.id)
        }
        const response = await deleteConversation(conversation.id)
        if (response.code && ![200, 204].includes(response.code)) {
          this.error = response.message || '删除会话失败'
          return
        }
        this.$delete(this.messagesByConversation, conversation.id)
        this.conversations = this.conversations.filter(item => item.id !== conversation.id)
        if (this.currentId === conversation.id) {
          this.currentId = ''
          const next = this.conversations[0]
          if (next) await this.selectConversation(next)
        }
        this.showMoreMenu = false
      } catch (error) {
        this.handleRequestError(error, '删除会话失败')
      }
    },
    cancelCreate() {
      this.showCreate = false
      this.newConversation = { title: '', selectedAgents: [] }
    },
    async selectConversation(conversation) {
      if (!conversation || !conversation.id) return
      if (this.currentId && this.currentId !== conversation.id) {
        socketClient.leaveConversation(this.currentId)
      }
      this.currentId = conversation.id
      this.activeTab = 'chat'
      this.showMoreMenu = false
      this.closeDetailPanel()
      this.resetMentionState()
      socketClient.joinConversation(conversation.id)
      await this.loadMessages(conversation.id)
    },
    async selectConversationFromRoute() {
      const id = this.$route && this.$route.query && this.$route.query.conversation_id
      if (!id) return false
      const target = this.conversations.find(item => String(item.id) === String(id))
      if (!target) return false
      if (String(this.currentId) !== String(target.id)) {
        await this.selectConversation(target)
      }
      return true
    },
    updateLocalConversation(conversation) {
      if (!conversation || !conversation.id) return
      const index = this.conversations.findIndex(item => String(item.id) === String(conversation.id))
      if (index >= 0) {
        this.$set(this.conversations, index, { ...this.conversations[index], ...conversation })
      }
    },
    async toggleFavorite() {
      if (!this.currentConversation) return
      const previous = Boolean(this.currentConversation.is_favorite)
      const nextValue = !previous
      const optimistic = { ...this.currentConversation, is_favorite: nextValue }
      this.updateLocalConversation(optimistic)
      this.error = ''
      try {
        const response = await updateConversationFavorite(this.currentConversation.id, nextValue)
        const payload = response && response.data && (response.data.conversation || response.data)
        const saved = payload && payload.id ? payload : optimistic
        if (saved.is_favorite === undefined) saved.is_favorite = nextValue
        this.updateLocalConversation(saved)
      } catch (error) {
        this.updateLocalConversation({ ...optimistic, is_favorite: previous })
        this.handleRequestError(error, nextValue ? '收藏会话失败' : '取消收藏失败')
      }
    },
    toggleSearchPanel() {
      if (!this.currentConversation) return
      if (this.detailPanelVisible && this.detailPanelMode === 'search') {
        this.closeDetailPanel()
        return
      }
      this.detailPanelMode = 'search'
      this.detailPanelVisible = true
      this.$nextTick(() => {
        if (this.$refs.messageSearchInput) this.$refs.messageSearchInput.focus()
      })
    },
    toggleHistoryPanel() {
      if (!this.currentConversation) return
      if (this.detailPanelVisible && this.detailPanelMode === 'history') {
        this.closeDetailPanel()
        return
      }
      this.detailPanelMode = 'history'
      this.detailPanelVisible = true
    },
    closeDetailPanel() {
      this.detailPanelVisible = false
      this.highlightedMessageId = ''
    },
    jumpToFirstSearchResult() {
      if (this.messageSearchResults.length) {
        this.jumpToMessage(this.messageSearchResults[0].message.id)
      }
    },
    jumpToMessage(messageId) {
      if (!messageId) return
      this.$nextTick(() => {
        const ref = this.$refs[`message-${messageId}`]
        const element = Array.isArray(ref) ? ref[0] : ref
        if (!element) return
        element.scrollIntoView({ behavior: 'smooth', block: 'center' })
        this.highlightedMessageId = messageId
        window.clearTimeout(this.highlightTimer)
        this.highlightTimer = window.setTimeout(() => {
          if (this.highlightedMessageId === messageId) this.highlightedMessageId = ''
        }, 1800)
      })
    },
    collectMessageText(message) {
      if (!message) return ''
      const chunks = [
        message.content,
        message.raw_output,
        message.sender_name,
        message.status,
      ]
      const visit = value => {
        if (value === null || value === undefined) return
        if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
          chunks.push(String(value))
          return
        }
        if (Array.isArray(value)) {
          value.forEach(visit)
          return
        }
        if (typeof value === 'object') {
          ;['title', 'name', 'filename', 'path', 'url', 'content', 'text', 'summary', 'status'].forEach(key => {
            if (value[key] !== undefined) visit(value[key])
          })
          if (value.data) visit(value.data)
          if (value.detail) visit(value.detail)
        }
      }
      visit(message.elements)
      visit(message.meta && message.meta.events)
      return chunks.filter(Boolean).join('\n')
    },
    buildMessageTitle(message) {
      const prefix = this.isOwnMessage(message) ? '我' : this.senderName(message)
      const text = this.collectMessageText(message).replace(/\s+/g, ' ').trim()
      return `${prefix}: ${text ? text.slice(0, 32) : '空消息'}${text.length > 32 ? '...' : ''}`
    },
    buildSearchSnippet(text, query) {
      const value = String(text || '').replace(/\s+/g, ' ').trim()
      if (!value) return '暂无可预览内容'
      if (!query) return `${value.slice(0, 80)}${value.length > 80 ? '...' : ''}`
      const lower = value.toLowerCase()
      const index = lower.indexOf(String(query || '').toLowerCase())
      if (index < 0) return `${value.slice(0, 80)}${value.length > 80 ? '...' : ''}`
      const start = Math.max(0, index - 24)
      const end = Math.min(value.length, index + String(query).length + 56)
      return `${start > 0 ? '...' : ''}${value.slice(start, end)}${end < value.length ? '...' : ''}`
    },
    async loadMessages(conversationId) {
      if (!conversationId) return
      this.error = ''
      this.messagesLoading = true
      try {
        const response = await getMessages(conversationId, { page: 1, per_page: 80 })
        const items = this.sortMessages((response.data && response.data.items) || [])
        this.$set(this.messagesByConversation, conversationId, items)
        this.$nextTick(this.scrollToBottom)
      } catch (error) {
        this.handleRequestError(error, '加载消息失败')
      } finally {
        this.messagesLoading = false
      }
    },
    async handleSendMessage() {
      const content = this.draft.trim()
      if (!this.currentConversation || !content || this.sending) return
      const payload = this.buildMessagePayload()
      this.error = ''
      this.sending = true

      const temp = {
        id: `temp_${Date.now()}`,
        conversation_id: this.currentConversation.id,
        sender_type: 'user',
        sender_id: this.profile.id,
        content,
        message_type: 'text',
        created_at: new Date().toISOString(),
        meta: payload.target_agent_ids.length
          ? { dispatch_mode: 'direct', mentions: payload.mentions }
          : undefined,
      }
        this.$set(this.messagesByConversation, this.currentConversation.id, this.sortMessages([
          ...this.currentMessages,
          temp,
        ]))
      this.draft = ''
      this.resetMentionState()
      this.$nextTick(this.scrollToBottom)

      try {
        const requestData = {
          conversation_id: this.currentConversation.id,
          content: payload.content,
          message_type: 'text',
        }
        if (payload.target_agent_ids.length) {
          requestData.target_agent_ids = payload.target_agent_ids
        }
        const response = await sendMessage(requestData)
        if (response.code === 201) {
          await this.loadMessages(this.currentConversation.id)
          await this.loadConversations()
        } else {
          this.error = response.message || '发送失败'
        }
      } catch (error) {
        this.handleRequestError(error, '发送失败')
        await this.loadMessages(this.currentConversation.id)
      } finally {
        this.sending = false
      }
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
    safeWorkspaceName(name) {
      return String(name || 'agent')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9\u4e00-\u9fa5_-]+/gi, '-')
        .replace(/^-+|-+$/g, '')
        .slice(0, 80) || 'agent'
    },
    agentAvatar(agent) {
      return agent && agent.avatar_url ? backendUrl(this.serverUrl, agent.avatar_url) : ''
    },
    agentAvatarStyle(agent) {
      return this.agentAvatar(agent) ? {} : { background: (agent && agent.avatar_color) || '#4080ff' }
    },
    participantCount(conversation) {
      return ((conversation && conversation.participants_info) || (conversation && conversation.participant_ids) || []).length
    },
    isOwnMessage(message) {
      return message && message.sender_type === 'user'
    },
    senderName(message) {
      if (message && message.sender_name) return message.sender_name
      return this.isOwnMessage(message) ? (this.profile.username || '我') : '智能体'
    },
    senderParticipant(message) {
      const participants = (this.currentConversation && this.currentConversation.participants_info) || []
      if (!message) return null
      return participants.find(p =>
        (p.participant_type === message.sender_type && String(p.participant_id) === String(message.sender_id))
        || (message.sender_name && p.name === message.sender_name)
      ) || null
    },
    messageAvatar(message) {
      if (this.isOwnMessage(message)) {
        return this.profile.avatar_url ? backendUrl(this.serverUrl, this.profile.avatar_url) : ''
      }
      return this.participantAvatar(this.senderParticipant(message))
    },
    messageAvatarStyle(message) {
      const avatar = this.messageAvatar(message)
      if (avatar) return {}
      const participant = this.senderParticipant(message)
      return { background: this.isOwnMessage(message) ? '#4080ff' : this.participantColor(participant) }
    },
    firstLetter(value) {
      return String(value || '?').charAt(0).toUpperCase()
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
        this.handleSendMessage()
      }
    },
    syncMentionState() {
      const match = /@([^\s@，,：:；;]*)$/.exec(this.draft)
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
      this.draft = this.draft.replace(/@([^\s@，,：:；;]*)$/, `@${name} `)
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
      this.selectedMentions = this.selectedMentions.filter(item => this.draft.includes(`@${item.name}`))
    },
    buildMessagePayload() {
      this.syncSelectedMentions()
      const targetIds = this.selectedMentions.map(item => item.agent_id)
      return {
        content: this.draft.trim(),
        target_agent_ids: targetIds,
        mentions: this.selectedMentions.slice(),
      }
    },
    resetMentionState() {
      this.mentionVisible = false
      this.mentionQuery = ''
      this.mentionIndex = 0
      this.selectedMentions = []
    },
    mentionName(agent) {
      return (agent && (agent.role || agent.name || agent.agent_id)) || ''
    },
    handleTabSwitch(key) {
      this.activeTab = key
      if (key !== 'chat') {
        this.error = key === 'agent_config'
          ? '智能体配置功能即将上线'
          : key === 'tool_calls'
            ? '工具调用记录功能即将上线'
            : '日志功能即将上线'
      }
    },
    sortMessages(messages) {
      return [...(messages || [])].sort((a, b) => {
        const at = new Date(a.created_at || 0).getTime() || 0
        const bt = new Date(b.created_at || 0).getTime() || 0
        if (at !== bt) return at - bt
        if (a.sender_type !== b.sender_type) {
          if (a.sender_type === 'user') return -1
          if (b.sender_type === 'user') return 1
        }
        return String(a.id || '').localeCompare(String(b.id || ''))
      })
    },
    async handleOpenAttachments() {
      if (!this.currentConversation) return
      this.attachmentsVisible = true
      if (!this.attachmentAgentId && this.currentSessionAgents.length) {
        this.attachmentAgentId = this.currentSessionAgents[0].agent_id
      }
      await this.loadAttachments({ silent: true })
    },
    async loadAttachments(options = {}) {
      if (!this.currentConversation) return
      this.attachmentsLoading = true
      if (!options.silent) this.error = ''
      try {
        const response = await getConversationAttachments(
          this.currentConversation.id,
          this.currentSessionAgents.length > 1 ? this.attachmentAgentId : ''
        )
        this.attachments = (response.data && response.data.files) || []
        if (response.data && response.data.agent_id) this.attachmentAgentId = response.data.agent_id
      } catch (error) {
        if (!options.silent) this.handleRequestError(error, '加载附件失败')
      } finally {
        this.attachmentsLoading = false
      }
    },
    handleAttachmentFileChange(event) {
      this.selectedUploadFile = event.target.files && event.target.files[0] ? event.target.files[0] : null
    },
    async handleAttachmentUpload() {
      if (!this.currentConversation || !this.selectedUploadFile) return
      this.attachmentsLoading = true
      this.error = ''
      try {
        const response = await uploadConversationAttachment(
          this.currentConversation.id,
          this.selectedUploadFile,
          this.currentSessionAgents.length > 1 ? this.attachmentAgentId : ''
        )
        const uploaded = response && response.data
        this.selectedUploadFile = null
        if (this.$refs.attachmentInput) this.$refs.attachmentInput.value = ''
        if (uploaded && uploaded.path && !this.attachments.some(item => item.path === uploaded.path)) {
          this.attachments = [uploaded, ...this.attachments]
        }
        await this.loadAttachments({ silent: true })
      } catch (error) {
        this.handleRequestError(error, '上传文件失败')
      } finally {
        this.attachmentsLoading = false
      }
    },
    async handleDeleteAttachment(file) {
      if (!file || !file.path) return
      if (!window.confirm(`删除文件「${file.name || file.path}」？`)) return
      this.attachmentsLoading = true
      try {
        await deleteConversationAttachment(this.currentConversation.id, file.path, file.agent_id || this.attachmentAgentId)
        await this.loadAttachments()
      } catch (error) {
        this.handleRequestError(error, '删除文件失败')
      } finally {
        this.attachmentsLoading = false
      }
    },
    previewAttachment(file) {
      if (!file || !file.path) return
      this.openArtifactWorkbench({
        path: file.path,
        root: this.fileRootForPath(file.path),
        agentId: file.agent_id || this.attachmentAgentId || '',
        artifact: file,
      })
    },
    async handleOpenMessageFile(file) {
      const filePath = this.normalizeWorkspaceFilePath(file && (file.path || file.url || file.raw || file.name))
      if (!filePath && !(file && file.type === 'diff')) return
      const agentId = (file && (file.agent_id || file.agentId)) || this.inferAgentIdFromFilePath(filePath) || ''
      this.openArtifactWorkbench({
        path: filePath,
        root: filePath ? this.fileRootForPath(filePath) : '/workspace',
        agentId,
        artifact: file,
      })
    },
    normalizeWorkspaceFilePath(value) {
      let path = String(value || '').trim()
      if (!path) return ''
      try {
        if (/^https?:\/\//i.test(path)) {
          const url = new URL(path)
          const queryPath = url.searchParams.get('path') || url.searchParams.get('file') || url.searchParams.get('file_path')
          const urlPath = decodeURIComponent(url.pathname || '')
          path = queryPath || (urlPath.includes('/workspace/') ? urlPath : '')
        }
      } catch (error) {
        // Keep the original value when URL parsing is not possible.
      }
      const workspaceIndex = path.indexOf('/workspace/')
      if (workspaceIndex >= 0) return path.slice(workspaceIndex)
      if (path.indexOf('workspace/') === 0) return `/${path}`
      return path
    },
    fileRootForPath(filePath) {
      const path = String(filePath || '')
      const lastSlash = path.lastIndexOf('/')
      if (lastSlash <= 0) return '/workspace'
      return path.slice(0, lastSlash) || '/workspace'
    },
    inferAgentIdFromFilePath(filePath) {
      const match = String(filePath || '').match(/\/workspace\/agents\/([^/]+)/)
      if (!match) return ''
      const workspaceName = decodeURIComponent(match[1])
      const agent = this.currentSessionAgents.find(item => {
        const names = [
          item.workspace_name,
          this.safeWorkspaceName(item.role),
          this.safeWorkspaceName(item.name),
          this.safeWorkspaceName(item.agent_id),
        ].filter(Boolean)
        return names.includes(workspaceName)
      })
      return agent ? agent.agent_id : ''
    },
    async handleOpenWorkspace(scope = 'workspace') {
      if (!this.currentConversation) return
      const nextScope = typeof scope === 'string' ? scope : 'workspace'
      let root = '/workspace'
      let agentId = ''
      if (nextScope === 'shared') {
        root = '/workspace/shared'
      } else if (nextScope && nextScope.startsWith('agent:')) {
        agentId = nextScope.slice('agent:'.length)
        const agent = this.currentSessionAgents.find(item => item.agent_id === agentId)
        root = `/workspace/agents/${(agent && agent.workspace_name) || this.safeWorkspaceName((agent && agent.role) || agentId)}`
      }
      this.openArtifactWorkbench({ root, agentId })
    },
    openArtifactWorkbench({ path = '', root = '/workspace', agentId = '', artifact = null } = {}) {
      this.artifactWorkbenchArtifact = artifact || null
      this.artifactWorkbenchPath = path || ''
      this.artifactWorkbenchRoot = root || '/workspace'
      this.artifactWorkbenchAgentId = agentId || ''
      this.artifactWorkbenchVisible = true
    },
    elementKey(element) {
      if (!element || typeof element !== 'object') return ''
      const data = element.data || {}
      const detail = element.detail || {}
      const title = data.title || detail.title || element.title || ''
      const content = element.content || data.content || detail.content || ''
      const stable = data.url || data.path || data.name || data.filename || detail.path || element.step_id || data.progress_key || detail.progress_key
      return stable || [element.type || '', element.status || '', title, String(content).slice(0, 240)].join('|')
    },
    mergeElements(existing = [], incoming = []) {
      const merged = []
      ;(Array.isArray(existing) ? existing : []).forEach(element => {
        const key = this.elementKey(element)
        if (!key || !merged.some(item => this.elementKey(item) === key)) merged.push(element)
      })
      ;(Array.isArray(incoming) ? incoming : []).forEach(element => {
        const key = this.elementKey(element)
        const progressKey = element && (element.data?.progress_key || element.detail?.progress_key || element.step_id)
        const replaceIndex = progressKey
          ? merged.findIndex(item => (item.data?.progress_key || item.detail?.progress_key || item.step_id) === progressKey)
          : -1
        if (replaceIndex >= 0) {
          this.$set(merged, replaceIndex, element)
        } else if (!key || !merged.some(item => this.elementKey(item) === key)) {
          merged.push(element)
        }
      })
      return merged
    },
    mergeMessage(oldMessage = {}, incoming = {}) {
      const next = { ...oldMessage, ...incoming }
      if (!incoming.raw_output && oldMessage.raw_output) next.raw_output = oldMessage.raw_output
      if (Array.isArray(oldMessage.elements) && oldMessage.elements.length) {
        next.elements = Array.isArray(incoming.elements) && incoming.elements.length
          ? this.mergeElements(oldMessage.elements, incoming.elements)
          : oldMessage.elements
      }
      if (oldMessage.meta || incoming.meta) {
        next.meta = { ...(oldMessage.meta || {}), ...(incoming.meta || {}) }
      }
      return next
    },
    addMessageEvent(conversationId, messageId, event, events) {
      const list = this.messagesByConversation[conversationId] || []
      const next = list.map(item => {
        if (item.id !== messageId) return item
        const meta = { ...(item.meta || {}) }
        if (Array.isArray(events)) {
          meta.events = events
        } else if (event) {
          const current = Array.isArray(meta.events) ? meta.events.slice() : []
          current.push(event)
          meta.events = current
        }
        return { ...item, meta }
      })
      this.$set(this.messagesByConversation, conversationId, next)
    },
    registerSocketHandlers() {
      this.unregisterSocketHandlers()
      const upsertMessage = message => {
        if (!message || !message.conversation_id) return
        const list = this.messagesByConversation[message.conversation_id] || []
        const index = list.findIndex(item => item.id === message.id)
        const next = this.sortMessages(index >= 0
          ? list.map(item => (item.id === message.id ? this.mergeMessage(item, message) : item))
          : [...list, message])
        this.$set(this.messagesByConversation, message.conversation_id, next)
        if (message.conversation_id === this.currentId) this.$nextTick(this.scrollToBottom)
        this.loadConversations()
      }
      const patchMessage = event => {
        if (!event || !event.conversation_id || !event.message_id) return
        const list = this.messagesByConversation[event.conversation_id] || []
        const next = list.map(item => {
          if (item.id !== event.message_id) return item
          return this.mergeMessage(item, {
            content: event.content == null ? item.content : event.content,
            elements: event.elements,
            raw_output: event.raw_output,
            status: event.status == null ? item.status : event.status,
            sender_name: event.sender_name == null ? item.sender_name : event.sender_name,
            meta: event.events ? { events: event.events } : undefined,
          })
        })
        this.$set(this.messagesByConversation, event.conversation_id, next)
        if (event.conversation_id === this.currentId) this.$nextTick(this.scrollToBottom)
      }
      const appendElement = event => {
        if (!event || !event.conversation_id || !event.message_id || !event.element) return
        const list = this.messagesByConversation[event.conversation_id] || []
        const next = list.map(item => {
          if (item.id !== event.message_id) return item
          return this.mergeMessage(item, {
            content: event.content,
            raw_output: event.raw_output,
            status: event.status,
            sender_name: event.sender_name,
            elements: this.mergeElements(item.elements || [], [event.element]),
          })
        })
        this.$set(this.messagesByConversation, event.conversation_id, next)
        this.addMessageEvent(event.conversation_id, event.message_id, null, event.events)
        if (event.conversation_id === this.currentId) this.$nextTick(this.scrollToBottom)
      }
      const addStep = event => {
        if (!event || !event.conversation_id || !event.message_id) return
        this.addMessageEvent(event.conversation_id, event.message_id, event.event, event.events)
      }
      this.socketHandlers = [
        ['new_message', upsertMessage],
        ['conversation_message_created', upsertMessage],
        ['conversation_message_delta', patchMessage],
        ['conversation_message_element_stream', appendElement],
        ['conversation_message_step', addStep],
        ['conversation_message_status', patchMessage],
      ]
      this.socketHandlers.forEach(([event, handler]) => socketClient.on(event, handler))
    },
    unregisterSocketHandlers() {
      this.socketHandlers.forEach(([event, handler]) => socketClient.off(event, handler))
      this.socketHandlers = []
    },
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return ''
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    },
    scrollToBottom() {
      const el = this.$refs.messagesContainer
      if (el) el.scrollTop = el.scrollHeight
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
