<template>
  <main class="android-conv">
    <section v-if="!currentConversation" class="android-conv-list-page">
      <header class="android-conv-list-header">
        <div>
          <span>WeAgent</span>
          <h1>会话</h1>
        </div>
        <button type="button" class="android-icon-btn primary" aria-label="新建会话" @click="openCreate">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
      </header>

      <div class="android-conv-list">
        <div v-if="loading" class="android-empty">正在加载会话...</div>
        <div v-else-if="conversations.length === 0" class="android-empty">暂无会话，先新建一个。</div>
        <button
          v-for="conv in conversations"
          v-else
          :key="conv.id"
          type="button"
          class="android-conv-card"
          @click="selectConversation(conv)"
        >
          <span class="android-composite-avatar">
            <span
              v-for="(avatar, index) in conversationAvatars(conv)"
              :key="`${conv.id}-avatar-${index}`"
              class="android-composite-item"
              :class="{ more: avatar.more }"
              :style="{ background: avatar.color }"
            >
              <img v-if="avatar.url" :src="avatar.url" alt="" />
              <span v-else>{{ avatar.text }}</span>
            </span>
          </span>
          <span class="android-conv-card-main">
            <span class="android-conv-card-top">
              <strong>{{ conversationTitle(conv) }}</strong>
              <time>{{ conversationTime(conv) }}</time>
            </span>
            <span class="android-conv-card-preview">{{ conversationPreview(conv) }}</span>
          </span>
        </button>
      </div>

      <BottomNav />
    </section>

    <section v-else class="android-chat-page">
      <header class="android-chat-header">
        <button type="button" class="android-chat-edge-btn" aria-label="返回" @click="backToList">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15.5 5.5 9 12l6.5 6.5" />
          </svg>
        </button>
        <div class="android-chat-title">
          <span>会话详情</span>
          <h1>{{ conversationTitle(currentConversation) }}</h1>
        </div>
        <button type="button" class="android-chat-edge-btn" aria-label="刷新" @click="loadMessages(currentConversation.id, true)">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 12a8 8 0 1 1-2.34-5.66M20 4v5h-5" />
          </svg>
        </button>
      </header>

      <div ref="messageList" class="android-message-list">
        <div v-if="messagesLoading" class="android-empty">正在加载消息...</div>
        <div v-else-if="messages.length === 0" class="android-empty">发送第一条消息开始对话。</div>
        <article
          v-for="message in messages"
          v-else
          :key="message.id"
          class="android-message-row"
          :class="{ user: isOwnMessage(message), agent: !isOwnMessage(message) }"
        >
          <span class="android-message-avatar" :style="{ background: messageAvatarColor(message) }">
            <img v-if="messageAvatarUrl(message)" :src="messageAvatarUrl(message)" alt="" />
            <span v-else>{{ firstLetter(messageSenderName(message)) }}</span>
          </span>
          <div class="android-message-stack">
            <span class="android-message-name">{{ messageSenderName(message) }}</span>
            <div class="android-message-bubble">
              <div v-if="currentProgress(message)" class="android-progress-line">
                <span class="dot" :class="currentProgress(message).status || 'running'"></span>
                <span>{{ elementContent(currentProgress(message)) }}</span>
              </div>

              <div v-if="displayTextContent(message)" class="android-message-text android-rendered" v-html="renderMarkdown(displayTextContent(message))"></div>

              <div
                v-for="(el, index) in contentElements(message)"
                :key="`content-${index}`"
                class="android-element-card"
                :class="`type-${el.type}`"
              >
                <strong>{{ elementTitle(el) }}</strong>
                <div class="android-rendered" v-html="renderMarkdown(elementContent(el))"></div>
              </div>

              <div v-if="artifactElements(message).length" class="android-artifact-group">
                <span class="android-section-label">产物</span>
                <div
                  v-for="(el, index) in artifactElements(message)"
                  :key="`artifact-${index}`"
                  class="android-artifact-card"
                  :class="[`artifact-${el.type}`, { openable: isFileArtifact(el) }]"
                  @click="isFileArtifact(el) && openArtifactFile(el)"
                >
                  <button v-if="el.type === 'file'" type="button" class="android-file-artifact" @click.stop="openArtifactFile(el)">
                    <span class="file-badge">{{ fileIconText(el) }}</span>
                    <span class="file-info">
                      <strong>{{ artifactFilePayload(el).name || elementContent(el) }}</strong>
                      <small>{{ artifactFilePayload(el).path || artifactFilePayload(el).raw }}</small>
                    </span>
                    <span class="file-open">查看</span>
                  </button>
                  <template v-else>
                    <div class="android-artifact-head" :class="{ table: el.type === 'table' }">
                      <strong>{{ elementTitle(el) }}</strong>
                      <small>{{ artifactMeta(el) }}</small>
                    </div>
                    <pre v-if="el.type === 'code'">{{ elementContent(el) }}</pre>
                  <div v-else-if="el.type === 'table'" class="android-table-scroll">
                    <table v-if="tableHeaders(el).length" class="android-artifact-table">
                      <thead>
                        <tr>
                          <th v-for="(header, hi) in tableHeaders(el)" :key="`h-${hi}`">{{ header }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, ri) in normalizeTable(el)" :key="`r-${ri}`">
                          <td v-for="(header, hi) in tableHeaders(el)" :key="`c-${hi}`">{{ row['col' + hi] }}</td>
                        </tr>
                      </tbody>
                    </table>
                    <div v-else class="android-rendered" v-html="renderMarkdown(elementContent(el))"></div>
                  </div>
                    <p v-else>{{ el.type === 'image' ? (artifactUrl(el) || elementContent(el)) : elementContent(el) }}</p>
                  </template>
                </div>
              </div>

              <details v-if="visibleRawOutput(message)" class="android-raw">
                <summary>Raw output</summary>
                <pre>{{ visibleRawOutput(message) }}</pre>
              </details>

              <p v-if="emptyMessage(message)" class="android-message-text muted">{{ renderElementSummary(message) || '暂无内容' }}</p>
            </div>
          </div>
        </article>
      </div>

      <form class="android-chat-input" @submit.prevent="handleSend">
        <input v-model.trim="draft" :disabled="sending" placeholder="输入消息..." />
        <button type="submit" :disabled="sending || !draft">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m5 12 14-7-4 14-3-6-7-1Z" />
          </svg>
        </button>
      </form>
    </section>

    <div v-if="createVisible" class="android-sheet-mask" @click.self="closeCreate">
      <section class="android-create-sheet">
        <header>
          <h2>新建会话</h2>
          <button type="button" aria-label="关闭" @click="closeCreate">×</button>
        </header>

        <label class="android-field">
          <span>会话标题</span>
          <input v-model.trim="createForm.title" readonly placeholder="选择 Agent 后自动生成" />
        </label>

        <div class="android-type-toggle">
          <button type="button" :class="{ active: createForm.type === 'single' }" @click="setCreateType('single')">单 Agent</button>
          <button type="button" :class="{ active: createForm.type === 'group' }" @click="setCreateType('group')">多 Agent</button>
        </div>

        <div class="android-agent-picker">
          <button
            v-for="agent in agents"
            :key="agent.id"
            type="button"
            class="android-agent-pick"
            :class="{ active: createForm.agentIds.includes(agent.id) }"
            @click="toggleCreateAgent(agent.id)"
          >
            <span class="check">{{ createForm.agentIds.includes(agent.id) ? '✓' : '' }}</span>
            <span class="mini" :style="{ background: agent.avatar_color || '#2563eb' }">{{ firstLetter(agent.name) }}</span>
            <span class="name">{{ agent.name }}</span>
          </button>
        </div>

        <p v-if="error" class="android-error">{{ error }}</p>

        <footer>
          <button type="button" class="secondary" @click="closeCreate">取消</button>
          <button type="button" class="primary" :disabled="creating || !createForm.agentIds.length" @click="handleCreate">
            {{ creating ? '创建中...' : '创建会话' }}
          </button>
        </footer>
      </section>
    </div>

    <div v-if="previewVisible" class="android-preview-backdrop" @click.self="closePreview">
      <section class="android-preview-panel">
        <header>
          <div>
            <span>文件预览</span>
            <h2>{{ previewTitle || fileNameFromPath(previewPath) }}</h2>
            <p>{{ previewPath }}</p>
          </div>
          <button type="button" @click="closePreview">×</button>
        </header>
        <div class="android-preview-body">
          <p v-if="previewLoading" class="android-preview-empty">加载中...</p>
          <iframe v-else-if="previewType === 'html'" class="android-preview-frame" :srcdoc="previewHtml"></iframe>
          <iframe v-else-if="previewType === 'pdf'" class="android-preview-frame" :src="previewUrl"></iframe>
          <img v-else-if="previewType === 'image'" class="android-preview-image" :src="previewUrl" alt="" />
          <div v-else-if="previewType === 'markdown'" class="android-rendered preview-rendered" v-html="renderMarkdown(previewContent)"></div>
          <pre v-else class="android-preview-code">{{ previewContent }}</pre>
        </div>
      </section>
    </div>
  </main>
