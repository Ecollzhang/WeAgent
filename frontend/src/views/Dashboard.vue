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
        @send-message="handleSendMessage"
        @pin-message="handlePinMessage"
        @delete-conversation="handleDeleteConversation"
        @search-messages="handleSearchMessages"
        @open-attachment="handleOpenAttachment"
        @toggle-star="handleToggleStar"
        @open-history="handleOpenHistory"
      />
    </div>

    <!-- 新建会话对话框 -->
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
import ConversationList from '../components/ConversationList/index.vue'
import ChatWindow from '../components/ChatWindow/index.vue'
import { getCategories, getAgents } from '../api/agent'
import { sendMessage as apiSendMessage, pollMessages } from '../api/message'

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
  components: { AppSidebar, ConversationList, ChatWindow },
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
      pollTimer: null,
      pollAfterId: null,
      eventSource: null,
      isAgentResponding: false,
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
  },
  async created() {
    await Promise.all([
      this.$store.dispatch('conversation/fetchConversations'),
      this.$store.dispatch('agent/fetchAgents'),
    ])
  },
  beforeDestroy() {
    this.stopPolling()
    this.stopSSE()
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
      this.$store.commit('conversation/SET_CURRENT_CONVERSATION', conversation)
      this.pollAfterId = null
      this.isAgentResponding = false
      this.stopPolling()
      this.stopSSE()
      this.$store.dispatch('message/fetchMessages', {
        conversationId: conversation.id,
      }).then(() => {
        const msgs = this.$store.getters['message/getMessagesByConversation'](conversation.id)
        if (msgs.length > 0) {
          this.pollAfterId = msgs[msgs.length - 1].id
        }
        this.startPolling()
      })
    },

    async handleSendMessage(content) {
      if (!this.currentConversation) return
      const convId = this.currentConversation.id

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
          created_at: new Date().toISOString(),
        },
      })

      this.isAgentResponding = true

      try {
        const res = await apiSendMessage({
          conversation_id: convId,
          content: content,
          message_type: 'text',
        })

        if (res.code === 201) {
          // Replace temp ID with real ID from server
          this.$store.commit('message/UPDATE_MESSAGE_ID', {
            conversationId: convId,
            tempId,
            realId: res.data.id,
          })

          // Start SSE streaming for agent responses
          this.pollAfterId = res.data.id
          this.stopPolling()
          this.startSSE(convId, res.data.id)
          this.$store.dispatch('conversation/fetchConversations')
        }
      } catch (e) {
        this.$message.error('发送失败')
        this.isAgentResponding = false
      }
    },

    startPolling() {
      this.stopPolling()
      this.pollTimer = setInterval(() => this._doPoll(), 1500)
    },
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    async _doPoll() {
      if (!this.currentConversation || this.eventSource) {
        // Don't poll while SSE is active
        return
      }
      try {
        const res = await pollMessages(this.currentConversation.id, this.pollAfterId)
        if (res.code === 200 && res.data.items.length > 0) {
          for (const msg of res.data.items) {
            this.$store.commit('message/APPEND_MESSAGE', {
              conversationId: this.currentConversation.id,
              message: msg,
            })
          }
          this.pollAfterId = res.data.items[res.data.items.length - 1].id
          this.$store.dispatch('conversation/fetchConversations')
        }
      } catch (e) {
        // Silently ignore polling errors
      }
    },

    // ====== SSE streaming ======
    startSSE(conversationId, afterId) {
      this.stopSSE()
      let cleanedUp = false

      const token = localStorage.getItem('access_token')
      if (!token) {
        this.startPolling()
        return
      }

      const url = `http://localhost:5000/api/messages/stream/${conversationId}?after=${afterId}&token=${token}`
      this.eventSource = new EventSource(url)

      const cleanup = () => {
        if (cleanedUp) return
        cleanedUp = true
        this.isAgentResponding = false
        this.stopSSE()
        this.startPolling()
      }

      this.eventSource.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          // Deduplicate: skip if message already exists in store
          const existing = this.$store.getters['message/getMessagesByConversation'](conversationId)
          if (existing.some(m => m.id === msg.id)) return
          this.$store.commit('message/APPEND_MESSAGE', {
            conversationId,
            message: msg,
          })
          this.pollAfterId = msg.id
          this.$store.dispatch('conversation/fetchConversations')
        } catch (e) {
          console.error('[SSE] parse error:', e)
        }
      }

      this.eventSource.addEventListener('done', () => {
        cleanup()
      })

      this.eventSource.onerror = () => {
        if (!this.eventSource) return
        cleanup()
      }
    },

    stopSSE() {
      if (this.eventSource) {
        this.eventSource.close()
        this.eventSource = null
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
        this.stopSSE()
        this.stopPolling()
        this.$message.success('会话已删除')
      } catch (e) {}
    },

    handleSearchMessages() {
      this.$message.info('搜索功能即将上线')
    },

    handleOpenAttachment() {
      this.$message.info('附件功能即将上线')
    },

    handleToggleStar() {
      this.$message.info('收藏功能即将上线')
    },

    handleOpenHistory() {
      this.$message.info('历史记录功能即将上线')
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
        const agents = agentRes.code === 200 ? agentRes.data : []

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
                adapterLabel: { claude: 'Claude', codex: 'Codex', opencode: 'OpenCode' }[agent.adapter_name] || agent.adapter_name,
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
            adapterLabel: { claude: 'Claude', codex: 'Codex', opencode: 'OpenCode' }[agent.adapter_name] || agent.adapter_name,
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
        const checked = this.$refs.agentTree.getCheckedKeys()
        this.newConversation.selectedAgents = checked
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
</style>
