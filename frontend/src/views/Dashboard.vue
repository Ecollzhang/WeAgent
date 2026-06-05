<template>
  <div class="dashboard">
    <!-- 第一栏：全局侧边导航栏 -->
    <AppSidebar />

    <!-- 第二栏：会话列表栏 -->
    <div class="conversation-panel">
      <ConversationList
        :conversations="conversations"
        :currentId="currentConversation?.id"
        :loading="convLoading"
        :userAvatar="userAvatar"
        @select="handleSelectConversation"
        @create-conversation="showCreateDialog = true"
      />
    </div>

    <!-- 第三栏：主聊天内容区 -->
    <div class="chat-panel">
      <ChatWindow
        :conversation="currentConversation"
        :messages="currentMessages"
        :userId="userId"
        :agentResponding="isAgentResponding"
        :sessionAgents="currentSessionAgents"
        @send-message="handleSendMessage"
        @pin-message="handlePinMessage"
        @delete-conversation="handleDeleteConversation"
        @search-messages="handleSearchMessages"
        @open-attachment="handleOpenAttachment"
        @toggle-star="handleToggleStar"
        @open-history="handleOpenHistory"
        @stop-agent="handleStopAgent"
        @open-workspace="handleOpenWorkspace"
        @open-file="handleOpenFile"
        @open-attachments="handleOpenAttachments"
        @open-services="handleOpenServices"
      />
    </div>

    <ArtifactWorkbench
      :visible.sync="artifactWorkbenchVisible"
      :artifact="currentWorkbenchArtifact"
      :session-id="currentSessionId"
    />

    <el-dialog
      :title="previewTitle"
      :visible.sync="previewVisible"
      width="78%"
      top="5vh"
      custom-class="file-preview-dialog"
    >
      <div v-loading="previewLoading" class="file-browser-body">
        <div class="file-tree-panel">
          <div class="file-scope-tabs">
            <el-button size="mini" :type="fileScope === 'workspace' ? 'primary' : 'text'" @click="switchFileScope('workspace')">全部</el-button>
            <el-button size="mini" :type="fileScope === 'shared' ? 'primary' : 'text'" @click="switchFileScope('shared')">公共</el-button>
            <el-dropdown trigger="click" @command="switchFileScope">
              <el-button size="mini" :type="fileScope.startsWith('agent:') ? 'primary' : 'text'">
                Agent<i class="el-icon-arrow-down el-icon--right" />
              </el-button>
              <el-dropdown-menu slot="dropdown">
                <el-dropdown-item
                  v-for="ag in currentSessionAgents"
                  :key="ag.agent_id"
                  :command="`agent:${ag.agent_id}`"
                >
                  {{ ag.role || ag.name || ag.agent_id }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </el-dropdown>
          </div>
          <div class="file-tree-header">
            <span>{{ fileTreeRoot }}</span>
            <el-button size="mini" type="text" @click="loadFileTree(fileTreeRoot)">刷新</el-button>
          </div>
          <el-tree
            :data="fileTreeData"
            :props="fileTreeProps"
            node-key="path"
            default-expand-all
            @node-click="handleFileNodeClick"
          >
            <span slot-scope="{ node, data }" class="file-tree-node">
              <i :class="data.type === 'directory' ? 'el-icon-folder' : getFileIcon(data.path)" />
              <span>{{ node.label }}</span>
              <span v-if="data.size" class="tree-file-size">{{ formatFileSize(data.size) }}</span>
            </span>
          </el-tree>
        </div>
        <div class="file-preview-panel">
          <div class="file-preview-toolbar" v-if="selectedFilePath">
            <span class="selected-file-path">{{ selectedFilePath }}</span>
            <el-button size="mini" type="text" @click="openContainingFolder(selectedFilePath)">所在目录</el-button>
            <el-button size="mini" type="text" @click="copyFilePath(selectedFilePath)">复制路径</el-button>
            <el-button size="mini" type="text" @click="downloadFile(selectedFilePath)">下载</el-button>
            <el-button v-if="isHtmlFile(selectedFilePath)" size="mini" type="text" @click="openWorkspaceFile(selectedFilePath)">打开 HTML</el-button>
          </div>
          <div v-else class="file-preview-empty">
            <i class="el-icon-folder-opened" />
            <span>选择左侧文件查看内容</span>
          </div>
          <div v-if="previewType === 'image'" class="image-preview-wrap">
            <img :src="previewUrl" class="image-preview" />
          </div>
          <iframe v-else-if="previewType === 'html'" :src="previewUrl" class="html-preview" />
          <iframe v-else-if="previewType === 'pdf'" :src="previewUrl" class="pdf-preview" />
          <div v-else-if="previewType === 'binary'" class="binary-preview">
            <i class="el-icon-document" />
            <p>该文件为二进制或不支持内嵌预览，请下载查看。</p>
          </div>
          <pre v-else class="file-preview-content">{{ previewContent }}</pre>
        </div>
      </div>
    </el-dialog>

    <el-drawer
      title="上传文件"
      :visible.sync="attachmentsVisible"
      direction="rtl"
      size="360px"
      custom-class="attachments-drawer"
    >
      <div class="attachments-body">
        <el-upload
          drag
          action=""
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleAttachmentPicked"
          class="attachment-upload"
        >
          <i class="el-icon-upload"></i>
          <div class="el-upload__text">拖拽文件到这里，或点击选择</div>
          <div class="el-upload__tip" slot="tip">支持图片、PDF、代码、文本等文件</div>
        </el-upload>

        <div class="attachment-list-header">
          <span>已上传</span>
          <el-button size="mini" type="text" @click="loadAttachments">刷新</el-button>
        </div>

        <div v-loading="attachmentsLoading" class="attachment-list">
          <div v-if="attachments.length === 0" class="attachment-empty">暂无上传文件</div>
          <div v-for="file in attachments" :key="file.path" class="attachment-item">
            <i :class="getFileIcon(file.path)"></i>
            <div class="attachment-info">
              <button class="attachment-name" @click="handleOpenFile(file)">{{ file.name }}</button>
              <span>{{ formatFileSize(file.size) }}</span>
            </div>
            <el-button size="mini" type="text" icon="el-icon-delete" @click="handleDeleteAttachment(file)"></el-button>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 新建会话对话框 -->
    <el-drawer
      title="预览服务"
      :visible.sync="servicesVisible"
      direction="rtl"
      size="420px"
      custom-class="services-drawer"
    >
      <div class="services-body">
        <el-form label-position="top" size="small">
          <el-form-item label="Agent">
            <el-select v-model="serviceForm.agent_id" placeholder="选择 Agent" style="width: 100%" @change="syncServiceCwd">
              <el-option
                v-for="ag in currentSessionAgents"
                :key="ag.agent_id"
                :label="ag.name || ag.role || ag.agent_id"
                :value="ag.agent_id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="端口">
            <el-select v-model="serviceForm.port" style="width: 100%" @change="syncServiceCommand">
              <el-option label="Vite / Vue3: 5173" :value="5173" />
              <el-option label="Vue CLI: 8081" :value="8081" />
              <el-option label="React / Node: 3000" :value="3000" />
              <el-option label="静态文件: 8000" :value="8000" />
              <el-option label="其他: 9000" :value="9000" />
            </el-select>
          </el-form-item>
          <el-form-item label="工作目录">
            <el-input v-model="serviceForm.cwd" />
          </el-form-item>
          <el-form-item label="启动命令">
            <el-input v-model="serviceForm.command" type="textarea" :rows="3" />
          </el-form-item>
          <el-button type="primary" size="small" :loading="serviceStarting" @click="handleStartService">
            启动服务
          </el-button>
          <el-button size="small" @click="loadServices">刷新</el-button>
        </el-form>

        <div class="service-tip">
          Vue/Vite 服务必须监听 0.0.0.0，否则只能在容器内访问。
        </div>

        <div class="service-list" v-loading="servicesLoading">
          <div v-if="services.length === 0" class="service-empty">暂无服务</div>
          <div v-for="svc in services" :key="svc.port" class="service-item">
            <div class="service-main">
              <div class="service-title">
                <span>容器端口 {{ svc.port }}</span>
                <el-tag size="mini" :type="svc.status === 'open' || svc.running ? 'success' : 'info'">
                  {{ svc.status || (svc.running ? 'open' : 'closed') }}
                </el-tag>
              </div>
              <a v-if="svc.url" :href="svc.url" target="_blank" rel="noopener" class="service-url">
                {{ svc.url }}
              </a>
              <div v-if="svc.command" class="service-command">{{ svc.command }}</div>
            </div>
            <el-button v-if="svc.url" size="mini" type="text" @click="copyServiceUrl(svc.url)">复制</el-button>
          </div>
        </div>
      </div>
    </el-drawer>

    <el-dialog title="新建会话" :visible.sync="showCreateDialog" width="500px" custom-class="create-conv-dialog" top="8vh">
      <div class="create-conv-body">
        <div class="conv-field">
          <label class="field-label">会话标题</label>
          <el-input
            v-model="newConversation.title"
            placeholder="自动生成标题"
            size="medium"
          >
            <i slot="prefix" class="el-icon-edit-outline"></i>
          </el-input>
        </div>

        <div class="conv-field">
          <label class="field-label">选择 Agent <span class="field-hint">（点击复选框选择，支持多选）</span></label>
          <div class="agent-tree-wrapper" v-loading="treeLoading">
            <el-tree
              ref="agentTree"
              :data="agentTreeData"
              :props="treeProps"
              show-checkbox
              node-key="id"
              default-expand-all
              highlight-current
              @check-change="handleTreeCheckChange"
              class="agent-tree"
            >
              <span class="tree-node" slot-scope="{ node, data }">
                <span v-if="data.isLeaf" class="node-agent">
                  <span class="node-avatar" :style="{ background: data.agentColor || '#4080ff' }">
                    <img v-if="data.agentAvatar" :src="data.agentAvatar" class="node-avatar-img" />
                    <span v-else class="node-avatar-letter">{{ data.label?.charAt(0) || '?' }}</span>
                  </span>
                  <span class="node-name">{{ data.label }}</span>
                  <span class="node-badge">{{ data.adapterLabel }}</span>
                </span>
                <span v-else class="node-category">
                  <i :class="data.icon || 'el-icon-folder-opened'"></i>
                  <span>{{ data.label }}</span>
                  <span class="node-count">{{ data.children?.length || 0 }}个Agent</span>
                </span>
              </span>
            </el-tree>
          </div>
        </div>

        <div class="conv-preview" v-if="selectedAgentList.length > 0">
          <div class="preview-avatars">
            <!-- 用户头像 -->
            <div class="preview-avatar user-avatar-mini" :title="currentUser?.username || '用户'">
              <img v-if="userAvatar" :src="userAvatar" class="avatar-img" />
              <i v-else class="el-icon-user-solid"></i>
            </div>
            <span class="preview-plus" v-if="selectedAgentList.length > 0">+</span>
            <!-- Agent头像 -->
            <div
              v-for="agent in selectedAgentList"
              :key="agent.id"
              class="preview-avatar"
              :style="{ background: agent.color || '#4080ff' }"
              :title="agent.name"
            >
              <img v-if="agent.avatar" :src="agent.avatar" class="avatar-img" />
              <span v-else class="avatar-letter">{{ agent.name?.charAt(0) || '?' }}</span>
            </div>
          </div>
          <div class="preview-type">
            <el-tag size="mini" :type="selectedAgentList.length > 1 ? 'success' : 'primary'">
              {{ selectedAgentList.length > 1 ? '群聊' : '单聊' }}
            </el-tag>
          </div>
        </div>
      </div>
      <span slot="footer" class="dialog-footer">
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateConversation" :loading="creating" class="create-btn">
          创建会话
        </el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import AppSidebar from '../components/Sidebar/index.vue'
import ArtifactWorkbench from '../components/ArtifactWorkbench/index.vue'
import ConversationList from '../components/ConversationList/index.vue'
import ChatWindow from '../components/ChatWindow/index.vue'
import { getCategories, getAgents } from '../api/agent'
import { sendMessage as apiSendMessage } from '../api/message'
import {
  stopConversationAgent,
  getConversationAttachments,
  uploadConversationAttachment,
  deleteConversationAttachment,
} from '../api/conversation'
import {
  getFileTree,
  readAgentFile,
  getSessionRawFileUrl,
  getWorkspaceFileUrl,
  getSessionDownloadUrl,
  listServices,
  startService,
} from '../api/sandbox'
import socketClient from '../utils/socket'

// ---------- localStorage helpers ----------
function loadAgentMeta() {
  try { return JSON.parse(localStorage.getItem('agent_meta') || '{}') } catch (e) { return {} }
}
function getAgentMeta(agentId) {
  const meta = loadAgentMeta()
  return meta[agentId] || {}
}

export default {
  name: 'Dashboard',
  components: { AppSidebar, ArtifactWorkbench, ConversationList, ChatWindow },
  data() {
    return {
      showCreateDialog: false,
      creating: false,
      treeLoading: false,
      agentTreeData: [],
      treeProps: { children: 'children', label: 'label' },
      newConversation: {
        title: '',
        type: 'single',
        selectedAgents: [],
      },
      socketHandlers: [],
      isAgentResponding: false,
      previewVisible: false,
      previewTitle: '',
      previewContent: '',
      previewLoading: false,
      previewType: 'text',
      previewUrl: '',
      selectedFilePath: '',
      artifactWorkbenchVisible: false,
      currentWorkbenchArtifact: null,
      fileTreeData: [],
      fileTreeRoot: '/workspace',
      fileScope: 'workspace',
      fileTreeProps: { children: 'children', label: 'name' },
      attachmentsVisible: false,
      attachments: [],
      attachmentsLoading: false,
      servicesVisible: false,
      servicesLoading: false,
      serviceStarting: false,
      services: [],
      serviceForm: {
        agent_id: '',
        port: 5173,
        cwd: '',
        command: 'npm run dev -- --host 0.0.0.0 --port 5173',
      },
      messageRefreshTimer: null,
    }
  },
  computed: {
    currentUser() {
      return this.$store.state.user.user
    },
    userId() {
      return this.$store.getters['user/userId']
    },
    conversations() {
      return this.$store.state.conversation.conversations
    },
    currentConversation() {
      return this.$store.state.conversation.currentConversation
    },
    convLoading() {
      return this.$store.state.conversation.loading
    },
    currentMessages() {
      const convId = this.currentConversation?.id
      if (!convId) return []
      return this.$store.getters['message/getMessagesByConversation'](convId)
    },
    agents() {
      return this.$store.state.agent.agents
    },
    allAvailableAgents() {
      // API agents already include user copies of public presets
      return this.agents.map(a => ({
        ...a,
        avatar: a.avatar_url || a.avatar || '',
        color: a.avatar_color || getAgentMeta(a.id).color || '#4080ff',
      }))
    },
    userAvatar() {
      return this.currentUser?.avatar || localStorage.getItem('user_avatar') || ''
    },
    selectedAgentList() {
      return this.newConversation.selectedAgents
        .map(id => this.findAgentWithMeta(id))
        .filter(Boolean)
    },
    currentSessionId() {
      return this.currentConversation?.sandbox_session_id || this.currentConversation?.id || ''
    },
    currentSessionAgents() {
      const participants = this.currentConversation?.participants_info || []
      return participants
        .filter(p => p.participant_type === 'agent')
        .map(p => ({
          agent_id: p.participant_id,
          role: p.name,
          name: p.name,
          workspace_name: this.safeWorkspaceName(p.name || p.participant_id),
          avatar: p.avatar,
          color: p.color,
        }))
    },
  },
  async created() {
    socketClient.connect()
    this.registerSocketHandlers()
    await Promise.all([
      this.$store.dispatch('conversation/fetchConversations'),
      this.$store.dispatch('agent/fetchAgents'),
    ])
  },
    beforeDestroy() {
      if (this.currentConversation?.id) {
        socketClient.leaveConversation(this.currentConversation.id)
      }
      this.stopMessageRefresh()
      this.unregisterSocketHandlers()
    },
  watch: {
    showCreateDialog(open) {
      if (open) {
        this.$nextTick(async () => { await this.buildAgentTree() })
      } else {
        this.newConversation = { title: '', type: 'single', selectedAgents: [] }
      }
    },
    'newConversation.selectedAgents': function(ids) {
      if (ids.length === 0) {
        this.newConversation.title = ''
        this.newConversation.type = 'single'
        return
      }
      // Auto-update title
      const userName = this.currentUser?.username || '用户'
      const agentNames = ids.map(id => {
        const agent = this.findAgentWithMeta(id)
        return agent?.name || id
      })
      this.newConversation.title = [userName, ...agentNames].join('、')
      // Update type
      this.newConversation.type = ids.length > 1 ? 'group' : 'single'
    },
  },
  methods: {
    handleSelectConversation(conversation) {
      const oldId = this.currentConversation?.id
      if (oldId && oldId !== conversation.id) {
        socketClient.leaveConversation(oldId)
      }
      this.stopMessageRefresh()
      this.$store.commit('conversation/SET_CURRENT_CONVERSATION', conversation)
      this.isAgentResponding = false
      socketClient.joinConversation(conversation.id)
      this.$store.dispatch('message/fetchMessages', {
        conversationId: conversation.id,
      })
    },

    async handleSendMessage(payload) {
      if (!this.currentConversation) return
      const convId = this.currentConversation.id
      const content = typeof payload === 'string' ? payload : payload?.content
      const targetAgentIds = Array.isArray(payload?.target_agent_ids) ? payload.target_agent_ids : []
      const mentions = Array.isArray(payload?.mentions) ? payload.mentions : []
      if (!content) return

      // === Optimistic UI: show user message immediately ===
      const tempId = 'temp_' + Date.now()
      this.$store.commit('message/APPEND_MESSAGE', {
        conversationId: convId,
        message: {
          id: tempId,
          conversation_id: convId,
          sender_type: 'user',
          sender_id: this.userId,
          content: content,
          message_type: 'text',
          created_at: this.localDateTimeString(),
          meta: targetAgentIds.length
            ? { dispatch_mode: 'direct', mentions }
            : undefined,
        },
      })

      this.isAgentResponding = true

      try {
        const requestData = {
          conversation_id: convId,
          content: content,
          message_type: 'text',
        }
        if (targetAgentIds.length) {
          requestData.target_agent_ids = targetAgentIds
        }
        const res = await apiSendMessage(requestData)

        if (res.code === 201) {
          // Replace temp ID with real ID from server
          this.$store.commit('message/UPDATE_MESSAGE_ID', {
            conversationId: convId,
            tempId,
            realId: res.data.id,
          })

          this.$store.dispatch('conversation/fetchConversations')
          this.startMessageRefresh(convId)
        }
      } catch (e) {
        this.$message.error('发送失败')
        this.isAgentResponding = false
        this.stopMessageRefresh()
      }
    },

    registerSocketHandlers() {
      this.unregisterSocketHandlers()
      const onCreated = (message) => {
        const convId = message.conversation_id
        this.$store.commit('message/UPSERT_MESSAGE', {
          conversationId: convId,
          message,
        })
        this.isAgentResponding = this.hasStreamingMessages(convId)
        this.$store.dispatch('conversation/fetchConversations')
      }
      const onDelta = (event) => {
        const patch = {
          content: event.content,
          elements: event.elements,
          raw_output: event.raw_output,
          status: event.status,
        }
        if (event.sender_name) {
          patch.sender_name = event.sender_name
        }
        this.$store.commit('message/UPDATE_MESSAGE', {
          conversationId: event.conversation_id,
          messageId: event.message_id,
          patch,
        })
        this.isAgentResponding = this.hasStreamingMessages(event.conversation_id)
      }
      const onElement = (event) => {
        const patch = {
          content: event.content,
          raw_output: event.raw_output,
          status: event.status,
        }
        if (event.sender_name) {
          patch.sender_name = event.sender_name
        }
        this.$store.commit('message/APPEND_MESSAGE_ELEMENT', {
          conversationId: event.conversation_id,
          messageId: event.message_id,
          element: event.element,
          patch,
        })
        this.$store.commit('message/ADD_MESSAGE_EVENT', {
          conversationId: event.conversation_id,
          messageId: event.message_id,
          events: event.events,
        })
      }
      const onStep = (event) => {
        this.$store.commit('message/ADD_MESSAGE_EVENT', {
          conversationId: event.conversation_id,
          messageId: event.message_id,
          event: event.event,
          events: event.events,
        })
      }
      const onElementStream = onElement
      const onStatus = (event) => {
        const patch = {
          content: event.content,
          elements: event.elements,
          raw_output: event.raw_output,
          status: event.status,
        }
        if (event.sender_name) {
          patch.sender_name = event.sender_name
        }
        if (event.events) {
          patch.meta = { events: event.events }
        }
        this.$store.commit('message/UPDATE_MESSAGE', {
          conversationId: event.conversation_id,
          messageId: event.message_id,
          patch,
        })
        this.isAgentResponding = this.hasStreamingMessages(event.conversation_id)
        this.$store.dispatch('conversation/fetchConversations')
        if (!this.isAgentResponding) {
          this.stopMessageRefresh()
        }
      }

      this.socketHandlers = [
        ['conversation_message_created', onCreated],
        ['conversation_message_delta', onDelta],
        ['conversation_message_element_stream', onElementStream],
        ['conversation_message_step', onStep],
        ['conversation_message_status', onStatus],
      ]
      this.socketHandlers.forEach(([event, handler]) => socketClient.on(event, handler))
    },

    unregisterSocketHandlers() {
      this.socketHandlers.forEach(([event, handler]) => socketClient.off(event, handler))
      this.socketHandlers = []
    },

    hasStreamingMessages(conversationId) {
      const msgs = this.$store.getters['message/getMessagesByConversation'](conversationId)
      return msgs.some(m => m.sender_type === 'agent' && ['pending', 'streaming'].includes(m.status))
    },

    startMessageRefresh(conversationId) {
      this.stopMessageRefresh()
      let ticks = 0
      this.messageRefreshTimer = setInterval(async () => {
        ticks += 1
        if (!this.currentConversation || this.currentConversation.id !== conversationId) {
          this.stopMessageRefresh()
          return
        }
        await this.$store.dispatch('message/fetchMessages', { conversationId })
        this.isAgentResponding = this.hasStreamingMessages(conversationId)
        if (!this.isAgentResponding || ticks >= 120) {
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

    async handlePinMessage(messageId) {
      await this.$store.dispatch('message/togglePin', messageId)
    },

    async handleDeleteConversation() {
      if (!this.currentConversation) return
      try {
        await this.$confirm('确认删除该会话？', '提示', {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        })
        await this.$store.dispatch('conversation/deleteConversation', this.currentConversation.id)
        this.$message.success('会话已删除')
      } catch (e) {}
    },

    async handleStopAgent(message) {
      if (!this.currentConversation || !message?.sender_id) return
      try {
        await stopConversationAgent(this.currentConversation.id, message.sender_id)
      } catch (e) {
        this.$message.error('停止 Agent 失败')
      }
    },

    async handleOpenWorkspace(scope = 'workspace') {
      if (!this.currentConversation) return
      let root = '/workspace'
      if (scope && scope.startsWith('agent:')) {
        const agentId = scope.split(':')[1]
        const agent = this.currentSessionAgents.find(item => item.agent_id === agentId)
        root = `/workspace/agents/${agent?.workspace_name || this.safeWorkspaceName(agent?.role || agentId)}`
      } else if (scope === 'shared') {
        root = '/workspace/shared'
      }
      this.currentWorkbenchArtifact = {
        path: '',
        root,
        type: 'workspace',
        name: '工作台',
      }
      this.artifactWorkbenchVisible = true
    },

    async handleOpenFile(file) {
      if (!this.currentConversation || !file?.path) return
      const path = this.normalizeWorkspacePath(file.path)
      this.currentWorkbenchArtifact = this.buildWorkbenchArtifact({
        ...file,
        path,
      })
      this.artifactWorkbenchVisible = true
    },

    handleSearchMessages() {
      this.$message.info('搜索功能即将上线')
    },

    handleOpenAttachment() {
      this.handleOpenWorkspace('workspace')
    },

    handleToggleStar() {
      this.$message.info('收藏功能即将上线')
    },

    handleOpenHistory() {
      this.$message.info('历史记录功能即将上线')
    },

    async handleOpenAttachments() {
      if (!this.currentConversation) return
      this.attachmentsVisible = true
      await this.loadAttachments()
    },

    async handleOpenServices() {
      if (!this.currentConversation) return
      this.servicesVisible = true
      if (!this.serviceForm.agent_id && this.currentSessionAgents.length) {
        const worker = this.currentSessionAgents.find(a => a.agent_id !== 'moderator') || this.currentSessionAgents[0]
        this.serviceForm.agent_id = worker.agent_id
        this.syncServiceCwd()
      }
      this.syncServiceCommand()
      await this.loadServices()
    },

    async loadServices() {
      if (!this.currentSessionId) return
      this.servicesLoading = true
      try {
        const res = await listServices(this.currentSessionId)
        if (res.code === 200) {
          this.services = res.data?.services || []
        }
      } catch (e) {
        this.$message.error(e?.message || '获取服务列表失败')
      } finally {
        this.servicesLoading = false
      }
    },

    async handleStartService() {
      if (!this.currentSessionId) return
      if (!this.serviceForm.agent_id) {
        this.$message.warning('请选择 Agent')
        return
      }
      this.serviceStarting = true
      try {
        const res = await startService(this.currentSessionId, {
          agent_id: this.serviceForm.agent_id,
          port: this.serviceForm.port,
          cwd: this.serviceForm.cwd,
          command: this.serviceForm.command,
        })
        if (res.code === 200) {
          const url = res.data?.url
          this.$message.success(url ? `服务已启动：${url}` : '服务已启动')
          await this.loadServices()
          if (url) window.open(url, '_blank')
        }
      } catch (e) {
        this.$message.error(e?.message || '启动服务失败')
      } finally {
        this.serviceStarting = false
      }
    },

    syncServiceCwd() {
      const agent = this.currentSessionAgents.find(a => a.agent_id === this.serviceForm.agent_id)
      if (!agent) return
      this.serviceForm.cwd = `/workspace/agents/${agent.workspace_name || this.safeWorkspaceName(agent.name || agent.role || agent.agent_id)}`
    },

    syncServiceCommand() {
      const port = Number(this.serviceForm.port)
      if (port === 5173) {
        this.serviceForm.command = 'npm run dev -- --host 0.0.0.0 --port 5173'
      } else if (port === 8081) {
        this.serviceForm.command = 'npm run serve -- --host 0.0.0.0 --port 8081'
      } else if (port === 3000) {
        this.serviceForm.command = 'npm start -- --host 0.0.0.0 --port 3000'
      } else if (port === 8000) {
        this.serviceForm.command = 'python3 -m http.server 8000 --bind 0.0.0.0'
      }
    },

    async copyServiceUrl(url) {
      try {
        await navigator.clipboard.writeText(url)
        this.$message.success('已复制访问链接')
      } catch (e) {
        this.$message.info(url)
      }
    },

    async loadAttachments() {
      if (!this.currentConversation) return
      this.attachmentsLoading = true
      try {
        const res = await getConversationAttachments(this.currentConversation.id)
        if (res.code === 200) {
          this.attachments = res.data.files || []
        }
      } catch (e) {
        this.$message.error('获取上传文件失败')
      } finally {
        this.attachmentsLoading = false
      }
    },

    async handleAttachmentPicked(file) {
      if (!this.currentConversation || !file?.raw) return
      this.attachmentsLoading = true
      try {
        await uploadConversationAttachment(this.currentConversation.id, file.raw)
        this.$message.success('文件已上传到 Agent 工作目录')
        await this.loadAttachments()
      } catch (e) {
        this.$message.error(e?.response?.data?.message || e?.message || '上传失败')
      } finally {
        this.attachmentsLoading = false
      }
    },

    async handleDeleteAttachment(file) {
      if (!this.currentConversation || !file?.path) return
      try {
        await this.$confirm(`删除 ${file.name}？`, '提示', {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        })
        await deleteConversationAttachment(this.currentConversation.id, file.path, file.agent_id)
        this.$message.success('文件已删除')
        await this.loadAttachments()
      } catch (e) {}
    },

    async switchFileScope(scope) {
      if (!this.currentSessionId) return
      let root = '/workspace'
      let title = '全部文件'
      if (scope === 'shared') {
        root = '/workspace/shared'
        title = '公共目录'
      } else if (scope && scope.startsWith('agent:')) {
        const agentId = scope.slice('agent:'.length)
        const agent = this.currentSessionAgents.find(a => a.agent_id === agentId)
        root = `/workspace/agents/${agent?.workspace_name || this.safeWorkspaceName(agent?.role || agentId)}`
        title = `${agent?.role || agentId} 文件`
      }
      this.fileScope = scope || 'workspace'
      this.previewTitle = title
      this.previewContent = ''
      this.previewType = 'text'
      this.previewUrl = ''
      this.selectedFilePath = ''
      await this.loadFileTree(root)
    },

    async loadFileTree(root) {
      if (!this.currentSessionId) return
      this.previewLoading = true
      try {
        const res = await getFileTree(this.currentSessionId, root)
        if (res.code === 200 && res.data?.tree) {
          this.fileTreeData = [res.data.tree]
          this.fileTreeRoot = root
        }
      } catch (e) {
        this.$message.error('获取文件树失败')
      } finally {
        this.previewLoading = false
      }
    },

    handleFileNodeClick(data) {
      if (data.type === 'directory') {
        this.selectedFilePath = ''
        this.previewContent = ''
        this.previewType = 'text'
        this.previewUrl = ''
        this.loadFileTree(data.path)
        return
      }
      this.previewFile(data.path)
    },

    previewFile(filePath) {
      if (!this.currentSessionId || !filePath) return
      this.previewLoading = true
      this.previewVisible = true
      this.previewTitle = filePath
      this.previewContent = ''
      this.previewUrl = ''
      this.selectedFilePath = filePath

      const ext = this.getExt(filePath)
      if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) {
        this.previewType = 'image'
        this.previewUrl = getSessionRawFileUrl(this.currentSessionId, filePath)
        this.previewLoading = false
        return
      }
      if (ext === 'pdf') {
        this.previewType = 'pdf'
        this.previewUrl = getSessionRawFileUrl(this.currentSessionId, filePath)
        this.previewLoading = false
        return
      }
      if (this.isHtmlFile(filePath)) {
        this.previewType = 'html'
        this.previewUrl = getWorkspaceFileUrl(this.currentSessionId, filePath)
        this.previewLoading = false
        return
      }
      if (!['txt', 'md', 'json', 'js', 'css', 'vue', 'html', 'htm', 'py', 'yml', 'yaml', 'xml', 'csv', 'log'].includes(ext)) {
        this.previewType = 'binary'
        this.previewLoading = false
        return
      }

      const agentId = this.currentSessionAgents[0]?.agent_id || ''
      this.previewType = 'text'
      readAgentFile(this.currentSessionId, agentId, filePath)
        .then(res => {
          this.previewContent = res.code === 200 && res.data?.content !== undefined
            ? res.data.content
            : '无法读取文件'
        })
        .catch(e => {
          this.previewContent = '加载失败: ' + (e?.message || '未知错误')
        })
        .finally(() => { this.previewLoading = false })
    },

    openContainingFolder(path) {
      if (!path) return
      const normalized = path.replace(/\\/g, '/')
      const idx = normalized.lastIndexOf('/')
      if (idx > 0) this.loadFileTree(normalized.slice(0, idx))
    },

    openWorkspaceFile(filePath) {
      if (!this.currentSessionId) return
      window.open(getWorkspaceFileUrl(this.currentSessionId, filePath), '_blank')
    },

    buildWorkbenchArtifact(file) {
      const path = this.normalizeWorkspacePath(file?.path || '')
      return {
        path,
        name: file?.name || path.split('/').pop() || '',
        type: file?.type || this.inferArtifactType(path),
        diffElement: file?.diffElement || null,
        imageUrl: file?.imageUrl || '',
        codeContent: file?.codeContent || '',
        tableHeaders: Array.isArray(file?.tableHeaders) ? file.tableHeaders : [],
        tableRows: Array.isArray(file?.tableRows) ? file.tableRows : [],
      }
    },

    inferArtifactType(path) {
      const ext = this.getExt(path)
      if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) return 'image'
      if (ext === 'csv') return 'table'
      if (['html', 'htm'].includes(ext)) return 'webpage'
      if (['txt', 'log'].includes(ext)) return 'text'
      if (['md', 'json', 'js', 'css', 'vue', 'py', 'yml', 'yaml', 'xml', 'sql', 'ts', 'tsx', 'jsx', 'java', 'go', 'rs', 'php', 'rb', 'sh', 'bat', 'ps1', 'kt', 'swift', 'dart', 'c', 'h', 'cpp', 'cc', 'cxx', 'hpp', 'cs', 'toml', 'scss', 'less'].includes(ext)) {
        return 'code'
      }
      return 'file'
    },

    downloadFile(path) {
      if (!this.currentSessionId || !path) return
      window.open(getSessionDownloadUrl(this.currentSessionId, path), '_blank')
    },

    copyFilePath(path) {
      navigator.clipboard?.writeText(path)
      this.$message.success('已复制路径')
    },

    localDateTimeString() {
      const date = new Date()
      const pad = n => String(n).padStart(2, '0')
      return [
        date.getFullYear(),
        pad(date.getMonth() + 1),
        pad(date.getDate()),
      ].join('-') + 'T' + [
        pad(date.getHours()),
        pad(date.getMinutes()),
        pad(date.getSeconds()),
      ].join(':')
    },

    getExt(path) {
      const clean = (path || '').split('?')[0].split('#')[0]
      const idx = clean.lastIndexOf('.')
      return idx >= 0 ? clean.slice(idx + 1).toLowerCase() : ''
    },

    isHtmlFile(path) {
      return ['html', 'htm'].includes(this.getExt(path))
    },

    getFileIcon(path) {
      const ext = this.getExt(path)
      if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return 'el-icon-picture'
      if (['html', 'htm'].includes(ext)) return 'el-icon-monitor'
      if (['js', 'css', 'vue', 'py', 'json', 'md'].includes(ext)) return 'el-icon-document'
      return 'el-icon-document'
    },

    formatFileSize(bytes) {
      if (!bytes) return ''
      const units = ['B', 'KB', 'MB', 'GB']
      let i = 0
      let size = bytes
      while (size >= 1024 && i < units.length - 1) {
        size /= 1024
        i++
      }
      return size.toFixed(1) + ' ' + units[i]
    },

    normalizeWorkspacePath(path) {
      if (!path) return ''
      const clean = String(path).replace(/\\/g, '/').replace(/^\/+/, '')
      return clean.startsWith('workspace/') ? `/${clean}` : `/workspace/${clean}`
    },

    safeWorkspaceName(name) {
      return String(name || 'agent')
        .trim()
        .replace(/[\\/:*?"<>|\x00-\x1f]/g, '_')
        .replace(/\s+/g, '_')
        .replace(/^[._ ]+|[._ ]+$/g, '')
        .slice(0, 80) || 'agent'
    },

    // ====== 新建会话 ======
    async buildAgentTree() {
      this.treeLoading = true
      const treeData = []

      try {
        // Fetch categories + agents fresh from API (no cache)
        const [catRes, agentRes] = await Promise.all([
          getCategories(),
          getAgents(),  // no class_id = all user agents
        ])
        const cats = catRes.code === 200 ? catRes.data : []
        const agents = agentRes.code === 200
          ? agentRes.data.filter(agent => agent.id !== 'moderator')
          : []

        for (const cat of cats) {
          const children = []
          for (const agent of agents) {
            if (agent.class_id === cat.id) {
              children.push({
                id: agent.id,
                label: agent.name,
                isLeaf: true,
                agentColor: agent.avatar_color || '#4080ff',
                agentAvatar: agent.avatar_url || '',
                adapterLabel: { claude: 'Claude', codex: 'Codex', opencode: 'OpenCode', mock: 'Mock' }[agent.adapter_name] || agent.adapter_name,
              })
            }
          }
          if (children.length > 0) {
            treeData.push({
              id: cat.id,
              label: cat.name,
              icon: cat.icon || 'el-icon-folder-opened',
              children,
            })
          }
        }

        // Uncategorized agents
        const uncategorized = agents.filter(a => !a.class_id)
        if (uncategorized.length > 0) {
          const children = uncategorized.map(agent => ({
            id: agent.id,
            label: agent.name,
            isLeaf: true,
            agentColor: agent.avatar_color || '#4080ff',
            agentAvatar: agent.avatar_url || '',
            adapterLabel: { claude: 'Claude', codex: 'Codex', opencode: 'OpenCode', mock: 'Mock' }[agent.adapter_name] || agent.adapter_name,
          }))
          treeData.push({
            id: '_uncategorized',
            label: '其他',
            icon: 'el-icon-folder-opened',
            children,
          })
        }
      } catch (e) {
        this.$message.error('加载Agent列表失败')
      }
      this.agentTreeData = treeData
      this.treeLoading = false
    },
    findAgentWithMeta(id) {
      const agent = this.allAvailableAgents.find(a => a.id === id)
      if (!agent) return null
      // Merge any locally-stored overrides (backward compat)
      const meta = getAgentMeta(id)
      return { ...agent, ...meta }
    },
    handleTreeCheckChange() {
      if (this.$refs.agentTree) {
        const checkedAgents = this.$refs.agentTree.getCheckedNodes(true)
          .filter(node => node.isLeaf && node.id !== 'moderator')
          .map(node => node.id)
        this.newConversation.selectedAgents = checkedAgents
      }
    },

    async handleCreateConversation() {
      if (!this.newConversation.title) {
        this.$message.warning('请输入标题')
        return
      }
      this.creating = true
      try {
        const participantIds = this.newConversation.selectedAgents
          .filter(id => id)
          .map(id => `agent_${id}`)
        const response = await this.$store.dispatch('conversation/createConversation', {
          title: this.newConversation.title,
          type: this.newConversation.type,
          participant_ids: participantIds,
        })
        if (response.code === 201) {
          this.$message.success('会话创建成功')
          this.showCreateDialog = false
          this.newConversation = { title: '', type: 'single', selectedAgents: [] }
          this.handleSelectConversation(response.data)
        } else {
          this.$message.error(response.message || '创建会话失败')
        }
      } finally {
        this.creating = false
      }
    },
  },
}
</script>

<style scoped>
.dashboard {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}

/* 第二栏：会话列表 - 固定 300px 圆角卡片 */
.conversation-panel {
  width: 250px;
  flex-shrink: 0;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 第三栏：主聊天区 - 自适应剩余宽度 圆角卡片 */
.chat-panel {
  flex: 1;
  min-width: 600px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  overflow: hidden;
}

.no-agents-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

/* ===== 新建会话对话框 ===== */
.create-conv-body {
  padding: 0 4px;
}
.conv-field {
  margin-bottom: 20px;
}
.field-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}
.field-hint {
  font-weight: 400;
  font-size: 12px;
  color: #94a3b8;
}
.conv-field .el-input__inner {
  border-radius: 10px;
  height: 40px;
}
.conv-field .el-input__inner:focus {
  border-color: #4080ff;
}

/* Agent 树 */
.agent-tree-wrapper {
  border: 1px solid #e8eaed;
  border-radius: 12px;
  padding: 8px 4px;
  max-height: 300px;
  overflow-y: auto;
  background: #fafbfc;
}
.agent-tree-wrapper::-webkit-scrollbar { width: 4px; }
.agent-tree-wrapper::-webkit-scrollbar-thumb { background: #dcdde1; border-radius: 4px; }
.agent-tree {
  background: transparent;
}
.agent-tree :deep(.el-tree-node__content) {
  height: 38px;
  border-radius: 8px;
  padding-left: 8px !important;
}
.agent-tree :deep(.el-tree-node__content:hover) {
  background: rgba(64,128,255,0.06);
}
.agent-tree :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #4080ff;
  border-color: #4080ff;
}
.agent-tree :deep(.el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: #4080ff;
  border-color: #4080ff;
}
.tree-node {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}
.node-category {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
}
.node-category i {
  font-size: 15px;
  color: #4080ff;
}
.node-count {
  font-size: 11px;
  color: #94a3b8;
  margin-left: 4px;
}
.node-agent {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.node-avatar {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.node-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 6px;
}
.node-avatar-letter {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
}
.node-name {
  font-size: 13px;
  color: #1e293b;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.node-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #f0f5ff;
  color: #4080ff;
  flex-shrink: 0;
  line-height: 18px;
}

/* 预览头像区 */
.conv-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e8eaed;
}
.preview-avatars {
  display: flex;
  align-items: center;
  gap: 4px;
}
.preview-avatar {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #4080ff;
  color: #fff;
  font-size: 13px;
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.preview-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 6px;
}
.preview-avatar i {
  font-size: 14px;
}
.user-avatar-mini {
  background: #e8eaed;
  color: #64748b;
}
.preview-plus {
  color: #94a3b8;
  font-size: 16px;
  font-weight: 300;
  margin: 0 2px;
}
.preview-type {
  flex-shrink: 0;
}

/* 底部按钮 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.create-btn {
  border: none;
  border-radius: 8px;
  background: #4080ff;
  padding: 8px 20px;
}

.file-browser-body {
  display: flex;
  gap: 12px;
  height: 70vh;
  overflow: hidden;
}

.file-tree-panel {
  width: 280px;
  flex-shrink: 0;
  overflow: auto;
  padding: 10px;
  background: #1a2332;
  border: 1px solid #334155;
  border-radius: 8px;
}

.file-scope-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #334155;
}

.file-scope-tabs .el-button {
  padding: 4px 8px;
}

.file-tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #94a3b8;
  font-size: 12px;
  margin-bottom: 8px;
}

.file-tree-panel :deep(.el-tree) {
  background: transparent;
  color: #cbd5e1;
}

.file-tree-panel :deep(.el-tree-node__content:hover),
.file-tree-panel :deep(.el-tree-node:focus > .el-tree-node__content) {
  background: #0f1f3a;
}

.file-tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  min-width: 0;
}

.tree-file-size {
  color: #64748b;
  font-size: 10px;
  margin-left: 4px;
}

.file-preview-panel {
  flex: 1;
  min-width: 0;
  overflow: auto;
}

.file-preview-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: #94a3b8;
  font-size: 12px;
}

.selected-file-path {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-preview-empty {
  height: 62vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #64748b;
  background: #1a2332;
  border: 1px dashed #334155;
  border-radius: 8px;
}

.file-preview-empty i {
  font-size: 34px;
}

.image-preview-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  background: #1a2332;
  border: 1px solid #334155;
  border-radius: 8px;
}

.image-preview {
  max-width: 100%;
  max-height: 62vh;
  object-fit: contain;
}

.pdf-preview,
.html-preview {
  width: 100%;
  height: 62vh;
  border: 1px solid #334155;
  border-radius: 8px;
  background: #fff;
}

.binary-preview {
  text-align: center;
  padding: 80px 20px;
  color: #94a3b8;
  background: #1a2332;
  border: 1px solid #334155;
  border-radius: 8px;
}

.file-preview-content {
  margin: 0;
  padding: 16px;
  background: #1a2332;
  border: 1px solid #334155;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: #cbd5e1;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
}

.attachments-body {
  padding: 0 18px 18px;
}

.attachment-upload {
  margin-bottom: 18px;
}

.attachment-upload :deep(.el-upload),
.attachment-upload :deep(.el-upload-dragger) {
  width: 100%;
}

.attachment-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.attachment-list {
  min-height: 160px;
}

.attachment-empty {
  padding: 28px 0;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #f1f5f9;
}

.attachment-item i {
  color: #4080ff;
  font-size: 18px;
}

.attachment-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.attachment-info span {
  color: #94a3b8;
  font-size: 11px;
}

.attachment-name {
  border: none;
  background: transparent;
  padding: 0;
  color: #1e293b;
  text-align: left;
  font-size: 13px;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-name:hover {
  color: #4080ff;
}

.services-body {
  padding: 0 18px 18px;
}

.service-tip {
  margin: 12px 0;
  padding: 8px 10px;
  border-radius: 6px;
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.service-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 120px;
}

.service-empty {
  padding: 24px 0;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

.service-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 10px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fff;
}

.service-main {
  flex: 1;
  min-width: 0;
}

.service-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  color: #1e293b;
  margin-bottom: 4px;
}

.service-url {
  display: block;
  color: #4080ff;
  font-size: 13px;
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.service-command {
  margin-top: 4px;
  color: #64748b;
  font-size: 11px;
  font-family: Consolas, monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

<style>
/* 新建会话弹窗圆角 */
.create-conv-dialog {
  border-radius: 16px !important;
  overflow: hidden;
}
.create-conv-dialog .el-dialog__header {
  padding: 20px 24px 0;
}
.create-conv-dialog .el-dialog__title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}
.create-conv-dialog .el-dialog__body {
  padding: 16px 24px 10px;
}
.create-conv-dialog .el-dialog__footer {
  padding: 0 24px 20px;
  border-top: none;
}

.file-preview-dialog .el-dialog__header {
  background: #1e293b;
  border-bottom: 1px solid #334155;
}

.file-preview-dialog .el-dialog__title {
  color: #e2e8f0;
  font-size: 14px;
}

.file-preview-dialog .el-dialog__body {
  background: #0f172a;
  padding: 16px;
}

.file-preview-dialog .el-dialog__headerbtn .el-dialog__close {
  color: #64748b;
}
</style>
