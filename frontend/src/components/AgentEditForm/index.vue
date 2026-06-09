<template>
  <div class="agent-edit-form">
    <div class="form-header">
      <el-button type="text" icon="el-icon-arrow-left" @click="$emit('back')">
        返回
      </el-button>
      <h2>{{ readonly ? '查看 Agent' : (isNew ? '创建 Agent' : '编辑 Agent') }}</h2>
      <el-tag v-if="readonly" size="mini" type="warning">只读</el-tag>
      <el-button v-else type="primary" @click="handleSave" :loading="saving">
        保存
      </el-button>
    </div>

    <div class="form-body" v-loading="loading || capabilityLoading">
      <div class="form-section avatar-section">
        <div class="avatar-area">
          <div
            class="agent-avatar"
            :style="{ background: form.color || '#4080ff' }"
            :class="{ readonly: readonly }"
            @click="triggerAvatarUpload"
          >
            <img v-if="form.avatar" :src="form.avatar" class="avatar-img" />
            <span v-else class="avatar-letter">{{ form.name.charAt(0) || '?' }}</span>
            <div class="avatar-overlay">
              <i class="el-icon-camera"></i>
            </div>
          </div>
          <div class="avatar-actions">
            <el-color-picker v-model="form.color" size="mini" :disabled="readonly"></el-color-picker>
            <el-button size="mini" type="text" @click="triggerAvatarUpload" :disabled="readonly">上传头像</el-button>
            <el-button size="mini" type="text" v-if="form.avatar" @click="form.avatar = ''" :disabled="readonly">清除</el-button>
          </div>
          <input ref="fileInput" type="file" accept="image/*" style="display:none" @change="handleAvatarFile" />
        </div>
      </div>

      <div class="form-section">
        <el-form label-position="top">
          <el-form-item label="Agent 名称">
            <el-input v-model="form.name" placeholder="输入 Agent 名称" :disabled="readonly"></el-input>
          </el-form-item>

          <el-form-item label="底层模型">
            <el-select v-model="form.adapter_name" style="width:100%" :disabled="readonly">
              <el-option label="Claude Code" value="claude"></el-option>
              <el-option label="Codex" value="codex"></el-option>
              <el-option label="OpenCode" value="opencode"></el-option>
              <el-option label="Mock" value="mock"></el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="系统提示词">
            <el-input
              type="textarea"
              :rows="5"
              v-model="form.system_prompt"
              placeholder="描述 Agent 的角色、边界和行为"
              :disabled="readonly"
            ></el-input>
          </el-form-item>

          <el-form-item label="标签">
            <div class="tags-wrapper">
              <el-tag
                v-for="(tag, i) in form.capability_tags"
                :key="i"
                :closable="!readonly"
                :disable-transitions="true"
                :color="tagColor(tag)"
                @close="handleDeleteTag(i)"
              >
                <span v-if="editingTagIdx !== i" @click="startEditTag(i)" class="tag-text">{{ tag }}</span>
                <el-input
                  v-else
                  v-model="editTagValue"
                  size="mini"
                  ref="tagInput"
                  @blur="finishEditTag(i)"
                  @keydown.enter.native="finishEditTag(i)"
                  style="width:80px"
                ></el-input>
              </el-tag>
              <el-input
                v-if="showTagInput"
                v-model="newTag"
                size="mini"
                placeholder="新标签"
                ref="newTagInput"
                @blur="confirmAddTag"
                @keydown.enter.native="confirmAddTag"
                style="width:100px"
              ></el-input>
              <el-button v-else-if="!readonly" size="mini" type="text" icon="el-icon-plus" @click="showTagInput = true">
                添加标签
              </el-button>
            </div>
          </el-form-item>
        </el-form>
      </div>

      <div class="form-section capability-section">
        <div class="section-heading">
          <div>
            <h3>默认工具能力</h3>
            <span>{{ form.capability_bindings.length }} 个已绑定，默认固定当前版本</span>
          </div>
        </div>

        <div class="capability-picker" v-if="!readonly">
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

          <el-tabs v-model="capabilityPickerType" class="picker-tabs">
            <el-tab-pane
              v-for="group in groupedCapabilities"
              :key="group.type"
              :name="group.type"
            >
              <span slot="label">{{ group.label }} <b>{{ group.items.length }}</b></span>
            </el-tab-pane>
          </el-tabs>

          <div class="picker-list">
            <button
              v-for="capability in pickerCapabilities"
              :key="capability.id"
              type="button"
              class="picker-card"
              :disabled="isCapabilityBound(capability.id)"
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
                <el-tag size="mini" :type="typeTag(binding.capability.type)">
                  {{ typeLabel(binding.capability.type) }}
                </el-tag>
                <strong>{{ binding.capability.name }}</strong>
                <span>v{{ binding.capability_version.version || '1.0.0' }}</span>
                <el-tag v-if="upgradeMap[binding.binding_id]" size="mini" type="warning">可升级</el-tag>
              </div>
              <p>{{ binding.capability.description || binding.capability.source_ref || '暂无描述' }}</p>
              <div class="permissions">
                <el-checkbox-group v-model="binding.granted_permissions" :disabled="readonly">
                  <el-checkbox
                    v-for="permission in declaredPermissions(binding)"
                    :key="permission"
                    :label="permission"
                    :disabled="readonly || requiredPermissions(binding).includes(permission)"
                  >
                    {{ permission }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
            </div>
            <div class="binding-side">
              <el-switch v-model="binding.enabled" :disabled="readonly"></el-switch>
              <span>{{ binding.version_policy || 'pinned' }}</span>
              <el-button
                v-if="!readonly"
                size="mini"
                type="text"
                icon="el-icon-delete"
                @click="removeBinding(index)"
              ></el-button>
            </div>
          </div>

          <div v-if="form.capability_bindings.length === 0" class="empty-bindings">
            <i class="el-icon-collection-tag"></i>
            <span>暂无绑定能力</span>
          </div>
        </div>
      </div>

      <div class="form-section legacy-section">
        <el-collapse>
          <el-collapse-item title="Legacy skill / tools" name="legacy">
            <el-form label-position="top">
              <el-form-item label="旧 Skill 文本">
                <el-input type="textarea" :rows="4" v-model="form.skill" :disabled="true"></el-input>
              </el-form-item>
              <el-form-item label="旧 Tool IDs">
                <el-select v-model="form.tool_ids" multiple filterable style="width:100%" :disabled="true">
                  <el-option v-for="tool in allTools" :key="tool.id" :label="tool.name" :value="tool.id"></el-option>
                </el-select>
              </el-form-item>
            </el-form>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </div>
</template>

<script>
import { getTools } from '../../api/tools'
import { uploadFile } from '../../api/upload'
import {
  deleteAgentCapability,
  getAgentCapabilities,
  getAgentCapabilityUpgrades,
  getCapabilities,
} from '../../api/capabilities'
import { getToolsetCategories } from '../../api/toolsets'

const TYPE_LABELS = {
  skill: 'Skill',
  tool: 'Tool',
  mcp: 'MCP',
  plugin: 'Plugin',
}

const TYPE_TAGS = {
  skill: 'success',
  tool: 'primary',
  mcp: 'warning',
  plugin: 'info',
}

export default {
  name: 'AgentEditForm',
  props: {
    agent: Object,
    loading: Boolean,
    readonly: { type: Boolean, default: false },
  },
  data() {
    return {
      saving: false,
      isNew: false,
      showTagInput: false,
      newTag: '',
      editingTagIdx: -1,
      editTagValue: '',
      allTools: [],
      allCapabilities: [],
      toolsetCategories: [],
      capabilityLoading: false,
      capabilityCategoryId: 'all',
      capabilityPickerType: 'skill',
      upgradeMap: {},
      form: this.emptyForm(),
    }
  },
  computed: {
    groupedCapabilities() {
      return ['skill', 'tool', 'mcp', 'plugin'].map(type => ({
        type,
        label: TYPE_LABELS[type],
        items: this.filteredCapabilitiesByCategory.filter(item => item.type === type),
      }))
    },
    bindableCapabilities() {
      return this.allCapabilities.filter(this.isCapabilitySelectable)
    },
    filteredCapabilitiesByCategory() {
      if (this.capabilityCategoryId === 'all') return this.bindableCapabilities
      return this.bindableCapabilities.filter(item => item.category_id === this.capabilityCategoryId)
    },
    pickerCapabilities() {
      const group = this.groupedCapabilities.find(item => item.type === this.capabilityPickerType)
      return group ? group.items : []
    },
  },
  created() {
    this.fetchTools()
    this.fetchToolsetCategories()
    this.fetchCapabilities()
  },
  watch: {
    agent: {
      immediate: true,
      handler(val) {
        this.applyAgent(val)
      },
    },
  },
  methods: {
    emptyForm() {
      return {
        name: '',
        adapter_name: 'claude',
        system_prompt: '',
        skill: '',
        capability_tags: [],
        tool_ids: [],
        capability_bindings: [],
        avatar: '',
        color: '#4080ff',
      }
    },
    applyAgent(agent) {
      const next = this.emptyForm()
      if (agent) {
        this.isNew = agent.is_new === true
        next.name = agent.name || ''
        next.adapter_name = agent.adapter_name || 'claude'
        next.system_prompt = agent.system_prompt || ''
        next.skill = agent.skill || ''
        next.capability_tags = [...(agent.capability_tags || [])]
        next.tool_ids = [...(agent.tool_ids || [])]
        next.capability_bindings = (agent.capability_bindings || []).map(this.normalizeBinding)
        next.avatar = agent.avatar || agent.avatar_url || ''
        next.color = agent.avatar_color || agent.color || '#4080ff'
      } else {
        this.isNew = true
      }
      this.form = next
      this.upgradeMap = {}
      if (agent && agent.id && !this.isNew && !this.readonly) {
        this.fetchAgentBindings(agent.id)
        this.fetchAgentUpgrades(agent.id)
      }
    },
    async fetchTools() {
      try {
        const res = await getTools()
        if (res.code === 200) this.allTools = res.data || []
      } catch (e) {
        console.error('Failed to load tools', e)
      }
    },
    async fetchToolsetCategories() {
      try {
        const res = await getToolsetCategories()
        if (res.code === 200) this.toolsetCategories = res.data || []
      } catch (e) {
        console.error('Failed to load toolset categories', e)
      }
    },
    async fetchCapabilities() {
      this.capabilityLoading = true
      try {
        const res = await getCapabilities()
        if (res.code === 200) this.allCapabilities = res.data || []
      } catch (e) {
        console.error('Failed to load capabilities', e)
      } finally {
        this.capabilityLoading = false
      }
    },
    async fetchAgentBindings(agentId) {
      try {
        const res = await getAgentCapabilities(agentId)
        if (res.code === 200) {
          this.form.capability_bindings = (res.data || []).map(this.normalizeBinding)
        }
      } catch (e) {
        console.error('Failed to load agent capability bindings', e)
      }
    },
    async fetchAgentUpgrades(agentId) {
      try {
        const res = await getAgentCapabilityUpgrades(agentId)
        if (res.code === 200) {
          this.upgradeMap = (res.data || []).reduce((acc, item) => {
            acc[item.binding_id] = item
            return acc
          }, {})
        }
      } catch (e) {
        this.upgradeMap = {}
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
        binding_id: binding.id,
        capability_id: binding.capability_id || capability.id,
        capability_version_id: binding.capability_version_id || version.id,
        capability,
        capability_version: version,
        enabled: binding.enabled !== false,
        version_policy: binding.version_policy || 'pinned',
        granted_permissions: Array.from(new Set([...required, ...granted])),
      }
    },
    latestVersion(capability) {
      return capability && capability.latest_version ? capability.latest_version : {}
    },
    isCapabilityBound(capabilityId) {
      return this.form.capability_bindings.some(item => item.capability_id === capabilityId && item.enabled !== false)
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
    addCapability(capability) {
      if (!capability || !capability.latest_version) return
      if (!this.isCapabilitySelectable(capability)) {
        this.$message.warning(this.capabilityDisabledReason(capability) || '该能力暂不可绑定')
        return
      }
      if (this.isCapabilityBound(capability.id)) {
        this.$message.warning('该能力已绑定')
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
      if (binding && binding.binding_id) {
        try {
          await this.$confirm(`解绑“${binding.capability.name}”？`, '解绑能力', {
            type: 'warning',
            confirmButtonText: '解绑',
            cancelButtonText: '取消',
          })
        } catch (e) {
          return
        }
        try {
          const res = await deleteAgentCapability(this.agent.id, binding.binding_id)
          if (res.code === 200) {
            this.form.capability_bindings.splice(index, 1)
            this.$message.success('能力已解绑')
          }
        } catch (e) {
          this.$message.error('解绑能力失败')
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
    ensureRequiredPermissions() {
      this.form.capability_bindings.forEach(binding => {
        const required = this.requiredPermissions(binding)
        binding.granted_permissions = Array.from(new Set([...required, ...(binding.granted_permissions || [])]))
      })
    },
    typeLabel(type) {
      return TYPE_LABELS[type] || type
    },
    typeTag(type) {
      return TYPE_TAGS[type] || 'info'
    },
    triggerAvatarUpload() {
      if (this.readonly) return
      this.$refs.fileInput.click()
    },
    async handleAvatarFile(e) {
      const file = e.target.files[0]
      if (!file) return
      if (file.size > 2 * 1024 * 1024) {
        this.$message.warning('图片不能超过 2MB')
        return
      }
      try {
        const res = await uploadFile(file)
        if (res.code === 200) {
          this.form.avatar = res.data.url
        } else {
          this.$message.error(res.message || '上传失败')
        }
      } catch (err) {
        this.$message.error('上传失败')
      }
      e.target.value = ''
    },
    handleDeleteTag(i) {
      if (this.readonly) return
      this.form.capability_tags.splice(i, 1)
    },
    tagColor(tag) {
      const palette = ['#2d7ce6', '#47b03a', '#cc7d20', '#d9534f', '#8e5cd6', '#2baaa0']
      let h = 0
      for (let i = 0; i < tag.length; i++) h = tag.charCodeAt(i) + ((h << 5) - h)
      return palette[Math.abs(h) % palette.length]
    },
    startEditTag(i) {
      if (this.readonly) return
      this.editingTagIdx = i
      this.editTagValue = this.form.capability_tags[i]
      this.$nextTick(() => {
        if (this.$refs.tagInput && this.$refs.tagInput[0]) this.$refs.tagInput[0].focus()
      })
    },
    finishEditTag(i) {
      if (this.editTagValue.trim()) {
        this.form.capability_tags.splice(i, 1, this.editTagValue.trim())
      }
      this.editingTagIdx = -1
      this.editTagValue = ''
    },
    confirmAddTag() {
      if (this.newTag.trim()) this.form.capability_tags.push(this.newTag.trim())
      this.newTag = ''
      this.showTagInput = false
    },
    handleSave() {
      if (!this.form.name.trim()) {
        this.$message.warning('请输入 Agent 名称')
        return
      }
      this.ensureRequiredPermissions()
      this.saving = true
      try {
        this.$emit('save', {
          ...this.form,
          capability_bindings: this.form.capability_bindings.map(binding => ({
            id: binding.binding_id,
            capability_version_id: binding.capability_version_id,
            granted_permissions: binding.granted_permissions || [],
            version_policy: binding.version_policy || 'pinned',
            enabled: binding.enabled !== false,
          })),
        })
      } finally {
        this.saving = false
      }
    },
  },
}
</script>

<style scoped>
.agent-edit-form {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.form-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid #edf0f5;
  flex-shrink: 0;
}

.form-header h2 {
  flex: 1;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.form-header .el-button--primary {
  background: #4080ff;
  border: none;
  border-radius: 8px;
}

.form-body {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
}

.form-section {
  max-width: 920px;
  margin-bottom: 24px;
}

.avatar-area {
  display: flex;
  align-items: center;
  gap: 16px;
}

.agent-avatar {
  width: 72px;
  height: 72px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  flex-shrink: 0;
  transition: transform 0.2s;
}

.agent-avatar:hover {
  transform: scale(1.04);
}

.agent-avatar.readonly {
  cursor: default;
}

.agent-avatar.readonly:hover {
  transform: none;
}

.agent-avatar .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-letter {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.38);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  color: #fff;
  font-size: 24px;
}

.agent-avatar:hover .avatar-overlay {
  opacity: 1;
}

.agent-avatar.readonly:hover .avatar-overlay {
  opacity: 0;
}

.avatar-actions,
.tags-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tag-text {
  cursor: text;
  display: inline-block;
  min-width: 20px;
}

.tags-wrapper .el-tag {
  cursor: default;
  color: #fff !important;
}

.capability-section {
  border: 1px solid #e5eaf2;
  border-radius: 8px;
  padding: 16px;
  background: #fbfdff;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-heading h3 {
  margin: 0 0 4px;
  font-size: 16px;
  color: #1f2937;
}

.section-heading span {
  color: #64748b;
  font-size: 12px;
}

.capability-picker {
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
  margin-bottom: 14px;
}

.picker-categories {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.picker-category {
  min-height: 32px;
  border: 1px solid #e8edf3;
  background: #fff;
  border-radius: 6px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #526070;
  cursor: pointer;
  white-space: nowrap;
}

.picker-category.active,
.picker-category:hover {
  border-color: #4080ff;
  color: #1f2937;
  background: #f5f9ff;
}

.picker-tabs {
  margin-bottom: 8px;
}

.picker-tabs b {
  min-width: 22px;
  display: inline-block;
  text-align: center;
  font-size: 12px;
  color: #64748b;
  background: #eef2f7;
  border-radius: 999px;
  margin-left: 4px;
}

.picker-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
  max-height: 220px;
  overflow-y: auto;
}

.picker-card {
  min-height: 76px;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: start;
  text-align: left;
  cursor: pointer;
}

.picker-card:hover:not(:disabled) {
  border-color: #4080ff;
  background: #f7fbff;
}

.picker-card:disabled {
  cursor: not-allowed;
  opacity: 0.54;
}

.picker-card strong,
.picker-card small {
  display: block;
}

.picker-card strong {
  color: #1f2937;
  margin-bottom: 4px;
}

.picker-card small,
.picker-card em {
  color: #64748b;
  font-size: 12px;
  font-style: normal;
}

.picker-empty {
  grid-column: 1 / -1;
  color: #8a94a3;
  text-align: center;
  padding: 28px 0;
}

.binding-list {
  display: grid;
  gap: 10px;
}

.binding-row {
  display: grid;
  grid-template-columns: 1fr 92px;
  gap: 12px;
  padding: 12px;
  background: #fff;
  border: 1px solid #e8edf3;
  border-radius: 8px;
}

.binding-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.binding-title strong {
  color: #1f2937;
}

.binding-title span {
  color: #64748b;
  font-size: 12px;
}

.binding-main p {
  margin: 0 0 8px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.permissions .el-checkbox {
  margin-right: 14px;
}

.binding-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
}

.empty-bindings {
  height: 92px;
  border: 1px dashed #cfd8e3;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #8a94a3;
}

.legacy-section {
  max-width: 920px;
}
</style>
