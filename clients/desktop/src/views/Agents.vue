<template>
  <main class="dashboard-shell">
    <aside class="app-sidebar">
      <div class="sidebar-logo">W</div>
      <nav class="sidebar-nav">
        <button class="sidebar-btn" title="会话" @click="$router.push('/conversations')"><i class="el-icon-chat-dot-round"></i></button>
        <button class="sidebar-btn active" title="智能体"><i class="el-icon-user"></i></button>
        <button class="sidebar-btn" title="工具" @click="$router.push('/tools')"><i class="el-icon-s-tools"></i></button>
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
                <span>默认能力</span>
                <div class="binding-summary-box">
                  <strong>{{ form.capability_bindings.length }}</strong>
                  <small>个已绑定能力，默认固定当前版本</small>
                </div>
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

            <section class="capability-editor">
              <div class="capability-editor-head">
                <div>
                  <h3>工具集能力</h3>
                  <span>按分类选择 Skill / MCP / Plugin / Tool，运行时会注入到该 Agent 的 .weagent 视图。</span>
                </div>
                <button type="button" class="workspace-secondary" @click="$router.push('/tools')">
                  打开工具集
                </button>
              </div>

              <div class="capability-picker" v-loading="capabilityLoading">
                <div class="picker-categories">
                  <button
                    type="button"
                    class="picker-category"
                    :class="{ active: capabilityCategoryId === 'all' }"
                    @click="capabilityCategoryId = 'all'"
                  >
                    全部
                  </button>
                  <button
                    v-for="category in toolsetCategories"
                    :key="category.id"
                    type="button"
                    class="picker-category"
                    :class="{ active: capabilityCategoryId === category.id }"
                    @click="capabilityCategoryId = category.id"
                  >
                    <i :class="category.icon || 'el-icon-folder'" :style="{ color: category.color || '#4080ff' }"></i>
                    {{ category.name }}
                  </button>
                </div>

                <div class="picker-types">
                  <button
                    v-for="group in groupedCapabilities"
                    :key="group.type"
                    type="button"
                    class="picker-type"
                    :class="{ active: capabilityPickerType === group.type }"
                    @click="capabilityPickerType = group.type"
                  >
                    {{ group.label }}
                    <b>{{ group.items.length }}</b>
                  </button>
                </div>

                <div class="picker-list">
                  <button
                    v-for="capability in pickerCapabilities"
                    :key="capability.id"
                    type="button"
                    class="picker-card"
                    :disabled="isCapabilityBound(capability.id) || !isCapabilitySelectable(capability)"
                    :title="capabilityDisabledReason(capability)"
                    @click="addCapability(capability)"
                  >
                    <span>
                      <strong>{{ capability.name }}</strong>
                      <small>{{ capability.description || capability.source_ref || '暂无描述' }}</small>
                    </span>
                    <em>v{{ latestVersion(capability).version || '1.0.0' }}</em>
                  </button>
                  <div v-if="pickerCapabilities.length === 0" class="picker-empty">
                    当前分类暂无 {{ typeLabel(capabilityPickerType) }}
                  </div>
                </div>
              </div>

              <div class="binding-list">
                <div
                  v-for="(binding, index) in form.capability_bindings"
                  :key="binding.local_key"
                  class="binding-row"
                >
                  <div class="binding-main">
                    <div class="binding-title">
                      <span class="binding-type">{{ typeLabel(binding.capability.type) }}</span>
                      <strong>{{ binding.capability.name }}</strong>
                      <small>v{{ binding.capability_version.version || '1.0.0' }}</small>
                    </div>
                    <p>{{ binding.capability.description || binding.capability.source_ref || '暂无描述' }}</p>
                    <div class="permission-line">
                      <label
                        v-for="permission in declaredPermissions(binding)"
                        :key="permission"
                      >
                        <input
                          v-model="binding.granted_permissions"
                          type="checkbox"
                          :value="permission"
                          :disabled="requiredPermissions(binding).includes(permission)"
                        />
                        {{ permission }}
                      </label>
                      <em v-if="declaredPermissions(binding).length === 0">无需额外权限</em>
                    </div>
                  </div>
                  <div class="binding-side">
                    <label>
                      <input v-model="binding.enabled" type="checkbox" />
                      启用
                    </label>
                    <span>{{ binding.version_policy || 'pinned' }}</span>
                    <button type="button" class="text-danger" @click="removeBinding(index)">解绑</button>
                  </div>
                </div>
                <div v-if="form.capability_bindings.length === 0" class="empty-bindings">
                  暂无绑定能力
                </div>
              </div>
            </section>

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
import {
  deleteAgentCapability,
  getAgentCapabilities,
  getCapabilities,
} from '../api/capabilities'
import { getToolsetCategories } from '../api/toolsets'
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
  capability_bindings: [],
})

