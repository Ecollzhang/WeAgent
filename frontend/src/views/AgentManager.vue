<template>
  <div class="agent-manager">
    <AppSidebar />

    <!-- 分类侧栏 -->
    <div class="category-panel">
      <div class="cat-header">
        <h3>Agent分类</h3>
        <el-button size="mini" icon="el-icon-plus" circle @click="handleAddCategory"></el-button>
      </div>
      <div class="cat-list">
        <div
          v-for="cat in categories"
          :key="cat.id"
          class="cat-item"
          :class="{ active: activeCategory === cat.id }"
          @click="selectCategory(cat.id)"
          @dragover.prevent
          @drop="handleDrop($event, cat.id)"
        >
          <el-popover
            placement="right"
            width="320"
            trigger="click"
            :visible-arrow="false"
            @show="iconPickerTarget = cat"
            @hide="iconPickerTarget = null"
          >
            <div class="icon-grid">
              <div
                v-for="icon in elementIcons"
                :key="icon"
                class="icon-option"
                :class="{ selected: iconPickerTarget?.icon === icon }"
                @click="selectCategoryIcon(icon)"
              >
                <i :class="icon"></i>
              </div>
            </div>
            <i slot="reference" :class="cat.icon || 'el-icon-folder-opened'" class="cat-icon"></i>
          </el-popover>
          <span class="cat-name">{{ cat.name }}</span>
          <span class="cat-count">{{ cat.agent_count || 0 }}</span>
          <el-dropdown trigger="click" @command="(cmd) => handleCatCommand(cmd, cat)">
            <el-button size="mini" type="text" icon="el-icon-more" class="cat-more"></el-button>
            <el-dropdown-menu slot="dropdown">
              <el-dropdown-item command="rename"><i class="el-icon-edit"></i> 重命名</el-dropdown-item>
              <el-dropdown-item command="delete"><i class="el-icon-delete"></i> 删除</el-dropdown-item>
            </el-dropdown-menu>
          </el-dropdown>
        </div>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="agent-content">
      <!-- ======= Agent 编辑态 ======= -->
      <template v-if="mode === 'agents' && editingAgent !== null">
        <AgentEditForm
          :agent="editingAgent"
          :loading="false"
          @back="editingAgent = null"
          @save="handleSaveAgent"
        />
      </template>

      <!-- ======= Agent 分类概览 ======= -->
      <!-- 编辑态 -->
      <template v-if="editingAgent !== null">
        <AgentEditForm
          :agent="editingAgent"
          :loading="false"
          @back="editingAgent = null"
          @save="handleSaveAgent"
        />
      </template>

      <!-- 分类概览态 -->
      <template v-else-if="activeCategory">
        <div class="content-header">
          <div class="header-left">
            <i :class="activeCategoryObj?.icon || 'el-icon-folder-opened'"></i>
            <h2>{{ activeCategoryObj?.name || 'Agent' }}</h2>
          </div>
          <el-button type="primary" icon="el-icon-plus" @click="handleCreateAgentInCat">
            新建Agent
          </el-button>
        </div>

        <div class="agent-grid" v-loading="loading" ref="agentGrid">
          <div
            v-for="agent in currentAgents"
            :key="agent.id"
            class="agent-card"
            draggable="true"
            @dragstart="handleDragStart($event, agent)"
            @click="openEditAgent(agent)"
          >
            <!-- 顶部头像 + 名称行 -->
            <div class="card-top">
              <div class="card-avatar" :style="{ background: agent.avatar_color || '#4080ff' }">
                <img v-if="agent.avatar_url" :src="agent.avatar_url" class="avatar-img" />
                <span v-else class="avatar-letter">{{ agent.name?.charAt(0) || '?' }}</span>
              </div>
              <div class="card-heading">
                <h3>{{ agent.name }}</h3>
                <span class="card-model-badge">{{ adapterLabel(agent.adapter_name) }}</span>
              </div>
            </div>

            <!-- 标签行 -->
            <div class="card-tags" v-if="agent.capability_tags?.length">
              <el-tag
                v-for="tag in agent.capability_tags.slice(0, 4)"
                :key="tag"
                size="mini"
                class="tag-chip"
                :color="tagColor(tag)"
              >{{ tag }}</el-tag>
              <span v-if="agent.capability_tags.length > 4" class="tag-more">
                +{{ agent.capability_tags.length - 4 }}
              </span>
            </div>

            <!-- 提示词预览 -->
            <div class="card-prompt" v-if="agent.system_prompt">
              <span class="prompt-label">提示词:</span>
              <span class="prompt-text">{{ agent.system_prompt }}</span>
            </div>

            <!-- 工具集 -->
            <div class="card-tools" v-if="agent.tool_ids?.length">
              <span class="tools-label">工具集:</span>
              <span class="tools-list">{{ toolsLabel(agent.tool_ids) }}</span>
            </div>

            <!-- Skill -->
            <div class="card-skill" v-if="agent.skill">
              <span class="skill-label">技能:</span>
              <span class="skill-text">{{ agent.skill }}</span>
            </div>
          </div>

          <div v-if="currentAgents.length === 0 && !agentLoading" class="empty-agents">
            <i class="el-icon-document"></i>
            <p>该分类暂无Agent</p>
            <el-button size="small" type="primary" @click="handleCreateAgentInCat">创建第一个</el-button>
          </div>
        </div>
      </template>

      <!-- 无选中分类 -->
      <template v-else>
        <div class="empty-state">
          <i class="el-icon-folder-opened"></i>
          <h2>选择分类</h2>
          <p>请从左侧选择一个Agent分类</p>
        </div>
      </template>
    </div>

    <!-- 重命名对话框 -->
    <el-dialog title="重命名分类" :visible.sync="showRenameDialog" width="400px">
      <el-input v-model="renameValue" placeholder="分类名称" @keydown.enter.native="confirmRename"></el-input>
      <span slot="footer">
        <el-button @click="showRenameDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmRename">确定</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import AppSidebar from '../components/Sidebar/index.vue'
