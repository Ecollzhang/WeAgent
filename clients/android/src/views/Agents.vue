<template>
  <main class="app-page with-bottom-nav agents-page">
    <header class="app-header">
      <div>
        <p class="eyebrow">Agent</p>
        <h1>我的 Agent</h1>
      </div>
      <button class="header-btn" type="button" @click="openCreate">新建</button>
    </header>

    <section class="screen-body agent-list-body">
      <div v-if="loading" class="mobile-state">正在加载 Agent...</div>
      <div v-else-if="agents.length === 0" class="empty-state">暂无 Agent，先新建一个。</div>

      <button
        v-for="agent in agents"
        v-else
        :key="agent.id"
        class="agent-card-mobile"
        type="button"
        @click="openEdit(agent)"
      >
        <span class="agent-avatar-mobile" :style="{ background: agent.avatar_color || '#2563eb' }">
          <img v-if="agentAvatarUrl(agent)" :src="agentAvatarUrl(agent)" alt="" />
          <span v-else>{{ firstLetter(agent.name) }}</span>
        </span>
        <span class="agent-card-main">
          <span class="agent-card-title">
            <strong>{{ agent.name || '未命名 Agent' }}</strong>
            <em>{{ agent.adapter_name || 'claude' }}</em>
          </span>
          <small class="agent-card-line">提示词：{{ agent.system_prompt || '暂无' }}</small>
          <small class="agent-card-line">技能：{{ agent.skill || '暂无' }}</small>
          <span v-if="agent.capability_tags && agent.capability_tags.length" class="agent-tags">
            <span v-for="tag in agent.capability_tags.slice(0, 3)" :key="tag">{{ tag }}</span>
            <span v-if="agent.capability_tags.length > 3">+{{ agent.capability_tags.length - 3 }}</span>
          </span>
        </span>
      </button>
    </section>

    <div v-if="editorVisible" class="mobile-modal agent-editor-modal" @click.self="closeEditor">
      <section class="mobile-sheet-panel agent-editor-panel">
        <header class="sheet-header">
          <h2>{{ isCreating ? '新建 Agent' : '编辑 Agent' }}</h2>
          <button type="button" @click="closeEditor">×</button>
        </header>

        <div class="agent-editor-preview">
          <span class="agent-editor-avatar" :style="{ background: form.avatar_color || '#2563eb' }">
            <img v-if="form.avatar_url" :src="resolveMediaUrl(form.avatar_url)" alt="" />
            <span v-else>{{ firstLetter(form.name) }}</span>
          </span>
          <div>
            <strong>{{ form.name || '未命名 Agent' }}</strong>
            <small>{{ form.adapter_name || 'claude' }}</small>
          </div>
        </div>

        <div class="agent-editor-section">
          <h3>基本信息</h3>
          <label class="mobile-field">
            <span>名称</span>
            <input v-model.trim="form.name" placeholder="例如：前端开发专家" />
          </label>

          <label class="mobile-field">
            <span>适配器</span>
            <select v-model="form.adapter_name">
              <option value="claude">claude</option>
              <option value="codex">codex</option>
              <option value="opencode">opencode</option>
            </select>
          </label>

          <div class="mobile-field">
            <span>头像颜色</span>
            <div class="agent-color-row">
              <button
                v-for="color in colors"
                :key="color"
                type="button"
                class="color-swatch"
                :class="{ active: form.avatar_color === color }"
                :style="{ background: color }"
                @click="form.avatar_color = color"
              ></button>
              <input v-model="form.avatar_color" type="color" aria-label="选择头像颜色" />
            </div>
          </div>
        </div>

        <div class="agent-editor-section">
          <h3>能力设定</h3>
          <label class="mobile-field">
            <span>系统提示词</span>
            <textarea v-model.trim="form.system_prompt" placeholder="描述 Agent 的角色、工作方式和边界"></textarea>
          </label>
          <label class="mobile-field">
            <span>技能说明</span>
            <textarea v-model.trim="form.skill" placeholder="可填写专长、约束或协作方式"></textarea>
          </label>
        </div>

        <div class="agent-editor-section">
          <h3>标签与工具</h3>
          <label class="mobile-field">
            <span>能力标签</span>
            <input v-model.trim="tagInput" placeholder="用逗号分隔，例如：前端, Vue, UI" />
          </label>

          <label class="mobile-field">
            <span>添加工具</span>
            <select v-model="selectedToolId" @change="addSelectedTool">
              <option value="">选择工具</option>
              <option v-for="tool in availableTools" :key="tool.id || tool.value" :value="tool.id || tool.value">
                {{ tool.name || tool.label || tool.id || tool.value }}
              </option>
            </select>
          </label>

          <div v-if="form.tool_ids.length" class="selected-tool-list">
            <button v-for="id in form.tool_ids" :key="id" type="button" @click="removeTool(id)">
              {{ toolName(id) }} ×
            </button>
          </div>
        </div>

        <p v-if="error" class="form-error">{{ error }}</p>

        <div class="sheet-actions agent-editor-actions">
          <button v-if="!isCreating" class="danger-btn" type="button" :disabled="saving" @click="handleDelete">删除</button>
          <button class="secondary-btn" type="button" :disabled="saving" @click="resetForm">重置</button>
          <button class="primary-btn" type="button" :disabled="saving || !form.name" @click="handleSave">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </section>
    </div>

    <BottomNav />
  </main>
