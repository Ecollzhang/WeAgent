<template>
  <main class="dashboard-shell">
    <aside class="app-sidebar">
      <div class="sidebar-logo">W</div>
      <nav class="sidebar-nav">
        <button class="sidebar-btn" title="会话" @click="$router.push('/conversations')"><i class="el-icon-chat-dot-round"></i></button>
        <button class="sidebar-btn active" title="智能体"><i class="el-icon-user"></i></button>
        <button class="sidebar-btn" title="工具" disabled><i class="el-icon-s-tools"></i></button>
        <button class="sidebar-btn" title="设置" @click="$router.push('/settings')"><i class="el-icon-setting"></i></button>
      </nav>
      <button class="sidebar-user" title="退出登录" @click="logout"><i class="el-icon-switch-button"></i></button>
    </aside>

    <section class="workspace-panel agents-workspace">
      <header class="workspace-header">
        <div>
          <p class="section-eyebrow">Desktop</p>
          <h1>我的 Agent</h1>
          <span>展示、创建并编辑你自己的智能体。</span>
        </div>
        <button class="workspace-primary" @click="startCreate">
          <i class="el-icon-plus"></i>
          新建 Agent
        </button>
      </header>

      <div class="agents-layout">
        <section class="agents-list-pane">
          <div v-if="loading" class="workspace-state">
            <i class="el-icon-loading"></i>
            <span>正在加载 Agent...</span>
          </div>

          <div v-else-if="agents.length === 0" class="workspace-state">
            <i class="el-icon-user"></i>
            <span>暂无 Agent，创建一个开始使用。</span>
          </div>

          <div v-else class="agent-grid agent-grid-compact">
            <article
              v-for="agent in agents"
              :key="agent.id"
              class="agent-card"
              :class="{ active: selectedAgent && selectedAgent.id === agent.id }"
              @click="selectAgent(agent)"
            >
              <div class="agent-card-head">
                <div class="agent-avatar" :style="agentAvatarStyle(agent)">
                  <img v-if="agentAvatar(agent)" :src="agentAvatar(agent)" class="agent-avatar-img" />
                  <span v-else>{{ firstLetter(agent.name) }}</span>
                </div>
                <div>
                  <h3>{{ agent.name }}</h3>
                  <p>{{ agent.adapter_name || agent.agent_type || 'custom' }}</p>
                </div>
              </div>
              <p class="agent-prompt">{{ agent.system_prompt || '暂无系统提示词' }}</p>
              <div class="agent-tags">
                <span
                  v-for="(tag, index) in agent.capability_tags || []"
                  :key="tag"
                  :style="tagStyle(index)"
                >{{ tag }}</span>
                <span v-if="!(agent.capability_tags || []).length">未设置标签</span>
              </div>
              <div class="card-tools" v-if="agent.tool_ids && agent.tool_ids.length">
                <span class="tools-label">工具集:</span>
                <span class="tools-list">{{ toolsLabel(agent.tool_ids) }}</span>
              </div>
              <div class="agent-actions">
                <button class="text-action" @click.stop="selectAgent(agent)">编辑</button>
                <button class="text-danger" @click.stop="handleDelete(agent)">删除</button>
              </div>
            </article>
          </div>
        </section>

        <section class="agent-editor-panel">
          <div v-if="!editorVisible" class="workspace-state editor-empty">
            <i class="el-icon-edit-outline"></i>
            <span>选择一个 Agent 查看并编辑信息。</span>
          </div>

          <form v-else class="agent-editor agent-editor-rich" @submit.prevent="handleSave">
            <div class="editor-title-row">
              <div>
                <h2>{{ isCreating ? '新建 Agent' : '编辑 Agent' }}</h2>
                <p>{{ isCreating ? '创建后可在新建会话时选择它。' : '修改会同步到后端，之后会话里继续使用最新配置。' }}</p>
              </div>
              <button type="button" class="icon-close" @click="closeEditor"><i class="el-icon-close"></i></button>
            </div>

            <div class="agent-avatar-edit">
              <button class="agent-avatar-large" type="button" :style="formAvatarStyle" @click="triggerUpload">
                <img v-if="formAvatarUrl" :src="formAvatarUrl" />
                <span v-else>{{ firstLetter(form.name) }}</span>
                <span class="avatar-overlay">
                  <i class="el-icon-camera"></i>
                </span>
              </button>
              <input
                ref="fileInput"
                type="file"
                class="hidden-file"
                accept="image/png,image/jpeg,image/gif,image/webp"
                @change="handleAvatarChange"
              />
              <div>
                <strong>{{ form.name || 'Agent 头像' }}</strong>
                <span>点击头像上传图片，也可以只使用头像色。</span>
              </div>
            </div>

            <div class="form-grid">
              <label>
                <span>名称</span>
                <input v-model.trim="form.name" placeholder="例如：代码审查助手" />
              </label>
              <label>
                <span>适配器</span>
                <select v-model="form.adapter_name">
                  <option value="claude">Claude</option>
                  <option value="codex">Codex</option>
                  <option value="opencode">OpenCode</option>
                </select>
              </label>
              <label>
                <span>头像色</span>
                <div class="color-picker-row">
                  <el-color-picker v-model="form.avatar_color" size="small"></el-color-picker>
                  <input v-model.trim="form.avatar_color" placeholder="#4080ff" />
                </div>
              </label>
              <label>
                <span>工具集</span>
                <el-select
                  v-model="form.tool_ids"
                  multiple
                  collapse-tags
                  size="small"
                  placeholder="选择工具"
                  class="desktop-tool-select"
                >
                  <el-option
                    v-for="tool in tools"
                    :key="tool.id"
                    :label="tool.name"
                    :value="tool.id"
                  >
                    <span>{{ tool.name }}</span>
                    <span class="tool-option-meta">
                      <i :class="tool.icon || 'el-icon-setting'"></i>
                      {{ tool.value }}
                    </span>
                  </el-option>
                </el-select>
              </label>
            </div>

            <label class="wide-field">
              <span>系统提示词</span>
              <textarea v-model.trim="form.system_prompt" rows="5" placeholder="描述 Agent 的行为、专业领域和边界"></textarea>
            </label>

            <label class="wide-field">
              <span>技能</span>
              <textarea v-model.trim="form.skill" rows="4" placeholder="补充 Agent 的技能、流程或固定工作方式"></textarea>
            </label>

            <div class="tag-editor">
              <span class="field-title">能力标签</span>
              <div class="editable-tags">
                <span
                  v-for="(tag, index) in form.capability_tags"
                  :key="tag + index"
                  class="editable-tag"
                  :style="tagStyle(index)"
                >
                  {{ tag }}
                  <button type="button" @click="removeTag(index)"><i class="el-icon-close"></i></button>
                </span>
                <span v-if="form.capability_tags.length === 0" class="empty-tag">未设置标签</span>
              </div>
              <div class="tag-input-row">
                <input v-model.trim="newTag" placeholder="输入标签后添加" @keyup.enter.prevent="addTag" />
                <button type="button" class="workspace-secondary" @click="addTag">添加</button>
              </div>
            </div>

            <div class="form-actions">
              <button type="button" class="workspace-secondary" @click="resetForm">重置</button>
              <button type="submit" class="workspace-primary" :disabled="saving || !form.name">
                {{ saving ? '保存中...' : (isCreating ? '创建 Agent' : '保存修改') }}
              </button>
            </div>
          </form>
        </section>
      </div>

      <div v-if="error" class="desktop-toast">{{ error }}</div>
      <div v-if="message" class="desktop-toast success-toast">{{ message }}</div>
    </section>
  </main>