import AgentEditForm from '../components/AgentEditForm/index.vue'
import { getAgents, getCategories, createCategory, updateCategory, deleteCategory, createAgent, updateAgent, deleteAgent } from '../api/agent'
import { getTools } from '../api/tools'

export default {
  name: 'AgentManager',
  components: { AppSidebar, AgentEditForm },
  data() {
    return {
      activeCategory: null,
      editingAgent: null,
      loading: false,
      showRenameDialog: false,
      renameValue: '',
      renameTarget: null,
      dragAgent: null,
      categories: [],
      currentAgents: [],
      agentLoading: false,
      toolMap: {},
      iconPickerTarget: null,
      elementIcons: [
        'el-icon-folder-opened', 'el-icon-folder', 'el-icon-document', 'el-icon-document-copy',
        'el-icon-document-checked', 'el-icon-notebook-1', 'el-icon-notebook-2',
        'el-icon-reading', 'el-icon-data-analysis', 'el-icon-data-board',
        'el-icon-data-line', 'el-icon-data-trend', 'el-icon-monitor',
        'el-icon-mobile-phone', 'el-icon-laptop', 'el-icon-tablet',
        'el-icon-s-promotion', 'el-icon-s-marketing', 'el-icon-s-management',
        'el-icon-s-operation', 'el-icon-s-platform', 'el-icon-s-home',
        'el-icon-s-custom', 'el-icon-s-check', 'el-icon-s-order',
        'el-icon-s-finance', 'el-icon-s-cooperation', 'el-icon-s-flag',
        'el-icon-s-claim', 'el-icon-s-shop', 'el-icon-s-release',
        'el-icon-s-comment', 'el-icon-s-unfold', 'el-icon-s-fold',
        'el-icon-s-tools', 'el-icon-s-help', 'el-icon-user',
        'el-icon-users', 'el-icon-brush', 'el-icon-edit',
        'el-icon-edit-outline', 'el-icon-share', 'el-icon-setting',
        'el-icon-search', 'el-icon-zoom-in', 'el-icon-zoom-out',
        'el-icon-picture', 'el-icon-picture-outline', 'el-icon-camera',
        'el-icon-video-camera', 'el-icon-mic', 'el-icon-headset',
        'el-icon-message', 'el-icon-chat-dot-square', 'el-icon-chat-line-square',
        'el-icon-connection', 'el-icon-link', 'el-icon-coin',
        'el-icon-money', 'el-icon-wallet', 'el-icon-goods',
        'el-icon-sell', 'el-icon-present', 'el-icon-bangzhu',
        'el-icon-circle-plus', 'el-icon-circle-check', 'el-icon-circle-close',
        'el-icon-download', 'el-icon-upload', 'el-icon-sort',
        'el-icon-star-on', 'el-icon-star-off', 'el-icon-collection',
        'el-icon-collection-tag', 'el-icon-phone', 'el-icon-service',
        'el-icon-date', 'el-icon-timer', 'el-icon-alarm-clock',
        'el-icon-warning-outline', 'el-icon-info', 'el-icon-success',
        'el-icon-error', 'el-icon-warning', 'el-icon-more',
        'el-icon-more-outline', 'el-icon-plus', 'el-icon-minus',
        'el-icon-check', 'el-icon-close', 'el-icon-menu',
        'el-icon-grid', 'el-icon-rank', 'el-icon-s-grid',
        'el-icon-s-data', 'el-icon-sugar', 'el-icon-cold-drink',
        'el-icon-ice-cream', 'el-icon-hot-water', 'el-icon-apple',
        'el-icon-grape', 'el-icon-watermelon', 'el-icon-cherry',
        'el-icon-mushroom', 'el-icon-corn', 'el-icon-orange',
        'el-icon-pear', 'el-icon-goblet', 'el-icon-cup',
        'el-icon-dish', 'el-icon-knife-fork', 'el-icon-bowl',
        'el-icon-umbrella', 'el-icon-help', 'el-icon-location',
        'el-icon-location-outline', 'el-icon-compass', 'el-icon-map-location',
        'el-icon-watch-1', 'el-icon-wind-power', 'el-icon-light-rain',
        'el-icon-lightning', 'el-icon-heavy-rain', 'el-icon-sunrise',
        'el-icon-sunset', 'el-icon-sunny', 'el-icon-cloudy',
        'el-icon-partly-cloudy', 'el-icon-snow', 'el-icon-moon',
        'el-icon-moon-night',
      ],
    }
  },
  computed: {
    currentUser() { return this.$store.state.user.user },
    userId() { return this.$store.getters['user/userId'] },
    activeCategoryObj() {
      return this.categories.find(c => c.id === this.activeCategory)
    },
  },
  created() {
    this.loadCategories()
    this.fetchTools()
  },
  methods: {
    async loadAgentsByCategory(catId) {
      if (!catId) { this.currentAgents = []; return }
      this.agentLoading = true
      try {
        const res = await getAgents(catId)
        if (res.code === 200) {
          this.currentAgents = res.data
        }
      } catch (e) {
        this.$message.error('加载Agent失败')
        this.currentAgents = []
      } finally {
        this.agentLoading = false
      }
    },
    tagColor(tag) {
      const palette = [
        '#2d7ce6', '#47b03a', '#cc7d20', '#d9534f',
        '#8e5cd6', '#2baaa0', '#d9538c', '#e68a2e',
      ]
      let h = 0
      for (let i = 0; i < tag.length; i++) {
        h = tag.charCodeAt(i) + ((h << 5) - h)
      }
      return palette[Math.abs(h) % palette.length]
    },
    adapterLabel(name) {
      return { claude: 'Claude', codex: 'Codex', opencode: 'OpenCode' }[name] || name
    },
    async loadCategories() {
      try {
        const res = await getCategories()
        if (res.code === 200) {
          this.categories = res.data
          // If there are categories and none selected, select first
          if (res.data.length > 0 && !this.activeCategory) {
            this.activeCategory = res.data[0].id
            this.loadAgentsByCategory(res.data[0].id)
          }
        }
      } catch (e) {
        this.$message.error('加载分类失败')
      }
    },
    openEditAgent(agent) {
      this.editingAgent = { ...agent }
    },
    selectCategory(catId) {
      this.activeCategory = catId
      this.editingAgent = null
      this.loadAgentsByCategory(catId)
    },
    isPreset(agent) {
      return agent.id?.startsWith('_')
    },
    async selectCategoryIcon(icon) {
      if (!this.iconPickerTarget) return
      const cat = this.iconPickerTarget
      try {
        await updateCategory(cat.id, { icon })
        cat.icon = icon
        this.iconPickerTarget = null
      } catch (e) {
        this.$message.error('更新图标失败')
      }
    },
    async handleAddCategory() {
      try {
        const res = await createCategory({ name: '新分类' })
        if (res.code === 201) {
          this.categories.push(res.data)
          this.activeCategory = res.data.id
          this.editingAgent = null
        }
      } catch (e) {
        this.$message.error('创建分类失败')
      }
    },
    handleCatCommand(cmd, cat) {
      if (cmd === 'rename') {
        this.renameTarget = cat
        this.renameValue = cat.name
        this.showRenameDialog = true
      } else if (cmd === 'delete') {
        this.$confirm(`确认删除分类"${cat.name}"？`, '提示', {
          type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
        }).then(async () => {
          try {
            await deleteCategory(cat.id)
            this.categories = this.categories.filter(c => c.id !== cat.id)
            if (this.activeCategory === cat.id) this.activeCategory = null
            this.$message.success('分类已删除')
          } catch (e) {
            this.$message.error('删除失败')
          }
        }).catch(() => {})
      }
    },
    async confirmRename() {
      if (this.renameValue.trim() && this.renameTarget) {
        try {
          await updateCategory(this.renameTarget.id, { name: this.renameValue.trim() })
          this.renameTarget.name = this.renameValue.trim()
        } catch (e) {
          this.$message.error('重命名失败')
        }
      }
      this.showRenameDialog = false
      this.renameTarget = null
    },
    handleDragStart(event, agent) {
      this.dragAgent = agent
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('text/plain', agent.id)
    },
    async handleDrop(event, targetCatId) {
      if (!this.dragAgent) return
      try {
        await updateAgent(this.dragAgent.id, { class_id: targetCatId })
        this.$message.success('已移动到新分类')
        // Refresh both source and target category agent lists
        if (this.activeCategory === targetCatId) {
          this.loadAgentsByCategory(targetCatId)
        }
        this.loadCategories()
      } catch (e) {
        this.$message.error('移动失败')
      }
      this.dragAgent = null
    },
    fetchToolName(toolId) {
      const tool = this.toolMap[toolId]
      return tool ? tool.name : toolId
    },
    toolsLabel(toolIds) {
      if (!toolIds?.length) return ''
      const names = toolIds.map(id => this.fetchToolName(id))
      const text = names.join(', ')
      return text.length > 30 ? text.slice(0, 28) + '...' : text
    },
    async fetchTools() {
      try {
        const res = await getTools()
        if (res.code === 200) {
          const map = {}
          res.data.forEach(t => { map[t.id] = t })
          this.toolMap = map
        }
      } catch (e) {
        console.error('Failed to load tools', e)
      }
    },
    handleCreateAgentInCat() {
      const newAgent = {
        id: 'new_' + Date.now(),
        name: '新Agent',
        adapter_name: 'claude',
        system_prompt: '',
        skill: '',
        capability_tags: [],
        tool_ids: [],
        avatar: '',
        color: '#4080ff',
        is_new: true,
      }
      this.editingAgent = newAgent
    },
    async handleSaveAgent(formData) {
      const editing = this.editingAgent
      if (!editing) return

      const apiData = {
        name: formData.name,
        adapter_name: formData.adapter_name,
        system_prompt: formData.system_prompt,
        skill: formData.skill || '',
        capability_tags: formData.capability_tags,
        avatar_color: formData.color || '',
        avatar_url: formData.avatar || '',
        class_id: this.activeCategory || null,
        tool_ids: formData.tool_ids || [],
      }

      if (editing.is_new) {
        const response = await createAgent(apiData)
        if (response.code === 201) {
          this.$message.success('Agent创建成功')
          this.editingAgent = null
          // Refresh current category agents
          await this.loadAgentsByCategory(this.activeCategory)
          // Also refresh categories (agent_count may have changed)
          this.loadCategories()
        } else {
          this.$message.error(response.message || '创建失败')
        }
      } else {
        try {
          const response = await updateAgent(editing.id, apiData)
          if (response.code === 200) {
            this.$message.success('Agent已更新')
            this.editingAgent = null
            await this.loadAgentsByCategory(this.activeCategory)
          } else {
            this.$message.error(response.message || '更新失败')
          }
        } catch (e) {
          this.$store.commit('agent/UPDATE_AGENT', { ...editing, ...apiData })
          this.$message.success('Agent已更新')
          this.editingAgent = null
        }
      }
    },
  },
}
</script>