const TYPE_LABELS = {
  skill: 'Skill',
  tool: 'Tool',
  mcp: 'MCP',
  plugin: 'Plugin',
}

const CAPABILITY_TYPES = [
  { type: 'skill', label: 'Skill' },
  { type: 'mcp', label: 'MCP' },
  { type: 'plugin', label: 'Plugin' },
  { type: 'tool', label: 'Tool' },
]

export default {
  name: 'Agents',
  data() {
    return {
      agents: [],
      tools: [],
      toolsetCategories: [],
      allCapabilities: [],
      selectedAgent: null,
      serverUrl: '',
      loading: false,
      saving: false,
      uploading: false,
      capabilityLoading: false,
      capabilityCategoryId: 'all',
      capabilityPickerType: 'skill',
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
    filteredCapabilitiesForCategory() {
      if (this.capabilityCategoryId === 'all') return this.bindableCapabilities
      return this.bindableCapabilities.filter(item => item.category_id === this.capabilityCategoryId)
    },
    groupedCapabilities() {
      return CAPABILITY_TYPES.map(type => ({
        ...type,
        items: this.filteredCapabilitiesForCategory.filter(item => item.type === type.type),
      }))
    },
    pickerCapabilities() {
      const group = this.groupedCapabilities.find(item => item.type === this.capabilityPickerType)
      return group ? group.items : []
    },
    bindableCapabilities() {
      return this.allCapabilities.filter(this.isVisibleCapability)
    },
  },
  async created() {
    this.serverUrl = await getServerUrl()
    await Promise.all([this.loadTools(), this.loadToolsetCategories(), this.loadCapabilities(), this.loadAgents()])
  },
  methods: {
    async loadToolsetCategories() {
      try {
        const response = await getToolsetCategories()
        this.toolsetCategories = Array.isArray(response.data) ? response.data : []
      } catch (error) {
        this.handleError(error, '加载工具集分类失败')
      }
    },
    async loadCapabilities() {
      this.capabilityLoading = true
      try {
        const response = await getCapabilities()
        this.allCapabilities = Array.isArray(response.data) ? response.data : []
      } catch (error) {
        this.handleError(error, '加载能力库失败')
      } finally {
        this.capabilityLoading = false
      }
    },
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
        capability_bindings: (agent.capability_bindings || []).map(this.normalizeBinding),
      }
      this.newTag = ''
      this.clearNotice()
      if (agent.id) this.loadAgentCapabilities(agent.id)
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
          capability_bindings: this.form.capability_bindings.map(this.bindingPayload),
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
    async loadAgentCapabilities(agentId) {
      try {
        const response = await getAgentCapabilities(agentId)
        if (response.code === 200) {
          this.form.capability_bindings = (response.data || []).map(this.normalizeBinding)
        }
      } catch (error) {
        this.handleError(error, '加载 Agent 能力绑定失败')
      }
    },
    normalizeBinding(binding) {
      const capability = binding.capability || {}
      const version = binding.capability_version || capability.latest_version || {}
      const permissions = version.permissions || { required: [], optional: [] }
      const required = permissions.required || []
      const granted = binding.granted_permissions || required
      return {
        local_key: binding.id || `${capability.id}-${version.id}`,
        binding_id: binding.id || '',
        capability_id: binding.capability_id || capability.id,
        capability_version_id: binding.capability_version_id || version.id,
        capability,
        capability_version: version,
        enabled: binding.enabled !== false,
        version_policy: binding.version_policy || 'pinned',
        granted_permissions: Array.from(new Set([...required, ...granted])),
      }
    },
    bindingPayload(binding) {
      this.ensureRequiredPermissions(binding)
      return {
        id: binding.binding_id || undefined,
        capability_version_id: binding.capability_version_id,
        granted_permissions: binding.granted_permissions || [],
        version_policy: binding.version_policy || 'pinned',
        enabled: binding.enabled !== false,
      }
    },
    latestVersion(capability) {
      return capability && capability.latest_version ? capability.latest_version : {}
    },
    isVisibleCapability(capability) {
      if (!capability) return false
      if (capability.visibility === 'hidden') return false
      if (capability.type !== 'tool') return true
      const manifest = this.latestVersion(capability).manifest || {}
      const ui = manifest.ui || {}
      return ui.status !== 'deferred' || ui.configurable === true || capability.configurable === true
    },
    isCapabilitySelectable(capability) {
      if (!capability) return false
      if (capability.visibility === 'hidden') return false
      if (capability.bindable === false) return false
      return true
    },
    capabilityDisabledReason(capability) {
      if (!capability) return ''
      if (capability.bindable === false && capability.configurable) return '需要先配置'
      if (capability.bindable === false) return '暂不可绑定'
      return ''
    },
    isCapabilityBound(capabilityId) {
      return this.form.capability_bindings.some(item => item.capability_id === capabilityId && item.enabled !== false)
    },
    addCapability(capability) {
      if (!capability || !capability.latest_version) return
      if (!this.isCapabilitySelectable(capability)) {
        this.handleError(null, this.capabilityDisabledReason(capability) || '该能力暂不可绑定')
        return
      }
      if (this.isCapabilityBound(capability.id)) {
        this.handleError(null, '该能力已绑定')
        return
      }
      this.form.capability_bindings.push(this.normalizeBinding({
        capability,
        capability_id: capability.id,
        capability_version: capability.latest_version,
        capability_version_id: capability.latest_version.id,
        enabled: true,
        version_policy: 'pinned',
        granted_permissions: (capability.latest_version.permissions || {}).required || [],
      }))
    },
    async removeBinding(index) {
      const binding = this.form.capability_bindings[index]
      if (!binding) return
      if (binding.binding_id && this.selectedAgent && this.selectedAgent.id) {
        if (!window.confirm(`解绑「${binding.capability.name}」？`)) return
        try {
          const response = await deleteAgentCapability(this.selectedAgent.id, binding.binding_id)
          if (response.code === 200) {
            this.form.capability_bindings.splice(index, 1)
            this.message = '能力已解绑'
          } else {
            this.error = response.message || '解绑能力失败'
          }
        } catch (error) {
          this.handleError(error, '解绑能力失败')
        }
        return
      }
      this.form.capability_bindings.splice(index, 1)
    },
    requiredPermissions(binding) {
      const permissions = binding.capability_version.permissions || {}
      return permissions.required || []
    },
    declaredPermissions(binding) {
      const permissions = binding.capability_version.permissions || {}
      return Array.from(new Set([...(permissions.required || []), ...(permissions.optional || [])]))
    },
    ensureRequiredPermissions(binding) {
      const required = this.requiredPermissions(binding)
      binding.granted_permissions = Array.from(new Set([...required, ...(binding.granted_permissions || [])]))
    },
    typeLabel(type) {
      return TYPE_LABELS[type] || type
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

<style scoped>
.binding-summary-box {
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  border: 1px solid #dce5f2;
  border-radius: 8px;
  background: #f8fbff;
}

.binding-summary-box strong {
  color: #2563eb;
  font-size: 18px;
}

.binding-summary-box small {
  color: #64748b;
}

.capability-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 14px;
  padding: 14px;
  border: 1px solid #e5edf7;
  border-radius: 8px;
  background: #fbfdff;
}

.capability-editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.capability-editor-head h3 {
  margin: 0;
  color: #172033;
  font-size: 15px;
}

.capability-editor-head span {
  display: block;
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
}

.capability-picker {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.picker-categories,
.picker-types {
  display: flex;
  gap: 8px;
  overflow-x: auto;
}

.picker-category,
.picker-type {
  flex: 0 0 auto;
  min-height: 32px;
  border: 1px solid #dce5f2;
  border-radius: 8px;
  padding: 0 10px;
  background: #ffffff;
  color: #475569;
}

.picker-category.active,
.picker-type.active {
  border-color: #3b82f6;
  color: #2563eb;
  background: #eff6ff;
}

.picker-type b {
  margin-left: 6px;
  color: #64748b;
}

.picker-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 8px;
  max-height: 210px;
  overflow-y: auto;
}

.picker-card {
  min-height: 68px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  background: #ffffff;
  color: #1f2937;
  text-align: left;
}

.picker-card:disabled {
  opacity: 0.55;
}

.picker-card span {
  min-width: 0;
}

.picker-card strong,
.picker-card small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.picker-card small {
  margin-top: 4px;
  color: #64748b;
}

.picker-card em {
  flex: 0 0 auto;
  color: #64748b;
  font-style: normal;
  font-size: 12px;
}

.picker-empty,
.empty-bindings {
  padding: 12px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  color: #64748b;
  background: #ffffff;
}

.binding-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.binding-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 120px;
  gap: 12px;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.binding-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.binding-title strong,
.binding-main p {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.binding-type {
  border-radius: 999px;
  padding: 2px 8px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
}

.binding-title small {
  color: #64748b;
}

.binding-main p {
  margin: 6px 0;
  color: #64748b;
  font-size: 12px;
}

.permission-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #475569;
  font-size: 12px;
}

.permission-line label,
.binding-side label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.binding-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
}
</style>