</template>

<script>
import { createAgent, deleteAgent, getAgents, getTools, updateAgent, uploadFile } from '../services/api'
import { backendUrl, getServerUrl } from '../services/config'
import { clearAuth } from '../services/session'

const defaultForm = () => ({
  name: '',
  adapter_name: 'claude',
  avatar_color: '#4080ff',
  avatar_url: '',
  system_prompt: '',
  skill: '',
  capability_tags: [],
  tool_ids: [],
})

export default {
  name: 'Agents',
  data() {
    return {
      agents: [],
      tools: [],
      selectedAgent: null,
      serverUrl: '',
      loading: false,
      saving: false,
      uploading: false,
      editorVisible: false,
      isCreating: false,
      error: '',
      message: '',
      newTag: '',
      form: defaultForm(),
    }
  },
  computed: {
    formAvatarUrl() {
      return this.form.avatar_url ? backendUrl(this.serverUrl, this.form.avatar_url) : ''
    },
    formAvatarStyle() {
      return this.formAvatarUrl ? {} : { background: this.form.avatar_color || '#4080ff' }
    },
  },
  async created() {
    this.serverUrl = await getServerUrl()
    await Promise.all([this.loadTools(), this.loadAgents()])
  },
  methods: {
    async loadTools() {
      try {
        const response = await getTools()
        this.tools = Array.isArray(response.data) ? response.data : []
      } catch (error) {
        this.handleError(error, '加载工具列表失败')
      }
    },
    async loadAgents() {
      this.loading = true
      this.error = ''
      try {
        const response = await getAgents()
        this.agents = Array.isArray(response.data) ? response.data : []
        if (this.selectedAgent) {
          const latest = this.agents.find(agent => agent.id === this.selectedAgent.id)
          if (latest) this.selectAgent(latest)
        }
      } catch (error) {
        this.handleError(error, '加载 Agent 失败')
      } finally {
        this.loading = false
      }
    },
    startCreate() {
      this.isCreating = true
      this.selectedAgent = null
      this.editorVisible = true
      this.form = defaultForm()
      this.newTag = ''
      this.clearNotice()
    },
    selectAgent(agent) {
      this.isCreating = false
      this.selectedAgent = agent
      this.editorVisible = true
      this.form = {
        name: agent.name || '',
        adapter_name: agent.adapter_name || 'claude',
        avatar_color: agent.avatar_color || agent.color || '#4080ff',
        avatar_url: agent.avatar_url || '',
        system_prompt: agent.system_prompt || '',
        skill: agent.skill || '',
        capability_tags: [...(agent.capability_tags || [])],
        tool_ids: [...(agent.tool_ids || [])],
      }
      this.newTag = ''
      this.clearNotice()
    },
    closeEditor() {
      this.editorVisible = false
      this.selectedAgent = null
      this.isCreating = false
    },
    resetForm() {
      if (this.isCreating) {
        this.form = defaultForm()
      } else if (this.selectedAgent) {
        this.selectAgent(this.selectedAgent)
      }
      this.newTag = ''
    },
    async handleSave() {
      if (!this.form.name || this.saving) return
      this.saving = true
      this.clearNotice()
      try {
        const payload = {
          ...this.form,
          agent_type: 'custom',
          capability_tags: [...this.form.capability_tags],
          tool_ids: [...(this.form.tool_ids || [])],
          config: {},
          is_public: false,
        }
        const response = this.isCreating
          ? await createAgent(payload)
          : await updateAgent(this.selectedAgent.id, payload)
        if ([200, 201].includes(response.code)) {
          this.message = this.isCreating ? 'Agent 已创建' : 'Agent 信息已保存'
          this.isCreating = false
          await this.loadAgents()
          if (response.data) this.selectAgent(response.data)
        } else {
          this.error = response.message || '保存 Agent 失败'
        }
      } catch (error) {
        this.handleError(error, '保存 Agent 失败')
      } finally {
        this.saving = false
      }
    },
    async handleDelete(agent) {
      if (!agent || !agent.id) return
      if (!window.confirm(`删除 Agent「${agent.name}」？`)) return
      this.clearNotice()
      try {
        await deleteAgent(agent.id)
        if (this.selectedAgent && this.selectedAgent.id === agent.id) this.closeEditor()
        await this.loadAgents()
        this.message = 'Agent 已删除'
      } catch (error) {
        this.handleError(error, '删除 Agent 失败')
      }
    },
    triggerUpload() {
      if (!this.uploading && this.$refs.fileInput) this.$refs.fileInput.click()
    },
    async handleAvatarChange(event) {
      const file = event.target.files && event.target.files[0]
      if (!file) return
      if (file.size > 2 * 1024 * 1024) {
        this.error = '图片大小不能超过 2MB'
        event.target.value = ''
        return
      }
      this.uploading = true
      this.clearNotice()
      try {
        const response = await uploadFile(file)
        if (response.code === 200 && response.data && response.data.url) {
          this.form.avatar_url = response.data.url
          this.message = '头像已上传，保存后生效'
        } else {
          this.error = response.message || '上传头像失败'
        }
      } catch (error) {
        this.handleError(error, '上传头像失败')
      } finally {
        this.uploading = false
        event.target.value = ''
      }
    },
    addTag() {
      const value = this.newTag.trim()
      if (!value) return
      if (!this.form.capability_tags.includes(value)) this.form.capability_tags.push(value)
      this.newTag = ''
    },
    removeTag(index) {
      this.form.capability_tags.splice(index, 1)
    },
    agentAvatar(agent) {
      return agent && agent.avatar_url ? backendUrl(this.serverUrl, agent.avatar_url) : ''
    },
    agentAvatarStyle(agent) {
      return this.agentAvatar(agent) ? {} : { background: (agent && (agent.avatar_color || agent.color)) || '#4080ff' }
    },
    fetchToolName(toolId) {
      const tool = this.tools.find(item => String(item.id) === String(toolId))
      return tool ? tool.name : toolId
    },
    toolsLabel(toolIds) {
      return (toolIds || []).map(id => this.fetchToolName(id)).join('、')
    },
    tagStyle(index) {
      const colors = [
        ['#e8f3ff', '#165dff'],
        ['#f0f9eb', '#389e0d'],
        ['#fff7e8', '#d46b08'],
        ['#f9f0ff', '#722ed1'],
        ['#e6fffb', '#08979c'],
        ['#fff1f0', '#cf1322'],
      ]
      const pair = colors[index % colors.length]
      return { background: pair[0], color: pair[1] }
    },
    firstLetter(value) {
      return String(value || '?').charAt(0).toUpperCase()
    },
    clearNotice() {
      this.error = ''
      this.message = ''
    },
    handleError(error, fallback) {
      this.error = (error && error.response && error.response.data && error.response.data.message) || (error && error.message) || fallback
      if (error && error.response && error.response.status === 401) this.logout()
    },
    logout() {
      clearAuth()
      this.$router.replace('/login')
    },
  },
}
</script>