<style scoped>
.agent-manager {
  display: flex;
  gap: 12px;
  padding: 12px;
  height: 100vh;
  background: linear-gradient(135deg, #e8f0ff 0%, #f0f5ff 50%, #f5f7fa 100%);
  overflow: hidden;
}

/* ===== 分类面板 ===== */
.category-panel {
  width: 220px;
  flex-shrink: 0;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.cat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 12px;
}
.mode-tabs {
  display: flex;
  background: #f0f2f5;
  border-radius: 8px;
  padding: 3px;
}
.mode-tab {
  flex: 1;
  text-align: center;
  padding: 5px 0;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.mode-tab.active {
  background: #fff;
  color: #4080ff;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.cat-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}
.cat-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
}
.cat-list::-webkit-scrollbar { width: 4px; }
.cat-list::-webkit-scrollbar-thumb { background: #dcdde1; border-radius: 4px; }
.cat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
}
.cat-item:hover { background: #f5f6f7; }
.cat-item.active { background: #f0f5ff; color: #4080ff; }
.cat-item i { font-size: 16px; color: inherit; }
.cat-name { flex: 1; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cat-count {
  font-size: 11px; color: #86909c;
  background: #f0f0f0; padding: 0 8px; border-radius: 10px; line-height: 20px;
}
.cat-item.active .cat-count { background: rgba(64,128,255,0.12); color: #4080ff; }
.cat-more { opacity: 0; transition: opacity 0.15s; color: #c0c4cc; }
.cat-item:hover .cat-more { opacity: 1; }

/* ===== 内容区 ===== */
.agent-content {
  flex: 1;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}
.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.header-left i {
  font-size: 22px;
  color: #4080ff;
}
.content-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
}
.content-header .el-button--primary {
  background: #4080ff;
  border: none;
  border-radius: 8px;
}

/* ===== Agent 卡片网格 ===== */
.agent-grid {
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
  align-content: start;
}
.agent-grid::-webkit-scrollbar { width: 4px; }
.agent-grid::-webkit-scrollbar-thumb { background: #dcdde1; border-radius: 4px; }

.agent-card {
  background: #ffffff;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  padding: 18px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.agent-card:hover {
  border-color: #4080ff;
  box-shadow: 0 4px 20px rgba(64,128,255,0.12);
  transform: translateY(-2px);
}

/* 顶栏: 头像 + 名称行 */
.card-top {
  display: flex;
  align-items: center;
  gap: 12px;
}
.card-avatar {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.card-avatar .avatar-img {
  width: 100%; height: 100%; object-fit: cover; border-radius: 12px;
}
.avatar-letter {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
}
.card-heading {
  flex: 1;
  min-width: 0;
}
.card-heading h3 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card-model-badge {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f0f5ff;
  color: #4080ff;
  font-weight: 500;
}

/* 标签行 */
.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.tag-chip {
  border: none !important;
  font-size: 11px !important;
  height: 22px !important;
  line-height: 22px !important;
  padding: 0 8px !important;
  color: #fff !important;
}
.tag-more {
  font-size: 11px;
  color: #86909c;
  line-height: 22px;
  padding: 0 4px;
}

/* 提示词预览 */
.card-prompt {
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  max-height: 48px;
  background: #f8fafc;
  padding: 3px 10px;
  border-radius: 6px;
}
.prompt-label {
  font-weight: 500;
  color: #475569;
}

/* 工具集 */
.card-tools {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tools-label {
  font-weight: 500;
  color: #475569;
  margin-right: 4px;
}

/* 技能 */
.card-skill {
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  max-height: 48px;
  background: #f8fafc;
  padding: 3px 10px;
  border-radius: 6px;
  white-space: pre-line;
}
.skill-label {
  font-weight: 500;
  color: #475569;
  margin-right: 4px;
}

/* 空状态 */
.empty-agents {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #86909c;
}
.empty-agents i { font-size: 48px; color: #dcdde1; margin-bottom: 12px; }
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #86909c;
}
.empty-state i { font-size: 64px; color: #dcdde1; margin-bottom: 16px; }
.empty-state h2 { margin: 0 0 8px; color: #1e293b; }

/* 图标选择器 */
.icon-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 4px;
  padding: 6px;
}
.icon-option {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 18px;
  color: #475569;
  transition: all 0.15s;
}
.icon-option:hover {
  background: #f0f5ff;
  color: #4080ff;
  transform: scale(1.15);
}
.icon-option.selected {
  background: #4080ff;
  color: #fff;
}
.cat-icon {
  font-size: 16px;
  cursor: pointer;
  transition: transform 0.15s;
}
.cat-icon:hover {
  transform: scale(1.2);
}
</style>