</template>

<script>
import BottomNav from '../components/BottomNav.vue'
import { backendUrl, getCurrentServerUrl } from '../services/config'
import { createAgent, deleteAgent, getAgents, getTools, updateAgent } from '../services/api'

const defaultForm = () => ({
  name: '',
  adapter_name: 'claude',
  avatar_color: '#2563eb',
  avatar_url: '',
  system_prompt: '',
  skill: '',
  capability_tags: [],
  tool_ids: [],
})

function unwrap(response) {
  const payload = response && response.data ? response.data : response
  if (payload && payload.data) return payload.data
  return payload || {}
}

export default {
  name: 'AgentsView',
  components: { BottomNav },
  data() {
    return {
      agents: [],
      tools: [],
      loading: false,
      saving: false,
      editorVisible: false,
      isCreating: false,
      selectedAgent: null,
      form: defaultForm(),
      tagInput: '',
      selectedToolId: '',
      error: '',
      colors: ['#2563eb', '#16a34a', '#f97316', '#7c3aed', '#0891b2', '#dc2626']
    }
  },
  computed: {
    availableTools() {
      return this.tools.filter(tool => {
        const id = tool.id || tool.value
        return id && !this.form.tool_ids.includes(id)
      })
    }
  },
  created() {
    this.loadAgents()
    this.loadTools()
  },
  methods: {
    async loadAgents() {
      this.loading = true
      try {
        const data = unwrap(await getAgents())
        this.agents = Array.isArray(data) ? data : (data.agents || data.items || [])
      } finally {
        this.loading = false
      }
    },
    async loadTools() {
      try {
        const data = unwrap(await getTools())
        this.tools = Array.isArray(data) ? data : (data.tools || data.items || [])
      } catch (error) {
        this.tools = []
      }
    },
    openCreate() {
      this.isCreating = true
      this.selectedAgent = null
      this.form = defaultForm()
      this.tagInput = ''
      this.selectedToolId = ''
      this.error = ''
      this.editorVisible = true
    },
    openEdit(agent) {
      this.isCreating = false
      this.selectedAgent = agent
      this.form = {
        name: agent.name || '',
        adapter_name: agent.adapter_name || 'claude',
        avatar_color: agent.avatar_color || '#2563eb',
        avatar_url: agent.avatar_url || '',
        system_prompt: agent.system_prompt || '',
        skill: agent.skill || '',
        capability_tags: [...(agent.capability_tags || [])],
        tool_ids: [...(agent.tool_ids || [])],
      }
      this.tagInput = this.form.capability_tags.join(',')
      this.selectedToolId = ''
      this.error = ''
      this.editorVisible = true
    },
    closeEditor() {
      this.editorVisible = false
    },
    resetForm() {
      if (this.isCreating || !this.selectedAgent) {
        this.form = defaultForm()
        this.tagInput = ''
      } else {
        this.openEdit(this.selectedAgent)
      }
    },
    parseTags() {
      return this.tagInput
        .split(',')
        .map(item => item.trim())
        .filter(Boolean)
    },
    addSelectedTool() {
      if (!this.selectedToolId) return
      if (!this.form.tool_ids.includes(this.selectedToolId)) {
        this.form.tool_ids.push(this.selectedToolId)
      }
      this.selectedToolId = ''
    },
    removeTool(id) {
      this.form.tool_ids = this.form.tool_ids.filter(item => item !== id)
    },
    toolName(id) {
      const tool = this.tools.find(item => String(item.id || item.value) === String(id))
      return (tool && (tool.name || tool.label)) || id
    },
    async handleSave() {
      if (!this.form.name) return
      this.saving = true
      this.error = ''
      try {
        const payload = {
          ...this.form,
          capability_tags: this.parseTags(),
          agent_type: 'custom',
          config: {},
          is_public: false,
        }
        if (this.isCreating) {
          await createAgent(payload)
        } else {
          await updateAgent(this.selectedAgent.id, payload)
        }
        await this.loadAgents()
        this.closeEditor()
      } catch (error) {
        this.error = '保存失败，请检查后端连接'
      } finally {
        this.saving = false
      }
    },
    async handleDelete() {
      if (!this.selectedAgent || !window.confirm(`确认删除 ${this.selectedAgent.name || '该 Agent'}？`)) return
      this.saving = true
      try {
        await deleteAgent(this.selectedAgent.id)
        await this.loadAgents()
        this.closeEditor()
      } finally {
        this.saving = false
      }
    },
    agentAvatarUrl(agent) {
      return this.resolveMediaUrl(agent && agent.avatar_url)
    },
    resolveMediaUrl(url) {
      if (!url) return ''
      if (/^https?:\/\//i.test(url) || /^data:/i.test(url)) return url
      return backendUrl(getCurrentServerUrl(), url)
    },
    firstLetter(value) {
      return String(value || '?').charAt(0).toUpperCase()
    }
  }
}
</script>