</template>

<script>
import BottomNav from '../components/BottomNav.vue'
import { backendUrl, getCurrentServerUrl } from '../services/config'
import {
  createConversation,
  getAgents,
  getConversations,
  getMessages,
  getProfile,
  getWorkspaceFileUrl,
  sendMessage,
} from '../services/api'
import { getCurrentUser } from '../services/session'

export default {
  name: 'Conversations',
  components: { BottomNav },
  data() {
    return {
      conversations: [],
      agents: [],
      profile: null,
      currentConversation: null,
      messages: [],
      draft: '',
      loading: false,
      messagesLoading: false,
      sending: false,
      creating: false,
      createVisible: false,
      error: '',
      messageRefreshTimer: null,
      previewVisible: false,
      previewLoading: false,
      previewTitle: '',
      previewPath: '',
      previewType: 'text',
      previewContent: '',
      previewHtml: '',
      previewUrl: '',
      createForm: {
        title: '',
        type: 'single',
        agentIds: [],
      },
    }
  },
  async created() {
    await Promise.all([this.loadProfile(), this.loadAgents(), this.loadConversations()])
  },
  beforeDestroy() {
    this.stopMessageRefresh()
  },
  methods: {
    payload(response) {
      return response && response.data !== undefined ? response.data : response
    },
    async loadProfile() {
      try {
        const response = await getProfile()
        const data = this.payload(response) || {}
        this.profile = data.user || data.profile || data || getCurrentUser() || null
      } catch (error) {
        this.profile = getCurrentUser() || null
      } finally {
        if (this.createVisible) this.syncCreateTitle()
      }
    },
    async loadAgents() {
      try {
        const response = await getAgents()
        const data = this.payload(response)
        const list = Array.isArray(data) ? data : (data && (data.agents || data.items)) || []
        this.agents = list.filter(agent => agent && agent.id !== 'moderator')
      } catch (error) {
        this.agents = []
      } finally {
        if (this.createVisible) this.syncCreateTitle()
      }
    },
    async loadConversations() {
      this.loading = true
      try {
        const response = await getConversations()
        const data = this.payload(response)
        this.conversations = Array.isArray(data) ? data : (data && (data.items || data.conversations)) || []
      } finally {
        this.loading = false
      }
    },
    async selectConversation(conversation) {
      this.currentConversation = conversation
      this.messages = []
      await this.loadMessages(conversation.id)
    },
    backToList() {
      this.stopMessageRefresh()
      this.currentConversation = null
      this.messages = []
      this.loadConversations()
    },
    async loadMessages(conversationId, silent = false) {
      if (!silent && this.messages.length === 0) this.messagesLoading = true
      try {
        const response = await getMessages(conversationId, { page: 1, per_page: 80 })
        const data = this.payload(response) || {}
        const items = data.items || data.messages || (Array.isArray(data) ? data : [])
        this.messages = this.sortMessages(items)
        this.scrollToLatestMessage()
      } finally {
        this.messagesLoading = false
      }
    },
    startMessageRefresh() {
      this.stopMessageRefresh()
      let ticks = 0
      this.messageRefreshTimer = setInterval(async () => {
        if (!this.currentConversation) {
          this.stopMessageRefresh()
          return
        }
        ticks += 1
        await this.loadMessages(this.currentConversation.id, true)
        if ((ticks >= 3 && !this.hasStreamingMessages()) || ticks >= 120) {
          this.stopMessageRefresh()
        }
      }, 2000)
    },
    stopMessageRefresh() {
      if (this.messageRefreshTimer) {
        clearInterval(this.messageRefreshTimer)
        this.messageRefreshTimer = null
      }
    },
    hasStreamingMessages() {
      return this.messages.some(message => ['pending', 'streaming'].includes(message.status))
    },
    openCreate() {
      this.error = ''
      this.createForm = { title: '', type: 'single', agentIds: [] }
      this.createVisible = true
      if (!this.agents.length) this.loadAgents()
      this.syncCreateTitle()
    },
    closeCreate() {
      this.createVisible = false
    },
    selectedCreateAgents() {
      const selected = new Set(this.createForm.agentIds.map(id => String(id)))
      return this.agents.filter(agent => selected.has(String(agent.id)))
    },
    profileDisplayName() {
      return (this.profile && (this.profile.username || this.profile.name || this.profile.email)) || '我'
    },
    createTitleFromSelection() {
      const agents = this.selectedCreateAgents()
      if (!agents.length) return ''
      const names = [this.profileDisplayName(), ...agents.map(agent => agent.name || agent.display_name)]
        .filter(Boolean)
      return [...new Set(names)].join('、')
    },
    syncCreateTitle() {
      this.createForm.title = this.createTitleFromSelection().slice(0, 200)
    },
    setCreateType(type) {
      this.createForm.type = type
      if (type === 'single' && this.createForm.agentIds.length > 1) {
        this.createForm.agentIds = this.createForm.agentIds.slice(0, 1)
      }
      this.syncCreateTitle()
    },
    toggleCreateAgent(agentId) {
      const checked = !this.createForm.agentIds.includes(agentId)
      if (this.createForm.type === 'single') {
        this.createForm.agentIds = checked ? [agentId] : []
        this.syncCreateTitle()
        return
      }
      if (checked) {
        this.createForm.agentIds.push(agentId)
      } else {
        this.createForm.agentIds = this.createForm.agentIds.filter(id => id !== agentId)
      }
      this.syncCreateTitle()
    },
    async handleCreate() {
      if (!this.createForm.agentIds.length) {
        this.error = '请选择 Agent'
        return
      }
      this.creating = true
      this.error = ''
      try {
        const participantIds = this.createForm.agentIds.map(id => `agent_${id}`)
        const title = (this.createForm.title || this.createTitleFromSelection()).slice(0, 200)
        const response = await createConversation({
          title: title || '新建会话',
          type: participantIds.length > 1 ? 'group' : 'single',
          participant_ids: participantIds,
        })
        if (response.code === 201 && response.data) {
          this.closeCreate()
          await this.loadConversations()
          await this.selectConversation(response.data)
        } else {
          this.error = response.message || '创建失败'
        }
      } catch (error) {
        const data = error && error.response && error.response.data
        const detail = data && (data.message || data.error || JSON.stringify(data))
        this.error = detail || (error && error.message) || '创建失败'
        console.error('[WeAgent Android] create conversation failed', {
          status: error && error.response && error.response.status,
          data,
        })
      } finally {
        this.creating = false
      }
    },
    async handleSend() {
      if (!this.currentConversation || !this.draft) return
      const content = this.draft
      this.draft = ''
      this.sending = true
      try {
        const response = await sendMessage({
          conversation_id: this.currentConversation.id,
          content,
          message_type: 'text',
        })
        if (response.code === 201) {
          await this.loadMessages(this.currentConversation.id, true)
          this.startMessageRefresh()
        }
      } finally {
        this.sending = false
      }
    },
    sortMessages(items) {
      return [...(items || [])].sort((a, b) => {
        if (a && b && b.parent_message_id && String(b.parent_message_id) === String(a.id)) return -1
        if (a && b && a.parent_message_id && String(a.parent_message_id) === String(b.id)) return 1

        const at = new Date((a && a.created_at) || 0).getTime()
        const bt = new Date((b && b.created_at) || 0).getTime()
        if (at !== bt) return at - bt

        if (a.sender_type !== b.sender_type) {
          if (a.sender_type === 'user') return -1
          if (b.sender_type === 'user') return 1
        }
        return String(a.id || '').localeCompare(String(b.id || ''))
      })
    },
    isOwnMessage(message) {
      return message && message.sender_type === 'user'
    },
    conversationParticipantTitle(conversation) {
      const participants = (conversation && conversation.participants_info) || []
      const names = participants
        .map((item, index) => this.participantName(item, item && item.participant_type === 'user' ? '我' : `Agent${index + 1}`))
        .filter(Boolean)
      return [...new Set(names)].join('、')
    },
    conversationTitle(conversation) {
      return this.conversationParticipantTitle(conversation) || (conversation && conversation.title) || '未命名会话'
    },
    conversationPreview(conversation) {
      return (conversation && conversation.last_message && conversation.last_message.content) || `${this.participantCount(conversation)} 个参与者`
    },
    participantCount(conversation) {
      return ((conversation && conversation.participants_info) || []).length
    },
    avatarParticipants(conversation) {
      if (!conversation || !conversation.participants_info) return []
      if (conversation.type === 'single') {
        return conversation.participants_info.filter(item => item.participant_type !== 'user').slice(0, 1)
      }
      return conversation.participants_info
    },
    conversationAvatars(conversation) {
      const participants = this.avatarParticipants(conversation)
      if (!participants.length) {
        return [{ text: this.firstLetter(this.conversationTitle(conversation)), color: '#2563eb' }]
      }
      const visible = participants.slice(0, 3).map((item, index) => ({
        text: this.firstLetter(this.participantName(item, `A${index + 1}`)),
        color: item.avatar_color || item.color || this.avatarPalette(index),
        url: this.participantAvatarUrl(item)
      }))
      if (participants.length > 3) {
        visible.push({ text: `+${participants.length - 3}`, color: '#98a2b3', more: true })
      }
      return visible
    },
    avatarPalette(index) {
      return ['#2563eb', '#16a34a', '#f97316', '#7c3aed', '#0891b2'][index % 5]
    },
    participantName(participant, fallback = 'Agent') {
      return (participant && (participant.name || participant.participant_name || participant.display_name || participant.username)) || fallback
    },
    participantAvatarUrl(participant) {
      return this.resolveMediaUrl(participant && (participant.avatar_url || participant.avatar || participant.image_url))
    },
    resolveMediaUrl(url) {
      if (!url) return ''
      if (/^https?:\/\//i.test(url) || /^data:/i.test(url)) return url
      return backendUrl(getCurrentServerUrl(), url)
    },
    conversationTime(conversation) {
      const raw = conversation && (conversation.updated_at || (conversation.last_message && conversation.last_message.created_at) || conversation.created_at)
      if (!raw) return ''
      const date = new Date(raw)
      if (Number.isNaN(date.getTime())) return ''
      const now = new Date()
      if (date.toDateString() === now.toDateString()) {
        return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
      }
      const yesterday = new Date(now)
      yesterday.setDate(now.getDate() - 1)
      if (date.toDateString() === yesterday.toDateString()) return '昨天'
      const month = date.getMonth() + 1
      const day = date.getDate()
      if (date.getFullYear() === now.getFullYear()) return `${month}/${day}`
      return `${date.getFullYear()}/${month}/${day}`
    },
    findParticipantForMessage(message) {
      const participants = (this.currentConversation && this.currentConversation.participants_info) || []
      return participants.find(item => (
        item.participant_type === message.sender_type &&
        String(item.participant_id || item.id || '') === String(message.sender_id || '')
      )) || null
    },
    messageSenderName(message) {
      if (this.isOwnMessage(message)) return (this.profile && (this.profile.username || this.profile.name)) || '我'
      const participant = this.findParticipantForMessage(message)
      return message.sender_name || this.participantName(participant, 'Agent')
    },
    messageAvatarUrl(message) {
      if (this.isOwnMessage(message)) {
        return this.resolveMediaUrl(this.profile && (this.profile.avatar_url || this.profile.avatar))
      }
      const participant = this.findParticipantForMessage(message)
      return this.resolveMediaUrl((participant && (participant.avatar_url || participant.avatar || participant.image_url)) || message.sender_avatar || message.avatar_url)
    },
    messageAvatarColor(message) {
      if (this.isOwnMessage(message)) return '#2563eb'
      const participant = this.findParticipantForMessage(message)
      return message.sender_color || (participant && (participant.avatar_color || participant.color)) || '#16a34a'
    },
    firstLetter(value) {
      return String(value || '?').charAt(0).toUpperCase()
    },
    messageElements(message) {
      const elements = message && message.elements
      if (Array.isArray(elements)) return elements
      if (typeof elements === 'string' && elements.trim()) {
        try {
          const parsed = JSON.parse(elements)
          return Array.isArray(parsed) ? parsed : []
        } catch (error) {
          return []
        }
      }
      return []
    },
    progressElements(message) {
      return this.messageElements(message).filter(el => el && el.type === 'progress')
    },
    currentProgress(message) {
      const list = this.progressElements(message)
      return list.length ? list[list.length - 1] : null
    },
    contentElements(message) {
      return this.messageElements(message).filter(el => ['text', 'summary', 'result', 'error'].includes(el && el.type))
    },
    artifactElements(message) {
      return this.messageElements(message).filter(el => ['code', 'table', 'image', 'file', 'service'].includes(el && el.type))
    },
    normalizeTable(el) {
      const data = this.elementData(el)
      const rows = Array.isArray(data.rows) ? data.rows : []
      if (rows.length && !Array.isArray(rows[0])) {
        const headers = Array.isArray(data.headers) && data.headers.length ? data.headers : Object.keys(rows[0] || {})
        return rows.map(row => {
          const item = {}
          headers.forEach((header, index) => {
            item[`col${index}`] = row[header] !== undefined ? row[header] : ''
          })
          return item
        })
      }
      return rows.map(row => {
        const item = {}
        ;(Array.isArray(row) ? row : []).forEach((value, index) => {
          item[`col${index}`] = value
        })
        return item
      })
    },
    tableHeaders(el) {
      const data = this.elementData(el)
      if (Array.isArray(data.headers) && data.headers.length) return data.headers
      const rows = this.normalizeTable(el)
      return rows[0] ? Object.keys(rows[0]).map((_, index) => `列 ${index + 1}`) : []
    },
    displayTextContent(message) {
      const content = String((message && message.content) || '').trim()
      if (!content) return ''
      if (this.contentElements(message).some(el => this.elementContent(el).trim() === content)) return ''
      if (content === String((message && message.raw_output) || '').trim()) return ''
      return content
    },
    visibleRawOutput(message) {
      if (!message || message.sender_type !== 'agent') return ''
      const raw = String(message.raw_output || '').trim()
      if (!raw) return ''
      if (raw === String(message.content || '').trim()) return ''
      return raw
    },
    emptyMessage(message) {
      return !this.displayTextContent(message) && !this.messageElements(message).length && !this.visibleRawOutput(message)
    },
    renderElementSummary(message) {
      const el = this.messageElements(message)[0]
      return el ? this.elementLabel(el) : ''
    },
    elementLabel(el) {
      const data = (el && el.data) || {}
      return data.title || data.name || el.content || el.type || '产物'
    },
    elementData(el) {
      return (el && el.data) || {}
    },
    elementContent(el) {
      if (!el) return ''
      if (el.content !== undefined && el.content !== null) return String(el.content)
      const data = this.elementData(el)
      return String(data.content || data.message || data.text || data.path || data.url || data.name || '')
    },
    elementTitle(el) {
      const data = this.elementData(el)
      const map = {
        text: '文本',
        summary: '完成摘要',
        result: '执行结果',
        error: '错误',
        progress: '进度',
        code: '代码产物',
        table: '表格产物',
        image: '图片产物',
        file: '文件产物',
        service: '服务'
      }
      return data.title || data.name || data.filename || map[el && el.type] || '信息'
    },
    artifactUrl(el) {
      const data = this.elementData(el)
      return this.resolveMediaUrl(data.url || data.src || this.elementContent(el))
    },
    artifactMeta(el) {
      const data = this.elementData(el)
      if (el.type === 'code') return data.language || data.filename || 'code'
      if (el.type === 'table') return `${this.tableHeaders(el).length || 0} 列`
      if (el.type === 'image') return data.path || data.url || 'image'
      if (el.type === 'service') return data.url || data.port || 'service'
      return data.path || data.url || data.size || el.type || ''
    },
    isFileArtifact(el) {
      return el && (el.type === 'file' || el.type === 'image')
    },
    artifactFilePayload(el) {
      const data = this.elementData(el)
      const raw = data.path || data.file_path || data.filePath || data.file || data.url || data.src || this.elementContent(el)
      const path = this.normalizeArtifactFilePath(raw)
      return {
        path,
        raw,
        name: data.name || data.filename || data.title || this.fileNameFromPath(path || raw),
        agent_id: data.agent_id || data.agentId || data.owner_agent_id || data.ownerAgentId || '',
      }
    },
    normalizeArtifactFilePath(value) {
      let path = String(value || '').trim()
      if (!path) return ''
      try {
        if (/^https?:\/\//i.test(path)) {
          path = decodeURIComponent(new URL(path).pathname)
        }
      } catch (error) {
        // Keep the original value when URL parsing fails.
      }
      const workspaceIndex = path.indexOf('/workspace/')
      if (workspaceIndex >= 0) return path.slice(workspaceIndex)
      if (path.indexOf('workspace/') === 0) return `/${path}`
      return path
    },
    fileNameFromPath(value) {
      const parts = String(value || '').split(/[\\/]/).filter(Boolean)
      return parts.length ? parts[parts.length - 1] : String(value || '')
    },
    fileIconText(el) {
      const value = String(this.artifactFilePayload(el).name || '').toLowerCase()
      if (/\.(png|jpe?g|gif|webp|svg)$/.test(value)) return 'IMG'
      if (/\.(html?|pdf)$/.test(value)) return value.endsWith('.pdf') ? 'PDF' : 'HTML'
      if (/\.(md|txt|json|csv|js|vue|ts|css|py|java|yaml|yml)$/.test(value)) return 'TXT'
      return 'FILE'
    },
    currentSessionId() {
      return (this.currentConversation && (this.currentConversation.sandbox_session_id || this.currentConversation.id)) || ''
    },
    inferAgentIdFromFilePath(filePath) {
      const match = String(filePath || '').match(/\/workspace\/agents\/([^/]+)/)
      if (!match) return ''
      const workspaceName = decodeURIComponent(match[1])
      const participants = (this.currentConversation && this.currentConversation.participants_info) || []
      const agent = participants.find(item => {
        const names = [item.workspace_name, item.name, item.participant_name, item.display_name]
          .filter(Boolean)
          .map(value => String(value))
        return names.includes(workspaceName)
      })
      return agent ? (agent.agent_id || agent.participant_id || agent.id || '') : ''
    },
    async openArtifactFile(el) {
      const payload = this.artifactFilePayload(el)
      const filePath = payload.path
      if (!filePath || !this.currentSessionId()) return
      this.previewVisible = true
      this.previewLoading = true
      this.previewTitle = payload.name
      this.previewPath = filePath
      this.previewType = this.previewTypeForPath(filePath)
      this.previewContent = ''
      this.previewHtml = ''
      this.previewUrl = ''
      try {
        const rawUrl = await getWorkspaceFileUrl(this.currentSessionId(), filePath)
        if (this.previewType === 'html') {
          this.previewUrl = rawUrl
          const html = await this.fetchTextFile(rawUrl)
          this.previewHtml = await this.buildHtmlPreviewDocument(html, rawUrl)
          return
        }
        if (['pdf', 'image'].includes(this.previewType)) {
          this.previewUrl = rawUrl
          return
        }
        this.previewUrl = rawUrl
        this.previewContent = await this.fetchTextFile(rawUrl)
      } catch (error) {
        this.previewContent = [
          '加载失败',
          this.previewUrl ? `URL: ${this.previewUrl}` : '',
          error && error.message ? `错误: ${error.message}` : '',
        ].filter(Boolean).join('\n')
      } finally {
        this.previewLoading = false
      }
    },
    async fetchTextFile(url) {
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      return response.text()
    },
    previewTypeForPath(path) {
      const value = String(path || '').toLowerCase()
      if (/\.(html?|htm)$/.test(value)) return 'html'
      if (/\.pdf$/.test(value)) return 'pdf'
      if (/\.(png|jpe?g|gif|webp|svg)$/.test(value)) return 'image'
      if (/\.(md|markdown)$/.test(value)) return 'markdown'
      return 'text'
    },
    closePreview() {
      this.previewVisible = false
      this.previewLoading = false
      this.previewTitle = ''
      this.previewPath = ''
      this.previewType = 'text'
      this.previewContent = ''
      this.previewHtml = ''
      this.previewUrl = ''
    },
    async buildHtmlPreviewDocument(html, rawUrl) {
      const baseHref = this.htmlPreviewBaseUrl(rawUrl)
      const baseTag = `<base href="${this.escapeHtml(baseHref)}">`
      let next = String(html || '').replace(/<base\s[^>]*>/i, '')
      next = await this.inlineHtmlStylesheets(next, baseHref)
      if (/<head[^>]*>/i.test(next)) {
        next = next.replace(/<head[^>]*>/i, match => `${match}${baseTag}`)
      } else {
        next = `${baseTag}${next}`
      }
      return next
    },
    async inlineHtmlStylesheets(html, baseHref) {
      const linkRegex = /<link\b[^>]*>/gi
      let result = ''
      let lastIndex = 0
      let match

      while ((match = linkRegex.exec(html)) !== null) {
        const tag = match[0]
        result += html.slice(lastIndex, match.index)
        lastIndex = linkRegex.lastIndex

        const rel = this.htmlAttribute(tag, 'rel')
        const href = this.htmlAttribute(tag, 'href')
        if (!href || !/\bstylesheet\b/i.test(rel || '')) {
          result += tag
          continue
        }

        try {
          const cssUrl = this.resolvePreviewAssetUrl(href, baseHref)
          const css = await this.fetchTextFile(cssUrl)
          const rewritten = this.rewriteCssUrls(css, cssUrl).replace(/<\/style/gi, '<\\/style')
          result += `<style data-weagent-inline-css="${this.escapeHtml(cssUrl)}">\n${rewritten}\n</style>`
        } catch (error) {
          result += tag
        }
      }

      return result + html.slice(lastIndex)
    },
    htmlAttribute(tag, name) {
      const pattern = new RegExp(`${name}\\s*=\\s*(['"])(.*?)\\1`, 'i')
      const match = String(tag || '').match(pattern)
      return match ? match[2] : ''
    },
    resolvePreviewAssetUrl(value, baseHref) {
      const raw = String(value || '').trim()
      if (!raw || /^(?:https?:|data:|blob:|mailto:|tel:|#)/i.test(raw)) return raw
      try {
        const base = new URL(baseHref)
        if (raw.startsWith('/api/')) {
          return `${base.origin}${raw}`
        }
        if (raw.startsWith('/')) {
          return new URL(raw.replace(/^\/+/, ''), baseHref).toString()
        }
        return new URL(raw, baseHref).toString()
      } catch (error) {
        return raw
      }
    },
    rewriteCssUrls(css, cssUrl) {
      return String(css || '')
        .replace(/url\(\s*(['"]?)(?!data:|blob:|https?:|#)([^'")]+)\1\s*\)/gi, (match, quote, url) => {
          return `url(${quote || ''}${this.resolvePreviewAssetUrl(url, this.htmlPreviewBaseUrl(cssUrl))}${quote || ''})`
        })
        .replace(/@import\s+(['"])(?!https?:|data:|blob:)([^'"]+)\1/gi, (match, quote, url) => {
          return `@import ${quote}${this.resolvePreviewAssetUrl(url, this.htmlPreviewBaseUrl(cssUrl))}${quote}`
        })
    },
    htmlPreviewBaseUrl(rawUrl) {
      try {
        const url = new URL(rawUrl)
        url.pathname = url.pathname.replace(/\/[^/]*$/, '/')
        url.search = ''
        url.hash = ''
        return url.toString()
      } catch (error) {
        return rawUrl
      }
    },
    renderMarkdown(text) {
      const source = String(text || '')
      const escaped = this.escapeHtml(source)
      const blocks = this.renderMarkdownTables(escaped)
      return blocks
        .replace(/```([\s\S]*?)```/g, '<pre class="md-code"><code>$1</code></pre>')
        .replace(/^### (.*)$/gm, '<h4>$1</h4>')
        .replace(/^## (.*)$/gm, '<h3>$1</h3>')
        .replace(/^# (.*)$/gm, '<h2>$1</h2>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>')
    },
    renderMarkdownTables(text) {
      const lines = String(text || '').split('\n')
      const out = []
      for (let i = 0; i < lines.length; i += 1) {
        if (this.isMarkdownTableStart(lines, i)) {
          const headers = this.splitMarkdownRow(lines[i])
          i += 2
          const rows = []
          while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) {
            rows.push(this.splitMarkdownRow(lines[i]))
            i += 1
          }
          i -= 1
          out.push(this.renderMarkdownTable(headers, rows))
        } else {
          out.push(lines[i])
        }
      }
      return out.join('\n')
    },
    isMarkdownTableStart(lines, index) {
      return /^\s*\|.*\|\s*$/.test(lines[index] || '') && /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[index + 1] || '')
    },
    splitMarkdownRow(line) {
      return String(line || '').trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim())
    },
    renderMarkdownTable(headers, rows) {
      const head = headers.map(header => `<th>${header}</th>`).join('')
      const body = rows.map(row => `<tr>${headers.map((_, index) => `<td>${row[index] || ''}</td>`).join('')}</tr>`).join('')
      return `<div class="md-table-wrap"><table class="md-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`
    },
    escapeHtml(value) {
      return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
    },
    scrollToBottom() {
      const el = this.$refs.messageList
      if (el) el.scrollTop = el.scrollHeight
    },
    scrollToLatestMessage() {
      this.$nextTick(() => {
        this.scrollToBottom()
        setTimeout(() => this.scrollToBottom(), 80)
        setTimeout(() => this.scrollToBottom(), 220)
      })
    },
  },
}
</script>

<style scoped>
.android-conv {
  min-height: 100vh;
  color: #172033;
  background: #f5f7fa;
  font-size: 14px;
}

.android-conv button,
.android-conv input {
  font: inherit;
}

.android-conv-list-page {
  min-height: 100vh;
  padding-bottom: calc(70px + env(safe-area-inset-bottom));
}

.android-conv-list-header {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: calc(10px + env(safe-area-inset-top)) 14px 10px;
  background: #ffffff;
  border-bottom: 1px solid #e3e8ef;
}

.android-conv-list-header span,
.android-chat-title span {
  display: block;
  color: #667085;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.2;
}

.android-conv-list-header h1,
.android-chat-title h1 {
  margin: 2px 0 0;
  overflow: hidden;
  color: #172033;
  font-size: 20px;
  font-weight: 750;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.android-icon-btn,
.android-chat-edge-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
}

.android-icon-btn {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  color: #ffffff;
  background: #2563eb;
}

.android-icon-btn svg,
.android-chat-edge-btn svg,
.android-chat-input svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.android-conv-list {
  padding: 12px;
}

.android-empty {
  margin: 16px 0;
  padding: 28px 16px;
  color: #667085;
  text-align: center;
  background: #ffffff;
  border: 1px dashed #cfd7e3;
  border-radius: 8px;
}

.android-conv-card {
  display: flex;
  width: 100%;
  min-height: 72px;
  align-items: center;
  gap: 12px;
  padding: 10px 11px;
  margin-bottom: 8px;
  color: inherit;
  text-align: left;
  background: #ffffff;
  border: 1px solid #e3e8ef;
  border-radius: 8px;
}

.android-composite-avatar {
  position: relative;
  display: block;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  overflow: hidden;
  background: #e4e9f2;
  border-radius: 10px;
}

.android-composite-item {
  position: absolute;
  top: 1px;
  left: 1px;
  display: inline-flex;
  width: 19px;
  height: 19px;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: #ffffff;
  border: 1px solid #ffffff;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 800;
}

.android-composite-item:only-child {
  top: 0;
  left: 0;
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 10px;
  font-size: 15px;
}

.android-composite-item:nth-child(2) {
  right: 1px;
  left: auto;
}

.android-composite-item:nth-child(2):last-child {
  top: auto;
  right: 1px;
  bottom: 1px;
}

.android-composite-item:nth-child(3) {
  top: auto;
  bottom: 1px;
  left: 1px;
}

.android-composite-item:nth-child(4) {
  top: auto;
  right: 1px;
  bottom: 1px;
  left: auto;
}

.android-composite-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.android-conv-card-main {
  min-width: 0;
  flex: 1;
}

.android-conv-card-top {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
}

.android-conv-card-top strong {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  color: #172033;
  font-size: 15px;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.android-conv-card-top time {
  flex: 0 0 auto;
  color: #98a2b3;
  font-size: 11px;
}

.android-conv-card-preview {
  display: block;
  margin-top: 5px;
  overflow: hidden;
  color: #667085;
  font-size: 12px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.android-chat-page {
  min-height: 100vh;
  padding-top: calc(60px + env(safe-area-inset-top));
  padding-bottom: calc(58px + env(safe-area-inset-bottom));
  background: #f5f7fa;
}

.android-chat-header {
  position: fixed;
  top: 0;
  right: 0;
  left: 0;
  z-index: 30;
  display: grid;
  grid-template-columns: 50px minmax(0, 1fr) 50px;
  align-items: center;
  width: 100vw;
  min-height: calc(60px + env(safe-area-inset-top));
  padding-top: env(safe-area-inset-top);
  background: #ffffff;
  border-bottom: 1px solid #e3e8ef;
}

.android-chat-edge-btn {
  width: 50px;
  height: 50px;
  color: #344054;
  background: transparent;
}

.android-chat-title {
  min-width: 0;
  text-align: center;
}

.android-message-list {
  height: calc(100vh - 118px - env(safe-area-inset-top) - env(safe-area-inset-bottom));
  overflow-y: auto;
  padding: 12px;
}

.android-message-row {
  display: flex;
  width: 100%;
  gap: 8px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.android-message-row.user {
  flex-direction: row-reverse;
}

.android-message-avatar {
  display: inline-flex;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: #ffffff;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 800;
}

.android-message-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.android-message-stack {
  display: flex;
  max-width: calc(100vw - 92px);
  flex-direction: column;
  align-items: flex-start;
}

.android-message-row.user .android-message-stack {
  align-items: flex-end;
}

.android-message-name {
  margin-bottom: 4px;
  color: #667085;
  font-size: 11px;
  font-weight: 650;
}

.android-message-bubble {
  width: fit-content;
  max-width: 100%;
  padding: 9px 11px;
  color: #172033;
  background: #ffffff;
  border: 1px solid #e3e8ef;
  border-radius: 8px;
}

.android-message-row.user .android-message-bubble {
  color: #ffffff;
  background: #2563eb;
  border-color: #2563eb;
}

.android-message-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
  line-height: 1.58;
}

.android-message-text.muted {
  color: #667085;
}

.android-progress-line,
.android-element-card,
.android-artifact-card {
  margin-top: 8px;
  padding: 8px;
  color: #344054;
  background: #f8fafc;
  border: 1px solid #e3e8ef;
  border-radius: 8px;
}

.android-progress-line {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 0;
  margin-bottom: 8px;
  font-size: 12px;
}

.android-progress-line .dot {
  width: 8px;
  height: 8px;
  flex: 0 0 8px;
  background: #2563eb;
  border-radius: 50%;
}

.android-progress-line .dot.done {
  background: #16a34a;
}

.android-progress-line .dot.error {
  background: #d92d20;
}

.android-element-card.type-error {
  background: #fff1f0;
  border-color: #fecdca;
}

.android-element-card strong,
.android-artifact-card strong {
  display: block;
  margin-bottom: 4px;
  color: #172033;
  font-size: 12px;
  font-weight: 750;
}

.android-element-card p,
.android-artifact-card p {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.55;
}

.android-artifact-group {
  margin-top: 10px;
}

.android-section-label {
  display: block;
  margin-bottom: 6px;
  color: #667085;
  font-size: 12px;
  font-weight: 750;
}

.android-artifact-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e3e8ef;
}

.android-artifact-head strong {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: #172033;
  font-size: 13px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.android-artifact-card.artifact-file {
  padding: 0;
  background: transparent;
  border: 0;
}

.android-artifact-card.artifact-table {
  padding: 8px;
  background: #ffffff;
}

.android-artifact-card.artifact-code {
  padding: 0;
  background: transparent;
  border: 0;
}

.android-artifact-head.table {
  align-items: flex-start;
  margin: 0 0 8px;
  padding: 8px 9px;
  background: #eef4ff;
  border: 1px solid #dbeafe;
  border-radius: 8px;
}

.android-artifact-head.table strong {
  color: #175cd3;
  font-size: 13px;
}

.android-artifact-head.table small {
  color: #175cd3;
  background: #ffffff;
}

.android-artifact-card small {
  display: inline-flex;
  flex: 0 0 auto;
  max-width: 45%;
  margin: 0;
  padding: 2px 6px;
  overflow: hidden;
  color: #475467;
  background: #eef2f7;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.android-artifact-card pre,
.android-raw pre {
  max-height: 220px;
  overflow: auto;
  margin: 0;
  padding: 8px;
  color: #d1e7ff;
  background: #111827;
  border-radius: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 11px;
  line-height: 1.5;
}

.android-artifact-card img {
  display: block;
  max-width: 100%;
  max-height: 220px;
  object-fit: contain;
  border-radius: 8px;
}

.android-artifact-card.openable {
  cursor: pointer;
}

.android-table-scroll,
.md-table-wrap {
  max-width: 100%;
  overflow-x: auto;
}

.android-artifact-table,
.md-table {
  width: 100%;
  min-width: 420px;
  border-collapse: collapse;
  background: #ffffff;
  font-size: 11px;
}

.android-artifact-table th,
.android-artifact-table td,
.md-table th,
.md-table td {
  padding: 7px 8px;
  border: 1px solid #e3e8ef;
  text-align: left;
  vertical-align: top;
}

.android-artifact-table th,
.md-table th {
  color: #344054;
  background: #f1f5f9;
  font-weight: 750;
}

.android-file-artifact {
  width: 100%;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 9px;
  color: inherit;
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  text-align: left;
}

.android-file-artifact .file-badge {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  color: #175cd3;
  background: #eff6ff;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 800;
}

.android-file-artifact .file-info {
  min-width: 0;
}

.android-file-artifact strong,
.android-file-artifact small {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.android-file-artifact strong {
  display: block;
  margin: 0;
  color: #172033;
  font-size: 13px;
  font-weight: 750;
}

.android-file-artifact small {
  margin-top: 3px;
  padding: 0;
  color: #667085;
  background: transparent;
  border-radius: 0;
  font-size: 11px;
  font-weight: 500;
}

.android-file-artifact .file-open {
  flex: 0 0 auto;
  padding: 4px 7px;
  color: #175cd3;
  background: #eff6ff;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
}

.android-rendered {
  color: #344054;
  font-size: 12px;
  line-height: 1.6;
  word-break: break-word;
}

.android-rendered :deep(h2),
.android-rendered :deep(h3),
.android-rendered :deep(h4) {
  margin: 8px 0 5px;
  color: #172033;
  line-height: 1.3;
}

.android-rendered :deep(code) {
  padding: 1px 4px;
  background: #eef2f7;
  border-radius: 4px;
}

.android-rendered :deep(.md-code) {
  max-height: 220px;
  overflow: auto;
  padding: 8px;
  color: #d1e7ff;
  background: #111827;
  border-radius: 8px;
  white-space: pre-wrap;
}

.android-rendered :deep(.md-code code) {
  padding: 0;
  background: transparent;
  border-radius: 0;
}

.android-preview-backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: flex-end;
  background: rgba(15, 23, 42, 0.42);
}

.android-preview-panel {
  width: 100%;
  max-height: 86vh;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px 12px 0 0;
}

.android-preview-panel header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border-bottom: 1px solid #e3e8ef;
}

.android-preview-panel header h2 {
  margin: 2px 0;
  font-size: 16px;
}

.android-preview-panel header p,
.android-preview-panel header span {
  margin: 0;
  color: #667085;
  font-size: 12px;
  word-break: break-all;
}

.android-preview-panel header button {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 8px;
  background: #f2f4f7;
  color: #475467;
  font-size: 20px;
}

.android-preview-body {
  min-height: 260px;
  overflow: auto;
  padding: 12px;
}

.android-preview-frame {
  width: 100%;
  height: 64vh;
  border: 0;
  background: #ffffff;
}

.android-preview-image {
  display: block;
  max-width: 100%;
  margin: 0 auto;
  border-radius: 8px;
}

.android-preview-code {
  min-height: 240px;
  margin: 0;
  padding: 10px;
  color: #d1e7ff;
  background: #111827;
  border-radius: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.55;
}

.android-preview-empty {
  margin: 36px 0;
  color: #667085;
  text-align: center;
}

.android-raw {
  margin-top: 8px;
}

.android-raw summary {
  color: #667085;
  font-size: 12px;
  font-weight: 750;
}

.android-chat-input {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 30;
  display: flex;
  gap: 8px;
  width: 100vw;
  padding: 8px 10px calc(8px + env(safe-area-inset-bottom));
  background: #ffffff;
  border-top: 1px solid #e3e8ef;
}

.android-chat-input input {
  min-width: 0;
  min-height: 42px;
  flex: 1;
  padding: 0 12px;
  color: #172033;
  background: #f8fafc;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  outline: none;
}

.android-chat-input input:focus {
  background: #ffffff;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}

.android-chat-input button {
  display: inline-flex;
  width: 46px;
  height: 42px;
  flex: 0 0 46px;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  background: #2563eb;
  border: 0;
  border-radius: 8px;
}

.android-chat-input button:disabled {
  color: #98a2b3;
  background: #edf1f7;
}

.android-sheet-mask {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: flex-end;
  background: rgba(15, 23, 42, 0.38);
}

.android-create-sheet {
  width: 100%;
  max-height: 88vh;
  overflow-y: auto;
  padding: 14px 14px calc(14px + env(safe-area-inset-bottom));
  background: #ffffff;
  border-radius: 8px 8px 0 0;
}

.android-create-sheet header,
.android-create-sheet footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.android-create-sheet header {
  padding-bottom: 10px;
  margin-bottom: 12px;
  border-bottom: 1px solid #e3e8ef;
}

.android-create-sheet h2 {
  margin: 0;
  font-size: 17px;
}

.android-create-sheet header button {
  width: 32px;
  height: 32px;
  color: #475467;
  background: #eef2f6;
  border: 0;
  border-radius: 8px;
}

.android-field {
  display: block;
  margin-bottom: 11px;
}

.android-field span {
  display: block;
  margin-bottom: 5px;
  color: #475467;
  font-size: 12px;
  font-weight: 650;
}

.android-field input {
  width: 100%;
  min-height: 40px;
  padding: 0 10px;
  color: #172033;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  outline: none;
}

.android-type-toggle {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 3px;
  margin-bottom: 10px;
  background: #edf1f7;
  border: 1px solid #e3e8ef;
  border-radius: 8px;
}

.android-type-toggle button {
  min-height: 34px;
  color: #667085;
  background: transparent;
  border: 0;
  border-radius: 6px;
  font-weight: 700;
}

.android-type-toggle button.active {
  color: #2563eb;
  background: #ffffff;
}

.android-agent-picker {
  overflow: hidden;
  border: 1px solid #e3e8ef;
  border-radius: 8px;
}

.android-agent-pick {
  display: flex;
  width: 100%;
  min-height: 48px;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  color: #172033;
  text-align: left;
  background: #ffffff;
  border: 0;
  border-bottom: 1px solid #eef2f6;
}

.android-agent-pick:last-child {
  border-bottom: 0;
}

.android-agent-pick.active {
  background: #eef4ff;
}

.android-agent-pick .check {
  display: inline-flex;
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  background: #d0d5dd;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 800;
}

.android-agent-pick.active .check {
  background: #2563eb;
}

.android-agent-pick .mini {
  display: inline-flex;
  width: 30px;
  height: 30px;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  border-radius: 8px;
  font-weight: 800;
}

.android-agent-pick .name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.android-error {
  margin: 10px 0 0;
  color: #d92d20;
  font-size: 12px;
}

.android-create-sheet footer {
  position: sticky;
  bottom: 0;
  padding-top: 12px;
  background: #ffffff;
}

.android-create-sheet footer button {
  min-height: 38px;
  padding: 0 14px;
  border: 0;
  border-radius: 8px;
  font-weight: 700;
}

.android-create-sheet footer .secondary {
  color: #344054;
  background: #eef2f6;
}

.android-create-sheet footer .primary {
  color: #ffffff;
  background: #2563eb;
}

.android-create-sheet footer .primary:disabled {
  opacity: 0.55;
}
</style>
